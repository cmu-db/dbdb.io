import logging

from django.core.management import BaseCommand
from django.db import connection

from dbdb.core.models import System, SystemVisit

LOG = logging.getLogger(__name__)

VISIT_FIELDS = ['id', 'system_id', 'ip_address', 'user_agent', 'created']


class Command(BaseCommand):
    help = 'Import SystemVisit rows from a copy table and recompute System.view_count'

    def add_arguments(self, parser):
        parser.add_argument('table', metavar='TABLE',
                            help='Name of the source Postgres table (copy of core_systemvisit)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show how many visits would be imported without writing anything')

    def handle(self, *args, **options):
        table = options['table']
        dry_run = options['dry_run']

        cols = ', '.join(VISIT_FIELDS)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {cols} FROM "{table}"')  # noqa: S608
            rows = cursor.fetchall()

        self.stdout.write(f"Read {len(rows)} rows from '{table}'")

        existing_ids = set(SystemVisit.objects.values_list('id', flat=True))
        valid_system_ids = set(System.objects.values_list('id', flat=True))

        imported = skipped = missing_system = 0

        with connection.cursor() as cursor:
            for row in rows:
                data = dict(zip(VISIT_FIELDS, row))
                if data['id'] in existing_ids:
                    skipped += 1
                    continue
                if data['system_id'] not in valid_system_ids:
                    LOG.warning("Skipping visit #%s — system_id=%s not found", data['id'], data['system_id'])
                    missing_system += 1
                    continue
                if not dry_run:
                    cursor.execute(
                        'INSERT INTO core_systemvisit (id, system_id, ip_address, user_agent, created) '
                        'VALUES (%s, %s, %s, %s, %s)',
                        [data['id'], data['system_id'], data['ip_address'], data['user_agent'], data['created']],
                    )
                imported += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"DRY RUN: {imported} visits would be imported ({skipped} existing, {missing_system} unknown systems)."
            ))
            return

        self.stdout.write(f"Imported {imported}, skipped {skipped} existing, {missing_system} unknown systems")

        # Reset the PK sequence so future auto-inserts don't collide.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('core_systemvisit', 'id'), "
                "COALESCE(MAX(id), 1)) FROM core_systemvisit"
            )

        # Recompute view_count for all systems.
        self.stdout.write("Recomputing view_count...")
        with connection.cursor() as cursor:
            cursor.execute('SELECT system_id, COUNT(*) FROM core_systemvisit GROUP BY system_id')
            counts = dict(cursor.fetchall())

        updated = 0
        for system in System.objects.only('id', 'view_count'):
            new_count = counts.get(system.id, 0)
            if system.view_count != new_count:
                system.view_count = new_count
                system.save(update_fields=['view_count'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Imported {imported} visits. Updated view_count for {updated} systems."
        ))
