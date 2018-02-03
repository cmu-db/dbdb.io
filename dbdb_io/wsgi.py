"""
WSGI config for DBDB.IO project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

base_dir = os.path.dirname(os.path.dirname(__file__))

# Change the env variable where django looks for the settings module
# http://stackoverflow.com/a/11817088
import django.conf
django.conf.ENVIRONMENT_VARIABLE = "DJANGO_DBDBIO_SETTINGS_MODULE"
os.environ.setdefault("DJANGO_DBDBIO_SETTINGS_MODULE", "dbdb_io.settings")
sys.path.append(base_dir)

# Activate virtual env
#env_dir = os.path.realpath(os.path.join(base_dir, "../../../env"))
#activate_env = os.path.expanduser(os.path.join(env_dir, "bin/activate_this.py"))
#execfile(activate_env, dict(__file__=activate_env))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()