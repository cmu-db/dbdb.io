import json
import string

from datetime import date, timedelta
from django.db.models import ObjectDoesNotExist
from django.contrib.syndication.views import Feed
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from systems.models import *
from systems.serializers import *

SYSTEM_FIELDS = {
    'support_checkpoints': 'Checkpoints',
    'support_concurrencycontrol': 'Concurrency Control',
    'support_datamodel': 'Data Model',
    'support_foreignkeys': 'Foreign Keys',
    'support_indexes': 'Indexes',
    'support_isolationlevels': 'Isolation Levels',
    'support_joins': 'Joins',
    'support_logging': 'Logging',
    'support_querycompilation': 'Query Compilation',
    'support_queryexecution': 'Query Execution',
    'support_queryinterface': 'Query Interface',
    'support_storagearchitecture': 'Storage Architecture',
    'support_storagemodel': 'Storage Model',
    'support_storedprocedures': 'Stored Procedures',
    'support_systemarchitecture': 'System Architecture',
    'support_views': 'Views'
}


class LoadContext(object):
    @staticmethod
    def load_base_context(request):
        context = {}
        context["user"] = request.user
        context["databases"] = map(lambda x: {'name': x.name, 'slug': x.slug},
                                   System.objects.all())
        context["languages"] = map(lambda x: {'name': x.name, 'slug': x.slug},
                                   ProgrammingLanguage.objects.all())
        context["oses"] = map(lambda x: {'name': x.name, 'slug': x.slug},
                              OperatingSystem.objects.all())
        context["system_fields"] = sorted(SYSTEM_FIELDS.values())
        return context

    @staticmethod
    def load_db_data(db_version):
        # This is called to ensure the rendered_descriptions for features exist
        # which is an issue for system_versions loaded through fixtures
        db_version.save()

        db = db_version.__dict__
        db["slug"] = db_version.system.slug
        link = db["website"]
        if not link.startswith("http://") and not link.startswith("https://"):
            link = "http://" + link
        db["website"] = link

        written_langs, oses, support_langs, pubs = [], [], [], []
        for os in db_version.oses.all():
            name = OperatingSystemSerializer(os).data['name']
            slug = OperatingSystemSerializer(os).data['slug']
            oses.append({'name': name, 'slug': slug})
        for lang in db_version.support_languages.all():
            name = ProgrammingLanguageSerializer(lang).data['name']
            slug = ProgrammingLanguageSerializer(lang).data['slug']
            support_langs.append({'name': name, 'slug': slug})
        for lang in db_version.written_in.all():
            name = ProgrammingLanguageSerializer(lang).data['name']
            slug = ProgrammingLanguageSerializer(lang).data['slug']
            written_langs.append({'name': name, 'slug': slug})
        for pub in db_version.publications.all():
            pubs.append((pub.number, {"cite": pub.cite, "number": pub.number,
                                      "link": pub.link}))
        pubs.sort()

        db["oses"] = oses
        db["written_in"] = written_langs
        db["support_languages"] = support_langs
        db['features'] = db_version.get_features()
        db["pubs"] = map(lambda x: x[1], pubs)
        # Start publication numbers from last citation or 0 if there are none.
        if len(db["pubs"]) > 0:
            max_pub = pubs[-1]
            max_pub_num = max_pub[0]
            db["num_pubs"] = max_pub_num
        else:
            db["num_pubs"] = 0

        for field in db:
            if field.startswith("_"):
                db["x" + field] = db[field]
                db.pop(field, None)
        return db

    @staticmethod
    def load_db_raw_markdown_fields(db_data, db_version):
        fields = db_version.__dict__.keys()
        for field in fields:
            if "rendered" in field:
                fieldName = field[2:-9]
                if db_version.__getattribute__(fieldName):
                    rawField = db_version.__getattribute__(fieldName).raw
                    db_data[fieldName + "_raw"] = rawField

    @staticmethod
    def get_fields(db):
        field_supports = []
        for field in db:
            if "support_" in field and field != "support_languages":
                name = SYSTEM_FIELDS[field]
                data = {"field_name": name,
                        "support": db[field]}
                field_supports.append(data)
        db["field_supports"] = field_supports


