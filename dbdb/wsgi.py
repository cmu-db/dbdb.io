"""
WSGI config for dbdb project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os
import sys

base_dir = os.path.dirname(os.path.dirname(__file__))

# Change the env variable where django looks for the settings module
# http://stackoverflow.com/a/11817088
import django.conf
django.conf.ENVIRONMENT_VARIABLE = "DJANGO_DBDBIO_SETTINGS_MODULE"
os.environ.setdefault("DJANGO_DBDBIO_SETTINGS_MODULE", "dbdb.settings")
sys.path.append(base_dir)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
