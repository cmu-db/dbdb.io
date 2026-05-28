import logging
import sys

from django.core.management import BaseCommand
from django.db import connection

from dbdb.core.models import CitationUrl
from dbdb.core.utils.citations import normalize_url

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

        cols = ', '.join(['id', 'url'] + COPY_FIELDS)
        sql = f'SELECT {cols} FROM "{table}"'  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        col_names = ['id', 'url'] + COPY_FIELDS
        success = 0
        not_found = 0

        for row in rows:
            data = dict(zip(col_names, row))
            row_id = data.pop('id')
            url = data.pop('url')

            try:
                obj = CitationUrl.objects.get(url=url)
            except CitationUrl.DoesNotExist:
                try:
                    obj = CitationUrl.objects.get(pk=row_id)
                    # print(f"IMPORT: {url}")
                    # print(f"FOUND: {obj}")
                    # print(f"NORMALIZE: {normalize_url(obj.url)}")

                    # if normalize_url(obj.url) != url:
                    #     LOG.warning(f"No CitationUrl found for URL: {url!r} [#{row_id}]")
                    #     not_found += 1
                    #     # sys.exit(1)
                    #     continue
                    LOG.debug(f"Matched CitationUrl by pk={row_id} via normalized URL: {url!r}")
                except CitationUrl.DoesNotExist:
                    LOG.warning(f"No CitationUrl found for URL: {url!r} [#{row_id}]")
                    # sys.exit(1)
                    not_found += 1
                    continue

            if obj.status == CitationUrl.Status.UNKNOWN and data["status"] != CitationUrl.Status.UNKNOWN:
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
