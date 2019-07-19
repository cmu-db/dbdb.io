import environ # http://django-environ.readthedocs.io/


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
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    #'autoslug',
    'bootstrap4',
    'easy_thumbnails',
    'django_countries',
    'haystack', # django-haystack

    'dbdb.core'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
            ],
            'string_if_invalid': 'ERR(%s)' if DEBUG else '',
        },
    },
]

APPEND_SLASH = False
LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'
ROOT_URLCONF = 'dbdb.urls'
WSGI_APPLICATION = 'dbdb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': env.db( default='sqlite:///{}'.format( root.path('data/db.sqlite3') ) )
}

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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


# Haystack
# https://django-haystack.readthedocs.io/

import xapian

HAYSTACK_XAPIAN_FLAGS = (
    xapian.QueryParser.FLAG_PHRASE |
    xapian.QueryParser.FLAG_BOOLEAN |
    xapian.QueryParser.FLAG_LOVEHATE |
    xapian.QueryParser.FLAG_WILDCARD |
    xapian.QueryParser.FLAG_PURE_NOT |
    xapian.QueryParser.FLAG_PARTIAL
)
HAYSTACK_XAPIAN_STEMMING_STRATEGY = 'STEM_ALL'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'xapian_backend.XapianEngine',
        'PATH': root.path('data/xapian')(),
        'FLAGS': HAYSTACK_XAPIAN_FLAGS,
    },
    # 'default': {
        # 'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        # 'PATH': root.path('data/whoosh')(),
    # },
}


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_L10N = False
USE_TZ = True

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
STATIC_ROOT = ''
STATIC_URL = '/static/'


# Thumbnails

THUMBNAIL_ALIASES = {
    '': {
        'thumb': {'size': (300, 300), 'crop': False},
        'search': {'size': (200, 200), 'crop': False},
        'homepage': {'size': (100, 60), 'crop': False},
        'recommendation': {'size': (200, 180), 'crop': False},
    },
}

# Django Countries
COUNTRIES_FIRST = ['US']

# Django Invisible reCaptcha
NORECAPTCHA_SITE_KEY = '6Lfo8VwUAAAAAEHNqeL01PSkiRul7ImQ8Bsw8Nqc'
NORECAPTCHA_SECRET_KEY = '6Lfo8VwUAAAAALFGUrGKqrzCR94pfgFahtd56WY9'
