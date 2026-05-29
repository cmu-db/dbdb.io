# django imports
from django.urls import path, re_path
from django.views.generic.base import RedirectView

# project imports
from dbdb.core import views

urlpatterns = [
    path('', views.HomeView.as_view(), name="home"),

    re_path(r'^db/(?P<slug>[\w-]+)[/]?$', views.SystemView.as_view(), name='system'),
    re_path(r'^db/(?P<slug>[\w-]+)/edit$', views.SystemEditView.as_view(), name='system_edit'),
    re_path(r'^db/(?P<slug>[\w-]+)/revisions/$', views.RecentChangesView.as_view(), name='system_revision'),
    re_path(r'^db/(?P<slug>[\w-]+)/revisions/(?P<ver>\d+)$', views.SystemRevisionView.as_view(), name='system_revision_view'),

    path('browse', views.BrowseView.as_view(), name='browse'),
    path('search', views.BrowseView.as_view(), name='search'),
    path('api/systems/autocomplete/', views.system_autocomplete, name='system_autocomplete'),
    path('api/organizations/autocomplete/', views.organization_autocomplete, name='organization_autocomplete'),
    path('search/advanced', views.BrowseView.as_view(), name='advanced_search'),

    path('create', views.SystemEditView.as_view(), name='create_system'),
    path('recent', views.RecentChangesView.as_view(), name='recent'),

    re_path(r'^stats[/]?$', views.StatsView.as_view(), name='stats'),
    re_path(r'^stats(?:/(?P<stats_type>[\w]+))$', views.StatsView.as_view(), name='stats_detailed'),

    path('fields', views.EmptyFieldsView.as_view(), name='empty_fields'),

    path('user/create', views.CreateUserView.as_view(), name='create_user'),
    path('user/create/', RedirectView.as_view(pattern_name='create_user')),
    path('user/setup', views.SetupUserView.as_view(), name='setup_user'),

    path('counter', views.CounterView.as_view(), name='counter'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap'),
]

