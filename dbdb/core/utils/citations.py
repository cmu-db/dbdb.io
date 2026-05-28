import io
import logging
import posixpath
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from subprocess import TimeoutExpired
from typing import Any
from urllib.parse import (
    parse_qsl,
    quote,
    unquote,
    urlencode,
    urlsplit,
    urlunsplit,
)

import requests
from bs4 import BeautifulSoup
from django.db import connection, transaction
from django.db.models import Q
from pptx import Presentation
from PyPDF2 import PdfReader
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from tldextract import tldextract

from dbdb.core.models import CitationUrl, System, SystemFeature, SystemVersion
from dbdb.core.utils import spam
from dbdb.core.utils.git import get_git_commit_metadata
from dbdb.core.utils.spam import UnexpectedResponseError

LOG = logging.getLogger(__name__)

# --- Configuration ---

MAX_DOWNLOAD_BYTES = 60 * 1024 * 1024
REQUEST_TIMEOUT = 15 # seconds

SKIP_DOMAINS = {
    "//www.crunchbase.com/", # Recaptcha blocks
    "//twitter.com",
    "//www.bloomberg.com/",
    "//dl.acm.org/",
    "//dbdb.io/",
    "//www.linkedin.com/",
    "//docs.4d.com/",
    "//doc.4d.com/",
    '//git-wip-us.apache.org',
    '//angel.co/',
    '//www.cnet.com/', # HTML never renders?
}

SPAM_IGNORE_DOMAINS = {
    # "apache.org",
    "//en.wikipedia.org/",
    "//www.postgresql.org/",
    "//www.slideshare.net/", # LLM spam checker can't handle it?
    "//news.ycombinator.com/",
    "//books.google.com/"
}

IGNORE_TITLES = map(str.lower, [
    "Redirecting to Google Groups",
    "PowerPoint Presentation",
    "PowerPoint 演示文稿",
    "Just a moment...",
    "File not found · GitHub",
    "Redirecting…",
])

REMOVE_TEXT = [
    "There was an error while loading. Please reload this page", # github
    " Uh oh! \n",  # github
]

# --- Exceptions ---

class SpamPageError(RuntimeError):
    pass


class UnsupportedContentTypeError(RuntimeError):
    pass


# --- Helpers ---

def _get_fragment(url: str) -> str:
    parts = urlsplit(url)
    return parts.fragment

def _extract_pdf_metadata(url:str, data: bytes, system: System | None = None) -> tuple[str | None, datetime | None]:
    """
    Extract title and oldest date (CreationDate or ModDate) from PDF metadata.

    Returns:
        tuple: (title, oldest_date) where title is a string or None,
               and oldest_date is a timezone-aware datetime or None
    """
    reader = PdfReader(io.BytesIO(data))
    meta = reader.metadata
    LOG.debug(f"meta: {meta}")

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

def _extract_ppt_title(url:str, data: bytes, system: System | None = None) -> str | None:
    prs = Presentation(io.BytesIO(data))
    core = prs.core_properties
    title = None
    if core.title:
        title = core.title.strip()
    return title


