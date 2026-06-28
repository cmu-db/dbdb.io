from django.conf import settings
from django.contrib.flatpages.models import FlatPage


def navbar_flatpages(request):
    pages = (
        FlatPage.objects
        .filter(meta__show_in_navbar=True)
        .order_by('meta__nav_order', 'title')
    )
    return {
        'navbar_flatpages':     pages,
        'DBDB_SITE_NAME':            settings.DBDB_SITE_NAME,
        'DBDB_SITE_TAGLINE':         settings.DBDB_SITE_TAGLINE,
        'DBDB_SITE_OGIMAGE':         settings.DBDB_SITE_OGIMAGE,
        'DBDB_SITE_FAVICON':         settings.DBDB_SITE_FAVICON,
        'DBDB_TITLE_SEPARATOR':      settings.DBDB_TITLE_SEPARATOR,
        'DBDB_META_DATETIME_FORMAT': settings.DBDB_META_DATETIME_FORMAT,
        'DBDB_FOUNDING_YEAR':   settings.DBDB_FOUNDING_YEAR,
        'FONTAWESOME_CSS_URL':  settings.FONTAWESOME_CSS_URL,
    }