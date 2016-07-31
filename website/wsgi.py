"""
WSGI config for DBDB.IO project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")


application = get_wsgi_application()
