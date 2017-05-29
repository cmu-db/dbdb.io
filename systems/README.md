# systems directory README

This directory holds most of the control code for the dbdb website.

## Directories:
* fixtures/ - Fixtures for models that can be loaded up for the website using `python manage.py loaddata`
* migrations/ - Django migrations. If they do not exists, run `python manage.py makemigrations systems` *See root directory README*

## Files:
* admin.py - Lays out structure of admin pages for viewing, editing, filtering, etc
* forms.py - Defines forms for website, specifically the database editing form
* models.py - Defines all models
* serializers.py - Used for serializing models
* tests.py - Currently unused
* urls.py - Maps urls to view classes in views.py
* util.py - Provide utility function such as creating secret keys (for editing), and possibly in the future for resolving slug collision?
* vies.py - Main control code for the website. Defines all the views

### To add a feature to databases:
1. Add the feature and its options to feature_options.json in the current_data/
2. Add the supported, options, and description fields, as seen in models.py, following the same format
3. Add the feature in forms.py to the features list
4. Create the fixture by running current_data/generate_options_fixtures.py and using `loaddata`, the feature should be integrated