def _parse_cache_control(header: str | None) -> dict[str, str | bool]:
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
        system: System | None = None,
        skip_spamcheck: bool = False,
        request_timeout: int | None = None,
    ) -> str:

    if any(d in url for d in SPAM_IGNORE_DOMAINS):
        skip_spamcheck = True

    title = None
    html = _get_html_page(url, request_timeout=request_timeout)
    soup = BeautifulSoup(html, "html.parser")

    if html and re.search(
        r'Visit\s+(?:<a[^>]*>)?cloudflare\.com(?:</a>)?\s+for more information',
        html, re.IGNORECASE
    ):
        LOG.debug(f"Cloudflare error page detected for {url}")
        return None

    if not skip_spamcheck:
        # Extract the text from the HTML and clean up the newlines and spaces
        # This is wasted space in our prompt context
        text_words = soup.get_text(" ")
        text_words = re.sub(r"(?:\t){1,}", " ", text_words, flags=re.DOTALL)
        text_words = re.sub(r"(?: ){2,}", " ", text_words, flags=re.DOTALL)
        text_words = re.sub(r"(?: \n){2,}", " \n", text_words, flags=re.DOTALL)
        text_words = re.sub(r"(?:\n \n)", " \n", text_words, flags=re.DOTALL)

        for s in REMOVE_TEXT:
            text_words = text_words.replace(s, "")

        # Make sure there is at least something for us to look
        # at when we use the spam checker
        if len(text_words) > 0:
            attempts = 3
            temperature = 0.0
            # model = "qwen3:14b" # "qwen3:8b"
            model = "qwen3:32b"
            is_spam = None
            while attempts > 0:
                attempts -= 1
                try:
                    is_spam = spam.is_spam(text_words, system,
                                           timeout=request_timeout,
                                           temperature=temperature,
                                           model=model
                    )
                    break
                except UnexpectedResponseError as e:
                    # Ignore if we get a weird LLM response
                    LOG.error(e)
                    if attempts == 0: raise e
                    pass
                model = "qwen3:14b" if attempts % 2 == 0 else "mistral:7b"
                temperature = max(temperature - 0.1, 0.0)
            if is_spam is not None and is_spam:
                raise SpamPageError(f"HTML page classified as spam for {system}")

    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    return title # ValueError("HTML page has no <title>")

def _get_html_page(
        url,
        render_wait: float = 10,
        request_timeout: int | None = None) -> BeautifulSoup | None:
    options = Options()
    options.add_argument("--headless")
    options.set_preference("javascript.enabled", True)

    driver = webdriver.Firefox(options=options)
    # driver = webdriver.Chrome()

    driver.get(url)
    try:
        # 2. Use WebDriverWait to wait for the title to be present
        # This ensures the dynamic content has loaded before proceeding
        LOG.debug(f"Waiting {render_wait} seconds for HTML page to render")
        # wait = WebDriverWait(driver, timeout=request_timeout)
                #.until(EC.presence_of_element_located((By.TAG_NAME, 'title'))))
        time.sleep(render_wait)
        LOG.debug("Page is ready and element is present!")

        # 3. Get the page source after the wait condition is met
        html_source = driver.page_source

    except TimeoutException:
        LOG.debug("Loading took too much time or element not found!")
        html_source = None  # Handle the case where the element was not found in time

    finally:
        # Always close the browser
        driver.quit()

    return html_source

# --- Main API ---

