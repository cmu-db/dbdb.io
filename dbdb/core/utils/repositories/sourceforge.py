from __future__ import annotations

import re

import requests

from .base import RepoCollector, SnapshotData


class SourceForgeCollector(RepoCollector):
    """Collect repository metadata from the SourceForge / Allura REST API.

    SourceForge exposes no git commit counts or branch lists via REST.
    Those fields (commit_count, branch_count, branch_names, last_commit_hash,
    last_commit_timestamp, open_pr_count, merged_pr_count) will always be
    None/empty — this is expected behaviour, not an error.

    Authentication: set SOURCEFORGE_API_TOKEN in Django settings if available.
    Public projects require no token; the token is passed as ?access_token=.
    """

    # Matches both sourceforge.net/projects/{name} and sourceforge.net/p/{name}
    URL_PATTERN = re.compile(r'sourceforge\.net/(?:projects|p)/([^/\s]+)', re.IGNORECASE)
    API_SLEEP   = 1   # conservative — SourceForge has no documented rate limit

    _API = 'https://sourceforge.net/rest'

    def _make_session(self, token: str | None) -> requests.Session:
        s = requests.Session()
        # Token is passed per-request as a query param, not a header.
        # Store it so _get_sf() can inject it.
        self._token = token
        return s

    def _get_sf(self, url: str, **params) -> requests.Response:
        """Like _get() but injects access_token if set."""
        if self._token:
            params['access_token'] = self._token
        return self._get(url, **params)

    def get_metadata(self, repo_url: str) -> SnapshotData:
        match = self.URL_PATTERN.search(repo_url)
        if not match:
            raise ValueError(f"Invalid SourceForge URL: {repo_url}")
        shortname = match.group(1).lower()

        self.log.debug("Fetching SourceForge metadata for %s (%s)",
                       shortname,
                       "with token" if self.token else "no token")

        base    = f'{self._API}/p/{shortname}'
        tickets = f'{base}/tickets'
        snap    = SnapshotData()

        # ── project info (forks) ──────────────────────────────────────────
        try:
            r = self._get_sf(f'{self._API}/p/{shortname}')
            proj = r.json().get('project') or r.json()
            snap.fork_count = len(proj.get('forks') or [])
        except Exception as exc:
            snap.errors.append(exc)

        # ── commit authors via local git clone (all branches) ────────────
        try:
            self.clone_url(repo_url, all_branches=True)
            snap.commit_authors = self.get_all_author_emails()
        except Exception as exc:
            snap.errors.append(exc)

        # ── open issue count ──────────────────────────────────────────────
        try:
            r = self._get_sf(tickets, limit=1, q='!status:closed')
            snap.open_issue_count = r.json().get('count', 0)
        except Exception as exc:
            snap.errors.append(exc)

        # ── closed issue count ────────────────────────────────────────────
        try:
            r = self._get_sf(tickets, limit=1, q='status:closed')
            snap.closed_issue_count = r.json().get('count', 0)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue submitted ──────────────────────────────────────────
        try:
            r = self._get_sf(tickets, limit=1, sort='created_date desc')
            items = r.json().get('tickets', [])
            snap.last_issue_submitted_at = (
                self._parse_dt(items[0].get('created_date')) if items else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue closed ─────────────────────────────────────────────
        try:
            r = self._get_sf(tickets, limit=1, q='status:closed', sort='mod_date desc')
            items = r.json().get('tickets', [])
            snap.last_issue_closed_at = (
                self._parse_dt(items[0].get('mod_date')) if items else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # Note: star_count, commit_count, branch_*, last_commit_*, open_pr_count,
        # merged_pr_count are not available via the SourceForge REST API and
        # remain at their SnapshotData defaults (None / 0 / '').

        return snap
