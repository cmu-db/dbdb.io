from django.db import connection, transaction
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
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

            # We will pick the first one as the one to keep
            # And then delete the rest. But we need to go through and update any references to them
            with (transaction.atomic()):
                for table in tables:
                    placeholders = ', '.join(['%s'] * len(url_ids[1:]))  # "%s, %s, %s, ... %s"
                    with connection.cursor() as cursor:
                        # Check whether there is already an entry for the url_id that we want to keep.
                        # If yes, then we just need to delete all these existing entries
                        ## FIXME: Need to handle core_systemfeature_citations differently
                        sql = "SELECT id, "
                        if table == "core_systemfeature_citations"
                            sql += "systemfeature_id"
                        else:
                            sql = "systemversion_id"
                        sql += " AS other_id, citationurl_id FROM {} WHERE citationurl_id = " + placeholders



                        where = 'citationurl_id IN ({})'.format(placeholders)
                        sql = "UPDATE {} SET citationurl_id = {} WHERE ".format(table, url_ids[0])
                        cursor.execute(sql+where, tuple(url_ids[1:]))
                        if cursor.rowcount > 0:
                            LOG.info("Updated {} records in table '{}".format(cursor.rowcount, table))

                # It is now safe to delete the duplicate entries
                result, _ = CitationUrl.objects.filter(id__in=url_ids[1:]).delete()
                LOG.info("Deleted %d objects for '%s'", result, url)

                # transaction.set_rollback(True)
                # raise Exception
                # break
        return

    pass
