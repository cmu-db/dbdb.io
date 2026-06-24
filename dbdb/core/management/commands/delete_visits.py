from django.core.management.base import BaseCommand
from django.db.models import Count

from dbdb.core.models import System, SystemVisit


class Command(BaseCommand):
    help = 'Delete SystemVisit rows whose ip_address contains KEYWORD and recompute view_count'

    def add_arguments(self, parser):
        parser.add_argument('keyword', help='Substring to match against ip_address')
        parser.add_argument(
            '--dry-run', action='store_true', default=False,
            help='Show what would be deleted without making changes',
        )

    def handle(self, *args, **options):
        keyword  = options['keyword']
        dry_run  = options['dry_run']
        prefix   = '[DRY RUN] ' if dry_run else ''

        qs = SystemVisit.objects.filter(ip_address__icontains=keyword)
        total = qs.count()

        if total == 0:
            self.stdout.write(f'No SystemVisit rows match ip_address containing "{keyword}".\n')
            return

        # Collect the affected system IDs before deletion
        affected_system_ids = list(
            qs.values_list('system_id', flat=True).distinct()
        )

        self.stdout.write(
            f'{prefix}Found {total} SystemVisit row(s) matching "{keyword}" '
            f'across {len(affected_system_ids)} system(s).\n'
        )
        for sv in qs.select_related('system').order_by('system__name', 'ip_address', 'created'):
            self.stdout.write(
                f'{prefix}  Delete SystemVisit : {sv.system.name} | {sv.ip_address} | {sv.created}\n'
            )

        if dry_run:
            return

        qs.delete()
        self.stdout.write(f'Deleted {total} SystemVisit row(s).\n')

        # Recompute view_count for every affected system
        for system in System.objects.filter(pk__in=affected_system_ids).order_by('name'):
            new_count = system.visits.count()
            system.view_count = new_count
            system.save(update_fields=['view_count'])
            self.stdout.write(f'  Updated view_count : {system.name} → {new_count}\n')
