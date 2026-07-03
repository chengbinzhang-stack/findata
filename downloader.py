import httpx
import os
import shutil
import platform
from pathlib import Path
from typing import Optional
from models import ValidateUrlResponse, DocumentType
from datetime import date


DOWNLOAD_DIR = Path(__file__).parent / "downloads"


def get_browser_headers():
    system = platform.system()
    if system == "Darwin":
        os_platform = "macOS"
        platform_icon = "\"Macintosh\""
    elif system == "Windows":
        os_platform = "Windows"
        platform_icon = "\"Windows\""
    else:
        os_platform = "Linux"
        platform_icon = "\"Linux\""
    return {
        "User-Agent": f"Mozilla/5.0 ({os_platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "",
        "Origin": "",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "sec-ch-ua": "\"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": platform_icon,
    }


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
        headers = get_browser_headers()
        headers["Referer"] = "/".join(url.split("/")[:3])
        headers["Origin"] = "/".join(url.split("/")[:3])
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "").split(";")[0].strip()
                file_size = int(response.headers.get("content-length", 0))
                return ValidateUrlResponse(valid=True, content_type=content_type, file_size=file_size)
            return ValidateUrlResponse(valid=False, error=f"HTTP {response.status_code}")
    except httpx.TimeoutException:
        return ValidateUrlResponse(valid=False, error="Connection timeout")
    except httpx.RequestError as e:
        return ValidateUrlResponse(valid=False, error=str(e))


async def validate_url_playwright(url: str) -> ValidateUrlResponse:
    """Validate URL using Playwright headless browser."""
    from playwright.async_api import async_playwright
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(url, wait_until="networkidle", timeout=30000)
            status = response.status if response else 0
            content_type = ""
            file_size = 0
            if response:
                content_type = response.headers.get("content-type", "").split(";")[0].strip()
            # Get content length from response body
            try:
                body = await page.content()
                file_size = len(body.encode())
            except Exception:
                pass
            await browser.close()
            if status == 200:
                return ValidateUrlResponse(valid=True, content_type=content_type, file_size=file_size)
            return ValidateUrlResponse(valid=False, error=f"HTTP {status}")
    except Exception as e:
        return ValidateUrlResponse(valid=False, error=str(e))


async def download_file(url: str, local_path: Path) -> tuple[bool, Optional[str]]:
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        headers = get_browser_headers()
        headers["Referer"] = "/".join(url.split("/")[:3])
        headers["Origin"] = "/".join(url.split("/")[:3])
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    return False, f"HTTP {response.status_code}"
                with open(local_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        return True, None
    except Exception as e:
        return False, str(e)


async def download_file_playwright(url: str, local_path: Path, timeout: int = 60) -> tuple[bool, Optional[str]]:
    """Download file using Playwright (headless browser) for sites with WAF."""
    from playwright.async_api import async_playwright
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            # Set up download handler
            download_task = None
            async def handle_download(download):
                nonlocal download_task
                download_task = download

            page.on("download", handle_download)
            await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            # Wait for download to start
            if download_task is None:
                await page.wait_for_timeout(3000)
            if download_task:
                await download_task.save_as(str(local_path))
                await browser.close()
                return True, None
            else:
                await browser.close()
                return False, "No download detected"
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