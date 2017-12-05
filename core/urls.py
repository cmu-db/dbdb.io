from django.conf.urls import url
from django.views.generic.base import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from core.views import CreateDatabase, SystemView, EditDatabase, SearchView, CreateUser, AdvancedSearchView, HomeView, \
    UpdateViewCount, RevisionList, RevisionView

urlpatterns = [
    url(r'^$', HomeView.as_view(), name="home"),
    url(r'^create-user/$', CreateUser.as_view(), name='create_user'),
    url(r'^create-db/$', CreateDatabase.as_view(), name='create_database'),
    url(r'^create-db/(?P<id>\d+)/(?P<kind>meta)/$', CreateDatabase.as_view(), name='create_db_meta'),
    url(r'^db/(?P<slug>[\w-]+)/$', SystemView.as_view(), name='system'),
    url(r'^db/(?P<slug>[\w-]+)/edit/$', EditDatabase.as_view(), name='system_edit'),
    url(r'^db/(?P<slug>[\w-]+)/revision/$', RevisionList.as_view(), name='system_revision'),
    url(r'^db/(?P<slug>[\w-]+)/revision/(?P<id>\d+)$', RevisionView.as_view(), name='system_revision_view'),
    url(r'^search/$', SearchView.as_view(), name='search'),
    url(r'^advanced-search/$', AdvancedSearchView.as_view(), name='advanced_search'),
    url(r'^update-view-count/$', UpdateViewCount.as_view(), name='update_view_count'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
