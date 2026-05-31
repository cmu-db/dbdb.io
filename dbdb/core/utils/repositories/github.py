from __future__ import annotations

import re

import requests

from .base import RepoCollector, SnapshotData


class GitHubCollector(RepoCollector):
    """Collect repository metadata from the GitHub REST API v3."""

    URL_PATTERN = re.compile(r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$')
    API_SLEEP   = 10   # seconds between requests (avoids secondary rate limits)

    _API = 'https://api.github.com'

    def _make_session(self, token: str | None) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        })
        if token:
            s.headers['Authorization'] = f'Bearer {token}'
        return s

    def _search_total(self, query: str) -> int:
        """Use the GitHub Search API to get an exact issue/PR count."""
        r = self._get(f'{self._API}/search/issues', q=query, per_page=1)
        return r.json().get('total_count', 0)

    def get_metadata(self, repo_url: str) -> SnapshotData:
        match = self.URL_PATTERN.search(repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        owner, repo_name = match.groups()
        repo_q = f'repo:{owner}/{repo_name}'

        self.log.debug("Fetching GitHub metadata for %s/%s (%s)",
                       owner, repo_name,
                       "with token" if self.token else "no token — rate limits apply")

        base = f'{self._API}/repos/{owner}/{repo_name}'
        snap = SnapshotData()

        # ── repo info (stars, forks, default branch) ──────────────────────
        try:
            r = self._get(base)
            d = r.json()
            snap.star_count          = d.get('stargazers_count', 0)
            snap.fork_count          = d.get('forks_count', 0)
            snap.branch_default_name = d.get('default_branch', '')
        except Exception as exc:
            snap.errors.append(exc)

        # ── commits (count + last hash/timestamp) ─────────────────────────
        try:
            r = self._get(f'{base}/commits', per_page=1)
            last_page = self._link_last_page(r)
            commits   = r.json()
            snap.commit_count = last_page if last_page is not None else (1 if commits else 0)
            if commits:
                snap.last_commit_hash      = commits[0]['sha']
                snap.last_commit_timestamp = self._parse_dt(
                    commits[0]['commit']['committer']['date']
                )
        except Exception as exc:
            snap.errors.append(exc)

        # ── PR counts (Search API gives exact totals) ─────────────────────
        try:
            snap.open_pr_count = self._search_total(f'{repo_q} type:pr is:open')
        except Exception as exc:
            snap.errors.append(exc)

        try:
            snap.merged_pr_count = self._search_total(f'{repo_q} type:pr is:merged')
        except Exception as exc:
            snap.errors.append(exc)

        # ── last PR submitted ─────────────────────────────────────────────
        try:
            r = self._get(f'{base}/pulls',
                          state='all', sort='created', direction='desc', per_page=1)
            prs = r.json()
            snap.last_pr_submitted_at = self._parse_dt(prs[0]['created_at']) if prs else None
        except Exception as exc:
            snap.errors.append(exc)

        # ── last PR closed/merged ─────────────────────────────────────────
        try:
            r = self._get(f'{base}/pulls',
                          state='closed', sort='updated', direction='desc', per_page=1)
            closed_prs = r.json()
            snap.last_pr_closed_at = (
                self._parse_dt(closed_prs[0].get('closed_at')) if closed_prs else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── issue counts (Search API excludes PRs) ────────────────────────
        try:
            snap.open_issue_count = self._search_total(f'{repo_q} type:issue is:open')
        except Exception as exc:
            snap.errors.append(exc)

        try:
            snap.closed_issue_count = self._search_total(f'{repo_q} type:issue is:closed')
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue submitted ──────────────────────────────────────────
        try:
            r = self._get(
                f'{self._API}/search/issues',
                q=f'{repo_q} type:issue', sort='created', order='desc', per_page=1,
            )
            items = r.json().get('items', [])
            snap.last_issue_submitted_at = self._parse_dt(items[0]['created_at']) if items else None
        except Exception as exc:
            snap.errors.append(exc)

        # ── last issue closed ─────────────────────────────────────────────
        try:
            r = self._get(
                f'{self._API}/search/issues',
                q=f'{repo_q} type:issue is:closed', sort='updated', order='desc', per_page=1,
            )
            items = r.json().get('items', [])
            snap.last_issue_closed_at = (
                self._parse_dt(items[0].get('closed_at')) if items else None
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── PR authors (most-recent 100) ──────────────────────────────────
        try:
            r = self._get(f'{base}/pulls',
                          state='all', sort='created', direction='desc', per_page=100)
            snap.pr_authors = self._collect_unique(
                r.json(), lambda pr: (pr.get('user') or {}).get('login', '')
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── issue authors (most-recent 100, PRs excluded) ─────────────────
        try:
            r = self._get(f'{base}/issues',
                          state='all', sort='created', direction='desc', per_page=100)
            snap.issue_authors = self._collect_unique(
                [i for i in r.json() if 'pull_request' not in i],
                lambda i: (i.get('user') or {}).get('login', ''),
            )
        except Exception as exc:
            snap.errors.append(exc)

        # ── commit authors / contributors (top 100) ───────────────────────
        try:
            r = self._get(f'{base}/contributors', per_page=100)
            snap.commit_authors = [
                c['login'] for c in r.json()
                if isinstance(c, dict) and c.get('login')
            ]
        except Exception as exc:
            snap.errors.append(exc)

        # ── branches (count via per_page=1, names via per_page=100) ───────
        try:
            r = self._get(f'{base}/branches', per_page=1)
            last_page = self._link_last_page(r)
            snap.branch_count = last_page if last_page is not None else len(r.json())
        except Exception as exc:
            snap.errors.append(exc)

        try:
            r = self._get(f'{base}/branches', per_page=100)
            snap.branch_name = [b['name'] for b in r.json() if b.get('name')]
        except Exception as exc:
            snap.errors.append(exc)

        return snap
