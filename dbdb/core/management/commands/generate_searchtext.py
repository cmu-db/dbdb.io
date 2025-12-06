from django.core.management import BaseCommand

from dbdb.core.models import SystemSearchText
from dbdb.core.models import SystemVersion
from dbdb.core.utils.searchtext import generate_searchtext


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

        for ver in versions.order_by("system__name"):
            sstext, created = SystemSearchText.objects.update_or_create(system=ver.system)
            try:
                sstext.system = ver.system
                sstext.name = ver.system.name
                sstext.search_text = generate_searchtext(ver)
                sstext.save()
                print(f"Added search text for {ver}")
            except:
                print(f"Failed to update search text for {ver}")
                raise
    pass
