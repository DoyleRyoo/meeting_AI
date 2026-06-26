import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.storage_service import download_supabase_storage_object
from app.services.summary_service import SummaryServiceError


class StorageServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_reports_missing_supabase_settings(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SummaryServiceError) as context:
                await download_supabase_storage_object("meeting-audio", "audio.mp3")

        self.assertIn(
            "missing=SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY",
            str(context.exception),
        )

    async def test_reports_http_status_when_download_fails(self) -> None:
        response = httpx.Response(
            status_code=403,
            text='{"message":"permission denied"}',
            request=httpx.Request("GET", "https://example.supabase.co/file"),
        )
        error = httpx.HTTPStatusError(
            "forbidden",
            request=response.request,
            response=response,
        )
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.get = AsyncMock(side_effect=error)

        with (
            patch.dict(
                "os.environ",
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "secret",
                },
            ),
            patch("app.services.storage_service.httpx.AsyncClient", return_value=client),
        ):
            with self.assertRaises(SummaryServiceError) as context:
                await download_supabase_storage_object("meeting-audio", "audio.mp3")

        message = str(context.exception)
        self.assertIn("status=403", message)
        self.assertIn("permission denied", message)


if __name__ == "__main__":
    unittest.main()
