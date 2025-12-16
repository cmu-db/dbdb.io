import io
import re
import logging

import requests
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, Any, List

from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from django.db.models import Q
from django.views.decorators.http import last_modified
from pptx import Presentation
from django.db import connection, transaction
from django.utils import timezone

from dbdb.core.models import CitationUrl, System, SystemFeature, SystemVersion
from dbdb.core.utils.git import get_git_commit_metadata
from dbdb.core.utils import spam

LOG = logging.getLogger('console')

# --- Configuration ---

MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
REQUEST_TIMEOUT = 15 # seconds

SPAM_IGNORE_DOMAINS = {
    "apache.org",
    "//en.wikipedia.org/",
    "//www.postgresql.org/"
}

IGNORE_TITLES = map(str.lower, [
    "Redirecting to Google Groups",
    "PowerPoint Presentation",
    "PowerPoint 演示文稿",
    "Just a moment...",
    "File not found · GitHub",
    "Redirecting…",
])

# --- Exceptions ---

class SpamPageError(RuntimeError):
    pass


class UnsupportedContentTypeError(RuntimeError):
    pass


# --- Helpers ---

def _extract_pdf_metadata(url:str, data: bytes, system_name: str | None ) -> tuple[str | None, datetime | None]:
    """
    Extract title and oldest date (CreationDate or ModDate) from PDF metadata.

    Returns:
        tuple: (title, oldest_date) where title is a string or None,
               and oldest_date is a timezone-aware datetime or None
    """
    reader = PdfReader(io.BytesIO(data))
    meta = reader.metadata
    print(f"meta: {meta}")

    # Extract title
    title = None
    if meta and meta.title:
        title = meta.title.strip() or None

    # Extract dates
    creation_date = None
    mod_date = None
    if meta:
        # Bad meta-data throws errors. We can just ignore it
        try:
            creation_date = meta.creation_date
        except:
            pass
        try:
            mod_date = meta.modification_date
        except:
            pass

    # Find the oldest date
    oldest_date = None
    if creation_date and mod_date:
        oldest_date = min(creation_date, mod_date)
    elif creation_date:
        oldest_date = creation_date
    elif mod_date:
        oldest_date = mod_date

    return title, oldest_date

def _extract_ppt_title(url:str, data: bytes) -> str | None:
    prs = Presentation(io.BytesIO(data))
    core = prs.core_properties
    title = None
    if core.title:
        title = core.title.strip()
    return title


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

def _extract_html_title(
        url: str,
        data: bytes,
        encoding: str | None = None,
        system_name: str | None = None,
        skip_spamcheck: bool = False,
        request_timeout: int | None = None,
    ) -> str:
    soup = BeautifulSoup(
        data.decode(encoding or "utf-8", errors="replace"),
        "html.parser",
    )

    spam_check = not skip_spamcheck
    for ignore in SPAM_IGNORE_DOMAINS:
        if ignore in url:
            spam_check = False
    html = soup.get_text(" ")
    if spam_check and spam.is_spam(html, system_name, timeout=request_timeout):
        raise SpamPageError(f"HTML page classified as spam for {system_name}")

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # Silently ignore pages without titles
    return None # ValueError("HTML page has no <title>")


# --- Main API ---

def fetch_url_metadata(
    url: str,
    *,
    system_name: str | None = None,
    skip_spamcheck: bool = False,
    request_timeout: int | None = None,
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

    if not request_timeout:
        request_timeout = REQUEST_TIMEOUT

    # Special Case: Github Commit
    m = re.match(
        r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)/commit/(?P<commit>[^/.]+)/?$",
        url,
    )
    if m:
        owner = m.group("owner")
        repo = m.group("repo")
        commit_id = m.group("commit")
        repo_url = f"https://github.com/{owner}/{repo}.git"
        title, last_modified = get_git_commit_metadata(repo_url, commit_id, timeout=request_timeout)
        return {
            "url": url,
            "status-code": 200,
            "content-type": None,
            "content-length": None,
            "dead": False,
            "title": title,
            "etag": None,
            "last-modified": last_modified,
            "cache-control": None,
            "revalidate": None
        }


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
        content_length = resp.headers.get("Content-Length", None)

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
                "content-length": content_length,
                "dead": False,
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
                raise RuntimeError(f"Download exceeds size limit [#bytes={len(data)}]")
        data = bytes(data)

    # --- Content-Type dispatch ---

    if content_type == "application/pdf":
        title, pdf_last_modified = _extract_pdf_metadata(url, data)
        if pdf_last_modified: last_modified = pdf_last_modified

    elif content_type in {
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }:
        title = _extract_ppt_title(url, data)

    elif content_type in {"text/html", "application/xhtml+xml"}:
        title = _extract_html_title(url, data,
                                    encoding=resp.encoding,
                                    skip_spamcheck=skip_spamcheck,
                                    system_name=system_name,
                                    request_timeout=request_timeout)

    else:
        title = None  # allow metadata-only fetches

    # Minor cleaning...
    if title:
        title = title.replace("\n", " ")
        title = re.sub(r' {2,}', ' ', title)
        if title and title.strip() == url: title = None
        if title and title.startswith("https://"): title = None
        if title and title.lower() in IGNORE_TITLES: title = None
        if title and status_code in [403, 404]: title = None

    return {
        "url": url,
        "status-code": status_code,
        "content-type": content_type,
        "content-length": content_length,
        "dead": not(200 <= status_code < 300),
        "title": title,
        "etag": etag,
        "last-modified": last_modified,
        "cache-control": cache_control,
        "revalidate": {
            "if-none-match": etag,
            "if-modified-since": last_modified,
        },
    }

