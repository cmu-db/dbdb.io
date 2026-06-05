from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from dbdb.core.models import SystemVersion, RepositoryInfo, RepositorySnapshot
from dbdb.core.utils.repositories import (
    BitbucketCollector,
    CodebergCollector,
    GitHubCollector,
    GitLabCollector,
    RepoCollector,
    SnapshotData,
    SourceForgeCollector,
)
from dbdb.core.utils.versions import clone_system_version, finalize_new_version


# Registry: host name → (collector class, Django settings key for API token).
# A None token key means the host requires no authentication.
_REGISTRY: dict[str, tuple[type[RepoCollector], str | None]] = {
    'github':      (GitHubCollector,      'GITHUB_API_TOKEN'),
    'gitlab':      (GitLabCollector,      'GITLAB_API_TOKEN'),
    'bitbucket':   (BitbucketCollector,   'BITBUCKET_API_TOKEN'),
    'sourceforge': (SourceForgeCollector, 'SOURCEFORGE_API_TOKEN'),
    'codeberg':    (CodebergCollector,    'CODEBERG_API_TOKEN'),
}


def detect_host(url: str) -> str | None:
    """Return the host key ('github', 'gitlab', 'bitbucket', 'sourceforge')
    for a repository URL, or None if unrecognised.
    """
    for host, (cls, _) in _REGISTRY.items():
        if cls.match_url(url):
            return host
    return None


def fetch_snapshot_data(citation_url) -> SnapshotData:
    """
    Given a CitationUrl instance, fetch repository statistics and return
    a SnapshotData whose fields map directly onto RepositorySnapshot fields.

    Raises:
        ValueError: Host is not supported.
    """
    url  = citation_url.url
    host = detect_host(url)
    if host is None:
        raise ValueError(f"Unsupported repository host: {url}")

    cls, token_key = _REGISTRY[host]
    token = (getattr(settings, token_key, '') or None) if token_key else None
    return cls(token=token).get_metadata(url)


def check_abandoned(system, *, inactivity_days: int = 1095) -> bool:
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
    no_new_prs     = _equal_or_none(latest.merged_pr_count, previous.merged_pr_count)
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


def _mark_abandoned(current_version:SystemVersion, repo_info:RepositoryInfo, snapshot:RepositorySnapshot):
    """Clone current_version, apply the abandoned tag, and disable scanning."""
    from dbdb.core.models import AttributeOption

    User        = get_user_model()
    bot_user    = User.objects.get(username=settings.DBDB_BOT_ACCOUNT)
    abandoned_tag = AttributeOption.objects.get(
        attribute__slug='tag', slug='abandoned'
    )

    old_logo = current_version.logo
    end_year = current_version.end_year or (
        snapshot.last_commit_timestamp.year if snapshot.last_commit_timestamp else None
    )

    comment = "Automatically marked as abandoned due to source code inactivity."
    if snapshot.last_commit_timestamp:
        comment += f"\nLast commit was {snapshot.last_commit_timestamp.strftime('%Y-%m-%d')}"
    elif snapshot.last_pr_closed_at:
        comment += f"\nLast closed PR was {snapshot.last_pr_closed_at.strftime('%Y-%m-%d')}"

    new_version = clone_system_version(
        current_version,
        creator=bot_user,
        comment=comment,
        end_year=end_year,
    )

    # Add the abandoned tag after cloning so search text includes it
    new_version.tags.add(abandoned_tag)

    finalize_new_version(new_version, old_logo=old_logo)

    # Disable further scanning for this repo
    repo_info.enabled = False
    repo_info.save(update_fields=['enabled', 'modified'])
