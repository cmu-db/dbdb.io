from django.conf.urls import url
from django.views.generic.base import TemplateView
from django.conf import settings
# project imports
from dbdb.core import views

urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name="home"),

    url(r'^db/(?P<slug>[\w-]+)$', views.SystemView.as_view(), name='system'),
    url(r'^db/(?P<slug>[\w-]+)/edit$', views.DatabasesEditView.as_view(), name='system_edit'),
    url(r'^db/(?P<slug>[\w-]+)/revisions/$', views.DatabaseRevisionList.as_view(), name='system_revision'),
    url(r'^db/(?P<slug>[\w-]+)/revisions/(?P<ver>\d+)$', views.DatabaseRevisionView.as_view(), name='system_revision_view'),
    url(r'^db/create$', views.CreateDatabase.as_view(), name='create_database'),
    url(r'^db/create/(?P<id>\d+)/(?P<kind>meta)/$', views.CreateDatabase.as_view(), name='create_db_meta'),

    url(r'^browse$', views.DatabaseBrowseView.as_view(), name='browse'),
    url(r'^search$', views.SearchView.as_view(), name='search'),
    url(r'^search/advanced$', views.AdvancedSearchView.as_view(), name='advanced_search'),

    url(r'^user/create$', views.CreateUser.as_view(), name='create_user'),

    url(r'^counter$', views.CounterView.as_view(), name='counter'),
]
