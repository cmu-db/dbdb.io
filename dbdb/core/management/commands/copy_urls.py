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

        # Map (legacy URLField attr, new FK attr) pairs
        URL_FIELD_MAP = [
            ('url',          'system_url'),
            ('tech_docs',    'docs_url'),
            ('source_url',   'sourcerepo_url'),
            ('wikipedia_url','wikipedia_new_url'),
        ]

        total_created = 0
        total_linked = 0
        for ver in versions.order_by("system__name"):
            changed = False
            for src_field, fk_field in URL_FIELD_MAP:
                raw_url = getattr(ver, src_field, '') or ''
                if not raw_url.strip():
                    continue
                url = normalize_url(raw_url)
                if not url.lower().startswith("http"):
                    LOG.info(f"SKIP: '{url}'")
                    continue

                citation, created = CitationUrl.objects.get_or_create(
                    url=url,
                    defaults={'status': CitationUrl.Status.UNKNOWN},
                )
                if created:
                    LOG.info(f"Created CitationUrl: {citation} (from {src_field})")
                    total_created += 1

                if getattr(ver, fk_field) != citation:
                    setattr(ver, fk_field, citation)
                    changed = True
                    total_linked += 1
                    LOG.info(f"Linked {ver} {fk_field} -> {citation}")

            if changed:
                ver.save()

        LOG.info(f"Done. Created {total_created} CitationUrls, linked {total_linked} FK fields across {versions.count()} versions.")
        return
