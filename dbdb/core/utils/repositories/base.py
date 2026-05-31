from __future__ import annotations

import dataclasses
import logging
import re
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
    branch_name:         list[str]   = field(default_factory=list)

    # Popularity
    fork_count: int = 0
    star_count: int = 0

    # Contributor lists (up to 100 each)
    commit_authors: list[str] = field(default_factory=list)
    pr_authors:     list[str] = field(default_factory=list)
    issue_authors:  list[str] = field(default_factory=list)

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
    API_SLEEP:   ClassVar[int] = 0       # seconds to sleep before each request

    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.session = self._make_session(token)
        self.log = logging.getLogger(type(self).__module__)

    @abstractmethod
    def _make_session(self, token: str | None) -> requests.Session: ...

    @abstractmethod
    def get_metadata(self, repo_url: str) -> SnapshotData: ...

    @classmethod
    def match_url(cls, url: str) -> bool:
        """Return True if this collector handles the given URL."""
        return bool(cls.URL_PATTERN.search(url))

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
