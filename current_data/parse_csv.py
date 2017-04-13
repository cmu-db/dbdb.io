import csv
import json

from StringIO import StringIO

with open('systems.csv', 'r') as input_file:
  reader = csv.reader(input_file)
  for row in reader:
    name = row[0]
    website = row[1]

    if name:
      try:
        with open(name + '.json', 'w') as output_file:
          output_file.write(json.dumps({
            'Name': name,
            'Website': website
          }))
      except Exception as e:
        print e