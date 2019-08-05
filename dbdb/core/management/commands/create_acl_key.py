# stdlib imports
# django imports
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from dbdb.core.views import SystemACLCheck

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemACL

import jwt


class Command(BaseCommand):
    
    def add_arguments(self, parser):
        parser.add_argument('--system', action='append', type=str,
                            help="List of system slugs to add to key")

    def handle(self, *args, **options):
        assert options['system']
        
        systems = set()
        for slug in options['system']:
            systems.add(System.objects.get(slug=slug))
        print("Systems:", list([sys.name for sys in systems]))
            
        key = SystemACLCheck.encode(systems)
        print("Key:", key)
        
        result = jwt.decode(
            key.encode('utf-8'),
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        print("Result:", result)

        return

    pass
