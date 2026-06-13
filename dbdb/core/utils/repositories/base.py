from __future__ import annotations

import dataclasses
import logging
import re
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar

import requests


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

    # Email suffixes to skip during get_all_author_emails(). Subclasses may
    # extend this list with host-specific noreply domains.
    IGNORED_EMAIL_SUFFIXES: ClassVar[tuple[str, ...]] = (
        # '@users.noreply.github.com',
    )

    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.session = self._make_session(token)
        self.log = logging.getLogger(type(self).__module__)
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self._repo = None  # git.Repo once clone_url() is called

    def __del__(self) -> None:
        tmpdir = getattr(self, '_tmpdir', None)
        if tmpdir is not None:
            self.log.debug("__del__: cleaning up temp directory")
            tmpdir.cleanup()
            self._tmpdir = None

    @abstractmethod
    def _make_session(self, token: str | None) -> requests.Session: ...

    @abstractmethod
    def get_metadata(self, repo_url: str) -> SnapshotData: ...

    @classmethod
    def match_url(cls, url: str) -> bool:
        """Return True if this collector handles the given URL."""
        return bool(cls.URL_PATTERN.search(url))

    # ── git clone / local repo helpers ───────────────────────────────────

    def clone_url(
        self,
        url: str,
        *,
        depth: int | None = None,
        commit: str | None = None,
        all_branches: bool = False,
    ) -> None:
        """Clone or fetch url into a managed temp directory using gitpython.

        Call with commit=<sha> to do a shallow fetch of a single commit.
        Call with all_branches=True to clone every branch (for email harvesting).
        Any previous temp directory is cleaned up before the new clone.
        """
        import git as gitpkg
        if self._tmpdir is not None:
            self.log.debug("clone_url: replacing existing temp directory for %s", url)
            self._tmpdir.cleanup()
        self._tmpdir = tempfile.TemporaryDirectory()
        # Disable all interactive credential prompts. Any URL that requires
        # authentication will cause git to exit non-zero immediately, which
        # gitpython raises as GitCommandError — treated as unavailable/dead.
        no_prompt = {'GIT_TERMINAL_PROMPT': '0'}
        if commit:
            self.log.debug("clone_url: bare init + shallow fetch commit %s from %s", commit, url)
            self._repo = gitpkg.Repo.init(self._tmpdir.name)
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
            self._repo = gitpkg.Repo.clone_from(url, self._tmpdir.name, **clone_kwargs)
            self.log.debug("clone_url: clone complete, %d refs", len(list(self._repo.references)))

    def get_commit_metadata(self, commit_id: str) -> tuple[str, datetime]:
        """Return (message, timestamp) for a specific commit in self._repo."""
        self.log.debug("get_commit_metadata: resolving commit %s", commit_id)
        commit = self._repo.commit(commit_id)
        message = commit.message.rstrip()
        timestamp = datetime.fromtimestamp(commit.committed_date, tz=UTC)
        self.log.debug("get_commit_metadata: timestamp=%s message=%r", timestamp, message[:80])
        return message, timestamp

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

    def get_all_author_emails(self) -> list[str]:
        """Return unique author emails from all commits across all refs.

        Emails ending with any suffix in IGNORED_EMAIL_SUFFIXES are skipped.
        """
        refs = list(self._repo.references)
        self.log.debug("get_all_author_emails: walking %d refs", len(refs))
        seen: set[str] = set()
        result: list[str] = []
        ignored = 0
        for ref in refs:
            for commit in self._repo.iter_commits(ref):
                email = commit.author.email
                if not email or email in seen:
                    continue
                if email.endswith(self.IGNORED_EMAIL_SUFFIXES):
                    self.log.debug("get_all_author_emails: ignoring %s", email)
                    ignored += 1
                    continue
                seen.add(email)
                result.append(email)
        self.log.debug(
            "get_all_author_emails: found %d unique author emails (%d ignored)",
            len(result), ignored,
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
