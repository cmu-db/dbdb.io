from __future__ import annotations

import re
from urllib.parse import quote

import requests

from .base import RepoCollector, SnapshotData


class GitLabCollector(RepoCollector):
    """Collect repository metadata from the GitLab REST API v4."""

    URL_PATTERN = re.compile(r'gitlab\.com/(.+?)(?:\.git)?/?$')
    API_SLEEP   = 0

    _API = 'https://gitlab.com/api/v4'

    def _make_session(self, token: str | None) -> requests.Session:
        s = requests.Session()
        if token:
            s.headers['PRIVATE-TOKEN'] = token
        return s

    @staticmethod
    def _gl_total(response: requests.Response) -> int:
        """Read X-Total header; return 0 if absent or non-numeric."""
        val = response.headers.get('X-Total', '').strip()
        return int(val) if val else 0

    def get_metadata(self, repo_url: str) -> SnapshotData:
        match = self.URL_PATTERN.search(repo_url)
        if not match:
            raise ValueError(f"Invalid GitLab URL: {repo_url}")
        project_path = match.group(1)
        encoded_path = quote(project_path, safe='')

        self.log.debug("Fetching GitLab metadata for %s (%s)",
                       project_path,
                       "with token" if self.token else "no token — statistics endpoint unavailable")

        base = f'{self._API}/projects/{encoded_path}'
        snap = SnapshotData()

        # ── project info (stars, forks, default branch, commit count via statistics) ─
        try:
            r = self._get(base, statistics='true')
            proj = r.json()
            snap.star_count          = proj.get('star_count', 0)
            snap.fork_count          = proj.get('forks_count', 0)
            snap.branch_default_name = proj.get('default_branch', '')
            stats = proj.get('statistics') or {}
            if stats.get('commit_count') is not None:
                snap.commit_count = stats['commit_count']
                self.log.debug("%s: commit_count=%d (from project statistics)",
                               project_path, snap.commit_count)
            else:
                self.log.debug("%s: project statistics not returned — "
                               "token may lack Reporter+ access", project_path)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last commit (hash, timestamp) ─────────────────────────────────
        try:
            r = self._get(f'{base}/repository/commits', per_page=1)
            commits = r.json()
            if commits:
                c = commits[0]
                snap.last_commit_hash      = c.get('id', '')
                snap.last_commit_timestamp = self._parse_dt(
                    c.get('committed_date') or c.get('authored_date')
                )
        except Exception as exc:
            snap.errors.append(exc)

        # ── commit count (pagination=legacy fallback if statistics didn't provide it) ─
        if snap.commit_count is None:
            try:
                r = self._get(f'{base}/repository/commits', per_page=1, pagination='legacy')
                snap.commit_count = self._gl_total(r)
                self.log.debug("%s: commit_count=%s (from X-Total header, pagination=legacy)",
                               project_path, snap.commit_count or 'not provided by GitLab')
            except Exception as exc:
                snap.errors.append(exc)

        # ── merge-request counts ──────────────────────────────────────────
        try:
            r = self._get(f'{base}/merge_requests', state='opened', per_page=1)
            snap.open_pr_count = self._gl_total(r)
        except Exception as exc:
            snap.errors.append(exc)

        try:
            r = self._get(f'{base}/merge_requests', state='merged', per_page=1)
            snap.merged_pr_count = self._gl_total(r)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last MR submitted ─────────────────────────────────────────────
        try:
            r = self._get(f'{base}/merge_requests',
                          state='all', order_by='created_at', sort='desc', per_page=1)
            mrs = r.json()
            snap.last_pr_submitted_at = self._parse_dt(mrs[0]['created_at']) if mrs else None
        except Exception as exc:
            snap.errors.append(exc)

        # ── last MR closed/merged ─────────────────────────────────────────
        try:
            r = self._get(f'{base}/merge_requests',
                          state='merged', order_by='updated_at', sort='desc', per_page=1)
            closed_mrs = r.json()
            if closed_mrs:
                snap.last_pr_closed_at = self._parse_dt(
                    closed_mrs[0].get('merged_at') or closed_mrs[0].get('closed_at')
                )
        except Exception as exc:
            snap.errors.append(exc)

        # ── issue counts ──────────────────────────────────────────────────
        try:
            r = self._get(f'{base}/issues', state='opened', per_page=1)
            snap.open_issue_count = self._gl_total(r)
        except Exception as exc:
            snap.errors.append(exc)

        try:
            r = self._get(f'{base}/issues', state='closed', per_page=1)
            snap.closed_issue_count = self._gl_total(r)
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue submitted ──────────────────────────────────────────
        try:
            r = self._get(f'{base}/issues',
                          state='all', order_by='created_at', sort='desc', per_page=1)
            issues = r.json()
            snap.last_issue_submitted_at = (
                self._parse_dt(issues[0]['created_at']) if issues else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue closed ─────────────────────────────────────────────
        try:
            r = self._get(f'{base}/issues',
                          state='closed', order_by='updated_at', sort='desc', per_page=1)
            closed_issues = r.json()
            snap.last_issue_closed_at = (
                self._parse_dt(closed_issues[0].get('closed_at')) if closed_issues else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── MR authors (most-recent 100) ──────────────────────────────────
        try:
            r = self._get(f'{base}/merge_requests',
                          state='all', order_by='created_at', sort='desc', per_page=100)
            snap.pr_authors = self._collect_unique(
                r.json(),
                lambda mr: (
                    (mr.get('author') or {}).get('username') or
                    (mr.get('author') or {}).get('name', '')
                ),
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── issue authors (most-recent 100) ───────────────────────────────
        try:
            r = self._get(f'{base}/issues',
                          state='all', order_by='created_at', sort='desc', per_page=100)
            snap.issue_authors = self._collect_unique(
                r.json(),
                lambda i: (
                    (i.get('author') or {}).get('username') or
                    (i.get('author') or {}).get('name', '')
                ),
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── commit authors via local git clone (all branches) ────────────
        try:
            self.clone_url(repo_url, all_branches=True)
            snap.commit_authors = self.get_author_emails(snap.branch_default_name or None)
        except Exception as exc:
            snap.errors.append(exc)

        # ── branches (count from X-Total, names from first 100) ───────────
        try:
            r = self._get(f'{base}/repository/branches', per_page=100)
            snap.branch_count = self._gl_total(r)
            snap.branch_names = [b['name'] for b in r.json() if b.get('name')]
        except Exception as exc:
            snap.errors.append(exc)

        return snap
