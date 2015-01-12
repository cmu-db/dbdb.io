from django.conf.urls import patterns, url, include
from rest_framework import routers
from systems import views

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = patterns('',

    # routing urls
    url(r'^$', views.HomePage.as_view()),
    url(r'^db/(?P<db_name>[A-Za-z0-9-_]+)/(?P<key>[A-Za-z0-9-_]+)', views.DatabaseEditingPage.as_view()),
    url(r'^db/(?P<db_name>[A-Za-z0-9-_]+)', views.DatabasePage.as_view()),
    url(r'^createdb/', views.DatabaseCreationPage.as_view()),
    # api urls
    url(r'^1/all_systems', views.FetchAllSystems.as_view())
)