class HomePage(View):
    def get(self, request):
        context = LoadContext.load_base_context(request)
        enddate = date.today() - timedelta(days=3)
        edits = SystemVersion.objects.filter(created__gt=enddate)
        context["edits"] = []

        # gets first 10 system versions edited within the past 3 days
        # by the most recently edited version (Recent Activity)
        for edit in edits[::-1][:10]:
            obj = {}
            obj["name"] = edit.name
            obj["date"] = edit.created
            obj["version_message"] = edit.version_message
            obj["creator"] = edit.creator
            obj["slug"] = edit.system.slug
            context["edits"].append(obj)

        # gets first 10 systems and orders them by which has the highest
        # current version (Most Edited Databases)
        sms = System.objects.all().order_by("current_version")[::-1][:10]
        context["top_sms"] = []
        for (i, sm) in enumerate(sms):
            # ignore the system if the current version is less than 1 (invalid)
            if sm.current_version < 1:
                continue
            obj = {}
            obj["name"] = sm.name
            obj["edits"] = sm.current_version
            obj["rank"] = i + 1
            obj["slug"] = sm.slug
            context["top_sms"].append(obj)
        return render(request, 'homepage.html',
                      context)


class DatabasePage(View):
    def get(self, request, db_name):
        db_article = System.objects.get(slug=slugify(db_name))
        db_version = SystemVersion.objects.get(system=db_article,
                                               version_number=db_article.current_version)
        context = LoadContext.load_base_context(request)
        context["db"] = LoadContext.load_db_data(db_version)
        context["isVersionPage"] = False
        return render(request, 'database.html',
                      context)


class SearchPage(View):
    def get(self, request, page_type, slug):
        context = LoadContext.load_base_context(request)
        if page_type == "os":
            os = OperatingSystem.objects.get(slug=slug)
            system_versions = os.systems_oses.all()
            obj_data = OperatingSystemSerializer(os).data
            page_info = {"page_type": "Operating System",
                         "name": obj_data["name"]}
        elif page_type == "written_lang":
            lang = ProgrammingLanguage.objects.get(slug=slug)
            system_versions = lang.systems_written.all()
            obj_data = ProgrammingLanguageSerializer(lang).data
            page_info = {"page_type": "Programming Language",
                         "name": "Written in " + obj_data["name"]}
        else:
            # page_type == "support_lang":
            lang = ProgrammingLanguage.objects.get(slug=slug)
            system_versions = lang.systems_supported.all()
            obj_data = ProgrammingLanguageSerializer(lang).data
            page_info = {"page_type": "Programming Language",
                         "name": "Supports " + obj_data["name"]}
        systems = set()
        for sys_ver in system_versions:
            # For each system version, get the system that is actually the current version
            systems.add(SystemVersion.objects.get(system=sys_ver.system,
                                                  version_number=sys_ver.system.current_version))

        systems_data = []
        for system in systems:
            data = LoadContext.load_db_data(system)
            LoadContext.get_fields(data)
            data["description"] = data["description"][:100] + "..."
            systems_data.append(data)
        context["page_data"] = page_info
        context["systems"] = systems_data
        return render(request, 'search_page.html', context)


