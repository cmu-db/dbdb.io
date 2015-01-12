from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.http import (HttpResponse, HttpResponseNotFound,
    HttpResponseBadRequest, HttpResponseServerError)
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response


from systems.models import System
from systems.serializers import SystemSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

import hashlib, time

class LoadContext(object):

  @staticmethod
  def load_base_context(request):
    context = {}
    context["user"] = request.user
    context["databases"] = map(lambda x: x.name, System.objects.all())
    return context

class HomePage(View):

  def get(self, request):
    
    return render(request, 'homepage.html',
      LoadContext.load_base_context(request))

class DatabasePage(View):

  def get(self, request, db_name):
    database = System.objects.get(name = db_name)
    return render(request, 'database.html',
      LoadContext.load_base_context(request))

class DatabaseEditingPage(View):

  def get(self, request, db_name, key):
    database = System.objects.get(name = db_name)
    if database.secret_key == key:
      return render(request, 'database_edit.html',
        LoadContext.load_base_context(request))
    else:
      return HttpResponseBadRequest()

class DatabaseCreationPage(View):

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(DatabaseCreationPage, self).dispatch(*args, **kwargs)

  @staticmethod
  def create_secret_key():
    key = hashlib.sha1()
    key.update(str(time.time()))
    return key.hexdigest()[:11]

  def get(self, request):
    return render(request, 'database_create.html',
      LoadContext.load_base_context(request))

  def post(self, request):
    if request.POST.get('name', False):
      name = request.POST.get('name')
      key = DatabaseCreationPage.create_secret_key()
      newDB = System(name = name, secret_key = key)
      newDB.save()
      return HttpResponseRedirect("/db/%s/%s" % (name, key))

class FetchAllSystems(APIView):

  def get(self, request):
    systems = SystemSerializer(System.objects.all(), many = True)
    return Response(systems.data)