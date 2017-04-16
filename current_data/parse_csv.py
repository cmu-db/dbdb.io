import csv
import json
import sys

directory = 'json_data/'
sys.path.append(directory)

with open('systems.csv', 'r') as input_file:
  reader = csv.reader(input_file)
  for row in reader:
    name = row[0]
    website = row[1]

    if name:
      try:
        with open(directory + name + '.json', 'w') as output_file:
          output_file.write(json.dumps({
            'Name': name,
            'Website': website
          },
            indent=4))
      except Exception as e:
        print e