# django imports
from django.conf import settings
from django.conf.urls import url
from django.urls import path
from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView
from django.views.decorators.cache import cache_page
# project imports
from dbdb.core import views


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name="home"),

    url(r'^db/(?P<slug>[\w-]+)[/]?$', views.SystemView.as_view(), name='system'),
    url(r'^db/(?P<slug>[\w-]+)/edit$', views.DatabasesEditView.as_view(), name='system_edit'),
    url(r'^db/(?P<slug>[\w-]+)/revisions/$', views.DatabaseRevisionList.as_view(), name='system_revision'),
    url(r'^db/(?P<slug>[\w-]+)/revisions/(?P<ver>\d+)$', views.DatabaseRevisionView.as_view(), name='system_revision_view'),

    url(r'^create$', views.DatabasesEditView.as_view(), name='create_database'),
    url(r'^browse$', views.DatabaseBrowseView.as_view(), name='browse'),
    url(r'^fields$', views.EmptyFieldsView.as_view(), name='empty_fields'),
    url(r'^search$', views.DatabaseBrowseView.as_view(), name='search'),
    url(r'^recent$', views.RecentChangesView.as_view(), name='recent'),
    url(r'^search/autocomplete/$', views.search_autocomplete, name='search_autocomplete'),
    url(r'^search/advanced$', views.DatabaseBrowseView.as_view(), name='advanced_search'),
    url(r'^stats[/]?$', views.StatsView.as_view(), name='stats'),
    url(r'^stats(?:/(?P<stats_type>[\w]+))$', views.StatsView.as_view(), name='stats_detailed'),

    path('user/create', views.CreateUserView.as_view(), name='create_user'),
    path('user/create/', RedirectView.as_view(pattern_name='create_user')),
    path('user/setup', views.SetupUserView.as_view(), name='setup_user'),

    path('counter', views.CounterView.as_view(), name='counter'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap'),
]
