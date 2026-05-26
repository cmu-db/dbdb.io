from django.contrib.flatpages.models import FlatPage


def navbar_flatpages(request):
    pages = (
        FlatPage.objects
        .filter(meta__show_in_navbar=True)
        .order_by('meta__nav_order', 'title')
    )
    return {'navbar_flatpages': pages}