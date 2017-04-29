import os
import sys

sys.path.append('data')
sys.path.append('models_data')

dirs = {
    'data/': 'cleaned_data/',
    'models_data/': 'cleaned_models_data/'
}

for directory in dirs:
    files = os.listdir(directory)
    for f in files:
        if not os.path.exists(dirs[directory]):
            os.makedirs(dirs[directory])
        with open(directory + f, 'r') as infile, open(dirs[directory] + f, 'w') as outfile:
            for line in infile:
                outfile.write(line.replace('(', '')
                              .replace(')', '')
                              .replace("'", '"')
                              .replace('": True, "', '": true, "')
                              .replace('": False, "', '": false, "'))