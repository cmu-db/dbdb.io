import sys

from django.db import connection, transaction
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from pprint import pprint
import logging

from dbdb.core.models import *

LOG = logging.getLogger('console')

class Command(BaseCommand):

    def handle(self, *args, **options):
        LOG.setLevel(logging.DEBUG)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        LOG.addHandler(console)

        # I used SQL to clean up a bunch of malformed citation urls
        # But then this created a bunch of duplicates and there are other parts of the code
        # expected to get back only one entry per URL.
        # Now we need to manually go through and clean up the references

        # The first thing we need to do is get the list of URLs with duplicates
        dupe_urls = []
        with connection.cursor() as cursor:
            sql = "SELECT url, COUNT(*) AS cnt FROM core_citationurl GROUP BY url HAVING COUNT(*) > 1 ORDER BY cnt,url ASC"
            cursor.execute(sql)
            dupe_urls = [row[0] for row in cursor.fetchall()]
        if not dupe_urls:
            LOG.info("No duplicate URLs found!")
            return
        LOG.info("Found %d duplicate URLs", len(dupe_urls))

        # Now for each URL we need to remove all of them except for one
        # But we don't want to just delete the entry in the database since that would
        # cascade to the other referencing tables. Instead we want to update the referencing
        # tables to point to just the remaining copy of the URL

        tables = [
            "core_systemfeature_citations",
            "core_systemversion_acquired_by_citations",
            "core_systemversion_description_citations",
            "core_systemversion_end_year_citations",
            "core_systemversion_history_citations",
            "core_systemversion_start_year_citations",
        ]

        for url in dupe_urls:
            url_ids = []
            with connection.cursor() as cursor:
                sql = "SELECT id FROM core_citationurl WHERE url = %s"
                cursor.execute(sql, [url])
                url_ids = [row[0] for row in cursor.fetchall()]
            assert len(url_ids) > 1
            LOG.info("Found %d entries for duplicate url '%s'", len(url_ids), url)
            url_id_to_keep = url_ids[0]

            # We will pick the first one as the one to keep
            # And then delete the rest. But we need to go through and update any references to them
            with (transaction.atomic()):
                placeholders = ', '.join(['%s'] * len(url_ids[1:]))  # "%s, %s, %s, ... %s"
                where = ' citationurl_id IN ({})'.format(placeholders)
                for table in tables:
                    with connection.cursor() as cursor:
                        # Check whether there is already an entry for the url_id that we want to keep.
                        # If yes, then we just need to delete all these existing entries
                        info_column = None
                        if table == "core_systemfeature_citations":
                            info_column = "systemfeature_id"
                        else:
                            info_column = "systemversion_id"
                        sql = "SELECT id, {} AS system_info_id, citationurl_id FROM {} WHERE "\
                            .format(info_column, table)
                        sql += where
                        print(sql)

                        cursor.execute(sql, tuple(url_ids[1:]))
                        table_url_ids = [row[2] for row in cursor.fetchall()]
                        if not table_url_ids: continue

                        # Now for every other_id except for the first one (which we want to keep),
                        # check whether we already have a citationurl_id for the first one
                        # for info_id in info_ids.keys():
                        # Delete!
                        # if url_id_to_keep in info_ids[info_id]:
                        if url_id_to_keep not in table_url_ids:
                            sql = "UPDATE {} SET citationurl_id = {} WHERE ".format(table, url_id_to_keep)
                            sql += "id = (SELECT id FROM {} WHERE ".format(table)
                            sql += where
                            sql += " LIMIT 1)"
                            cursor.execute(sql, tuple(url_ids[1:]))
                            assert cursor.rowcount > 0
                            LOG.info("Modified {} records in table '{}".format(cursor.rowcount, table))

                # It is now safe to delete the duplicate entries
                result, _ = CitationUrl.objects.filter(id__in=url_ids[1:]).delete()
                LOG.info("Deleted %d objects for '%s'", result, url)

                # transaction.set_rollback(True)
                # raise Exception
                # break
        return

    pass
