from django.core.management import BaseCommand

from dbdb.core.models import System, SystemVersion
from dbdb.core.utils.versions import is_spotlight_eligible


class Command(BaseCommand):
    help = "Recompute System.spotlight_enabled for all systems (or a single system)"

    def add_arguments(self, parser):
        parser.add_argument(
            'system', metavar='S', type=str, nargs='?',
            help='System keyword or numeric ID to process (default: all)')

    def handle(self, *args, **options):
        versions = (
            SystemVersion.objects
            .filter(is_current=True)
            .select_related('system')
            .prefetch_related(
                'developer_orgs', 'tags', 'licenses', 'project_types',
                'features__options', 'features__citations',
            )
        )

        if options.get('system'):
            keyword = options['system'].strip()
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        total = eligible = ineligible = updated = 0

        for ver in versions.order_by('system__name'):
            total += 1
            is_eligible = is_spotlight_eligible(ver)
            system = ver.system

            if is_eligible:
                eligible += 1
            else:
                ineligible += 1

            if system.spotlight_enabled != is_eligible:
                system.spotlight_enabled = is_eligible
                system.save(update_fields=['spotlight_enabled'])
                updated += 1

        self.stdout.write(
            f"\n{'Systems checked':<22} {total:>6}"
            f"\n{'Eligible':<22} {eligible:>6}"
            f"\n{'Ineligible':<22} {ineligible:>6}"
            f"\n{'Updated':<22} {updated:>6}"
        )
