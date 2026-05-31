from __future__ import annotations

import re
import time
from datetime import UTC, datetime

import requests


GITHUB_URL_PATTERN = re.compile(r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$')
GITHUB_API = 'https://api.github.com'

# Seconds to sleep before each API request to avoid secondary rate limits.
GITHUB_API_SLEEP = 1.0


def _make_session(token: str | None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    if token:
        s.headers['Authorization'] = f'Bearer {token}'
    return s


def _link_last_page(response: requests.Response) -> int | None:
    """Parse the Link header to get the last page number (= total count when per_page=1)."""
    link = response.headers.get('Link', '')
    m = re.search(r'<[^>]+[?&]page=(\d+)[^>]*>;\s*rel="last"', link)
    return int(m.group(1)) if m else None


def _search_total(session: requests.Session, query: str) -> int:
    """Use the GitHub Search API to get an exact total count."""
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(
        f'{GITHUB_API}/search/issues',
        params={'q': query, 'per_page': 1},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get('total_count', 0)


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(UTC)


def get_metadata(repo_url: str, token: str | None = None) -> dict:
    """
    Retrieve snapshot metadata for a GitHub repository.

    Returns a dict whose keys map directly onto RepositorySnapshot fields.

    Raises:
        ValueError: URL does not look like a GitHub repo.
        requests.HTTPError: API request failed.
    """
    match = GITHUB_URL_PATTERN.search(repo_url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    owner, repo_name = match.groups()
    repo_q = f'repo:{owner}/{repo_name}'

    session = _make_session(token)
    base = f'{GITHUB_API}/repos/{owner}/{repo_name}'

    # ── repo info (stars, forks) ──────────────────────────────────────────────
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(base, timeout=30)
    r.raise_for_status()
    repo_data = r.json()
    star_count = repo_data.get('stargazers_count', 0)
    fork_count = repo_data.get('forks_count', 0)

    # ── commits ───────────────────────────────────────────────────────────────
    # per_page=1 so last-page number == total commit count on default branch
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(f'{base}/commits', params={'per_page': 1}, timeout=30)
    r.raise_for_status()
    last_page = _link_last_page(r)
    commits = r.json()
    commit_count = last_page if last_page is not None else (1 if commits else 0)

    last_commit_hash = ''
    last_commit_timestamp = None
    if commits:
        last_commit_hash = commits[0]['sha']
        last_commit_timestamp = _parse_dt(commits[0]['commit']['committer']['date'])

    # ── pull-request counts (GitHub Search API gives exact totals) ────────────
    open_pr_count   = _search_total(session, f'{repo_q} type:pr is:open')
    merged_pr_count = _search_total(session, f'{repo_q} type:pr is:merged')

    # ── last PR submitted (newest created_at across all states) ───────────────
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(f'{base}/pulls',
                    params={'state': 'all', 'sort': 'created', 'direction': 'desc', 'per_page': 1},
                    timeout=30)
    r.raise_for_status()
    newest_pr = r.json()
    last_pr_submitted_at = _parse_dt(newest_pr[0]['created_at']) if newest_pr else None

    # ── last PR closed/merged ─────────────────────────────────────────────────
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(f'{base}/pulls',
                    params={'state': 'closed', 'sort': 'updated', 'direction': 'desc', 'per_page': 1},
                    timeout=30)
    r.raise_for_status()
    newest_closed_pr = r.json()
    last_pr_closed_at = (
        _parse_dt(newest_closed_pr[0].get('closed_at')) if newest_closed_pr else None
    )

    # ── issue counts (Search API excludes PRs, gives exact totals) ───────────
    open_issue_count   = _search_total(session, f'{repo_q} type:issue is:open')
    closed_issue_count = _search_total(session, f'{repo_q} type:issue is:closed')

    # ── last issue submitted (newest created_at, non-PR) ─────────────────────
    # Use the Search API so we never accidentally pick up a PR
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(
        f'{GITHUB_API}/search/issues',
        params={'q': f'{repo_q} type:issue', 'sort': 'created', 'order': 'desc', 'per_page': 1},
        timeout=30,
    )
    r.raise_for_status()
    newest_issue = r.json().get('items', [])
    last_issue_submitted_at = _parse_dt(newest_issue[0]['created_at']) if newest_issue else None

    # ── last issue closed ─────────────────────────────────────────────────────
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(
        f'{GITHUB_API}/search/issues',
        params={'q': f'{repo_q} type:issue is:closed', 'sort': 'updated', 'order': 'desc', 'per_page': 1},
        timeout=30,
    )
    r.raise_for_status()
    newest_closed_issue = r.json().get('items', [])
    last_issue_closed_at = (
        _parse_dt(newest_closed_issue[0].get('closed_at')) if newest_closed_issue else None
    )

    # ── PR authors (most-recent 100 PRs) ─────────────────────────────────────
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(f'{base}/pulls',
                    params={'state': 'all', 'sort': 'created', 'direction': 'desc', 'per_page': 100},
                    timeout=30)
    r.raise_for_status()
    seen: set[str] = set()
    pr_authors: list[str] = []
    for pr in r.json():
        login = (pr.get('user') or {}).get('login', '')
        if login and login not in seen:
            seen.add(login)
            pr_authors.append(login)

    # ── issue authors (most-recent 100 issues, PRs excluded) ─────────────────
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(f'{base}/issues',
                    params={'state': 'all', 'sort': 'created', 'direction': 'desc', 'per_page': 100},
                    timeout=30)
    r.raise_for_status()
    seen = set()
    issue_authors: list[str] = []
    for issue in r.json():
        if 'pull_request' in issue:
            continue
        login = (issue.get('user') or {}).get('login', '')
        if login and login not in seen:
            seen.add(login)
            issue_authors.append(login)

    # ── commit authors / contributors (top 100 by contribution count) ─────────
    time.sleep(GITHUB_API_SLEEP)
    r = session.get(f'{base}/contributors', params={'per_page': 100}, timeout=30)
    r.raise_for_status()
    commit_authors = [
        c['login'] for c in r.json()
        if isinstance(c, dict) and c.get('login')
    ]

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
    }
