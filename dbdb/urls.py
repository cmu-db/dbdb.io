# django imports
from django.urls import path
from django.urls import re_path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
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
