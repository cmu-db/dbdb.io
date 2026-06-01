from django.core.management.base import BaseCommand

from dbdb.core.models import System
from dbdb.core.utils.versions import delete_latest_version


class Command(BaseCommand):
    help = 'Delete the latest SystemVersion for a system'

    def add_arguments(self, parser):
        parser.add_argument('slug', help='System slug')
        parser.add_argument(
            '--dry-run', action='store_true', default=False,
            help='Show what would be deleted without making changes',
        )

    def handle(self, *args, **options):
        try:
            system = System.objects.get(slug=options['slug'])
        except System.DoesNotExist:
            self.stderr.write(f"System '{options['slug']}' not found.\n")
            return
        delete_latest_version(system, dry_run=options['dry_run'], out=self.stdout)
