# stdlib imports
import logging
import os

from django.conf import settings
from django.db.models import Q

from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import Organization, SystemVersion
from dbdb.core.utils.twitter_card import create_twitter_card

LOG = logging.getLogger(__name__)


class Command(DbdbBaseCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('name', metavar='N', type=str, nargs='?',
                            help='Name/slug filter to limit which entries are processed')
        parser.add_argument('--type', dest='card_type', choices=['db', 'org', 'all'],
                            default='all', help='Which card type to generate (default: all)')
        parser.add_argument('--force', action='store_true',
                            help='Recreate all Twitter card images, even if up to date')
        parser.add_argument('--skip-errors', action='store_true',
                            help='Ignore errors and keep processing')

    def handle(self, *args, **options):
        assert os.path.exists(settings.TWITTER_CARD_TEMPLATE), \
            "Missing: " + settings.TWITTER_CARD_TEMPLATE

        card_type = options['card_type']
        force = options['force']
        name_filter = options.get('name')
        if name_filter:
            force = True

        if card_type in ('db', 'all'):
            self._process_systems(name_filter, force, options['skip_errors'])
        if card_type in ('org', 'all'):
            self._process_orgs(name_filter, force, options['skip_errors'])

    def _process_systems(self, name_filter, force, skip_errors):
        versions = SystemVersion.objects.filter(is_current=True)
        if name_filter:
            if name_filter.isdigit():
                versions = versions.filter(system__id=int(name_filter))
            else:
                versions = versions.filter(system__name__icontains=name_filter)

        for ver in versions:
            card_img = os.path.join(settings.TWITTER_CARD_ROOT, ver.get_twitter_card_image())
            logo_img = os.path.join(settings.MEDIA_ROOT, ver.logo.name) if ver.logo else None

            if not force:
                if os.path.exists(card_img) and logo_img and os.path.exists(logo_img):
                    if os.path.getmtime(logo_img) <= os.path.getmtime(card_img):
                        continue
                elif os.path.exists(card_img):
                    continue
            try:
                create_twitter_card(ver)
            except Exception:
                LOG.error("FAIL: %s -> %s", ver.get_twitter_card_name(), card_img)
                if not skip_errors:
                    raise
            LOG.info("%s -> %s", ver.get_twitter_card_name(), card_img)

    def _process_orgs(self, name_filter, force, skip_errors):
        orgs = Organization.objects.exclude(logo='').exclude(logo__isnull=True)
        if name_filter:
            if name_filter.isdigit():
                orgs = orgs.filter(id=int(name_filter))
            else:
                orgs = orgs.filter(
                    Q(name__icontains=name_filter) |
                    Q(slug__icontains=name_filter)
                )

        for org in orgs:
            card_img = os.path.join(settings.TWITTER_CARD_ROOT, org.get_twitter_card_image())
            logo_img = os.path.join(settings.MEDIA_ROOT, org.logo.name)

            if not force:
                if os.path.exists(card_img) and os.path.exists(logo_img):
                    if os.path.getmtime(logo_img) <= os.path.getmtime(card_img):
                        continue
                elif os.path.exists(card_img):
                    continue
            try:
                create_twitter_card(org)
            except Exception:
                LOG.error("FAIL: %s -> %s", org.get_twitter_card_name(), card_img)
                if not skip_errors:
                    raise
            LOG.info("%s -> %s", org.get_twitter_card_name(), card_img)
