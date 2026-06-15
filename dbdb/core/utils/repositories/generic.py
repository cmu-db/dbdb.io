from __future__ import annotations

import re

import requests

from .base import RepoCollector, SnapshotData


class GenericGitCollector(RepoCollector):
    """Concrete RepoCollector for raw git operations — no hosting-platform API."""

    URL_PATTERN = re.compile(r'.*')

    def _make_session(self, token: str | None) -> requests.Session:
        return requests.Session()

    def get_metadata(self, repo_url: str) -> SnapshotData:
        return SnapshotData()

    def get_commit_url(self, branch: str, commit: str) -> str:
        raise NotImplementedError("GenericGitCollector has no platform commit URL")