def merge_citations(merge_to: CitationUrl, merge_from: List[CitationUrl]) -> CitationUrl:
    LOG.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    LOG.addHandler(console)

    LOG.debug(f"Merging {len(merge_from)} citations to {merge_to}")

    tables = [
        "core_systemfeature_citations",
        "core_systemversion_acquired_by_citations",
        "core_systemversion_description_citations",
        "core_systemversion_end_year_citations",
        "core_systemversion_history_citations",
        "core_systemversion_start_year_citations",
    ]

    # We will pick the first one as the one to keep
    # And then delete the rest. But we need to go through and update any references to them
    with (transaction.atomic()):
        url_ids = [c.id for c in merge_from] + [merge_to.id]
        placeholders = ', '.join(['%s'] * len(url_ids))  # "%s, %s, %s, ... %s"
        where = ' citationurl_id IN ({})'.format(placeholders)
        for table in tables:
            with connection.cursor() as cursor:
                # Check whether there is already an entry for the url_id that we want to keep.
                # If yes, then we just need to delete all these existing entries
                if table == "core_systemfeature_citations":
                    info_column = "systemfeature_id"
                else:
                    info_column = "systemversion_id"
                sql = "SELECT id, {} AS system_info_id, citationurl_id FROM {} WHERE " \
                    .format(info_column, table)
                sql += where
                LOG.debug(sql)


                # Check whether the merge_to URL already exists for a system.
                # If yes, then we delete it.
                # If no, then we just update it
                cursor.execute(sql, tuple(url_ids))
                rows = cursor.fetchall()
                existing_citations = [ (row[1],row[2]) for row in rows if row[2] == merge_to.id ]
                to_delete = []
                to_update = []
                for row in rows:
                    if row[2] == merge_to.id: continue
                    target = (row[1], merge_to.id)
                    p = (row[1], row[2])
                    if target not in existing_citations:
                        to_update.append(p)
                    else:
                        to_delete.append(p)
                    pass

                # LOG.debug(f"Existing: {existing_citations}")
                # LOG.debug(f" +MergeFrom: {url_ids}")
                # LOG.debug(f" +ToDelete: {to_delete}")
                # LOG.debug(f" +ToUpdate: {to_update}")

                for p in to_update:
                    sql = "UPDATE {} SET citationurl_id = {} WHERE citationurl_id = {} AND {} = {};"\
                            .format(table, merge_to.id, p[1], info_column, p[0])
                    # LOG.debug(sql)
                    cursor.execute(sql)
                    assert cursor.rowcount > 0
                    LOG.info("Modified {} records in table '{}".format(cursor.rowcount, table))
                for p in to_delete:
                    sql = "DELETE FROM {} WHERE citationurl_id = {} AND {} = {};" \
                            .format(table, p[1], info_column, p[0])
                    # LOG.debug(sql)
                    cursor.execute(sql)
                    assert cursor.rowcount > 0
                    LOG.info("Deleted {} records in table '{}".format(cursor.rowcount, table))

        # It is now safe to delete the duplicate entries
        # result, _ = CitationUrl.objects.filter(id__in=[c.id for c in merge_from]).delete()
        # LOG.info(f"Merged {result} objects into '{merge_to}'")

        return merge_to

def get_systems(c: CitationUrl,
                current_only: bool | None = False) -> List[System]:
    """
    Return the list of systems that reference this CitationURL
    :param citation:
    :return:
    """

    # Check the SystemFeatures first
    # features = SystemFeature.objects.filter(citations__in=[c])
    features = SystemFeature.objects.filter(citations__in=[c])
    if current_only:
        features = features.filter(version__is_current=True)
    systems = set([sf.version.system for sf in features])

    # Then check SystemVersions
    versions = SystemVersion.objects.filter(
        Q(description_citations__in=[c]) |
        Q(start_year_citations__in=[c]) |
        Q(end_year_citations__in=[c]) |
        Q(history_citations__in=[c]) |
        Q(acquired_by_citations__in=[c])
    )
    if current_only:
        versions = versions.filter(is_current=True)
    systems.update(v.system for v in versions)

    return list(systems)
