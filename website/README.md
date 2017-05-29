# website directory README

This directory is the front end portion of dbdb.

## Directories:
### static/
* admin - Admin directory
* css/ - All css files
* images/ - Some icons, also original and thumbnail version of database logos
* js/ - Javascript files
* rest_framework - For REST view, available at dbdb.io/all_systems

### templates/
about.html - About page for contributors
advanced_search.html - Advanced search page for searching based on options
base.html - Base html file all templates inherit from
database.html - Standard page for viewing a database
database_create.html - Page for creating new database
database_edit.html - Page for editing a database if given secret key
database_revision.html - Page for looking at revision of past databases
hompage.html - Front page of dbdb.io
missing_system.html - Suggest a new database system
search_page.html - Search databases based on common properties
