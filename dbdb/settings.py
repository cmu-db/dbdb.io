import os

import environ  # http://django-environ.readthedocs.io/
from django.conf.locale.en import formats

root = environ.Path(__file__) - 2
env = environ.Env(
    DEBUG=(bool, False)
)
env.read_env(env_file=root('.env')) # reading .env file

BASE_DIR = root()
DEBUG = env('DEBUG') # False if not in os.environ

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.sites',
    'django.contrib.flatpages',

    #'autoslug',
    'django_bootstrap5',
    'easy_thumbnails',
    'django_countries',
    'colorfield',
    'captcha',
    'turnstile',
    'rest_framework', # djangorestframework
    'markdownify.apps.MarkdownifyConfig',
    'meta',

    'dbdb.core'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'dbdb.core.middleware.LowercasePathMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'dbdb.core.middleware.CloudflareAuthCacheMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]

if DEBUG:
    MIDDLEWARE.remove('django.middleware.cache.UpdateCacheMiddleware')
    MIDDLEWARE.remove('django.middleware.cache.FetchFromCacheMiddleware')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            root.path('templates')(),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dbdb.core.context_processors.navbar_flatpages',
            ],
            'string_if_invalid': 'ERR(%s)' if DEBUG else '',
        },
    },
]

SITE_ID = 1

APPEND_SLASH = False
LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'
ROOT_URLCONF = 'dbdb.urls'
WSGI_APPLICATION = 'dbdb.wsgi.application'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(filename)s:%(lineno)d %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'dbdb': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Uncomment to enable SQL query logging:
        # 'django.db.backends': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG',
        #     'propagate': False,
        # },
    },
}


# Database
DATABASES = {
    'default': env.db(default='postgres://localhost/dbdb_io'),
}

