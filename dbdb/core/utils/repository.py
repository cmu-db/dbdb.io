from __future__ import annotations

import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from dbdb.core.utils.githubrepo import get_metadata as _github_metadata
from dbdb.core.utils.gitlabrepo import get_metadata as _gitlab_metadata
from dbdb.core.utils.versions import clone_system_version, finalize_new_version


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


def check_abandoned(system, *, inactivity_days: int = 365) -> bool:
    """
    Determine whether a system's source repository appears abandoned and, if
    so, record that conclusion as a new SystemVersion.

    Abandonment requires both conditions to be true:
    1. No new activity between the two most recent RepositorySnapshots
       (commit_count and merged_pr_count are unchanged).
    2. The most recent commit predates the current time by at least
       ``inactivity_days``.

    If abandoned:
    - Creates a new SystemVersion copied from the current one.
    - Adds the 'abandoned' AttributeOption tag.
    - Sets end_year from last_commit_timestamp.year if end_year is unset.
    - Saves with the 'dbdb-bot' user and an automated comment.
    - Sets RepositoryInfo.enabled = False to stop future scans.

    Returns True if the system was marked abandoned, False otherwise.

    Raises:
        ValueError: The system has no sourcerepo_url or no RepositoryInfo.
    """
    from dbdb.core.models import AttributeOption, RepositoryInfo, SystemVersion

    current = SystemVersion.objects.get(system=system, is_current=True)

    if not current.sourcerepo_url_id:
        raise ValueError(f"System '{system.slug}' has no sourcerepo_url")

    try:
        repo_info = RepositoryInfo.objects.select_related('current').get(
            sourcerepo_url_id=current.sourcerepo_url_id
        )
    except RepositoryInfo.DoesNotExist:
        raise ValueError(f"No RepositoryInfo for system '{system.slug}'")

    snapshots = list(repo_info.snapshots.order_by('-created')[:2])
    if len(snapshots) < 2:
        return False

    latest, previous = snapshots

    # Condition 1 — no new activity between the two snapshots
    def _equal_or_none(a, b):
        return a is not None and b is not None and a == b

    no_new_commits = _equal_or_none(latest.commit_count, previous.commit_count)
    no_new_prs = _equal_or_none(latest.merged_pr_count, previous.merged_pr_count)
    if not (no_new_commits and no_new_prs):
        return False

    # Condition 2 — last commit is older than the inactivity threshold
    if not latest.last_commit_timestamp:
        return False
    cutoff = timezone.now() - timedelta(days=inactivity_days)
    if latest.last_commit_timestamp > cutoff:
        return False

    # Both conditions satisfied — mark as abandoned
    _mark_abandoned(current, repo_info, latest)
    return True


def _mark_abandoned(current_version, repo_info, snapshot):
    """Clone current_version, apply the abandoned tag, and disable scanning."""
    from dbdb.core.models import AttributeOption

    User = get_user_model()
    bot_user = User.objects.get(username='dbdb-bot')
    abandoned_tag = AttributeOption.objects.get(
        attribute__slug='tag', slug='abandoned'
    )

    old_logo = current_version.logo
    end_year = current_version.end_year or (
        snapshot.last_commit_timestamp.year if snapshot.last_commit_timestamp else None
    )

    new_version = clone_system_version(
        current_version,
        creator=bot_user,
        comment=(
            "Automatically marked as abandoned: no new commits or merged pull "
            "requests detected across the last two repository snapshots, and the "
            "most recent commit predates the inactivity threshold."
        ),
        end_year=end_year,
    )

    # Add the abandoned tag after cloning so search text includes it
    new_version.tags.add(abandoned_tag)

    finalize_new_version(new_version, old_logo=old_logo)

    # Disable further scanning for this repo
    repo_info.enabled = False
    repo_info.save(update_fields=['enabled', 'modified'])
