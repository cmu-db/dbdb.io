# stdlib imports
import os
import sys

# django imports
from django.core.management import BaseCommand
from django.conf import settings

from dbdb.core.utils import *
from dbdb.core.models import SystemVersion
from dbdb.core.utils import logos

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('system', metavar='S', type=str, nargs='?',
                    help='System to extract logo information')
        parser.add_argument('--skip-errors', action='store_true',
                            help="Ignore errors and keep processing")
        return

    def handle(self, *args, **options):
        versions = SystemVersion.objects.all() # filter(is_current=True)
        if options['system']:
            keyword = options['system']
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        cache = { } # logo_img -> (color, height, width)
        for ver in versions.order_by("system__name", "id"):
            logo_img = os.path.join(settings.MEDIA_ROOT, ver.logo.name)
            if not logo_img or os.path.isdir(logo_img): continue

            logo_color, logo_width, logo_height = None, None, None
            if logo_img not in cache:
                try:
                    color = logos.extract_color(str(logo_img), exclude_dark=True)
                    logo_color = logos.color_to_hex(color)
                    logo_width, logo_height = logos.extract_dimensions(str(logo_img))
                    cache[logo_img] = (logo_color, logo_width, logo_height)
                except:
                    self.stderr.write(f"FAIL: {ver} -> {logo_img}")
                    if not options['skip_errors']: raise
                    continue
            else:
                logo_color, logo_width, logo_height = cache[logo_img]

            ver.logo_color = logo_color
            ver.logo_width = logo_width
            ver.logo_height = logo_height
            ver.save()
            self.stdout.write(f"{ver} -> {ver.logo_color} [{ver.logo_width}x{ver.logo_height}]")

        # FOR
        return

    pass
