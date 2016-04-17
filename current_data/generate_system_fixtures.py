#!/usr/bin/env python

import os
import sys
import csv
import re
import string
import json

sys.path.append("..")
from systems import util

entries = [ ]
with open('systems.csv', 'r') as fd:
    systems = [ row[0] for row in csv.reader(fd) ]
    
    pk = 1
    for name in map(string.strip, sorted(systems)):
        if len(name) == 0: continue
        fields = {
            "name": name,
            "secret_key": util.generateSecretKey()
        }
        data = {
            "pk": pk,
            "model": "systems.System",
            "fields": fields
        }
        entries.append(data)
        pk += 1
    ## FOR
## WITH

print json.dumps(entries, indent=3, separators=(',', ': '))
