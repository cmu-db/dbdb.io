from django.core.management import BaseCommand

from dbdb.core.models import SystemSearchText
from dbdb.core.models import SystemVersion

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('system', metavar='S', type=str, nargs='?',
                    help='System to force rewriting SystemVersionMeta information')
        return

    def print_copy(self, label, objects):
        if objects is not None and objects.count() > 0:
            self.stdout.write(f"  {label}: " + ",".join(map(str, objects)))
        else:
            self.stdout.write(f'  {label}?: {objects}')

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
            if ver.meta is None: continue

            try:
                self.stdout.write(f"Copying meta data for {ver} [id={ver.system.id}]")

                ver.derived_from.clear()
                for x in ver.meta.derived_from.all(): ver.derived_from.add(x)
                self.print_copy("Derived", ver.derived_from.all())

                ver.embedded.clear()
                for x in ver.meta.embedded.all(): ver.embedded.add(x)
                self.print_copy("Embedded", ver.embedded.all())

                ver.inspired_by.clear()
                for x in ver.meta.inspired_by.all(): ver.inspired_by.add(x)
                self.print_copy("Inspired", ver.inspired_by.all())

                ver.compatible_with.clear()
                for x in ver.meta.compatible_with.all(): ver.compatible_with.add(x)
                self.print_copy("Compatible", ver.compatible_with.all())

                ver.licenses.clear()
                for x in ver.meta.licenses.all(): ver.licenses.add(x)
                self.print_copy("Licenses", ver.licenses.all())

                ver.oses.clear()
                for x in ver.meta.oses.all(): ver.oses.add(x)
                self.print_copy("OS", ver.oses.all())

                ver.supported_languages.clear()
                for x in ver.meta.supported_languages.all(): ver.supported_languages.add(x)
                self.print_copy("SupportedLangs", ver.supported_languages.all())

                ver.written_in.clear()
                for x in ver.meta.written_in.all(): ver.written_in.add(x)
                self.print_copy("WrittenIn", ver.written_in.all())

                ver.save()
            except:
                self.stdout.write(f"Failed: {ver}")
                raise
    pass
