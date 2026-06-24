# django imports
from django.urls import path, re_path
from django.views.generic.base import RedirectView

# project imports
from dbdb.core import views

urlpatterns = [
    path('', views.HomeView.as_view(), name="home"),

    re_path(r'^db/(?P<slug>[\w-]+)[/]?$', views.SystemView.as_view(), name='system'),
    re_path(r'^org/(?P<slug>[\w-]+)[/]?$', views.OrganizationView.as_view(), name='organization'),
    re_path(r'^db/(?P<slug>[\w-]+)/edit$', views.SystemEditView.as_view(), name='system_edit'),
    re_path(r'^db/(?P<slug>[\w-]+)/revisions/$', views.RecentChangesView.as_view(), name='system_revision'),
    re_path(r'^db/(?P<slug>[\w-]+)/revisions/(?P<ver>\d+)$', views.SystemView.as_view(), name='system_version'),
    re_path(r'^db/(?P<slug>[\w-]+)/diff/(?P<ver1>\d+)/(?P<ver2>\d+)$', views.SystemVersionDiffView.as_view(), name='system_diff'),
    re_path(r'^db/(?P<slug>[\w-]+)/revisions/(?P<ver>\d+)/delete$', views.SystemVersionDeleteView.as_view(), name='system_version_delete'),
    re_path(r'^db/(?P<slug>[\w-]+)/logos$', views.SystemLogosView.as_view(), name='system_logos'),

    path('browse', views.BrowseView.as_view(), name='browse'),
    path('search', views.BrowseView.as_view(), name='search'),
    path('api/systems/autocomplete/', views.system_autocomplete, name='system_autocomplete'),
    path('api/organizations/autocomplete/', views.organization_autocomplete, name='organization_autocomplete'),
    path('api/citation-urls/autocomplete/', views.citation_url_autocomplete, name='citation_url_autocomplete'),
    path('search/advanced', views.BrowseView.as_view(), name='advanced_search'),

    path('create', views.SystemEditView.as_view(), name='create_system'),
    path('recent', views.RecentChangesView.as_view(), name='recent'),

    re_path(r'^stats[/]?$', views.StatsView.as_view(), name='stats'),
    re_path(r'^stats(?:/(?P<stats_type>[\w]+))$', views.StatsView.as_view(), name='stats_detailed'),

    path('fields', views.EmptyFieldsView.as_view(), name='empty_fields'),

    path('user/create', views.CreateUserView.as_view(), name='create_user'),
    path('user/create/', RedirectView.as_view(pattern_name='create_user')),
    path('user/setup', views.SetupUserView.as_view(), name='setup_user'),
    path('user/signup', views.SignupRequestView.as_view(), name='signup_request'),
    path('user/signup/pending', views.SignupPendingView.as_view(), name='signup_pending'),
    path('user/profile', views.ProfileView.as_view(), name='user_profile'),

    path('suggest', views.SystemSuggestionView.as_view(), name='system_suggestion'),
    path('suggest/success', views.SystemSuggestionSuccessView.as_view(), name='system_suggestion_success'),

    # path('docs/', views.DocOverviewView.as_view(), name='docs'),
    # path('docs/feature/<slug:slug>/', views.DocFeatureView.as_view(), name='docs-feature'),
    # path('docs/attribute/<slug:slug>/', views.DocAttributeView.as_view(), name='docs-attribute'),
    # path('docs/system-attributes/', views.DocSysAttrsView.as_view(), name='docs-sys-attrs'),

    path('counter', views.CounterView.as_view(), name='counter'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap'),

    path('citation/<int:pk>/reset-status', views.CitationResetStatusView.as_view(), name='citation_reset_status'),
]

