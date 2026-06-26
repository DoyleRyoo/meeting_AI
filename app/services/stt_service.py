import asyncio
import os
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import UploadFile
from faster_whisper import WhisperModel

from app.services.summary_service import SummaryServiceError


DEFAULT_STT_MODEL = "small"
DEFAULT_STT_DEVICE = "cpu"
DEFAULT_STT_COMPUTE_TYPE = "int8"


@lru_cache(maxsize=1)
def _get_whisper_model() -> WhisperModel:
    model_name = os.getenv("STT_MODEL", DEFAULT_STT_MODEL)
    device = os.getenv("STT_DEVICE", DEFAULT_STT_DEVICE)
    compute_type = os.getenv("STT_COMPUTE_TYPE", DEFAULT_STT_COMPUTE_TYPE)

    try:
        return WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception as exc:
        raise SummaryServiceError("로컬 STT 모델을 초기화하지 못했습니다.") from exc


def _transcribe_path(path: str) -> str:
    model = _get_whisper_model()
    language = os.getenv("STT_LANGUAGE", "ko")

    try:
        segments, _ = model.transcribe(path, language=language, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments if segment.text)
    except Exception as exc:
        raise SummaryServiceError("로컬 STT 변환에 실패했습니다.") from exc

    if not text.strip():
        raise SummaryServiceError("STT 결과가 비어 있습니다.")
    return text.strip()


async def transcribe_audio(file: UploadFile) -> str:
    audio = await file.read()
    suffix = Path(file.filename or "").suffix or ".audio"
    return await transcribe_audio_bytes(audio, suffix=suffix)


async def transcribe_audio_bytes(audio: bytes, suffix: str = ".audio") -> str:
    if not audio:
        raise SummaryServiceError("음성 파일이 비어 있습니다.")

    if not suffix.startswith("."):
        suffix = f".{suffix}"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio)
            temp_path = temp_file.name

        return await asyncio.to_thread(_transcribe_path, temp_path)
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
