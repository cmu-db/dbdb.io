# stdlib imports
# django imports
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from dbdb.core.models import SystemACL, SystemVersion


class Command(BaseCommand):

    def handle(self, *args, **options):
        User = get_user_model()
        for user in User.objects.all():
            if user.username == "developer" or user.is_superuser: continue

            systems = set()
            # Find what systems this user has editted
            for ver in SystemVersion.objects.filter(creator=user):
                if ver.system not in systems:
                    acl = SystemACL(system=ver.system, user=user)
                    acl.save()
                    print(acl)
                systems.add(ver.system)
            #if len(systems) > 0:
                #print("%s: [%s]" % (user.username, ",".join([ s.name for s in systems ])))
        ## FOR
        return

    pass
