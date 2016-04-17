#!/usr/bin/env python

import os
import sys
import csv
import re
import string
import json
from pprint import pprint

sys.path.append("..")
from systems import util

# First load in all of the features to get their ids
features = { }
with open('../systems/fixtures/features.json', 'r') as fd:
    data = json.loads(fd.read())
    for x in data:
        f_label = x["fields"]["label"]
        f_id = int(x["pk"])
        features[f_label] = f_id
    ## FOR
## WITH
#pprint(sorted(features.keys()))

# Then load in our template taxonomy and generate the fixture
entries = [ ]
with open('feature_options.json', 'r') as fd:
    data = json.loads(fd.read())
    
    pk = 1
    for feature in data.keys():
        for option in data[feature]:
            assert feature in features, "Missing Feature: '%s'" % feature
            entry = {
                "pk": pk,
                "model": "systems.FeatureOption",
                "fields": {
                    "feature": features[feature],
                    "value": option
                }
            }
            entries.append(entry)
            pk += 1
        ## FOR
    ## FOR
## WITH
print json.dumps(entries, indent=3, separators=(',', ': '))
