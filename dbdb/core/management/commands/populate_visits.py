# stdlib imports
import glob
import gzip
import re
import sys
import dateutil.parser

# django imports
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVisit

class Command(BaseCommand):

    def handle(self, *args, **options):
        
        regex = re.compile('([(\d\.)]+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"')
        
        sys_regex = re.compile('/db/([\w\d\-]+)')
        
        for x in glob.glob("/home/pavlo/temp/logs/*.gz"):
            print(x)
            with gzip.open(x, 'r') as fd:
                for line in fd:
                    if not line: continue
                    line = line.decode("utf-8")
                
                    m = regex.match(line)
                    if not m:
                        print(line)
                        sys.exit(1)
                    
                    # We only care about the counter page
                    page = m.groups()[2]
                    if page.find("/counter") == -1: continue
                    #print(m.groups())
                    #sys.exit(1)
                    
                    # IP
                    ip = m.groups()[0]
                    
                    # TIMESTAMP
                    t = m.groups()[1]
                    timestamp = dateutil.parser.parse(t[:11] + " " + t[12:])
                    
                    # SYSTEM
                    sys_m = sys_regex.search(m.groups()[5])
                    if not sys_m:
                        print(m.groups())
                        sys.exit(1)
                    system = System.objects.get(slug=sys_m.groups()[0])

                    # Store it!
                    system_visit = SystemVisit(system=system, ip_address=ip, created=timestamp)
                    system_visit.save()
                    print(system)
                    print(ip)
                    print(timestamp)
                    sys.exit(1)
        ## FOR

        return

    pass
