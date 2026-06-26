import unittest
from unittest.mock import AsyncMock, patch

from app.services.stt_job_service import _JOBS, create_stt_job, process_stt_job


class SttJobServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _JOBS.clear()

    async def test_processes_storage_audio_job(self) -> None:
        job = create_stt_job("meeting-audio", "meetings/1/audio.mp3")

        with (
            patch(
                "app.services.stt_job_service.download_supabase_storage_object",
                new=AsyncMock(return_value=b"audio-bytes"),
            ) as download,
            patch(
                "app.services.stt_job_service.transcribe_audio_bytes",
                new=AsyncMock(return_value="회의 텍스트"),
            ) as transcribe,
        ):
            await process_stt_job(job.job_id)

        self.assertEqual(job.status, "DONE")
        self.assertEqual(job.text, "회의 텍스트")
        self.assertIsNone(job.error)
        download.assert_awaited_once_with("meeting-audio", "meetings/1/audio.mp3")
        transcribe.assert_awaited_once_with(b"audio-bytes", suffix="mp3")

    async def test_marks_job_failed_when_storage_download_fails(self) -> None:
        job = create_stt_job("meeting-audio", "meetings/1/audio.mp3")

        with patch(
            "app.services.stt_job_service.download_supabase_storage_object",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            await process_stt_job(job.job_id)

        self.assertEqual(job.status, "FAILED")
        self.assertIn("STT job 처리 중 알 수 없는 오류", job.error or "")


if __name__ == "__main__":
    unittest.main()
