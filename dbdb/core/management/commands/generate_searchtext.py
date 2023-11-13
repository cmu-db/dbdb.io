from django.core.management import BaseCommand

from dbdb.core.models import SystemSearchText
from dbdb.core.models import SystemVersion

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('system', metavar='S', type=str, nargs='?',
                    help='System to force search text genration')
        return

    def handle(self, *args, **options):

        versions = SystemVersion.objects.filter(is_current=True)
        if options['system']:
            keyword = options['system']
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        for s in versions.order_by("system__name"):
            sstext, created = SystemSearchText.objects.update_or_create(system=s.system)
            try:
                sstext.system = s.system
                sstext.name = s.system.name
                sstext.search_text = s.generate_searchtext()
                sstext.save()
                print("Added search text for %s [id=%d]" % (s.system.name, s.system.id))
            except:
                print("Failed", s.system)
                raise
    pass
