# stdlib imports
import os

# django imports
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVersionMetadata
from dbdb.core.views import EmptyFieldsView

class Command(BaseCommand):

    def handle(self, *args, **options):
        template = os.path.join(settings.BASE_DIR, "static", settings.TWITTER_CARD_TEMPLATE)
        assert os.path.exists(template), "Missing: " + template

        ctr = 10
        for ver in SystemVersion.objects.filter(is_current=True):
            card_img = os.path.join(settings.TWITTER_CARD_ROOT, ver.get_twitter_card_image())
            if not ver.logo:
                print("SKIP:", ver.system.name)
            
            print(ver.system.name, "->", card_img)
            ver.create_twitter_card()
            
            ctr = ctr - 1
            if ctr == 0: break
        # FOR
        return

    pass
