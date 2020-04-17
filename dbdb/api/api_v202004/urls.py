# django imports
from django.urls import path
# third-party imports
from rest_framework.urlpatterns import format_suffix_patterns
# local imports
from . import views


app_name = 'api_v202004'

urlpatterns = [
    path('systems', views.SystemsView.as_view(), name='systems'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
