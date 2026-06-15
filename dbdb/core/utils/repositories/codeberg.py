from __future__ import annotations

import re

import requests

from .base import RepoCollector, SnapshotData


class CodebergCollector(RepoCollector):
    """Collect repository metadata from the Codeberg (Gitea) REST API v1."""

    URL_PATTERN = re.compile(r'codeberg\.org/([^/]+)/([^/]+?)(?:\.git)?/?$')
    API_SLEEP   = 0

    _API = 'https://codeberg.org/api/v1'

    def _make_session(self, token: str | None) -> requests.Session:
        s = requests.Session()
        s.headers['Accept'] = 'application/json'
        if token:
            s.headers['Authorization'] = f'token {token}'
        return s

    @staticmethod
    def _total(response: requests.Response) -> int:
        """Read X-Total-Count header; return 0 if absent or non-numeric."""
        val = response.headers.get('X-Total-Count', '').strip()
        return int(val) if val.isdigit() else 0

    def get_commit_url(self, branch: str, commit: str) -> str:
        match = self.URL_PATTERN.search(self._origin_url)
        owner, repo_name = match.groups()
        return f'https://codeberg.org/{owner}/{repo_name}/commit/{commit}'

    def get_metadata(self, repo_url: str) -> SnapshotData:
        match = self.URL_PATTERN.search(repo_url)
        if not match:
            raise ValueError(f"Invalid Codeberg URL: {repo_url}")
        owner, repo_name = match.groups()

        self.log.debug("Fetching Codeberg metadata for %s/%s (%s)",
                       owner, repo_name,
                       "with token" if self.token else "no token — rate limits apply")

        base = f'{self._API}/repos/{owner}/{repo_name}'
        snap = SnapshotData()

        # ── repo info (stars, forks, default branch, open issue/PR counts) ─
        try:
            r = self._get(base)
            d = r.json()
            snap.star_count          = d.get('stars_count', 0)
            snap.fork_count          = d.get('forks_count', 0)
            snap.branch_default_name = d.get('default_branch', '')
            snap.open_issue_count    = d.get('open_issues_count', 0)
            snap.open_pr_count       = d.get('open_pr_counter', 0)
        except Exception as exc:
            snap.errors.append(exc)

        # ── commits (count via Link header, last hash + timestamp) ─────────
        try:
            r = self._get(f'{base}/commits', limit=1, page=1)
            last_page = self._link_last_page(r)
            commits   = r.json()
            snap.commit_count = last_page if last_page is not None else (1 if commits else 0)
            if commits:
                snap.last_commit_hash      = commits[0].get('sha', '')
                snap.last_commit_timestamp = self._parse_dt(commits[0].get('created'))
        except Exception as exc:
            snap.errors.append(exc)

        # ── merged PR count (closed pulls — count via Link / X-Total-Count) ─
        try:
            r = self._get(f'{base}/pulls', state='closed', limit=1, page=1)
            snap.merged_pr_count = self._link_last_page(r) or self._total(r)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last PR submitted (all pulls, newest-first by default) ─────────
        try:
            r = self._get(f'{base}/pulls', state='all', limit=1, page=1)
            prs = r.json()
            snap.last_pr_submitted_at = self._parse_dt(prs[0].get('created') if prs else None)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last PR closed/merged ──────────────────────────────────────────
        try:
            r = self._get(f'{base}/pulls', state='closed', limit=1, page=1)
            prs = r.json()
            if prs:
                snap.last_pr_closed_at = self._parse_dt(
                    prs[0].get('merged') or prs[0].get('closed')
                )
        except Exception as exc:
            snap.errors.append(exc)

        # ── closed issue count ─────────────────────────────────────────────
        try:
            r = self._get(f'{base}/issues', type='issues', state='closed', limit=1, page=1)
            snap.closed_issue_count = self._link_last_page(r) or self._total(r)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue submitted (all issues, newest-first by default) ──────
        try:
            r = self._get(f'{base}/issues', type='issues', state='all', limit=1, page=1)
            issues = r.json()
            snap.last_issue_submitted_at = self._parse_dt(
                issues[0].get('created') if issues else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue closed ──────────────────────────────────────────────
        try:
            r = self._get(f'{base}/issues', type='issues', state='closed', limit=1, page=1)
            issues = r.json()
            snap.last_issue_closed_at = self._parse_dt(
                issues[0].get('closed') if issues else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── PR authors (most-recent 50) ────────────────────────────────────
        try:
            r = self._get(f'{base}/pulls', state='all', limit=50, page=1)
            snap.pr_authors = self._collect_unique(
                r.json(),
                lambda pr: (pr.get('user') or {}).get('login', ''),
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── issue authors (most-recent 50) ─────────────────────────────────
        try:
            r = self._get(f'{base}/issues', type='issues', state='all', limit=50, page=1)
            snap.issue_authors = self._collect_unique(
                r.json(),
                lambda i: (i.get('user') or {}).get('login', ''),
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── commit authors via local git clone (all branches) ────────────
        try:
            self.clone_url(repo_url, all_branches=True)
            snap.commit_authors = self.get_author_emails(snap.branch_default_name or None)
        except Exception as exc:
            snap.errors.append(exc)

        # ── branches (count + names) ───────────────────────────────────────
        try:
            r = self._get(f'{base}/branches', limit=1, page=1)
            snap.branch_count = self._link_last_page(r) or self._total(r)
        except Exception as exc:
            snap.errors.append(exc)

        try:
            r = self._get(f'{base}/branches', limit=100, page=1)
            snap.branch_names = [b['name'] for b in r.json() if b.get('name')]
        except Exception as exc:
            snap.errors.append(exc)

        return snap
