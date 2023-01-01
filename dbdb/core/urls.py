# django imports
from django.urls import re_path, path
from django.views.generic.base import RedirectView
# project imports
from dbdb.core import views


urlpatterns = [
    re_path(r'^$', views.HomeView.as_view(), name="home"),

    re_path(r'^db/(?P<slug>[\w-]+)[/]?$', views.SystemView.as_view(), name='system'),
    re_path(r'^db/(?P<slug>[\w-]+)/edit$', views.DatabasesEditView.as_view(), name='system_edit'),
    re_path(r'^db/(?P<slug>[\w-]+)/revisions/$', views.DatabaseRevisionList.as_view(), name='system_revision'),
    re_path(r'^db/(?P<slug>[\w-]+)/revisions/(?P<ver>\d+)$', views.DatabaseRevisionView.as_view(), name='system_revision_view'),

    re_path(r'^create$', views.DatabasesEditView.as_view(), name='create_database'),
    re_path(r'^browse$', views.DatabaseBrowseView.as_view(), name='browse'),
    re_path(r'^fields$', views.EmptyFieldsView.as_view(), name='empty_fields'),
    re_path(r'^search$', views.DatabaseBrowseView.as_view(), name='search'),
    re_path(r'^recent$', views.RecentChangesView.as_view(), name='recent'),
    re_path(r'^search/autocomplete/$', views.search_autocomplete, name='search_autocomplete'),
    re_path(r'^search/advanced$', views.DatabaseBrowseView.as_view(), name='advanced_search'),
    re_path(r'^stats[/]?$', views.StatsView.as_view(), name='stats'),
    re_path(r'^stats(?:/(?P<stats_type>[\w]+))$', views.StatsView.as_view(), name='stats_detailed'),

    path('user/create', views.CreateUserView.as_view(), name='create_user'),
    path('user/create/', RedirectView.as_view(pattern_name='create_user')),
    path('user/setup', views.SetupUserView.as_view(), name='setup_user'),

    path('counter', views.CounterView.as_view(), name='counter'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap'),
]
