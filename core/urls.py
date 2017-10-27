from django.conf.urls import url
from django.views.generic.base import TemplateView

from .views import CreateUser

urlpatterns = (
    url(r'^$', TemplateView.as_view(template_name='core/home.html')),
    url(r'^create_user/$', CreateUser.as_view())
)
