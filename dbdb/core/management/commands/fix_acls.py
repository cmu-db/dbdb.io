# stdlib imports
# django imports
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemACL

class Command(BaseCommand):

    def handle(self, *args, **options):
        User = get_user_model()
        for user in User.objects.all():
            if user.username == "developer" or user.is_superuser: continue
            
            systems = set()
            # Find what systems this user has editted
            for ver in SystemVersion.objects.filter(creator=user):
                if not ver.system in systems:
                    acl = SystemACL(system=ver.system, user=user)
                    acl.save()
                    print(acl)
                systems.add(ver.system)
            #if len(systems) > 0:
                #print("%s: [%s]" % (user.username, ",".join([ s.name for s in systems ])))
        ## FOR
        return

    pass
