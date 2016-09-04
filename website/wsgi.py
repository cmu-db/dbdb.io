"""
WSGI config for DBDB.IO project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

# Change the env variable where django looks for the settings module
# http://stackoverflow.com/a/11817088
import django.conf
django.conf.ENVIRONMENT_VARIABLE = "DJANGO_DBDBIO_SETTINGS_MODULE"
os.environ.setdefault("DJANGO_DBDBIO_SETTINGS_MODULE", "website.settings")
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
