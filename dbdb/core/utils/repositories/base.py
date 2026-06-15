from __future__ import annotations

import dataclasses
import logging
import os
import re
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar

import requests
from django.conf import settings

# Trailer keys recognised as agent-attribution signals in commit messages.
# The regex captures the value after the colon on each matching line so we
# can search only those values rather than free-form message prose.
# Covers patterns used by: Claude Code, GitHub Copilot, Cursor, Aider,
# Devin, Windsurf/Codeium, and generic AI tooling.
_AGENT_TRAILER_RE = re.compile(
    r'^(?:'
    r'co-authored?-by'      # Co-authored-by / Co-author-by  (Claude Code, Copilot, Cursor …)
    r'|made-with'           # Made-with  (Cursor, generic)
    r'|generated-(?:by|with)'  # Generated-by / Generated-with
    r'|powered-by'          # Powered-by  (some tools)
    r'|ai-author'           # AI-Author
    r'|signed-off-by'       # Signed-off-by  (Aider uses this)
    r')\s*:(.+)$',
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class SnapshotData:
    """
    Typed return value for every RepoCollector.get_metadata() implementation.
    All fields match RepositorySnapshot model field names so the result can be
    passed directly to RepositorySnapshot.objects.create(**snap.to_model_kwargs()).
    """
    # Commit statistics
    commit_count:          int | None      = None
    last_commit_hash:      str             = ''
    last_commit_timestamp: datetime | None = None

    # Pull-request / merge-request statistics
    open_pr_count:      int             = 0
    merged_pr_count:    int             = 0
    last_pr_submitted_at: datetime | None = None
    last_pr_closed_at:    datetime | None = None

    # Issue statistics
    open_issue_count:      int             = 0
    closed_issue_count:    int             = 0
    last_issue_submitted_at: datetime | None = None
    last_issue_closed_at:    datetime | None = None

    # Branch statistics
    branch_count:        int | None  = None
    branch_default_name: str         = ''
    branch_names:        list[str]   = field(default_factory=list)

    # Popularity
    fork_count: int = 0
    star_count: int = 0

    # Contributor lists (up to 100 each)
    commit_authors: list[str] = field(default_factory=list)
    pr_authors:     list[str] = field(default_factory=list)
    issue_authors:  list[str] = field(default_factory=list)

    # Archival status (GitHub only; None means not archived or unknown)
    archival_timestamp: datetime | None = None

    # Errors accumulated during collection (never written to the model)
    errors: list[Exception] = field(default_factory=list)

    # ── convenience ───────────────────────────────────────────────────────

    @property
    def has_data(self) -> bool:
        """True if any substantive field was populated.
        Used to distinguish ERROR (partial data) from FAILED (nothing at all).
        """
        return any([
            self.star_count, self.fork_count, self.commit_count,
            self.last_commit_hash, self.last_commit_timestamp,
            self.open_pr_count, self.merged_pr_count,
            self.open_issue_count, self.closed_issue_count,
            self.commit_authors, self.pr_authors, self.issue_authors,
        ])

    def to_model_kwargs(self) -> dict:
        """Return all fields except 'errors', suitable for
        RepositorySnapshot.objects.create(**snap.to_model_kwargs()).
        """
        return {
            f.name: getattr(self, f.name)
            for f in dataclasses.fields(self)
            if f.name != 'errors'
        }


class RepoCollector(ABC):
    """
    Abstract base class for all repository metadata collectors.

    Subclasses must define:
        URL_PATTERN  – compiled regex that matches URLs for this host
        _make_session(token) – return an authenticated requests.Session
        get_metadata(repo_url) – fetch and return a SnapshotData

    Shared utilities available to all subclasses:
        _get(url, **params)      – sleep-then-GET with raise_for_status
        _parse_dt(s)             – ISO-8601 string → UTC datetime
        _link_last_page(r)       – parse Link header for last page number
        _collect_unique(items, key_fn) – deduplicated list from API objects
    """

    URL_PATTERN: ClassVar[re.Pattern]
    API_SLEEP:   ClassVar[int] = 10      # seconds to sleep before each request

    # Email suffixes to skip during get_author_emails(). Subclasses may
    # extend this list with host-specific noreply domains.
    IGNORED_EMAIL_SUFFIXES: ClassVar[tuple[str, ...]] = (
        # '@users.noreply.github.com',
    )

    # Branch name prefixes to skip during get_author_emails(). Refs whose
    # short name starts with any of these are excluded from the walk.
    IGNORED_BRANCH_PREFIXES: ClassVar[tuple[str, ...]] = (
        'dependabot',
    )

    @property
    def _CLONE_ROOT(self) -> str:
        return settings.DBDB_SOURCEREPO_DIRECTORY.rstrip('/')

    def __init__(self, token: str | None = None, *, delete_on_exit: bool = False) -> None:
        self.token = token
        self.delete_on_exit = delete_on_exit
        self.session = self._make_session(token)
        self.log = logging.getLogger(type(self).__module__)
        self._repo_dir: str | None = None
        self._repo = None  # git.Repo once clone_url() is called

    def __del__(self) -> None:
        repo_dir = getattr(self, '_repo_dir', None)
        if repo_dir and self.delete_on_exit and os.path.isdir(repo_dir):
            self.log.debug("__del__: removing cloned repository at %s", repo_dir)
            shutil.rmtree(repo_dir, ignore_errors=True)
            self._repo_dir = None

    @abstractmethod
    def _make_session(self, token: str | None) -> requests.Session: ...

    @abstractmethod
    def get_metadata(self, repo_url: str) -> SnapshotData: ...

    @abstractmethod
    def get_commit_url(self, branch: str, commit: str) -> str:
        """Return the web URL for a specific commit on this platform.

        *branch* is the branch the commit belongs to; some platforms
        include it in the URL path.  *commit* is the full commit SHA.
        """
        ...

    @classmethod
    def match_url(cls, url: str) -> bool:
        """Return True if this collector handles the given URL."""
        return bool(cls.URL_PATTERN.search(url))

    # ── git clone / local repo helpers ───────────────────────────────────

    def fetch_latest(self) -> None:
        """Fetch the latest commits from all remotes in the locally cloned repository."""
        self.log.debug("fetch_latest: fetching all remotes in %s", self._repo_dir)
        self._repo.git.fetch('--all')
        self.log.debug("fetch_latest: fetch complete")

    def clone_url(
        self,
        url: str,
        *,
        depth: int | None = None,
        commit: str | None = None,
        all_branches: bool = False,
        pull: bool = False,
    ) -> None:
        """Clone or fetch *url* into /tmp/dbdb/<reponame> using gitpython.

        If the directory already exists it is reused without re-cloning.
        Pass pull=True to fetch the latest commits when reusing an existing clone.
        Call with commit=<sha> to do a shallow fetch of a single commit.
        Call with all_branches=True to clone every branch (for email harvesting).
        The clone is only removed on instance destruction when delete_on_exit=True.
        """
        import git as gitpkg

        # Derive a stable name from the last path component of the URL.
        name = url.rstrip('/').split('/')[-1]
        if name.endswith('.git'):
            name = name[:-4]
        repo_dir = os.path.join(self._CLONE_ROOT, name)
        os.makedirs(self._CLONE_ROOT, exist_ok=True)

        self._repo_dir = repo_dir

        if os.path.isdir(repo_dir):
            self.log.debug("clone_url: reusing existing clone at %s", repo_dir)
            self._repo = gitpkg.Repo(repo_dir)
            if pull:
                self.fetch_latest()
            return

        self.log.debug(f"clone_url: cloning repo to {repo_dir}")

        # Disable all interactive credential prompts. Any URL that requires
        # authentication will cause git to exit non-zero immediately, which
        # gitpython raises as GitCommandError — treated as unavailable/dead.
        no_prompt = {'GIT_TERMINAL_PROMPT': '0'}
        if commit:
            self.log.debug("clone_url: bare init + shallow fetch commit %s from %s", commit, url)
            os.makedirs(repo_dir)
            self._repo = gitpkg.Repo.init(repo_dir)
            self._repo.git.update_environment(**no_prompt)
            depth_arg = f'--depth={depth}' if depth is not None else '--depth=1'
            self._repo.git.fetch(depth_arg, url, commit)
            self.log.debug("clone_url: fetched commit %s", commit)
        else:
            clone_kwargs: dict = {'env': no_prompt}
            if depth is not None:
                clone_kwargs['depth'] = depth
            if all_branches:
                clone_kwargs['no_single_branch'] = True
            self.log.debug("clone_url: cloning %s (all_branches=%s, depth=%s)", url, all_branches, depth)
            self._repo = gitpkg.Repo.clone_from(url, repo_dir, **clone_kwargs)
            self.log.debug("clone_url: clone complete, %d refs", len(list(self._repo.references)))

    def get_commit_metadata(self, commit_id: str) -> tuple[str, datetime]:
        """Return (message, timestamp) for a specific commit in self._repo."""
        self.log.debug("get_commit_metadata: resolving commit %s", commit_id)
        commit = self._repo.commit(commit_id)
        message = commit.message.rstrip()
        timestamp = datetime.fromtimestamp(commit.committed_date, tz=UTC)
        self.log.debug("get_commit_metadata: timestamp=%s message=%r", timestamp, message[:80])
        return message, timestamp

    def get_readme(self) -> str | None:
        """Return the contents of README.md from the root of the cloned repository, or None."""
        if not self._repo_dir:
            return None
        readme_path = os.path.join(self._repo_dir, 'README.md')
        if not os.path.isfile(readme_path):
            return None
        with open(readme_path, encoding='utf-8', errors='replace') as fh:
            return fh.read()

    def get_first_commit_timestamp(self) -> datetime | None:
        """Return the timestamp of the earliest commit across all branches in self._repo."""
        refs = list(self._repo.references)
        self.log.debug("get_first_commit_timestamp: scanning %d refs", len(refs))
        seen: set[str] = set()
        earliest: datetime | None = None
        for ref in refs:
            for commit in self._repo.iter_commits(ref):
                if commit.hexsha in seen:
                    continue
                seen.add(commit.hexsha)
                ts = datetime.fromtimestamp(commit.committed_date, tz=UTC)
                if earliest is None or ts < earliest:
                    earliest = ts
        self.log.debug("get_first_commit_timestamp: earliest=%s (across %d unique commits)", earliest, len(seen))
        return earliest

    def get_author_emails(self, branch: str | None = None) -> list[str]:
        """Return unique author emails from commits in the cloned repository.

        If *branch* is given, only commits reachable from that branch are
        walked. If *branch* is None, all refs are walked.
        Emails ending with any suffix in IGNORED_EMAIL_SUFFIXES are skipped.
        """
        if branch:
            if branch.startswith(self.IGNORED_BRANCH_PREFIXES):
                self.log.debug("get_author_emails: skipping ignored branch %r", branch)
                return []
            refs = [self._repo.refs[branch]]
            self.log.debug("get_author_emails: walking branch %r", branch)
        else:
            refs = [
                r for r in self._repo.references
                if not r.name.startswith(self.IGNORED_BRANCH_PREFIXES)
            ]
            self.log.debug("get_author_emails: walking %d refs", len(refs))
        seen: set[str] = set()
        result: list[str] = []
        ignored = 0
        for ref in refs:
            for commit in self._repo.iter_commits(ref):
                email = commit.author.email
                if not email or email in seen:
                    continue
                if email.endswith(self.IGNORED_EMAIL_SUFFIXES):
                    self.log.debug("get_author_emails: ignoring %s", email)
                    ignored += 1
                    continue
                seen.add(email)
                result.append(email)
        self.log.debug(
            "get_author_emails: found %d unique author emails (%d ignored)",
            len(result), ignored,
        )
        return result

    @property
    def _origin_url(self) -> str:
        """HTTPS URL of the origin remote, normalising SSH remote URLs.

        Converts ``git@github.com:owner/repo.git`` to
        ``https://github.com/owner/repo`` so subclasses can apply their
        URL_PATTERN uniformly regardless of how the repo was cloned.
        """
        url = self._repo.remotes.origin.url
        url = re.sub(r'^git@([^:]+):(.+?)(?:\.git)?$', r'https://\1/\2', url)
        return url.rstrip('/')

    def get_coding_agent_commits(
        self, branch: str | None = None
    ) -> 'dict[AttributeOption, str]':
        """Scan commits for AI coding-agent co-authorship and return latest hits.

        Checks two things per commit:
          1. The commit author name (for repos where the agent is the literal author).
          2. Values of recognised agent-attribution trailers in the commit message:
               Co-authored-by, Co-author, Made-with, Generated-by, Generated-with,
               Powered-by, Ai-author, Signed-off-by.

        The search is *not* a free-text scan of the whole message; only the trailer
        values are matched.  This avoids false positives from commit messages that
        happen to mention an agent name (e.g. "add cursor-based pagination").

        Args:
            branch: If given, only commits reachable from that branch are
                    scanned.  If None, all refs are walked.

        Returns:
            A dict mapping AttributeOption → hexsha of the latest commit where
            that agent appears as author or co-author.  Agents with no matching
            commit are omitted.
        """
        from dbdb.core.models import AttributeOption

        agents = list(
            AttributeOption.objects
            .filter(attribute__slug='agent')
            .select_related('attribute')
        )
        if not agents:
            return {}

        agent_patterns: dict = {
            agent: re.compile(re.escape(agent.slug), re.IGNORECASE)
            for agent in agents
        }

        if branch:
            refs = [self._repo.refs[branch]]
            self.log.debug("get_coding_agent_commits: scanning branch %r", branch)
        else:
            refs = list(self._repo.references)
            self.log.debug("get_coding_agent_commits: scanning %d refs", len(refs))

        # agent -> (committed_date, hexsha) for the best (latest) match found
        best: dict = {}
        seen: set[str] = set()

        for ref in refs:
            for commit in self._repo.iter_commits(ref):
                if commit.hexsha in seen:
                    continue
                seen.add(commit.hexsha)

                # Build candidate text from author name and recognised trailer values only.
                # _AGENT_TRAILER_RE extracts the value portion (after the colon) of each
                # matching trailer line so we never match free-form message prose.
                trailer_values = _AGENT_TRAILER_RE.findall(commit.message)
                candidate = commit.author.name + '\n' + '\n'.join(trailer_values)

                for agent, pattern in agent_patterns.items():
                    if not pattern.search(candidate):
                        continue
                    date = commit.committed_date
                    if agent not in best or date > best[agent][0]:
                        best[agent] = (date, commit.hexsha)

        result = {agent: hexsha for agent, (_, hexsha) in best.items()}
        self.log.debug(
            "get_coding_agent_commits: found %d agent(s): %s",
            len(result),
            ', '.join(a.slug for a in result),
        )
        return result

    # ── shared request helper ─────────────────────────────────────────────

    def _get(self, url: str, **params) -> requests.Response:
        """Sleep (API_SLEEP seconds), then GET url, then raise on non-2xx."""
        if self.API_SLEEP:
            time.sleep(self.API_SLEEP)
        r = self.session.get(url, params=params or None, timeout=30)
        r.raise_for_status()
        return r

    # ── shared static utilities ───────────────────────────────────────────

    @staticmethod
    def _parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(UTC)

    @staticmethod
    def _link_last_page(response: requests.Response) -> int | None:
        """Parse the Link header to get the last page number.
        When per_page=1 this equals the total item count.
        """
        link = response.headers.get('Link', '')
        m = re.search(r'<[^>]+[?&]page=(\d+)[^>]*>;\s*rel="last"', link)
        return int(m.group(1)) if m else None

    @staticmethod
    def _collect_unique(items: list, key_fn) -> list[str]:
        """Return a deduplicated list of non-empty strings produced by key_fn."""
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            val = key_fn(item)
            if val and val not in seen:
                seen.add(val)
                result.append(val)
        return result
