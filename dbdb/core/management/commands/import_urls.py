import logging

from django.core.management import BaseCommand
from django.db import connection

from dbdb.core.models import CitationUrl

LOG = logging.getLogger(__name__)

# Fields to copy from the source table into the live CitationUrl row.
# 'url' is used only for lookup — it is never overwritten.
COPY_FIELDS = [
    'status',
    'last_checked',
    'last_modified',
    'last_title',
    'last_contenttype',
    'last_contentsize',
    'last_etag',
    'last_cachecontrol',
    'last_statuscode',
]


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('table', metavar='TABLE',
                            help='Name of the source Postgres table (copy of core_citationurl)')
        return

    def handle(self, *args, **options):
        table = options['table']

        cols = ', '.join(['url'] + COPY_FIELDS)
        sql = f'SELECT {cols} FROM "{table}"'  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        col_names = ['url'] + COPY_FIELDS
        success = 0
        not_found = 0

        for row in rows:
            data = dict(zip(col_names, row))
            url = data.pop('url')

            try:
                obj = CitationUrl.objects.get(url=url)
            except CitationUrl.DoesNotExist:
                LOG.warning(f"No CitationUrl found for URL: {url!r}")
                not_found += 1
                continue

            for field, value in data.items():
                setattr(obj, field, value)
            obj.save(update_fields=COPY_FIELDS)
            success += 1
            LOG.debug(f"Updated: {obj}")

        LOG.info(f"Done. Updated {success} CitationUrls ({not_found} not found) from table '{table}'.")
        self.stdout.write(self.style.SUCCESS(
            f"Updated {success} CitationUrls ({not_found} not found) from '{table}'."
        ))
        return
