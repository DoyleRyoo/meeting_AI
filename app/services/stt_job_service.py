from dataclasses import dataclass
from uuid import uuid4

from app.schemas import SttJobStatus
from app.services.storage_service import download_supabase_storage_object
from app.services.stt_service import transcribe_audio_bytes
from app.services.summary_service import SummaryServiceError


@dataclass
class SttJob:
    job_id: str
    status: SttJobStatus
    bucket: str
    path: str
    text: str | None = None
    error: str | None = None


_JOBS: dict[str, SttJob] = {}


def create_stt_job(bucket: str, path: str) -> SttJob:
    job = SttJob(
        job_id=str(uuid4()),
        status=SttJobStatus.PENDING,
        bucket=bucket,
        path=path,
    )
    _JOBS[job.job_id] = job
    return job


def get_stt_job(job_id: str) -> SttJob | None:
    return _JOBS.get(job_id)


async def process_stt_job(job_id: str) -> None:
    job = _JOBS[job_id]
    job.status = SttJobStatus.RUNNING

    try:
        audio = await download_supabase_storage_object(job.bucket, job.path)
        suffix = job.path.rsplit(".", 1)[-1] if "." in job.path else "audio"
        job.text = await transcribe_audio_bytes(audio, suffix=suffix)
        job.status = SttJobStatus.DONE
    except SummaryServiceError as exc:
        job.error = str(exc)
        job.status = SttJobStatus.FAILED
    except Exception as exc:
        job.error = f"STT job 처리 중 알 수 없는 오류가 발생했습니다: {exc}"
        job.status = SttJobStatus.FAILED
