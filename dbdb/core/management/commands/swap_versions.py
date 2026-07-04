"""
swap_versions — fix out-of-order version numbering for a system.

Swaps the ver numbers of a pending version (lower ver) and a live version
(higher ver), and merges the live version's additive changes into the pending
version first so nothing is lost when the pending version is eventually approved.

Usage:
    python manage.py swap_versions <slug> <ver1> <ver2> [--dry-run]
    python manage.py swap_versions --check

    slug  — system slug (substring match)
    ver1  — current ver number of the PENDING version (must be lower)
    ver2  — current ver number of the LIVE version (must be higher)
    --check — scan all systems and report any with a pending ver lower than the live ver
"""
from django.core.management.base import CommandError
from django.db.models import F, OuterRef, Subquery

from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import System, SystemVersion
from dbdb.core.utils.versions import swap_versions


class Command(DbdbBaseCommand):
    help = 'Swap ver numbers between a pending and live SystemVersion, merging live changes into pending'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('slug', nargs='?', help='System slug (substring match)')
        parser.add_argument('ver1', nargs='?', type=int, help='Pending version number (lower)')
        parser.add_argument('ver2', nargs='?', type=int, help='Live version number (higher)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would happen without making changes')
        parser.add_argument('--check', action='store_true',
                            help='Scan all systems and report any where pending ver < live ver')

    def handle(self, *args, **options):
        if options['check']:
            self._run_check()
            return

        slug = options['slug']
        ver1 = options['ver1']
        ver2 = options['ver2']

        if not slug or ver1 is None or ver2 is None:
            raise CommandError('slug, ver1, and ver2 are required unless --check is used.')

        system = System.objects.filter(slug__icontains=slug).first()
        if system is None:
            raise CommandError(f"No system found matching '{slug}'")

        try:
            swap_versions(system, ver1, ver2, dry_run=options['dry_run'], out=self.stdout)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if not options['dry_run']:
            self.stdout.write(self.style.SUCCESS('Done.'))

    def _run_check(self):
        # Find the pending ver for each system (there can only be one)
        pending_ver_sq = (
            SystemVersion.objects
            .filter(system=OuterRef('system'), approved=False)
            .values('ver')[:1]
        )

        # Live versions where a pending version exists with a lower ver number
        problems = (
            SystemVersion.objects
            .filter(is_current=True, approved=True)
            .annotate(pending_ver=Subquery(pending_ver_sq))
            .filter(pending_ver__isnull=False, pending_ver__lt=F('ver'))
            .select_related('system')
            .order_by('system__name')
        )

        if not problems:
            self.stdout.write(self.style.SUCCESS('No out-of-order versions found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {problems.count()} system(s) with out-of-order versions:\n'))
        for sv in problems:
            self.stdout.write(
                f"  {sv.system.name:<40}  "
                f"pending=ver {sv.pending_ver}  live=ver {sv.ver}  "
                f"→  swap_versions {sv.system.slug} {sv.pending_ver} {sv.ver}"
            )
