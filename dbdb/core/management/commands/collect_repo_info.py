import logging
import time

from django.core.management import BaseCommand
from django.utils import timezone

from dbdb.core.models import RepositoryInfo, RepositorySnapshot, SystemVersion
from dbdb.core.utils.repository import fetch_snapshot_data

_FAILED_DISABLE_THRESHOLD = 3

LOG = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Collect repository statistics for systems that have a source-repo URL"

    def add_arguments(self, parser):
        parser.add_argument(
            'system', metavar='S', type=str, nargs='?',
            help='System slug or numeric ID to process (default: all enabled)')
        parser.add_argument(
            '--debug', action='store_true',
            help='Enable debug logging')
        parser.add_argument(
            '--sleep', type=int, default=0, metavar='SECONDS',
            help='Seconds to sleep between repositories (default: 0)')
        parser.add_argument(
            '--ignore-last-checked', type=int, default=None, metavar='DAYS',
            help='Skip repositories scanned in the last N days')
        parser.add_argument(
            '--limit', type=int, default=None, metavar='N',
            help='Stop after successfully retrieving information for N repositories')
        return

    def handle(self, *args, **options):
        if options['debug']:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(name)s %(levelname)s: %(message)s',
                force=True,
            )

        versions = (
            SystemVersion.objects
            .filter(is_current=True, sourcerepo_url__isnull=False)
            .select_related('sourcerepo_url', 'system')
            .order_by('system__name')
        )

        if options.get('system'):
            keyword = options['system'].strip()
            LOG.debug(f"Searching for system based on keyword '{keyword}'")
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        ignore_days = options['ignore_last_checked']
        sleep_secs = options['sleep']
        limit = options['limit']

        seen_citation_ids: set[int] = set()
        ok = err = skipped = 0
        first = True
        last_was_skipped = False

        if versions.count() == 0:
            LOG.warning(f"No systems found!")

        for ver in versions.order_by("system__name"):
            citation = ver.sourcerepo_url
            if citation.id in seen_citation_ids:
                LOG.debug("Skipping duplicate citation: %s", citation.url)
                last_was_skipped = True
                continue
            seen_citation_ids.add(citation.id)

            repo_info, _ = RepositoryInfo.objects.get_or_create(sourcerepo_url=citation)
            if not repo_info.enabled:
                LOG.debug("Skipping disabled repo: %s", citation.url)
                skipped += 1
                last_was_skipped = True
                continue

            if ignore_days is not None and repo_info.last_snapshot is not None:
                age = timezone.now() - repo_info.last_snapshot
                if age.days < ignore_days:
                    LOG.debug(
                        "Skipping recently checked repo (%d days ago): %s",
                        age.days, citation.url,
                    )
                    skipped += 1
                    last_was_skipped = True
                    continue

            if sleep_secs > 0 and not first and not last_was_skipped:
                LOG.debug("Sleeping %d seconds before next repo...", sleep_secs)
                time.sleep(sleep_secs)
            first = False
            last_was_skipped = False

            self.stdout.write(f"{ver.system.name}  {citation.url}")
            try:
                data = fetch_snapshot_data(citation)
            except ValueError as exc:
                self.stderr.write(f"  Skipped — {exc}")
                skipped += 1
                last_was_skipped = True
                continue
            except Exception as exc:
                self.stderr.write(f"  ERROR — {exc}")
                LOG.exception("Failed to fetch repo data for %s", citation.url)
                err += 1
                continue

            fetch_errors = data.pop('errors', [])
            for exc in fetch_errors:
                self.stderr.write(f"  WARNING — partial data: {exc}")
                LOG.warning("Partial repo data for %s: %s", citation.url, exc)

            if fetch_errors:
                has_data = any([
                    data.get('star_count'),
                    data.get('fork_count'),
                    data.get('commit_count'),
                    data.get('last_commit_hash'),
                    data.get('last_commit_timestamp'),
                    data.get('open_pr_count'),
                    data.get('merged_pr_count'),
                    data.get('open_issue_count'),
                    data.get('closed_issue_count'),
                    data.get('commit_authors'),
                    data.get('pr_authors'),
                    data.get('issue_authors'),
                ])
                data['status'] = (
                    RepositorySnapshot.Status.ERROR
                    if has_data
                    else RepositorySnapshot.Status.FAILED
                )
            else:
                data['status'] = RepositorySnapshot.Status.VALID

            snapshot = RepositorySnapshot.objects.create(repo=repo_info, **data)
            repo_info.current = snapshot
            repo_info.last_snapshot = timezone.now()
            repo_info.save(update_fields=['current', 'last_snapshot', 'modified'])
            ok += 1
            self.stdout.write(
                f"  commits={snapshot.commit_count}  "
                f"open_prs={snapshot.open_pr_count}  merged_prs={snapshot.merged_pr_count}  "
                f"open_issues={snapshot.open_issue_count}  closed_issues={snapshot.closed_issue_count}  "
                f"stars={snapshot.star_count}  forks={snapshot.fork_count}  "
                f"branches={snapshot.branch_count}  branch_default={snapshot.branch_default_name}  "
                f"status={snapshot.get_status_display()}"
            )

            if snapshot.status == RepositorySnapshot.Status.FAILED:
                recent = list(
                    repo_info.snapshots
                    .order_by('-created')
                    .values_list('status', flat=True)[:_FAILED_DISABLE_THRESHOLD]
                )
                if (
                    len(recent) == _FAILED_DISABLE_THRESHOLD
                    and all(s == RepositorySnapshot.Status.FAILED for s in recent)
                ):
                    repo_info.enabled = False
                    repo_info.save(update_fields=['enabled', 'modified'])
                    self.stderr.write(
                        f"  Disabled {citation.url} — "
                        f"{_FAILED_DISABLE_THRESHOLD} consecutive FAILED snapshots"
                    )

            if limit is not None and ok >= limit:
                self.stdout.write(f"Limit of {limit} reached, stopping.")
                break

        self.stdout.write(
            self.style.SUCCESS(f"\nDone: {ok} updated, {skipped} skipped, {err} errors")
        )
