# django imports
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=f'{settings.STATIC_URL}core/images/favicon.ico', permanent=True)),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),

    path('', include('django.contrib.auth.urls')),
    path('', include('dbdb.core.urls')),

    re_path(r'^admin/', admin.site.urls),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    pass
