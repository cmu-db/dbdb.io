"""
swap_versions — fix out-of-order version numbering for a system.

Swaps the ver numbers of a pending version (lower ver) and a live version
(higher ver), and merges the live version's additive changes into the pending
version first so nothing is lost when the pending version is eventually approved.

Usage:
    python manage.py swap_versions <slug> <ver1> <ver2> [--dry-run]

    slug  — system slug (substring match)
    ver1  — current ver number of the PENDING version (must be lower)
    ver2  — current ver number of the LIVE version (must be higher)
"""
from django.core.management.base import CommandError

from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import System
from dbdb.core.utils.versions import swap_versions


class Command(DbdbBaseCommand):
    help = 'Swap ver numbers between a pending and live SystemVersion, merging live changes into pending'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('slug', help='System slug (substring match)')
        parser.add_argument('ver1', type=int, help='Pending version number (lower)')
        parser.add_argument('ver2', type=int, help='Live version number (higher)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would happen without making changes')

    def handle(self, *args, **options):
        slug    = options['slug']
        ver1    = options['ver1']
        ver2    = options['ver2']
        dry_run = options['dry_run']

        system = System.objects.filter(slug__icontains=slug).first()
        if system is None:
            raise CommandError(f"No system found matching '{slug}'")

        try:
            swap_versions(system, ver1, ver2, dry_run=dry_run, out=self.stdout)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('Done.'))
