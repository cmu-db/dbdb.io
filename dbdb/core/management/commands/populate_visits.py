# stdlib imports
import glob
import gzip
import re
import sys
import dateutil.parser

# django imports
from django.core.management import BaseCommand
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import get_user_model

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVisit


MANUAL_FIXES = {
    "firstsql": "firstsqlj",
    "sybase-ads": "advantage-database-server",
    "sybase-ase": "adaptive-server-enterprise",
    "scylla-db": "scylla",
    "infinitum": "blobcity",
    "concoursedb": "concourse",
    "northgate-reality": "reality",
    "raima-database-server": "raima-database-manager",
    "blazingdb": "blazingsql",
    "citusdb": "citus",
    "akumulidb": "akumuli",
    "": "",
}

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
                        continue
                        #sys.exit(1)
                    
                    # We only care about the counter page
                    if m.groups()[2].find("/counter") == -1: continue

                    # And it has to load correctly
                    if m.groups()[3] != "200": continue

                    # And we can skip bots
                    #if m.groups()[6].lower().find("bot") != -1:
                        #print(m.groups())
                        #sys.exit(1)

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
                        # print(m.groups())
                        continue
                        #sys.exit(1)
                    
                    keyword = sys_m.groups()[0].strip()
                    if keyword in MANUAL_FIXES:
                        keyword = MANUAL_FIXES[keyword]
                    if not keyword == "sybase-iq":
                        for prefix in ["amazon", "apache", "sybase"]:
                            keyword = keyword.replace(prefix+"-", "")
                    
                    try:
                        system = System.objects.get(slug=keyword)
                    except:
                        # Check the slug and former name
                        try:       
                            system_version =  SystemVersion.objects.get( \
                                Q(former_names__icontains=keyword) |
                                Q(former_names__icontains=keyword)
                            )
                            system = system_version.system
                            print(keyword + " => " + system.slug)
                        except:
                            print("Slug: " + keyword)
                            raise
                            pass
                        pass
                    if not system:
                        print("MISSING: slug = " + keyword)
                    
                    if system is None: continue
                        #raise

                    # Store it!
                    # system_visit = SystemVisit(system=system, ip_address=ip, created=timestamp)
                    # system_visit.save()
                    #print(str(system_visit) + " -- " + m.groups()[6])
                    
        ## FOR

        return

    pass
