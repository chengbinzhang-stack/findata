import httpx
import os
import shutil
from pathlib import Path
from typing import Optional
from models import ValidateUrlResponse, DocumentType
from datetime import date


DOWNLOAD_DIR = Path(__file__).parent / "downloads"


def get_file_extension(url: str) -> str:
    if not url:
        return ""
    path = httpx.URL(url).path
    ext = Path(path).suffix.lower()
    if ext in ['.mp3', '.mp4', '.wav', '.m4a', '.pdf']:
        return ext
    return ".pdf"


def generate_filename(event_date: date, scrip_code: str, doc_type: DocumentType, url: str) -> str:
    date_str = event_date.strftime("%Y%m%d") if event_date else date.today().strftime("%Y%m%d")
    extension = get_file_extension(url)
    return f"{date_str}_{scrip_code}_{doc_type.value}{extension}"


def generate_folder_path(scrip_code: str, fy: str, quarter: str) -> str:
    return f"Transcripts_Repository/{scrip_code}/{fy}/{quarter}/"


async def validate_url(url: str) -> ValidateUrlResponse:
    if not url:
        return ValidateUrlResponse(valid=False, error="URL is empty")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.head(url)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "").split(";")[0].strip()
                file_size = int(response.headers.get("content-length", 0))
                return ValidateUrlResponse(valid=True, content_type=content_type, file_size=file_size)
            return ValidateUrlResponse(valid=False, error=f"HTTP {response.status_code}")
    except httpx.TimeoutException:
        return ValidateUrlResponse(valid=False, error="Connection timeout")
    except httpx.RequestError as e:
        return ValidateUrlResponse(valid=False, error=str(e))


async def download_file(url: str, local_path: Path) -> tuple[bool, Optional[str]]:
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    return False, f"HTTP {response.status_code}"
                with open(local_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        return True, None
    except Exception as e:
        return False, str(e)


async def process_download(
    task_id: str,
    file_type: str,
    url: str,
    local_dir: Path,
    scrip_code: str,
    fy: str,
    quarter: str,
    event_date: date,
    doc_type: DocumentType,
    db_record_id: int,
    update_callback
):
    from database import update_file_record, update_task_status

    filename = generate_filename(event_date, scrip_code, doc_type, url)
    local_path = local_dir / filename

    await update_callback("downloading", db_record_id, local_path=str(local_path))

    success, error = await download_file(url, local_path)

    if success:
        await update_file_record(db_record_id, "downloaded", local_path=str(local_path))
        await update_callback("uploading", db_record_id, local_path=str(local_path))
        return True, str(local_path), filename
    else:
        await update_file_record(db_record_id, "failed", error_message=error)
        await update_callback("failed", db_record_id, error=error)
        return False, None, error