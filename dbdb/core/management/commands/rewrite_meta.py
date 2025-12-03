from django.core.management import BaseCommand

from dbdb.core.models import SystemSearchText
from dbdb.core.models import SystemVersion

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('system', metavar='S', type=str, nargs='?',
                    help='System to force search text genration')
        return

    def handle(self, *args, **options):

        versions = SystemVersion.objects.all() # filter(is_current=True)
        if options['system']:
            keyword = options['system']
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        for ver in versions.order_by("system__name"):
            # Copy the old meta information into the version object

            try:
                ver.derived_from.clear()
                if ver.meta is not None and ver.meta.derived_from is not None:
                    for d in ver.meta.derived_from.all():
                        ver.derived_from.add(d)
                    self.stdout.write(f"Copied meta data for {ver} [id={ver.system.id}]")
                    self.stdout.write(" => " + ",".join(map(str, ver.derived_from.all())))
                ver.save()
            except:
                self.stdout.write(f"Failed: {ver}")
                raise
    pass
