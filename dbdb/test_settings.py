from dbdb.settings import *  # noqa: F401,F403

import environ
from django.test.runner import DiscoverRunner

env = environ.Env()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     env('PGDATABASE', default='postgres'),
        'USER':     env('PGUSER',     default='pavlo'),
        'PASSWORD': env('PGPASSWORD', default=''),
        'HOST':     env('PGHOST',     default=''),
        'PORT':     env('PGPORT',     default='5432'),
        'TEST': {'NAME': 'test_dbdb_io'},
    }
}


class FreshTestRunner(DiscoverRunner):
    """Always drop and recreate the test DB without prompting."""
    def __init__(self, **kwargs):
        kwargs['interactive'] = False
        super().__init__(**kwargs)


TEST_RUNNER = 'dbdb.test_settings.FreshTestRunner'

TURNSTILE_ENABLE = False