def fetch_url_metadata(
    url: str,
    *,
    system: System | None = None,
    skip_spamcheck: bool = False,
    request_timeout: int | None = None,
    if_none_match: str | None = None,
    if_modified_since: datetime | None = None,
    allow_redirects: bool = False,
    redirect_ctr: int = 0,
) -> dict[str, Any]:

    headers = {"User-Agent": "dbdb.io/1.0"}
    if if_none_match:
        headers["If-None-Match"] = if_none_match
    if if_modified_since:
        headers["If-Modified-Since"] = if_modified_since.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

    if not request_timeout:
        request_timeout = REQUEST_TIMEOUT

    # Special Case: Busted Domains
    if any(s in url for s in SKIP_DOMAINS):
        LOG.debug(f"Skipping '{url}' because it is from a domain to ignore")
        return {
            "url": url,
            "status-code": None,
            "content-type": None,
            "content-length": None,
            "status": CitationUrl.Status.IGNORE,
            "title": None,
            "etag": None,
            "last-modified": None,
            "cache-control": None,
            "revalidate": None
        }

    # Special Case: Github Commit
    m = re.match(
        r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)/commit/(?P<commit>[^/.]+)/?$",
        url,
    )
    if m and "#diff-" not in url:
        owner = m.group("owner")
        repo = m.group("repo")
        commit_id = m.group("commit")
        repo_url = f"https://github.com/{owner}/{repo}.git"
        try:
            # If the Github repo is no longer available, then this will time out
            # So we'll just treat it like a regular page and record the 404 status-code
            title, last_modified = get_git_commit_metadata(repo_url, commit_id, timeout=request_timeout)
            return {
                "url": url,
                "status-code": 200,
                "content-type": None,
                "content-length": None,
                "status": CitationUrl.Status.VALID,
                "title": title,
                "etag": None,
                "last-modified": last_modified,
                "cache-control": None,
                "revalidate": None
            }
        except TimeoutExpired as e:
            LOG.debug(f"Timeout: {e}")
            pass

    title = None
    status: CitationUrl.Status = CitationUrl.Status.UNKNOWN

    with requests.get(
        url,
        stream=True,
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        allow_redirects=True if redirect_ctr > 8 else allow_redirects,
    ) as resp:
        status_code = resp.status_code
        LOG.debug(f"{url}\nstatus_code={status_code}")

        # If we get redirected, then recursively call ourselves
        # with allowing the redirect so that we can get the new URL
        if status_code in (301, 302):
            new_url = resp.headers['Location']
            if not new_url.startswith("http"):
                orig_extracted = tldextract.extract(url)
                new_url = "https://" + orig_extracted.fqdn + new_url
            # Don't normalize because we may get stuck in an infinite loop
            # if the server-side adds back the trailing slash
            normalized_url = normalize_url(new_url)
            if normalized_url + '/' != new_url: new_url = normalized_url

            # Add back the fragment after normalize the redirect
            fragment = _get_fragment(url)
            if fragment: new_url += f"#{fragment}"

            LOG.debug(f"Redirect: {new_url}")
            result = fetch_url_metadata(
                new_url,
                system=system,
                skip_spamcheck=skip_spamcheck,
                request_timeout=request_timeout,
                if_none_match=if_none_match,
                if_modified_since=if_modified_since,
                allow_redirects=False,
                redirect_ctr=redirect_ctr+1,
            )
            if not result: return None
            if result["status"] != CitationUrl.Status.SPAM:
                # Only update the URL redirect if the domains are the same.
                # Otherwise they will redirect to a spam cite and we lose the original URL
                orig_extracted = tldextract.extract(url)
                new_extracted = tldextract.extract(new_url)
                if orig_extracted.domain == new_extracted.domain and \
                    orig_extracted.suffix == new_extracted.suffix:
                    LOG.debug(f"Updating URL: status={result['status']} / {new_url}")
                    result["url"] = new_url
            else:
                result["url"] = url
            return result

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
                "status": CitationUrl.Status.VALID,
                "status-code": status_code,
                "content-type": content_type,
                "content-length": content_length,
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
        if status_code != 404 and len(data) == 0:
            LOG.error(f"Unexpected empty contents for '{url}'")
            status = CitationUrl.Status.IGNORE

    if status == CitationUrl.Status.UNKNOWN:
        status = CitationUrl.Status.VALID if status_code >= 200 and status_code < 300 else CitationUrl.Status.DEAD

    # --- Content-Type dispatch ---

    if status_code != 404 and status != CitationUrl.Status.IGNORE:
        # PDF
        if content_type == "application/pdf":
            title, pdf_last_modified = _extract_pdf_metadata(url, data)
            if pdf_last_modified: last_modified = pdf_last_modified

        # PPTX
        elif content_type in {
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }:
            title = _extract_ppt_title(url, data)

        # HTML
        elif content_type in {"text/html", "application/xhtml+xml"}:
            try:
                title = _extract_html_title(url, data,
                                            encoding=resp.encoding,
                                            skip_spamcheck=skip_spamcheck,
                                            system=system,
                                            request_timeout=request_timeout)
            except SpamPageError:
                status = CitationUrl.Status.SPAM

    # Minor cleaning...
    if title is not None and title:
        title = title.replace("\n", " ")
        title = re.sub(r' {2,}', ' ', title)
        if title and title.strip() == url: title = None
        if title and title.startswith("https://"): title = None
        if title and title.lower() in IGNORE_TITLES: title = None
        if title and status_code in [403, 404]: title = None

    return {
        "url": url,
        "status": status,
        "status-code": status_code,
        "content-type": content_type,
        "content-length": content_length,
        "title": title,
        "etag": etag,
        "last-modified": last_modified,
        "cache-control": cache_control,
        "revalidate": {
            "if-none-match": etag,
            "if-modified-since": last_modified,
        },
    }