class DatabaseEditingPage(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(DatabaseEditingPage, self).dispatch(*args, **kwargs)

    def save_fields(self, data, new_version):
        for field in data:
            db_field = field
            # Skip model_stuff and citations key
            if field == "model_stuff" or field == "citations":
                continue

            # Convert to db_field for support and features
            # Set support and feature description if db_field is set
            # Otherwise just set field directly in db model
            if "support_" in field:
                db_field = str(field.lower().replace(' ', ''))
                data[field][0] = True if data[field][0] == "1" else False
            elif 'description_' in field:
                db_field = str(field.lower().replace(' ', ''))
            elif "year" in field:
                data[field][0] = int(data[field][0])
            # getattribute and setattr could raise an AttributeError if the field isn't in the db_version model
            if new_version.__getattribute__(db_field) != data[field][0]:
                new_version.__setattr__(db_field, data[field][0])

    def save_citations(self, citations, old_version, new_version):
        # Get existing/added/removed citations which are identified by number
        existing_citations = old_version.publications.all()  # Citation models
        existing_citations = set(map(lambda c: int(c.number), existing_citations))

        add_citations = citations["adds"]  # add_citations is a list of cite dictionaries
        add_citations = set(map(lambda c: c["number"], add_citations.itervalues()))

        remove_citations = set(map(lambda c: int(c), citations["removes"]))  # revome_citations is a list of cite numbers

        # Accumulate added citations, get rid of removed citations
        new_citations = existing_citations | add_citations
        new_citations = new_citations - remove_citations

        # For each new citation check if citation number exists for old version
        # create new citation if not
        for new_citation in new_citations:
            try:
                existing = old_version.publications.get(number=new_citation)
                new_version.publications.add(existing)
            except ObjectDoesNotExist:
                # str because citations was converted from a javascript array which can't use
                # integers as keys
                citation = citations["adds"][str(new_citation)]
                link = citation["link"]
                if not link.startswith("http://") and not link.startswith("https://"):
                    link = "http://" + link
                cite = Publication(title=citation["title"], authors=citation["authors"],
                                   link=link, year=citation["year"], number=citation["number"],
                                   cite=AddPublication.create_cite(citation))
                cite.save()
                new_version.publications.add(cite)

    def save_model_stuff(self, model, options, old_version, new_version):
        # Get existing/added/removed options for the field, whether the field is written_in, support_langs, oses, etc,
        # which are identified by the name field in the model
        existing_options = old_version.__getattribute__(model).all()  # List of models
        existing_options = set(map(lambda o: o.name, existing_options))

        add_options = set(options["adds"][model])  # List of added options names
        remove_options = set(options["removes"][model])  # List of removed options names

        new_options = existing_options | add_options
        new_options = new_options - remove_options

        for new_option in new_options:
            try:
                existing = old_version.__getattribute__(model).get(name=new_option)
                new_version.__getattribute__(model).add(existing)
            except ObjectDoesNotExist:
                if model == "written_in":
                    lang = ProgrammingLanguage.objects.get(name=new_option)
                    new_version.written_in.add(lang)
                elif model == "support_languages":
                    lang = ProgrammingLanguage.objects.get(name=new_option)
                    new_version.support_languages.add(lang)
                elif model == "oses":
                    os = OperatingSystem.objects.get(name=new_option)
                    new_version.oses.add(os)

    def save_feature_options(self, options, old_version, new_version):
        # Get existing/added/removed feature options which are identified by label
        old_features = old_version.get_features()

        # data-type name is featurename_feature, ex.
        add_feature_options = {}
        for addition in options["adds"]:
            if addition.endswith("_feature"):
                feature_name = addition[:addition.index('_')]
                add_feature_options[feature_name] = options["adds"][addition]

        rem_feature_options = {}
        for removal in options["removes"]:
            if removal.endswith("_feature"):
                feature_name = removal[:removal.index('_')]
                rem_feature_options[feature_name] = options["removes"][removal]

        for old_feature in old_features:
            existing_options = old_feature.get('feature_options', None)
            added_options = add_feature_options.get(old_feature['label'], None)
            removed_options = rem_feature_options.get(old_feature['label'], None)
            new_options = set(existing_options)

            # new options that are existing or added and not removed
            if added_options:
                added_options = [x for x in added_options]
                new_options = new_options | set(added_options)
            if removed_options:
                removed_options = [x for x in removed_options]
                new_options = new_options - set(removed_options)

            for new_option in new_options:
                feature = Feature.objects.get(label=old_feature['label'])
                feature_option = FeatureOption.objects.get(value=new_option, feature=feature)
                option = SystemVersionFeatureOption(system_version=new_version,
                                                    feature_option=feature_option)
                option.save()

    def post(self, request, db_name, key):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        db = System.objects.get(slug=slugify(db_name))
        if db.secret_key != key:
            return HttpResponseBadRequest()

        # Get the latest revision of the article
        db_version = SystemVersion.objects.get(name=db.name,
                                               version_number=db.current_version)

        # Copy the model instance into a new one
        db_version.pk = None
        db_version.id = None
        db_version.save()

        # From now on db_version points to a new SystemVersion object

        # Update the current version number of the article
        db.current_version += 1
        db.save()
        db_version.version_number = db.current_version
        db_version.creator = str(ip)
        db_version.save()

        # Get previous version
        old_version = SystemVersion.objects.get(system=db, version_number=db_version.version_number - 1)

        data = dict(request.POST)
        # Index 0 is peculiar. On the javascript side it isn't an array but on the python side it is
        citations = eval(data["citations"][0])
        options = eval(data["model_stuff"][0])
        self.save_fields(data, db_version)
        self.save_citations(citations, old_version, db_version)
        self.save_model_stuff("written_in", options, old_version, db_version)
        self.save_model_stuff("support_languages", options, old_version, db_version)
        self.save_model_stuff("oses", options, old_version, db_version)
        self.save_feature_options(options, old_version, db_version)

        db_version.save()
        url = '/db/%s' % slugify(db_name)
        return JsonResponse({'redirect': url})

    def get(self, request, db_name, key):
        db_article = System.objects.get(slug=slugify(db_name))
        db_version = SystemVersion.objects.get(name=db_article.name,
                                               version_number=db_article.current_version)
        if db_article.secret_key == key:
            context = LoadContext.load_base_context(request)
            context["db"] = LoadContext.load_db_data(db_version)
            context["key"] = key
            LoadContext.load_db_raw_markdown_fields(context["db"], db_version)
            return render(request, 'database_edit.html',
                          context)
        else:
            return HttpResponseBadRequest()


class DatabaseVersionPage(View):
    def get(self, request, db_name, version):
        version = int(version)
        db_article = System.objects.get(slug=slugify(db_name))
        if version > db_article.current_version:
            return HttpResponseRedirect("/")

        db_version = SystemVersion.objects.get(system=db_article, version_number=version)
        context = LoadContext.load_base_context(request)
        context["db"] = LoadContext.load_db_data(db_version)
        context["isVersionPage"] = True
        return render(request, 'database.html',
                      context)


class DatabaseRevisionsPage(View):
    def get(self, request, db_name, key=""):
        db_article = System.objects.get(slug=slugify(db_name))
        db_version = SystemVersion.objects.get(name=db_article.name,
                                               version_number=db_article.current_version)
        context = LoadContext.load_base_context(request)
        context["db"] = LoadContext.load_db_data(db_version)
        revisions = SystemVersion.objects.filter(system=db_article).order_by("created")[::-1]
        context["revisions"] = []
        for revision in revisions:
            obj = {}
            if revision.created:
                obj["date"] = revision.created.strftime("%m/%d/%Y %H:%H:%S")
            obj["isCurrent"] = (revision.version_number == db_article.current_version)
            obj["user"] = revision.creator
            obj["comment"] = revision.version_message
            obj["version_number"] = revision.version_number
            context["revisions"].append(obj)
        context["key"] = key
        return render(request, 'database_revision.html', context)


class DatabaseCreationPage(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(DatabaseCreationPage, self).dispatch(*args, **kwargs)

    # @login_required
    def get(self, request):
        return render(request, 'database_create.html',
                      LoadContext.load_base_context(request))

    # @login_required
    def post(self, request):
        if request.POST.get('name', False):
            name = request.POST.get('name')
            existingDB = System.objects.filter(slug=slugify(name))
            if len(existingDB) == 0:
                key = util.generateSecretKey()
                newDBSystem = System(name=name, secret_key=key, current_version=0,
                                     slug=slugify(name))
                newDBSystem.save()

                newDBVersion = SystemVersion(name=name, version_number=0,
                                             system=newDBSystem)
                newDBVersion.save()
                return redirect("/db/%s/%s" % (slugify(name), key))
        return render(request, 'database_create.html',
                      LoadContext.load_base_context(request))


class PLCreationView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PLCreationView, self).dispatch(*args, **kwargs)

    def post(self, request):
        if request.POST.get('name', False):
            name = request.POST.get('name')
            newDB = ProgrammingLanguage(slug=slugify(name))
            newDB.save()
            return HttpResponseRedirect("/createdb")


class OSCreationView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(OSCreationView, self).dispatch(*args, **kwargs)

    def post(self, request):
        if request.POST.get('name', False):
            name = request.POST.get('name')
            newDB = OperatingSystem(slug=slugify(name))
            newDB.save()
            return HttpResponseRedirect("/createdb")


class FetchAllSystems(APIView):
    def get(self, request):
        systems = SystemVersionSerializer(SystemVersion.objects.all(), many=True)
        return Response(systems.data)


class AdvancedSearchView(View):

    @staticmethod
    def get_current_version_dbs():
        sms = System.objects.all()
        dbs = []
        for sm in sms:
            dbs.append(SystemVersion.objects.get(name=sm.name,
                                                 version_number=sm.current_version))
        return dbs

    def create_query_dict(self, raw_dict):
        new_dict = {}
        questioncheck = []
        greencheck = []
        greycheck = []
        inv_fields = {v: k for k, v in SYSTEM_FIELDS.items()}
        for key in raw_dict:
            if raw_dict[key][0] == "question-check":
                questioncheck.append(key)
            elif raw_dict[key][0] == "green-check":
                new_dict[inv_fields[key]] = True
                greencheck.append(key)
            else:
                new_dict[inv_fields[key]] = False
                greycheck.append(key)
        return new_dict, questioncheck, greencheck, greycheck

    def make_ordered_list(self, dbs, params=None):
        start_letters = string.ascii_lowercase + string.digits
        ordered_list = [{"letter": letter, "dbs": []} for letter in start_letters]
        for db in dbs:
            if params:
                invalid = False
                for field in params:
                    if db.__getattribute__(field) != params[field]:
                        invalid = True
                if invalid:
                    continue
            name = db.name
            letter_idx = start_letters.index(name[0].lower())
            ordered_list[letter_idx]["dbs"].append({"screen_name": name,
                                                    "hash_name": slugify(name)})
        return ordered_list

    def get(self, request):
        context = LoadContext.load_base_context(request)
        params, question, green, grey = self.create_query_dict(dict(request.GET))
        context["questionchecks"] = question
        context["greenchecks"] = green
        context["greychecks"] = grey
        dbs = AdvancedSearchView.get_current_version_dbs()
        context["ordered_dbs_list"] = self.make_ordered_list(dbs, params)
        return render(request, 'advanced_search.html', context)


class AlphabetizedData(APIView):
    def get(self, request):
        return Response(AdvancedSearchView.alphabetize_dbs_data())


class MissingSystemView(View):
    def post(self, request):
        data = dict(request.POST)
        data = {k: v[0] for k, v in data.items()}
        data.pop("csrfmiddlewaretoken", None)
        data["secret_key"] = util.generateSecretKey()
        system = SuggestedSystem(**data)
        system.save()
        return HttpResponseRedirect("/")

    def get(self, request):
        context = LoadContext.load_base_context(request)
        return render(request, 'missing_system.html', context)


class AboutView(View):
    def get(self, request):
        return render(request, 'about.html')


class AddPublication(View):

    @staticmethod
    def create_cite(data):
        cite = ""
        cite += data["authors"] + ". "
        if data["title"][0] == '"':
            cite += data["title"]
        else:
            cite += '"' + data["title"]
        if data["title"][-1] != '"':
            cite += '"'
        cite += ". "
        cite += data["journal"] + " "
        cite += data["year"] + ". "
        cite += data["pages"] + "."
        return cite

    def post(self, request):
        data = dict(request.POST)
        data = {k: v[0] for k, v in data.items()}
        cite = AddPublication.create_cite(data)
        link = data["link"]
        if not link.startswith("http://") and not link.startswith("https://"):
            link = "http://" + link
        return HttpResponse(json.dumps({"cite": cite, "link": link}), content_type="application/json")


class LatestEdits(Feed):
    title = "Latest edits to databas pages."
    link = '/editrss/'
    description = "A live feed of all changes made to any database recently"

    def items(self):
        return SystemVersion.objects.all().order_by("created")[::-1][:30]

    def item_title(self, item):
        return item.creator + " edited " + item.name

    def item_description(self, item):
        return item.version_message

    def item_link(self, item):
        return "/db/version/" + item.name + "/" + str(item.version_number)
