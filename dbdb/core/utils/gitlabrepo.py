from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import quote

import requests


GITLAB_URL_PATTERN = re.compile(r'gitlab\.com/(.+?)(?:\.git)?/?$')
GITLAB_API = 'https://gitlab.com/api/v4'


def _make_session(token: str | None) -> requests.Session:
    s = requests.Session()
    if token:
        s.headers['PRIVATE-TOKEN'] = token
    return s


def _total(response: requests.Response) -> int:
    """Read the X-Total header that GitLab includes on every paginated response."""
    return int(response.headers.get('X-Total', 0))


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s).astimezone(UTC)


def get_metadata(repo_url: str, token: str | None = None) -> dict:
    """
    Retrieve snapshot metadata for a GitLab project.

    Returns a dict whose keys map directly onto RepositorySnapshot fields plus
    an 'errors' key containing a list of exceptions raised during collection.
    Fields that could not be fetched retain their zero/None defaults.

    Raises:
        ValueError: URL does not look like a GitLab repo.
    """
    match = GITLAB_URL_PATTERN.search(repo_url)
    if not match:
        raise ValueError(f"Invalid GitLab URL: {repo_url}")
    project_path = match.group(1)
    encoded_path = quote(project_path, safe='')

    session = _make_session(token)
    base = f'{GITLAB_API}/projects/{encoded_path}'

    errors: list[Exception] = []

    # Defaults — overwritten section by section as each request succeeds.
    star_count = 0
    fork_count = 0
    commit_count = 0
    last_commit_hash = ''
    last_commit_timestamp = None
    open_pr_count = 0
    merged_pr_count = 0
    last_pr_submitted_at = None
    last_pr_closed_at = None
    open_issue_count = 0
    closed_issue_count = 0
    last_issue_submitted_at = None
    last_issue_closed_at = None
    commit_authors: list[str] = []
    pr_authors: list[str] = []
    issue_authors: list[str] = []

    # ── project info (stars, forks) ───────────────────────────────────────────
    try:
        r = session.get(base, timeout=30)
        r.raise_for_status()
        proj = r.json()
        star_count = proj.get('star_count', 0)
        fork_count = proj.get('forks_count', 0)
    except Exception as exc:
        errors.append(exc)

    # ── commits ───────────────────────────────────────────────────────────────
    try:
        r = session.get(f'{base}/repository/commits', params={'per_page': 1}, timeout=30)
        r.raise_for_status()
        commit_count = _total(r)
        commits = r.json()
        if commits:
            c = commits[0]
            last_commit_hash = c.get('id', '')
            last_commit_timestamp = _parse_dt(c.get('committed_date') or c.get('authored_date'))
    except Exception as exc:
        errors.append(exc)

    # ── merge-request counts ──────────────────────────────────────────────────
    try:
        r = session.get(f'{base}/merge_requests', params={'state': 'opened', 'per_page': 1}, timeout=30)
        r.raise_for_status()
        open_pr_count = _total(r)
    except Exception as exc:
        errors.append(exc)

    try:
        r = session.get(f'{base}/merge_requests', params={'state': 'merged', 'per_page': 1}, timeout=30)
        r.raise_for_status()
        merged_pr_count = _total(r)
    except Exception as exc:
        errors.append(exc)

    # ── last MR submitted ─────────────────────────────────────────────────────
    try:
        r = session.get(f'{base}/merge_requests',
                        params={'state': 'all', 'order_by': 'created_at', 'sort': 'desc', 'per_page': 1},
                        timeout=30)
        r.raise_for_status()
        newest_mr = r.json()
        last_pr_submitted_at = _parse_dt(newest_mr[0]['created_at']) if newest_mr else None
    except Exception as exc:
        errors.append(exc)

    # ── last MR closed/merged ─────────────────────────────────────────────────
    try:
        r = session.get(f'{base}/merge_requests',
                        params={'state': 'merged', 'order_by': 'updated_at', 'sort': 'desc', 'per_page': 1},
                        timeout=30)
        r.raise_for_status()
        newest_closed_mr = r.json()
        if newest_closed_mr:
            last_pr_closed_at = _parse_dt(
                newest_closed_mr[0].get('merged_at') or newest_closed_mr[0].get('closed_at')
            )
    except Exception as exc:
        errors.append(exc)

    # ── issue counts ──────────────────────────────────────────────────────────
    try:
        r = session.get(f'{base}/issues', params={'state': 'opened', 'per_page': 1}, timeout=30)
        r.raise_for_status()
        open_issue_count = _total(r)
    except Exception as exc:
        errors.append(exc)

    try:
        r = session.get(f'{base}/issues', params={'state': 'closed', 'per_page': 1}, timeout=30)
        r.raise_for_status()
        closed_issue_count = _total(r)
    except Exception as exc:
        errors.append(exc)

    # ── last issue submitted ──────────────────────────────────────────────────
    try:
        r = session.get(f'{base}/issues',
                        params={'state': 'all', 'order_by': 'created_at', 'sort': 'desc', 'per_page': 1},
                        timeout=30)
        r.raise_for_status()
        newest_issue = r.json()
        last_issue_submitted_at = _parse_dt(newest_issue[0]['created_at']) if newest_issue else None
    except Exception as exc:
        errors.append(exc)

    # ── last issue closed ─────────────────────────────────────────────────────
    try:
        r = session.get(f'{base}/issues',
                        params={'state': 'closed', 'order_by': 'updated_at', 'sort': 'desc', 'per_page': 1},
                        timeout=30)
        r.raise_for_status()
        newest_closed_issue = r.json()
        last_issue_closed_at = (
            _parse_dt(newest_closed_issue[0].get('closed_at')) if newest_closed_issue else None
        )
    except Exception as exc:
        errors.append(exc)

    # ── MR authors (most-recent 100) ──────────────────────────────────────────
    try:
        r = session.get(f'{base}/merge_requests',
                        params={'state': 'all', 'order_by': 'created_at', 'sort': 'desc', 'per_page': 100},
                        timeout=30)
        r.raise_for_status()
        seen: set[str] = set()
        for mr in r.json():
            name = (mr.get('author') or {}).get('username') or (mr.get('author') or {}).get('name', '')
            if name and name not in seen:
                seen.add(name)
                pr_authors.append(name)
    except Exception as exc:
        errors.append(exc)

    # ── issue authors (most-recent 100) ───────────────────────────────────────
    try:
        r = session.get(f'{base}/issues',
                        params={'state': 'all', 'order_by': 'created_at', 'sort': 'desc', 'per_page': 100},
                        timeout=30)
        r.raise_for_status()
        seen = set()
        for issue in r.json():
            name = (issue.get('author') or {}).get('username') or (issue.get('author') or {}).get('name', '')
            if name and name not in seen:
                seen.add(name)
                issue_authors.append(name)
    except Exception as exc:
        errors.append(exc)

    # ── commit authors / contributors (ordered by commit count) ───────────────
    try:
        r = session.get(f'{base}/repository/contributors',
                        params={'per_page': 100, 'order_by': 'commits'},
                        timeout=30)
        r.raise_for_status()
        commit_authors = [
            c.get('name') or c.get('email', '')
            for c in r.json()
            if c.get('name') or c.get('email')
        ]
    except Exception as exc:
        errors.append(exc)

    return {
        'commit_count':             commit_count,
        'last_commit_timestamp':    last_commit_timestamp,
        'last_commit_hash':         last_commit_hash,
        'open_pr_count':            open_pr_count,
        'merged_pr_count':          merged_pr_count,
        'last_pr_submitted_at':     last_pr_submitted_at,
        'last_pr_closed_at':        last_pr_closed_at,
        'open_issue_count':         open_issue_count,
        'closed_issue_count':       closed_issue_count,
        'last_issue_submitted_at':  last_issue_submitted_at,
        'last_issue_closed_at':     last_issue_closed_at,
        'fork_count':               fork_count,
        'star_count':               star_count,
        'commit_authors':           commit_authors,
        'pr_authors':               pr_authors,
        'issue_authors':            issue_authors,
        'errors':                   errors,
    }
