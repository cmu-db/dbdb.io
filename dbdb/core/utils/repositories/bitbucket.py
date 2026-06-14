from __future__ import annotations

import re

import requests

from .base import RepoCollector, SnapshotData


# Bitbucket issue statuses considered "open" vs "closed"
_OPEN_STATUSES   = ('new', 'open', 'on hold')
_CLOSED_STATUSES = ('resolved', 'closed', 'invalid', 'duplicate', 'wontfix')

_OPEN_Q   = ' OR '.join(f'status="{s}"' for s in _OPEN_STATUSES)
_CLOSED_Q = ' OR '.join(f'status="{s}"' for s in _CLOSED_STATUSES)


class BitbucketCollector(RepoCollector):
    """Collect repository metadata from the Bitbucket Cloud REST API v2.

    Authentication: set BITBUCKET_API_TOKEN in Django settings.
    Tokens can be:
      - A Bitbucket HTTP access token (Bearer)
      - A base64-encoded "username:app_password" (Basic) — prefix with "Basic "
    Unauthenticated requests work for public repos at reduced rate limits.

    Bitbucket paginated responses carry a `size` field for the total item count,
    so a single per-page-1 request returns both the total AND the first item.

    The issue tracker is optional per repo; all /issues calls are individually
    wrapped so a 404 simply leaves those fields at zero.
    """

    URL_PATTERN = re.compile(r'bitbucket\.org/([^/]+)/([^/]+?)(?:\.git)?/?$')
    API_SLEEP   = 0   # rate limits are enforced via HTTP 429

    _API = 'https://api.bitbucket.org/2.0'

    def _make_session(self, token: str | None) -> requests.Session:
        s = requests.Session()
        if token:
            if token.startswith('Basic '):
                s.headers['Authorization'] = token
            else:
                s.headers['Authorization'] = f'Bearer {token}'
        return s

    @staticmethod
    def _size(response: requests.Response) -> int:
        """Return the `size` field from a Bitbucket paginated response."""
        return response.json().get('size', 0)

    @staticmethod
    def _values(response: requests.Response) -> list:
        return response.json().get('values', [])

    def get_metadata(self, repo_url: str) -> SnapshotData:
        match = self.URL_PATTERN.search(repo_url)
        if not match:
            raise ValueError(f"Invalid Bitbucket URL: {repo_url}")
        workspace, repo_slug = match.groups()

        self.log.debug("Fetching Bitbucket metadata for %s/%s (%s)",
                       workspace, repo_slug,
                       "with token" if self.token else "no token — rate limits apply")

        base = f'{self._API}/repositories/{workspace}/{repo_slug}'
        snap = SnapshotData()

        # ── repo info (forks, default branch) ────────────────────────────
        try:
            r = self._get(base)
            d = r.json()
            snap.fork_count          = d.get('forks_count', 0)
            snap.branch_default_name = (d.get('mainbranch') or {}).get('name', '')
        except Exception as exc:
            snap.errors.append(exc)

        # ── watchers → star_count ─────────────────────────────────────────
        try:
            r = self._get(f'{base}/watchers', pagelen=1)
            snap.star_count = self._size(r)
        except Exception as exc:
            snap.errors.append(exc)

        # ── commits (count + last hash/timestamp) ─────────────────────────
        # Bitbucket never returns a `size` field for the commits endpoint.
        # Paginate with pagelen=100 and follow `next` links to count all commits.
        try:
            r = self._get(f'{base}/commits', pagelen=100)
            values = self._values(r)
            if values:
                snap.last_commit_hash      = values[0].get('hash', '')
                snap.last_commit_timestamp = self._parse_dt(values[0].get('date'))
            count = len(values)
            next_url = r.json().get('next')
            while next_url:
                r = self._get(next_url)
                count += len(self._values(r))
                next_url = r.json().get('next')
            snap.commit_count = count
        except Exception as exc:
            snap.errors.append(exc)

        # ── PR counts ─────────────────────────────────────────────────────
        try:
            r = self._get(f'{base}/pullrequests', state='OPEN', pagelen=1)
            snap.open_pr_count = self._size(r)
        except Exception as exc:
            snap.errors.append(exc)

        try:
            r = self._get(f'{base}/pullrequests', state='MERGED', pagelen=1)
            snap.merged_pr_count = self._size(r)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last PR submitted ─────────────────────────────────────────────
        try:
            r = self._get(f'{base}/pullrequests', sort='-created_on', pagelen=1)
            values = self._values(r)
            snap.last_pr_submitted_at = self._parse_dt(values[0]['created_on']) if values else None
        except Exception as exc:
            snap.errors.append(exc)

        # ── last PR closed/merged ─────────────────────────────────────────
        try:
            r = self._get(f'{base}/pullrequests',
                          state='MERGED', sort='-updated_on', pagelen=1)
            values = self._values(r)
            snap.last_pr_closed_at = self._parse_dt(values[0]['updated_on']) if values else None
        except Exception as exc:
            snap.errors.append(exc)

        # ── issue counts (issue tracker may be disabled → 404 is silenced) ─
        try:
            r = self._get(f'{base}/issues', pagelen=1, q=f'({_OPEN_Q})')
            snap.open_issue_count = self._size(r)
        except Exception as exc:
            snap.errors.append(exc)

        try:
            r = self._get(f'{base}/issues', pagelen=1, q=f'({_CLOSED_Q})')
            snap.closed_issue_count = self._size(r)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue submitted ──────────────────────────────────────────
        try:
            r = self._get(f'{base}/issues', sort='-created_on', pagelen=1)
            values = self._values(r)
            snap.last_issue_submitted_at = (
                self._parse_dt(values[0]['created_on']) if values else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue closed ─────────────────────────────────────────────
        try:
            r = self._get(f'{base}/issues',
                          q=f'({_CLOSED_Q})', sort='-updated_on', pagelen=1)
            values = self._values(r)
            snap.last_issue_closed_at = (
                self._parse_dt(values[0]['updated_on']) if values else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── branches ──────────────────────────────────────────────────────
        try:
            r = self._get(f'{base}/refs/branches', pagelen=1)
            snap.branch_count = self._size(r)
        except Exception as exc:
            snap.errors.append(exc)

        try:
            r = self._get(f'{base}/refs/branches', pagelen=100)
            snap.branch_names = [
                b['name'] for b in self._values(r) if b.get('name')
            ]
        except Exception as exc:
            snap.errors.append(exc)

        # ── PR authors (most-recent 100) ──────────────────────────────────
        try:
            r = self._get(f'{base}/pullrequests', sort='-created_on', pagelen=100)
            snap.pr_authors = self._collect_unique(
                self._values(r),
                lambda pr: (pr.get('author') or {}).get('display_name', ''),
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── issue authors (most-recent 100) ───────────────────────────────
        try:
            r = self._get(f'{base}/issues', sort='-created_on', pagelen=100)
            snap.issue_authors = self._collect_unique(
                self._values(r),
                lambda i: (i.get('reporter') or {}).get('display_name', ''),
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── commit authors via local git clone (all branches) ────────────
        try:
            self.clone_url(repo_url, all_branches=True)
            snap.commit_authors = self.get_author_emails(snap.branch_default_name or None)
        except Exception as exc:
            snap.errors.append(exc)

        return snap
