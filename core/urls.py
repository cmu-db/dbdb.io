from django.conf.urls import url
from django.views.generic.base import TemplateView

from core.views import CreateDatabase, SystemView
from .views import CreateUser

urlpatterns = (
    url(r'^$', TemplateView.as_view(template_name='core/home.html')),
    url(r'^create_user/$', CreateUser.as_view()),
    url(r'^create-db/$', CreateDatabase.as_view()),
    url(r'^create-db/(?P<id>\d+)/(?P<kind>meta)/$', CreateDatabase.as_view(), name='create_db_meta'),
    url(r'^create-db/(?P<id>\d+)/(?P<kind>features)/$', CreateDatabase.as_view(), name='create_db_features'),
    url(r'^system/(?P<id>\d+)/$', SystemView.as_view(), name='system'),
)