DEFAULT_AUTO_FIELD='django.db.models.AutoField'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# CACHE
CACHES = {
    'default': {
        #'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        #'LOCATION': 'dbdb_io_cache',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_L10N = False
formats.DATE_FORMAT = "Y-m-d"
formats.TIME_FORMAT = "H:i:s"
formats.DATETIME_FORMAT = f"{formats.DATE_FORMAT} {formats.TIME_FORMAT}"
DBDB_SV_DATETIME_FORMAT = "Y-m-d H:i"

FIXTURE_DIRS = [
    root.path('data/fixtures')(),
]

# Media files (uploads)
MEDIA_ROOT = root.path('media')()
MEDIA_URL = '/media/'

# Security
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])
SECRET_KEY = env('SECRET_KEY')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/
STATICFILES_DIRS = (
   root.path('static')(),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATIC_ROOT = os.path.join(BASE_DIR, 'static-live')
STATIC_URL = '/static/'

FONTAWESOME_CSS_URL = '//use.fontawesome.com/releases/v7.2.0/css/all.css'

# Custom Twitter Cards
TWITTER_CARD_ROOT = os.path.join(MEDIA_ROOT, 'twitter')
TWITTER_CARD_URL = MEDIA_URL + "twitter/"
TWITTER_URL = "https://twitter.com/"

TWITTER_CARD_TEMPLATE = os.path.join(STATIC_ROOT, '../static/core/images/dbdb_io-card-template.svg')
TWITTER_CARD_FONT_PATH = os.path.join(STATIC_ROOT, 'core/fonts/IBMPlexMono-Bold.ttf')
TWITTER_CARD_BASE_OFFSET_X = 250
TWITTER_CARD_MARGIN = 40
TWITTER_CARD_MAX_WIDTH = 1200 - TWITTER_CARD_MARGIN*2
TWITTER_CARD_MAX_HEIGHT = 630 - TWITTER_CARD_MARGIN*2

LINKEDIN_URL = "https://www.linkedin.com/"

# Logos
LOGO_DEFAULT_COLOR = "#d3d3d3"
THUMBNAIL_ALIASES = {
    '': {
        'thumb': {'size': (280, 250), 'crop': False},
        'search': {'size': (200, 200), 'crop': False},
        'homepage': {'size': (100, 60), 'crop': False},
        'stats': {'size': (60, 40), 'crop': False},
        'recent': {'size': (40, 40), 'crop': False},
        'recommendation': {'size': (200, 50), 'crop': False},
    },
}
THUMBNAIL_PRESERVE_EXTENSIONS = ['png', 'svg']

# Django Countries
COUNTRIES_FIRST = ['US']

# Django Invisible reCaptcha
RECAPTCHA_PUBLIC_KEY = '' # env('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = '' # env('RECAPTCHA_PRIVATE_KEY')

# Cloudflare Turnstile — set TURNSTILE_SITEKEY / TURNSTILE_SECRET in .env for production.
# The defaults below are Cloudflare's always-pass test keys (safe for development).
TURNSTILE_SITEKEY = env('TURNSTILE_SITEKEY', default='1x00000000000000000000AA')
TURNSTILE_SECRET  = env('TURNSTILE_SECRET',  default='1x0000000000000000000000000000000AA')
TURNSTILE_ENABLE  = env.bool('TURNSTILE_ENABLE', default=True)

# Email Configuration
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@dbdb.io')

# Markdown Configuration
MARKDOWNIFY = {
    "default": {
        "BLEACH": False
    }
}

DBDB_SITE_NAME            = 'Database of Databases'
DBDB_SITE_TAGLINE         = 'The Encyclopedia of Database Systems'
DBDB_SITE_FAVICON         = 'core/images/favicon.png'
DBDB_TITLE_SEPARATOR      = ' · '
DBDB_META_DATETIME_FORMAT = '%B %-d, %Y'

DBDB_FOUNDING_YEAR = 2017
DBDB_BOT_ACCOUNT = env('DBDB_BOT_ACCOUNT', default='dbdb-bot')
DBDB_HOME_LISTINGS_NUM_ENTRIES    = 5
DBDB_HOME_SAVEDSEARCH_NUM_ENTRIES = 3
DBDB_LEADERBOARD_NUM_ENTRIES      = 10
DBDB_AUTOCOMPLETE_CITATION_NUM_ENTRIES      = 12
DBDB_AUTOCOMPLETE_ORGANIZATION_NUM_ENTRIES  = 12
DBDB_AUTOCOMPLETE_SYSTEM_NUM_ENTRIES        = 10

# Repository scanning (collect_repo_info management command)
DBDB_SOURCEREPO_DIRECTORY = env('DBDB_SOURCEREPO_DIRECTORY', default='/tmp/dbdb/')
GITHUB_API_TOKEN   = env('GITHUB_API_TOKEN',   default='')
GITLAB_API_TOKEN   = env('GITLAB_API_TOKEN',   default='')
CODEBERG_API_TOKEN = env('CODEBERG_API_TOKEN', default='')
REPOSITORY_INACTIVITY_DAYS = 730 # two years

CRAWLER_USER_AGENT = env('CRAWLER_USER_AGENT', default='dbdb.io/1.0')

ANTHROPIC_API_KEY             = env('ANTHROPIC_API_KEY',             default='')
OPENAI_API_KEY                = env('OPENAI_API_KEY',                default='')
OPENAI_MODEL                  = env('OPENAI_MODEL',                  default='gpt-5.4-mini')
PERPLEXITY_API_KEY            = env('PERPLEXITY_API_KEY',            default='')
PERPLEXITY_MODEL              = env('PERPLEXITY_MODEL',              default='sonar-pro')
OLLAMA_MODEL                  = env('OLLAMA_MODEL',                  default='qwen3.6:35b')

CRAWLER_SPAM_CHECKER_MODEL            = env('CRAWLER_SPAM_CHECKER_MODEL', default='qwen3.6:35b')
CRAWLER_SPAM_CHECKER_FALLBACK_MODEL_A = env('CRAWLER_SPAM_CHECKER_FALLBACK_MODEL_A', default='qwen3.6:35b')
CRAWLER_SPAM_CHECKER_FALLBACK_MODEL_B = env('CRAWLER_SPAM_CHECKER_FALLBACK_MODEL_B', default='qwen3.6:35b')
CRAWLER_SPAM_VALIDATION_MODEL         = env('CRAWLER_SPAM_VALIDATION_MODEL', default='qwen3.6:35b')

# django-meta
META_SITE_PROTOCOL      = env('META_SITE_PROTOCOL', default='https')
META_SITE_DOMAIN        = env('META_SITE_DOMAIN',   default='dbdb.io')
META_SITE_NAME          = DBDB_SITE_NAME
META_USE_OG_PROPERTIES  = True
META_USE_TWITTER_PROPERTIES = True
META_TWITTER_TYPE       = 'summary'
META_USE_TITLE_TAG      = False
META_INCLUDE_KEYWORDS   = False