def merge_citations(merge_to: CitationUrl, merge_from: list[CitationUrl]) -> CitationUrl:


    LOG.debug(f"Merging {len(merge_from)} citations to {merge_to}")

    tables = [
        "core_systemfeature_citations",
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
        where = f' citationurl_id IN ({placeholders})'
        for table in tables:
            with connection.cursor() as cursor:
                # Check whether there is already an entry for the url_id that we want to keep.
                # If yes, then we just need to delete all these existing entries
                if table == "core_systemfeature_citations":
                    info_column = "systemfeature_id"
                else:
                    info_column = "systemversion_id"
                sql = f"SELECT id, {info_column} AS system_info_id, citationurl_id FROM {table} WHERE " \
                    
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
                    sql = f"UPDATE {table} SET citationurl_id = {merge_to.id} WHERE citationurl_id = {p[1]} AND {info_column} = {p[0]};"\
                            
                    # LOG.debug(sql)
                    cursor.execute(sql)
                    assert cursor.rowcount > 0
                    LOG.info(f"Modified {cursor.rowcount} records in table '{table}")
                for p in to_delete:
                    sql = f"DELETE FROM {table} WHERE citationurl_id = {p[1]} AND {info_column} = {p[0]};" \
                            
                    # LOG.debug(sql)
                    cursor.execute(sql)
                    assert cursor.rowcount > 0
                    LOG.info(f"Deleted {cursor.rowcount} records in table '{table}")

        # It is now safe to delete the duplicate entries
        # result, _ = CitationUrl.objects.filter(id__in=[c.id for c in merge_from]).delete()
        # LOG.info(f"Merged {result} objects into '{merge_to}'")

        return merge_to

def get_systems(c: CitationUrl,
                current_only: bool | None = False) -> list[System]:
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
        Q(history_citations__in=[c])
    )
    if current_only:
        versions = versions.filter(is_current=True)
    systems.update(v.system for v in versions)

    return list(systems)



def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison/deduplication while preserving fragments.
    """

    # HACK: Remove any URLs that already link to archive.org
    m = re.match(r"https://web\.archive\.org/web/.*?/(?P<url>http[s]?:/[/]?.*?)$", url, re.IGNORECASE)
    if m:
        url = m.group('url').strip()
        LOG.debug(f"Removed archive.org prefix: {url}")

    parts = urlsplit(url)

    # 1. Lowercase scheme and hostname
    scheme = parts.scheme.lower()
    hostname = parts.hostname.lower() if parts.hostname else ""

    # 2. Remove default ports
    try:
        port = parts.port
    except ValueError:
        port = 443 if scheme == "https" else 80
    except:
        raise
    if port and not (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    ):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    # Preserve userinfo if present
    if parts.username:
        userinfo = parts.username
        if parts.password:
            userinfo += f":{parts.password}"
        netloc = f"{userinfo}@{netloc}"
    # HACK: We sometimes got two dots at the end of a netloc?
    if netloc.endswith(".."):
        netloc = netloc[:-2]

    # 3. Normalize path
    path = unquote(parts.path)
    path = posixpath.normpath(path)

    # If there is no path, then this will add a dot. Remove that if we only have a dot
    if path in {".", "/"}: path = ""
    # If there is a path and it doesn't start with '/', then add the slash
    # We will purposely exclude a path for root domain URLs
    if path and not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    # Re-encode path
    path = quote(path, safe="/~:@")

    # 4. Normalize query (sorted)
    query_params = parse_qsl(parts.query, keep_blank_values=True)
    query = urlencode(sorted(query_params), doseq=True)

    # 5. Preserve fragment
    fragment = parts.fragment

    LOG.info(f"Normalize: {url}\n+ scheme: {scheme}\n+ netloc: {netloc}\n+ path: {path}\n+ query: {query}\n+ fragment: {fragment}")
    return urlunsplit((scheme, netloc, path, query, fragment))
