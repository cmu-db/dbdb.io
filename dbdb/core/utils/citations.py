import io
import requests
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, Any

from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from pptx import Presentation


# --- Configuration ---

MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
REQUEST_TIMEOUT = 15

SPAM_KEYWORDS = {
    "porn", "xxx", "sex", "escort", "nude", "camgirl",
    "casino", "bet", "betting", "gambling", "slot", "poker"
}


# --- Exceptions ---

class SpamPageError(RuntimeError):
    pass


class UnsupportedContentTypeError(RuntimeError):
    pass


# --- Helpers ---

def _is_spam_html(text: str) -> bool:
    """
    Very conservative keyword-based spam detection.
    """
    text = text.lower()
    hits = sum(1 for kw in SPAM_KEYWORDS if kw in text)
    return hits >= 2


def _extract_pdf_title(data: bytes) -> str | None:
    reader = PdfReader(io.BytesIO(data))
    meta = reader.metadata
    if meta and meta.title:
        return meta.title.strip() or None
    return None


def _extract_ppt_title(data: bytes) -> str | None:
    prs = Presentation(io.BytesIO(data))
    core = prs.core_properties
    return core.title.strip() if core.title else None


def _extract_html_title(data: bytes, encoding: str | None) -> str:
    soup = BeautifulSoup(
        data.decode(encoding or "utf-8", errors="replace"),
        "html.parser",
    )

    if _is_spam_html(soup.get_text(" ")):
        raise SpamPageError("HTML page classified as spam")

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    raise ValueError("HTML page has no <title>")

def _parse_cache_control(header: str | None) -> Dict[str, str | bool]:
    """
    Parse Cache-Control header into a structured dict.
    """
    if not header:
        return {}

    directives = {}
    for part in header.split(","):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            directives[k.lower()] = v.strip('"')
        else:
            directives[part.lower()] = True
    return directives


# --- Main API ---

def fetch_url_metadata(
    url: str,
    *,
    if_none_match: str | None = None,
    if_modified_since: datetime | None = None,
) -> Dict[str, Any]:

    headers = {"User-Agent": "dbdb.io/1.0"}
    if if_none_match:
        headers["If-None-Match"] = if_none_match
    if if_modified_since:
        headers["If-Modified-Since"] = if_modified_since.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

    with requests.get(
        url,
        stream=True,
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        allow_redirects=True,
    ) as resp:

        status_code = resp.status_code
        content_type = (
            resp.headers.get("Content-Type", "").split(";")[0].lower() or None
        )

        etag = resp.headers.get("ETag")

        last_modified_hdr = resp.headers.get("Last-Modified")
        try:
            last_modified = (
                parsedate_to_datetime(last_modified_hdr)
                if last_modified_hdr
                else None
            )
        except (TypeError, ValueError):
            last_modified = None

        cache_control = _parse_cache_control(
            resp.headers.get("Cache-Control")
        )

        # --- Short-circuit on 304 ---
        if status_code == 304:
            return {
                "url": url,
                "status-code": status_code,
                "content-type": content_type,
                "title": None,
                "etag": etag,
                "last-modified": last_modified,
                "cache-control": cache_control,
                "revalidate": {
                    "if-none-match": etag or if_none_match,
                    "if-modified-since": last_modified or if_modified_since,
                },
            }

        # --- Download body ---
        data = bytearray()
        for chunk in resp.iter_content(chunk_size=8192):
            data.extend(chunk)
            if len(data) > MAX_DOWNLOAD_BYTES:
                raise RuntimeError("Download exceeds size limit")
        data = bytes(data)

    # --- Content-Type dispatch ---

    if content_type == "application/pdf":
        title = _extract_pdf_title(data)

    elif content_type in {
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }:
        title = _extract_ppt_title(data)

    elif content_type in {"text/html", "application/xhtml+xml"}:
        title = _extract_html_title(data, resp.encoding)

    else:
        title = None  # allow metadata-only fetches

    return {
        "url": url,
        "status-code": status_code,
        "content-type": content_type,
        "title": title,
        "etag": etag,
        "last-modified": last_modified,
        "cache-control": cache_control,
        "revalidate": {
            "if-none-match": etag,
            "if-modified-since": last_modified,
        },
    }
