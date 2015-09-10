from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from django.contrib.syndication.views import Feed
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import date, timedelta

from systems.models import *
from systems.serializers import *

import hashlib, time, string

system_fields = {
  'support_sql': 'SQL',
  'support_userconcepts': 'USER CONCEPTS',
  'support_triggers': 'TRIGGERS',
  'support_mapreduce': 'MAP REDUCE',
  'support_xml': 'XML',
  'support_transactionconcepts': 'TRANSACTION CONCEPTS',
  'support_concurrency': 'CONCURRENCY',
  'support_durability': 'DURABILITY',
  'support_serverside': 'SERVER SIDE',
  'support_secondary': 'SECONDARY INDEXES',
  'support_datascheme': 'DATA SCHEME',
  'support_typing': 'TYPING',
  'support_foreignkeys': 'FOREIGN KEYS'
}

inv_fields = {v: k for k, v in system_fields.items()}

class LoadContext(object):

  @staticmethod
  def load_base_context(request):
    context = {}
    context["user"] = request.user
    context["databases"] = map(lambda x: x.name.replace(" ", "-"), System.objects.all())
    context["languages"] = map(lambda x: x.name.replace(" ", "-"), ProgrammingLanguage.objects.all())
    context["oses"] = map(lambda x: x.name.replace(" ", "-"), OperatingSystem.objects.all())
    context["system_fields"] = system_fields.values()
    return context

  @staticmethod
  def load_db_data(db):
    db["name"] = db["name"].replace(" ", "-")
    written_lang, oses, support_langs = [], [], []
    for os_id in db["oses"]:
      os = OperatingSystem.objects.get(id = os_id)
      oses.append(OperatingSystemSerializer(os).data['name'].replace(" ", "-"))
    for lang_id in db["support_languages"]:
      lang = ProgrammingLanguage.objects.get(id = lang_id)
      support_langs.append(ProgrammingLanguageSerializer(lang).data['name'].replace(" ", "-"))
    for lang_id in db["written_in"]:
      lang = ProgrammingLanguage.objects.get(id = lang_id)
      written_lang.append(ProgrammingLanguageSerializer(lang).data['name'].replace(" ", "-"))
    db["oses"] = oses
    db["written_in"] = written_lang
    db["support_languages"] = support_langs
    return db

  @staticmethod
  def load_db_raw_markdown_fields(db_data, db_ojb):
    for field in db_ojb.__dict__:
      if "rendered" in field:
        fieldName = field[1:-9]
        if db_ojb.__getattribute__(fieldName):
          rawField = db_ojb.__getattribute__(fieldName).raw
          db_data[fieldName + "_raw"] = rawField
        else:
          db_data[fieldName + "_raw"] = rawField

  @staticmethod
  def get_fields(db):
    field_supports = []
    for field in db: 
      if "support_" in field and field != "support_languages":
        name = system_fields[field]
        data = {"field_name": name,
                "support": db[field]}
        field_supports.append(data)
    db["field_supports"] = field_supports

class HomePage(View):

  def get(self, request):
    context = LoadContext.load_base_context(request)
    enddate = date.today() - timedelta(days=3)
    edits = System.objects.filter(created__gt=enddate)
    context["edits"] = []
    today = date.today()
    for edit in edits[::-1][:10]:
      obj = {}
      obj["name"] = edit.name
      obj["date"] = edit.created
      obj["version_message"] = edit.version_message
      obj["creator"] = edit.creator
      context["edits"].append(obj)

    sms = SystemManager.objects.all().order_by("max_version")[::-1][:10]
    context["top_sms"] = []
    for (i, sm) in enumerate(sms):
      if sm.max_version < 1:
        continue
      obj = {}
      obj["name"] = sm.name
      obj["edits"] = sm.max_version
      obj["rank"] = i + 1
      context["top_sms"].append(obj)
    return render(request, 'homepage.html',
      context)

class DatabasePage(View):

  def get(self, request, db_name):
    db_name = db_name.replace("-", " ")
    dbManager = SystemManager.objects.get(name = db_name)
    database = dbManager.current_version.all()[0]
    context = LoadContext.load_base_context(request)
    context["db"] = LoadContext.load_db_data(SystemSerializer(database).data)
    context["isVersionPage"] = False
    return render(request, 'database.html',
        context)

