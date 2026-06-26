import os
from urllib.parse import quote

import httpx

from app.services.summary_service import SummaryServiceError


DEFAULT_SUPABASE_AUDIO_BUCKET = "meeting-audio"


async def download_supabase_storage_object(bucket: str, path: str) -> bytes:
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    missing_settings = [
        name
        for name, value in (
            ("SUPABASE_URL", supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", service_key),
        )
        if not value
    ]
    if missing_settings:
        missing = ", ".join(missing_settings)
        raise SummaryServiceError(f"Supabase Storage 설정이 필요합니다. missing={missing}")

    base_url = supabase_url.rstrip("/")
    encoded_bucket = quote(bucket, safe="")
    encoded_path = quote(path.lstrip("/"), safe="/")
    url = f"{base_url}/storage/v1/object/{encoded_bucket}/{encoded_path}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        response_text = exc.response.text[:300]
        raise SummaryServiceError(
            "Supabase Storage 파일을 다운로드하지 못했습니다. "
            f"status={status_code}, body={response_text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise SummaryServiceError("Supabase Storage 요청에 실패했습니다.") from exc

    if not response.content:
        raise SummaryServiceError("Supabase Storage 파일이 비어 있습니다.")
    return response.content


def default_audio_bucket() -> str:
    return os.getenv("SUPABASE_AUDIO_BUCKET", DEFAULT_SUPABASE_AUDIO_BUCKET)
