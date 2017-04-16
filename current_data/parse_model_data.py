import json
import os
import sys

directory_in = 'cleaned_models_data/'
directory_out = 'models_json_data/'

sys.path.append('cleaned_models_data/')
sys.path.append('models_json_data/')

files = os.listdir('cleaned_models_data/')
print_output = {}
for f in files:
    filename = directory_in + f
    with open(filename, 'r') as input_file, open((directory_out + f).replace('txt', 'json'), 'w') as output_file:

            system = {}
            for line in input_file:
                try:
                    system.update(json.loads(line))
                except Exception as e:
                    if print_output.get(filename):
                        print_output[filename].append(str(e))
                    else:
                        print_output[filename] = [str(e)]
            output_file.write(json.dumps(system, indent=4))


with open('models_data_output.txt', 'w') as error_file:
    error_file.write(json.dumps(print_output, indent=4))
    print 'Output can be found in models_data_output.txt'

metadata_mapping = {
    "Name": "name",
    "Description": "description",
    "Website": "website",
    "Technical documentation": "tech_docs", # html href
    "Developer": "developer",
    "Initial release": "start_year",
}

manytomany_mapping = {
    "Database model": "dbmodel", # list of models
    "License": "license", # list of liscenses
    "APIs and other access methods": "access_methods", # list of things
    "Implementation language": "written_in", #list of languages"
    "Server operating systems": "oses",
    "Supported programming languages": "support_languages"
}

features_mapping = {
    "SQL": "sql", #yes no
    "Foreign keys": "foreignkeys", #yes, no
    "Server-side scripts": "serverside", #yes, no, javascript
    "MapReduce": "mapreduce", # no, yes
    "Secondary indexes": "secondary", # yes,no, resitricted
    "Durability": "durability",
    "Triggers": "triggers", # yes or no
    "Concurrency": "concurrency", # yes or not there
    "Data scheme": "datascheme", # yes or schema-free
    "XML support": "xml",
    "Typing": "typing",
    "User concepts": "userconcepts",
    "Transaction concepts": "transactionconcepts",
}
