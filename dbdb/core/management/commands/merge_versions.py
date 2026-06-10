"""
merge_versions — squash the two most recent SystemVersions into one.

Deletes the second-newest version and reassigns its ver number to the newest,
so the history doesn't show a gap.  System.ver is updated when the newest
version is the live (is_current) version.

Usage:
    python manage.py merge_versions <slug> [--dry-run]
"""
from argparse import ArgumentParser

from django.db import transaction

from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import System, SystemVersion


class Command(DbdbBaseCommand):
    help = 'Merge the two most recent SystemVersions by deleting the second-newest and renumbering the newest'

    def add_arguments(self, parser: ArgumentParser):
        super().add_arguments(parser)
        parser.add_argument('slug', help='System slug or slug keyword')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would happen without making changes')

    def handle(self, *args, **options):
        slug: str = options['slug']
        dry_run: bool = options['dry_run']

        system = System.objects.filter(slug__icontains=slug).first()
        if system is None:
            raise SystemExit(f"No system found matching '{slug}'")

        versions = list(
            SystemVersion.objects.filter(system=system).order_by('-ver')[:2]
        )
        if len(versions) < 2:
            self.stdout.write(self.style.WARNING(
                f"{system.name} has fewer than 2 versions — nothing to merge."
            ))
            return

        newest, second_newest = versions[0], versions[1]

        self.stdout.write(f"System : {system.name}")
        self.stdout.write(
            f"Delete : ver {second_newest.ver} "
            f"(approved={'yes' if second_newest.approved else 'no'}, "
            f"is_current={'yes' if second_newest.is_current else 'no'})"
        )
        self.stdout.write(
            f"Renumber: ver {newest.ver} → ver {second_newest.ver} "
            f"(approved={'yes' if newest.approved else 'no'}, "
            f"is_current={'yes' if newest.is_current else 'no'})"
        )
        if newest.is_current:
            self.stdout.write(f"Update system.ver: {system.ver} → {second_newest.ver}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes made."))
            return

        with transaction.atomic():
            second_newest.delete()
            SystemVersion.objects.filter(pk=newest.pk).update(ver=second_newest.ver)
            if newest.is_current:
                System.objects.filter(pk=system.pk).update(ver=second_newest.ver)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {system.name} newest version is now ver {second_newest.ver}."
        ))
