from __future__ import annotations

import re

from django.conf import settings

from dbdb.core.utils.githubrepo import get_metadata as _github_metadata
from dbdb.core.utils.gitlabrepo import get_metadata as _gitlab_metadata


_GITHUB = re.compile(r'github\.com/')
_GITLAB = re.compile(r'gitlab\.com/')


def detect_host(url: str) -> str | None:
    """Return 'github', 'gitlab', or None for unrecognised hosts."""
    if _GITHUB.search(url):
        return 'github'
    if _GITLAB.search(url):
        return 'gitlab'
    return None


def fetch_snapshot_data(citation_url) -> dict:
    """
    Given a CitationUrl instance, fetch repository statistics and return
    a dict whose keys match RepositorySnapshot field names.

    Raises:
        ValueError: Host is not GitHub or GitLab.
        requests.HTTPError: API request failed.
    """
    url = citation_url.url
    host = detect_host(url)

    if host == 'github':
        token = getattr(settings, 'GITHUB_API_TOKEN', '') or None
        return _github_metadata(url, token=token)

    if host == 'gitlab':
        token = getattr(settings, 'GITLAB_API_TOKEN', '') or None
        return _gitlab_metadata(url, token=token)

    raise ValueError(f"Unsupported repository host: {url}")
