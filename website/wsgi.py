"""
WSGI config for DBDB.IO project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "..")))

os.environ["DJANGO_SETTINGS_MODULE"] = "website.settings"
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