class OSPage(View):

  def get(self, request, page_type, name):
    name = name.replace("-", " ")
    context = LoadContext.load_base_context(request)
    if page_type == "os":
      os = OperatingSystem.objects.get(name = name)
      systems = SystemSerializer(os.systems.all(), many=True).data
      obj_data = OperatingSystemSerializer(os).data
      page_info = {"page_type": "Operating System",
                   "name": obj_data["name"]}
    elif page_type == "written_lang":
      lang = ProgrammingLanguage.objects.get(name = name)
      systems = SystemSerializer(lang.systems_written.all(), many=True).data
      obj_data = ProgrammingLanguageSerializer(lang).data
      page_info = {"page_type": "Programming Language",
                 "name": "Written in " + obj_data["name"]}
    elif page_type == "support_lang":
      lang = ProgrammingLanguage.objects.get(name = name)
      systems = SystemSerializer(lang.systems_supported.all(), many=True).data
      obj_data = ProgrammingLanguageSerializer(lang).data
      page_info = {"page_type": "Programming Language",
                 "name": "Supports " + obj_data["name"]}
    systems_data = []
    for system in systems:
      data = LoadContext.load_db_data(system)
      LoadContext.get_fields(data)
      data["description"] = data["description"][:100] + "..."
      systems_data.append(data)
    context["page_data"] = page_info
    context["systems"] = systems_data
    return render(request, 'search_page.html', context)

class LangPage(View):

  def get(self, request, lang_name):
    lang_name = lang_name.replace("-", " ")
    lang = ProgrammingLanguage.objects.get(name = lang_name)
    systems = SystemSerializer(lang.systems_supported.all(), many=True).data
    systems_data = []
    for system in systems:
      systems_data.append(LoadContext.load_db_data(system))
    context = LoadContext.load_base_context(request)
    context["lang"] = ProgrammingLanguageSerializer(lang).data
    context["systems"] = systems_data
    return render(request, 'lang.html', context)

class DatabaseEditingPage(View):

  savedModels = {}

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(DatabaseEditingPage, self).dispatch(*args, **kwargs)

  def post(self, request, db_name, key):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    db_name = db_name.replace("-", " ")
    savedModels = DatabaseEditingPage.savedModels
    dbManager = SystemManager.objects.get(name = db_name)
    db = dbManager.current_version.all()[0]
    dbManager.current_version.remove(db)
    db.pk = None
    db.save()
    db.version = dbManager.max_version + 1
    db.save()
    dbManager.version_number = db.version
    dbManager.max_version = db.version
    dbManager.save()
    dbManager.current_version.add(db)
    if db.secret_key != key:
      return HttpResponseBadRequest()
    data = dict(request.POST)
    for field in data:
      if field == "model_stuff":
        continue
      if "support_" in field:
        data[field][0] = True if data[field][0] == "1" else False
      elif "year" in field:
        data[field][0] = int(data[field][0])
      if db.__getattribute__(field) != data[field][0]:
        db.__setattr__(field, data[field][0])
    db.creator = str(ip)
    db.save()
    options = eval(data["model_stuff"][0])
    adds = dict(map(lambda x: (x, map(lambda y: "add_" + y, options["adds"][x])), options["adds"]))
    removes = dict(map(lambda x: (x, map(lambda y: "rem_" + y, options["removes"][x])), options["removes"]))
    map(lambda x: adds[x].extend(removes[x]), adds)
    for lang_name in adds["written_in"]:
      task, lang_name = lang_name[:3], lang_name[4:]
      if lang_name in savedModels and savedModels[lang_name]:
        lang = savedModels[lang_name]
      else:
        lang = ProgrammingLanguage.objects.get(name = lang_name)
        savedModels[lang_name] = lang
      if task == "add": db.written_in.add(lang)
      else: db.written_in.remove(lang)
    for lang_name in adds["support_languages"]:
      task, lang_name = lang_name[:3], lang_name[4:]
      if lang_name in savedModels and savedModels[lang_name]:
        lang = savedModels[lang_name]
      else:
        lang = ProgrammingLanguage.objects.get(name = lang_name)
        savedModels[lang_name] = lang
      if task == "add": db.support_languages.add(lang)
      else: db.support_languages.remove(lang)
    for os_name in adds["oses"]:
      task, os_name = os_name[:3], os_name[4:]
      if os_name in savedModels and savedModels[os_name]:
        os = savedModels[os_name]
      else:
        os = OperatingSystem.objects.get(name = os_name)
        savedModels[os_name] = os
      if task == "add": db.oses.add(os)
      else: db.oses.remove(os) 
    return HttpResponseRedirect("/db/%s" % db_name)

  def get(self, request, db_name, key):
    db_name = db_name.replace("-", " ")
    dbManager = SystemManager.objects.get(name = db_name)
    database = dbManager.current_version.all()[0]
    if database.secret_key == key:
      context = LoadContext.load_base_context(request)
      context["db"] = LoadContext.load_db_data(SystemSerializer(database).data)
      context["key"] = key
      LoadContext.load_db_raw_markdown_fields(context["db"], database)
      return render(request, 'database_edit.html',
        context)
    else:
      return HttpResponseBadRequest()

