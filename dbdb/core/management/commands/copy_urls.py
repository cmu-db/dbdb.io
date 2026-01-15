# dbdb/core/management/commands/copy_urls.py

import logging

from django.core.management import BaseCommand
from dbdb.core.models import *
from dbdb.core.utils.citations import normalize_url

# Use Django's default logger for this command
LOG = logging.getLogger(__name__)

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('system', metavar='S', type=str, nargs='?',
                            help='System to force URL copying')
        return

    def handle(self, *args, **options):
        versions = SystemVersion.objects.all()
        if options.get('system'):
            keyword = options['system']
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        # Copy all the non-Citation URLs to Citations
        total = 0
        for ver in versions.order_by("system__name"):
            urls = {ver.url, ver.source_url, ver.wikipedia_url}
            for url in urls:
                orig_url = url
                url = normalize_url(url)
                if not url.lower().startswith("http"):
                    print(f"SKIP: '{url}'")
                    continue

                cnt = CitationUrl.objects.filter(url=url).count()
                LOG.info(f"URL: {url}")
                assert cnt in {0, 1}, f"Unexpected number [{cnt}] of CitationUrls found for {url}"
                if cnt == 0:
                    c = CitationUrl()
                    c.url = url
                    c.status = CitationUrl.Status.UNKNOWN
                    c.save()
                    LOG.info(f"Created CitationUrl: {c}\n+ Orig: '{orig_url}'")
                    total += 1
            pass

        LOG.info(f"Added {total} new CitationUrls for {versions.count()} versions")
        return
