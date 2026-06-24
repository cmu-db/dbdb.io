"""
migrate_repo_dirs — one-shot command to rename flat repo clones to org/repo layout.

Previously RepoCollector cloned into <CLONE_ROOT>/<reponame>, using only the last
URL path segment.  The updated collector uses <CLONE_ROOT>/<org>/<reponame> so that
repos from different organizations with the same name don't collide.

This command reads every RepositoryInfo entry, computes both the old and new local
paths, and renames directories on disk accordingly.

Usage:
    python manage.py migrate_repo_dirs [--dry-run]
"""
import os
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from dbdb.core.models import RepositoryInfo


def _old_path(clone_root: str, url: str) -> str:
    name = url.rstrip('/').split('/')[-1]
    if name.endswith('.git'):
        name = name[:-4]
    return os.path.join(clone_root, name)


def _new_path(clone_root: str, url: str) -> str:
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.strip('/').split('/') if p]
    if path_parts and path_parts[-1].endswith('.git'):
        path_parts[-1] = path_parts[-1][:-4]
    if len(path_parts) >= 2:
        name = '/'.join(path_parts[-2:])
    else:
        name = path_parts[-1] if path_parts else url.rstrip('/').split('/')[-1]
    return os.path.join(clone_root, name)


class Command(BaseCommand):
    help = 'Rename existing repo clones from <repo> to <org>/<repo> layout (one-shot migration)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be done without making any changes',
        )

    def handle(self, *args, **options):
        dry_run: bool = options['dry_run']
        clone_root = settings.DBDB_SOURCEREPO_DIRECTORY.rstrip('/')
        prefix = '[DRY RUN] ' if dry_run else ''

        entries = list(
            RepositoryInfo.objects
            .select_related('sourcerepo_url')
            .order_by('sourcerepo_url__url')
        )
        self.stdout.write(f"Found {len(entries)} RepositoryInfo entries.\n")

        # Detect conflicts: multiple entries sharing the same old path
        old_path_map: dict[str, list[str]] = {}
        for ri in entries:
            url = ri.sourcerepo_url.url
            old = _old_path(clone_root, url)
            old_path_map.setdefault(old, []).append(url)

        conflicted_old_paths: set[str] = {
            p for p, urls in old_path_map.items() if len(urls) > 1
        }
        if conflicted_old_paths:
            self.stdout.write(self.style.WARNING(
                "\nConflicts detected — multiple URLs share the same old path:"
            ))
            for old, urls in old_path_map.items():
                if len(urls) > 1:
                    self.stdout.write(f"  {old}:")
                    for u in urls:
                        self.stdout.write(f"    {u}")
            self.stdout.write("")

        moved = already_correct = missing = conflicted = 0

        for ri in entries:
            url = ri.sourcerepo_url.url
            old = _old_path(clone_root, url)
            new = _new_path(clone_root, url)

            if old == new:
                already_correct += 1
                continue

            if old in conflicted_old_paths:
                self.stdout.write(self.style.WARNING(
                    f"  SKIP (conflict)  {url}\n"
                    f"    old: {old}"
                ))
                conflicted += 1
                continue

            if not os.path.isdir(old):
                self.stdout.write(f"  SKIP (not on disk)  {url}")
                missing += 1
                continue

            if os.path.exists(new):
                self.stdout.write(self.style.WARNING(
                    f"  SKIP (dest exists) {url}\n"
                    f"    old: {old}\n"
                    f"    new: {new}"
                ))
                conflicted += 1
                continue

            self.stdout.write(
                f"  {prefix}MOVE  {url}\n"
                f"    {old}\n"
                f"    → {new}"
            )
            if not dry_run:
                os.makedirs(os.path.dirname(new), exist_ok=True)
                os.rename(old, new)
            moved += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. moved={moved}  already_correct={already_correct}  "
            f"missing={missing}  conflicted/skipped={conflicted}"
        ))
