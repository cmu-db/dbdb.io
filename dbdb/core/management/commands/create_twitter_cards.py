# stdlib imports
import os
import sys

# django imports
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVersionMetadata
from dbdb.core.views import EmptyFieldsView

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('system', metavar='S', type=str, nargs='?',
                    help='System to force twiter card creation')
        parser.add_argument('--skip-errors', action='store_true',
                            help="Ignore errors and keep processing")
        return

    def handle(self, *args, **options):
        template = os.path.join(settings.BASE_DIR, "static", settings.TWITTER_CARD_TEMPLATE)
        assert os.path.exists(template), "Missing: " + template

        versions = SystemVersion.objects.filter(is_current=True)
        force = False
        if options['system']:
            keyword = options['system']
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)
            force = True

        for ver in versions:
            card_img = os.path.join(settings.TWITTER_CARD_ROOT, ver.get_twitter_card_image())
            logo_img = os.path.join(settings.MEDIA_ROOT, ver.logo.name)
            
            # Only create ones that are missing or where the logo 
            # is newer than the existing twitter image
            if not force:
                if os.path.exists(card_img) and os.path.exists(logo_img):
                    if os.path.getmtime(logo_img) <= os.path.getmtime(card_img):
                        #print(logo_img, "=>", os.path.getmtime(logo_img))
                        #print(card_img, "=>", os.path.getmtime(card_img))
                        #self.stdout.write("SKIP: %s -> %s" % (ver.system.name, card_img))
                        continue
                elif os.path.exists(card_img):
                    continue
            try:
                ver.create_twitter_card()
            except:
                self.stdout.write("FAIL: %s -> %s" % (ver.system.name, card_img))
                if not options['skip_errors']: raise
            self.stdout.write("%s -> %s" % (ver.system.name, card_img))
        # FOR
        return

    pass
