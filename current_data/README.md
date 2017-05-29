# current_data directory README

This directory holds data on databases.
It also contains various scripts for creating the fixtures that can be loaded into the website's database.

## Directories:
* data/ - Text files with information on databases
* cleaned_data/ - Same files from data/ with parentheses, single quotes removed, boolean values fixed for JSON format (ignored by .gitignore)
* models_data/ - Text files with additional information on databases, most are repeats from data/
* cleaned_models_data/ - Same files from models_data/ with parentheses, single quotes removed, boolean values fixed for JSON format (ignored by .gitignore)

*See cleanfiles.py*

* json_data/ - Files parsed from systems.csv (not exactly necessary to convert to JSON)
* models_json_data/ - Models data converted to JSON

*See parse_model_data.py*

* spring2016/ - Json files from spring 2016 iteration of course

## Files:
* cleanfiles.py - Remove parentheses, single quotes and fix boolean values to convert JSON format
* feature_options.json - All options for defined for dbdb
* generate_options_fixtures.py - Generate fixtures for feature options
* generate_system_fixtures.py - Generate fixtures for database systems
* misc_scripts.py - Script for generating rankings (deprecated)
* models_data_output.txt - Error output for parse_model_data.py if issues arise with parsing

### Important
* parse_system_data.py - Parse system data and create fixtures. Creates fixtures of all systems in spring2016/, data/, json_data/
Saves system fixtures to systems/fixtures/ (ignored by .gitignore)

* system_data_output.txt - Error output for parse_system_data.py if issues arise with parsing
* systems.csv - CSV file of database systems
* systems.json - JSON file of database systems (same as systems.csv)