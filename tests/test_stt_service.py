import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import UploadFile

from app.services.stt_service import transcribe_audio
from app.services.summary_service import SummaryServiceError


class SttServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_transcribes_uploaded_audio_with_local_whisper_model(self) -> None:
        upload = UploadFile(filename="meeting.mp3", file=MagicMock())
        upload.file.read.return_value = b"audio-bytes"
        segment_one = SimpleNamespace(text=" 첫 번째 문장 ")
        segment_two = SimpleNamespace(text="두 번째 문장")

        with (
            patch("app.services.stt_service._get_whisper_model") as get_model,
            patch.dict("os.environ", {"STT_LANGUAGE": "ko"}),
        ):
            get_model.return_value.transcribe.return_value = (
                [segment_one, segment_two],
                object(),
            )
            result = await transcribe_audio(upload)

        self.assertEqual(result, "첫 번째 문장 두 번째 문장")
        get_model.return_value.transcribe.assert_called_once()
        transcribe_path = get_model.return_value.transcribe.call_args.args[0]
        self.assertTrue(transcribe_path.endswith(".mp3"))
        self.assertEqual(
            get_model.return_value.transcribe.call_args.kwargs,
            {"language": "ko", "vad_filter": True},
        )

    async def test_rejects_empty_audio_file(self) -> None:
        upload = UploadFile(filename="empty.mp3", file=MagicMock())
        upload.file.read.return_value = b""

        with self.assertRaises(SummaryServiceError):
            await transcribe_audio(upload)


if __name__ == "__main__":
    unittest.main()
