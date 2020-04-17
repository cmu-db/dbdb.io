# django imports
from django.urls import path
from django.urls import include
from django.conf.urls import url


urlpatterns = [
    path('v202004/', include('dbdb.api.v202004.urls')),
]
