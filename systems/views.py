from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from django.http import (HttpResponse, HttpResponseNotFound,
    HttpResponseBadRequest, HttpResponseServerError)

from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response


from systems.models import System, ProgrammingLanguage, OperatingSystem
from systems.serializers import SystemSerializer, OperatingSytemSerializer, ProgrammingLanguageSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

import hashlib, time

class LoadContext(object):

  @staticmethod
  def load_base_context(request):
    context = {}
    context["user"] = request.user
    context["databases"] = map(lambda x: x.name, System.objects.all())
    context["languages"] = map(lambda x: x.name, ProgrammingLanguage.objects.all())
    context["oses"] = map(lambda x: x.name, OperatingSystem.objects.all())
    return context

class HomePage(View):

  def get(self, request):
    
    return render(request, 'homepage.html',
      LoadContext.load_base_context(request))

class DatabasePage(View):

  def get(self, request, db_name):
    database = System.objects.get(name = db_name)
    context = LoadContext.load_base_context(request)
    context["db"] = SystemSerializer(database).data
    return render(request, 'database.html',
        context)

class OSPage(View):

  def get(self, request, db_name):
    os = OperatingSystem.objects.get(name = db_name)
    context = LoadContext.load_base_context(request)
    context["os"] = OperatingSystemSerializer(os).data
    return render(request, 'os.html',
        context)

class LangPage(View):

  def get(self, request, db_name):
    lang = ProgrammingLanguage.objects.get(name = db_name)
    context = LoadContext.load_base_context(request)
    context["lang"] = ProgrammingLanguageSerializer(lang).data
    return render(request, 'lang.html',
        context)

class DatabaseEditingPage(View):

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(DatabaseEditingPage, self).dispatch(*args, **kwargs)

  def post(self, request, db_name, key):
    db = System.objects.get(name = db_name)
    if db.secret_key != key:
      return HttpResponseBadRequest()
    data = dict(request.POST)
    for field in data:
      if "support_" in field:
        data[field][0] = True if data[field][0] == "1" else False
      elif "year" in field:
        data[field][0] = int(data[field][0])
      if db.__getattribute__(field) != data[field][0]:
        db.__setattr__(field, data[field][0])
    db.save()
    return redirect("/db/%s" % db_name)

  def get(self, request, db_name, key):
    database = System.objects.get(name = db_name)
    if database.secret_key == key:
      context = LoadContext.load_base_context(request)
      context["db"] = SystemSerializer(database).data
      return render(request, 'database_edit.html',
        context)
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
      return redirect("/db/%s/%s" % (name, key))

class PLCreationView(View):

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(PLCreationView, self).dispatch(*args, **kwargs)

  def post(self, request):
    if request.POST.get('name', False):
      name = request.POST.get('name')
      newDB = ProgrammingLanguage(name = name)
      newDB.save()
      return HttpResponseRedirect("/createdb")

class OSCreationView(View):

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(OSCreationView, self).dispatch(*args, **kwargs)

  def post(self, request):
    if request.POST.get('name', False):
      name = request.POST.get('name')
      newDB = OperatingSystem(name = name)
      newDB.save()
      return HttpResponseRedirect("/createdb")

class FetchAllSystems(APIView):

  def get(self, request):
    systems = SystemSerializer(System.objects.all(), many = True)
    return Response(systems.data)