class DatabaseVersionPage(View):

  def get(self, request, db_name, version):
    version = int(version)
    db_name = db_name.replace("-", " ")
    dbManager = SystemManager.objects.get(name = db_name)
    if dbManager.max_version < version:
      return HttpResponseRedirect("/")
    database = System.objects.get(name=db_name, version = version)
    context = LoadContext.load_base_context(request)
    context["db"] = LoadContext.load_db_data(SystemSerializer(database).data)
    context["isVersionPage"] = True
    return render(request, 'database.html',
        context)

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

class DatabaseRevisionsPage(View):

  def get(self, request, db_name, key = ""):
    db_name = db_name.replace("-", " ")
    dbManager = SystemManager.objects.get(name = db_name)
    database = dbManager.current_version.all()[0]
    context = LoadContext.load_base_context(request)
    context["db"] = LoadContext.load_db_data(SystemSerializer(database).data)
    revisions = System.objects.filter(name = db_name).order_by("created")[::-1]
    context["revisions"] = []
    for revision in revisions:
      obj = {}
      if revision.created:
        obj["date"] = revision.created.strftime("%m/%d/%Y %H:%H:%S")
      obj["isCurrent"] = (revision.version == dbManager.version_number)
      obj["user"] = revision.creator
      obj["comment"] = revision.version_message
      obj["version_number"] = revision.version
      context["revisions"].append(obj)
    context["key"] = key
    return render(request, 'database_revision.html', context)

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

class AdvancedSearchView(View):

  def create_query_dict(self, raw_dict):
    drop_keys = []
    new_dict = {}
    questioncheck = []
    greencheck = []
    greycheck = []
    for key in raw_dict:
      if raw_dict[key][0] == "question-check":
        questioncheck.append(key)
      elif raw_dict[key][0] == "green-check":
        new_dict[inv_fields[key]] = True
        greencheck.append(key)
      else:
        new_dict[inv_fields[key]] = False
        greycheck.append(key);
    return new_dict, questioncheck, greencheck, greycheck

  def make_ordered_list(self, dbs):
    start_letters = string.ascii_lowercase + string.digits
    ordered_list = [ {"letter": letter, "dbs": []} for letter in start_letters]
    for db in dbs:
      name = db.name
      letter_idx = start_letters.index(name[0].lower())
      ordered_list[letter_idx]["dbs"].append(name)
    return ordered_list

  def get(self, request):
    context = LoadContext.load_base_context(request)
    params, question, green, grey = self.create_query_dict(dict(request.GET))
    context["questionchecks"] = question
    context["greenchecks"] = green
    context["greychecks"] = grey
    dbs = System.objects.filter(**params)
    context["ordered_dbs_list"] = self.make_ordered_list(dbs)
    return render(request, 'advanced_search.html', context)

class AlphabetizedData(APIView):

  def get(self, request):
    return Response(AdvancedSearchView.alphabetize_dbs_data());

class MissingSystemView(View):

  def post(self, request):
    data = dict(request.POST)
    data = {k: v[0] for k, v in data.items()}
    data.pop("csrfmiddlewaretoken", None)
    data["secret_key"] = DatabaseCreationPage.create_secret_key()
    system = SuggestedSystem(**data)
    system.save()
    return HttpResponseRedirect("/")

  def get(self, request):
    context = LoadContext.load_base_context(request)
    return render(request, 'missing_system.html', context)

class LatestEdits(Feed):
  title = "Latest edits to databas pages."
  link = '/editrss/'
  description = "A live feed of all changes made to any database recently"

  def items(self):
    return System.objects.all().order_by("created")[::-1][:30]

  def item_title(self, item):
    return item.creator + " edited " + item.name

  def item_description(self, item):
    return item.version_message

  def item_link(self, item):
    return "/db/version/" + item.name + "/" + str(item.version) 
