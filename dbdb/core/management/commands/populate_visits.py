# stdlib imports
import glob
import gzip
import re
import os
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
    "fauna": "faunadb",
    "brtylyt": "brytlyt",
    "sirix": "sirixdb",
    "goldstar": "gold-star",
    "goldstart": "gold-star",
    "eventstore": "event-store",
    "microsoft-access": "access",
    "cincom-total": "total",
    "azure-cosmos-db": "cosmos-db",
    "project-voldemort": "voldemort",
    "dali": "datablitz",
    "berkeleydb": "berkeley-db",
    "sql-server": "microsoft-sql-server",
}
SLUGS_TO_IGNORE = [
    "extenium",
    "terraindb",
    "redland",
    "giraph",
    "wei-cui",
    "ganesha",
    "sisodb",
]

APACHE_REGEX = re.compile('([(\d\.)]+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"')

SYS_REGEX = re.compile('/db/([\w\d\-]+)')


class Command(BaseCommand):
    
    def add_arguments(self, parser):
        parser.add_argument('log_dir', type=str)
        return

    def handle(self, *args, **options):
        
        log_dir = options['log_dir']
        assert os.path.exists(log_dir)
        
        for x in glob.glob(os.path.join(log_dir, "*.gz")):
            self.stdout.write(x)
            with gzip.open(x, 'r') as fd:
                for line in fd:
                    if not line: continue
                    line = line.decode("utf-8")
                
                    m = APACHE_REGEX.match(line)
                    if not m:
                        self.stdout.write(line)
                        continue
                        #sys.exit(1)
                    
                    # We only care about the counter page
                    if m.groups()[2].find("/counter") == -1: continue

                    # And it has to load correctly
                    if m.groups()[3] != "200": continue

                    # And we can skip bots
                    if m.groups()[6].lower().find("bot") != -1:
                        continue
                        #self.stdout.write(m.groups())
                        #sys.exit(1)

                    # IP ADDRESS
                    ip = m.groups()[0]
                    
                    # TIMESTAMP
                    t = m.groups()[1]
                    timestamp = dateutil.parser.parse(t[:11] + " " + t[12:])
                    
                    # USER AGENT
                    ua = m.groups()[-1][:127]
                    #self.stdout.write(ua)
                    
                    # SYSTEM
                    sys_m = SYS_REGEX.search(m.groups()[5])
                    if not sys_m: continue
                    
                    keyword = sys_m.groups()[0].strip().lower()
                    orig_keyword = keyword
                    
                    if keyword in SLUGS_TO_IGNORE: 
                        # self.stdout.write("Ignored Slug: " + keyword)
                        continue
                    
                    if keyword in MANUAL_FIXES:
                        keyword = MANUAL_FIXES[keyword]
                    if keyword not in ["sybase-iq", "google-f1"]:
                        for prefix in ["amazon", "apache", "sybase", "google"]:
                            keyword = keyword.replace(prefix+"-", "")
                    
                    try:
                        system = System.objects.get(slug=keyword)
                    except:
                        # Check the slug and former name
                        try:       
                            vers = SystemVersion.objects.filter( \
                                Q(former_names__icontains=keyword)
                            #| Q(former_names__icontains=keyword)
                            ).order_by('-id')
                            if len(vers) > 0:
                                system = vers[0].system
                                # self.stdout.write(keyword + " => " + system.slug)
                        except:
                            raise
                            #pass
                        pass
                    if not system:
                        self.stdout.write("Bad Slug: %s (orig=%s)" % (keyword, orig_keyword))
                        sys.exit(1)
                        #self.stdout.write("MISSING: slug = " + keyword)
                    
                    if system is None: continue
                        #raise

                    # Store it!
                    system_visit = SystemVisit(system=system, ip_address=ip, user_agent=ua, created=timestamp)
                    system_visit.save()
                    #self.stdout.write(str(system_visit) + " -- " + m.groups()[6])
                ## FOR
        ## FOR

        return

    pass
