# stdlib imports
import os
import sys

# django imports
from django.core.management import BaseCommand
from django.conf import settings

from dbdb.core.utils import *
from dbdb.core.models import SystemVersion

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('system', metavar='S', type=str, nargs='?',
                    help='System to calculate logo color')
        parser.add_argument('--skip-errors', action='store_true',
                            help="Ignore errors and keep processing")
        return

    def handle(self, *args, **options):
        versions = SystemVersion.objects.filter(is_current=True)
        if options['system']:
            keyword = options['system']
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        for ver in versions:
            logo_img = os.path.join(settings.MEDIA_ROOT, ver.logo.name)
            # if ver.logo_color: continue

            if logo_img and not os.path.isdir(logo_img):
                try:
                    color = extract_color(str(logo_img))
                    ver.logo_color = color_to_hex(color)
                    self.stdout.write("%s -> %s" % (ver.system.name, color_to_hex(color)))
                except:
                    self.stdout.write("FAIL: %s -> %s" % (ver.system.name, logo_img))
                    if not options['skip_errors']: raise
            else:
                # Default color is a neutral gray
                ver.logo_color = "#bababa"

            ver.save()
        # FOR
        return

    pass
