# stdlib imports
import os

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
        parser.add_argument('--system', type=str)
        return

    def handle(self, *args, **options):
        template = os.path.join(settings.BASE_DIR, "static", settings.TWITTER_CARD_TEMPLATE)
        assert os.path.exists(template), "Missing: " + template
        
        versions = SystemVersion.objects.filter(is_current=True)
        if options['system']:
            keyword = options['system']
            
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)
        
        for ver in versions:
            card_img = os.path.join(settings.TWITTER_CARD_ROOT, ver.get_twitter_card_image())
            if not ver.logo:
                self.stdout.write("SKIP: %s" % ver.system.name)
            
            self.stdout.write("%s -> %s" % (ver.system.name, card_img))
            ver.create_twitter_card()
            
        # FOR
        return

    pass
