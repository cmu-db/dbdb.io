import json
import string

from datetime import date, timedelta
from django.db.models import ObjectDoesNotExist
from django.contrib.syndication.views import Feed
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template.defaulttags import register
from django.utils.text import slugify
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from systems.models import Feature, FeatureOption, License, OperatingSystem, ProgrammingLanguage, ProjectType, \
    Publication, SuggestedSystem, System, SystemVersion, SystemVersionFeatureOption
from systems.serializers import LicenseSerializer, SystemVersionSerializer
import util


# Dictionary lookup in template.
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


class LoadContext(object):
    @staticmethod
    def get_all_features():
        return sorted([feature.label for feature in Feature.objects.all()])

    @staticmethod
    def get_all_feature_options():
        feature_options = {}
        for fo in FeatureOption.objects.all():
            if not feature_options.get(fo.feature.label):
                feature_options[fo.feature.label] = [fo.value]
            else:
                feature_options[fo.feature.label].append(fo.value)
        for options in feature_options.values():
            options.sort()
        return feature_options


    @staticmethod
    def load_base_context(request):
        return {
            "user":                 request.user,
            # TODO: don't load all databases when only looking at one. Pass template as argument to load specific context
            "databases":            map(lambda db: {'name': db.name, 'slug': db.slug}, System.objects.all()),
            "languages":            map(lambda lang: {'name': lang.name, 'slug': lang.slug},
                                        ProgrammingLanguage.objects.all()),
            "oses":                 map(lambda os: {'name': os.name, 'slug': os.slug}, OperatingSystem.objects.all()),
            "licenses":             map(lambda license: {'name': license.name, 'slug': license.slug}, License.objects.all()),
            "project_types":        map(lambda type: {'name': type.name, 'slug': type.slug}, ProjectType.objects.all()),
            "all_features":         LoadContext.get_all_features(),
            "all_feature_options":  LoadContext.get_all_feature_options()
        }

    @staticmethod
    def load_db_data(db_version):

        # Save db_version.
        db_version.save()

        # Create dictionary from db_version object.
        db = db_version.__dict__

        # Add slug and website link.
        db["slug"] = db_version.system.slug
        link = db["website"]
        if not link.startswith("http://") and not link.startswith("https://"):
            link = "http://" + link
        db["website"] = link

        # Add metadata.
        db["written_in"] = [{'name': lang.name,
                             'slug': lang.slug}
                            for lang in db_version.written_in.all()]

        db["oses"] = [{'name': os.name,
                       'slug': os.slug}
                      for os in db_version.oses.all()]

        db["support_languages"] = [{'name': lang.name,
                                    'slug': lang.slug}
                                   for lang in db_version.support_languages.all()]

        db["licenses"] = [{'name': license.name,
                           'slug': license.slug}
                          for license in db_version.licenses.all()]

        db["derived_from"] = [{'name': system.name,
                               'slug': system.slug}
                              for system in db_version.derived_from.all()]

        # TODO This is a hotfix for versions without a project_type
        if db_version.project_type:
            db["project_type"] = {
                'name': db_version.project_type.name,
                'slug': db_version.project_type.slug
            }

        # Load database features.
        db['features'] = db_version.get_features()

        # Load publications.
        db["pubs"] = [{"cite": pub.cite,
                       "number": pub.number,
                       "link": pub.link}
                      for pub in db_version.publications.all()]

        # Sort in ascending citation number.
        db["pubs"].sort(cmp=lambda a, b: a["number"] < b["number"])

        # Set latest publication.
        if len(db["pubs"]) > 0:
            db["last_pub"] = db["pubs"][-1][0]
        else:
            db["last_pub"] = 0

        # Load remaining database fields.
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
                field_name = field[2:-9]
                if db_version.__getattribute__(field_name):
                    raw_field = db_version.__getattribute__(field_name).raw
                    db_data[field_name + "_raw"] = raw_field


class HomePage(View):
    def get(self, request):
        context = LoadContext.load_base_context(request)
        enddate = date.today() - timedelta(days=3)
        edits = SystemVersion.objects.filter(created__gt=enddate)
        context["edits"] = []

        # Get 10 recently edited system versions.
        for edit in edits[::-1][:10]:
            context["edits"].append(
                {
                    "name":            edit.name,
                    "date":            edit.created,
                    "version_message": edit.version_message,
                    "creator":         edit.creator,
                    "slug":            edit.system.slug
                }
            )

        # Get most edited systems.
        sms = System.objects.all().order_by("current_version")[::-1][:10]
        context["top_sms"] = []
        for (i, sm) in enumerate(sms):
            obj = {
                "name": sm.name,
                "edits": sm.current_version,
                "rank": i + 1,
                "slug": sm.slug
            }
            context["top_sms"].append(obj)
        return render(request, 'homepage.html',
                      context)


class DatabasePage(View):
    def get(self, request, db_name):
        # TODO: filter by slug, not get. Or just filter by name?
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
            page_info = {"page_type": "Operating System",
                         "name": "Runs on: " + os.name}
        elif page_type == "written_in":
            lang = ProgrammingLanguage.objects.get(slug=slug)
            system_versions = lang.systems_written.all()
            page_info = {"page_type": "Programming Language",
                         "name": "Written in: " + lang.name}
        elif page_type == "support_lang":
            lang = ProgrammingLanguage.objects.get(slug=slug)
            system_versions = lang.systems_supported.all()
            page_info = {"page_type": "Programming Language",
                         "name": "Supports: " + lang.name}
        elif page_type == "license":
            license = License.objects.get(slug=slug)
            system_versions = license.systems_licenses.all()
            obj_data = LicenseSerializer(license).data
            page_info = {"page_type": "License",
                         "name": "Uses: " + obj_data["name"]}
        elif page_type == "derived_from":
            system = System.objects.get(slug=slug)
            system_versions = system.systems_derived.all()
            page_info = {"page_type": "License",
                         "name": "Derived From: " + system.name}
        else:
            # page_type == "project":
            project_type = ProjectType.objects.get(slug=slug)
            system_versions = SystemVersion.objects.filter(project_type=project_type)
            page_info = {"page_type": "Project Type",
                         "name": "Operates as: " + project_type.name}

        systems = set()
        for sys_ver in system_versions:
            # For each system version, get the system that is actually the current version
            systems.add(SystemVersion.objects.get(system=sys_ver.system,
                                                  version_number=sys_ver.system.current_version))

        systems_data = []
        for db_version in systems:
            data = LoadContext.load_db_data(db_version)
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
            # Skip model_stuff, citations, and image
            if field == "model_stuff" or field == "citations" or field == "image":
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

    def save_image(self, data, new_version):
        # file_like = cStringIO.StringIO(data["image"][0].encode('utf8'))
        # img = PIL.Image.open(file_like)
        file_name = new_version.system.slug + '-' + str(new_version.version_number) + '.png'
        # with open(file_name, "wb") as fh:
        #     fh.write(data["image"][0].encode('utf8'))

        # img = Image.open(fh)
        # img.show()
        # if data["image"] and len(data["image"]) == 1:
        #     print data["image"][0].encode('utf8')
        #     file_name = new_version.system.slug + '-' + str(new_version.version_number) + '.png'
        #     with open(file_name, "wb") as fh:
        #         fh.write(data["image"][0].encode('utf8'))
        #
        #     new_version.logo_orig = fh
        #     new_version.save()

    def save_citations(self, citations, old_version, new_version):
        # Get existing/added/removed citations which are identified by number
        existing_citations = old_version.publications.all()  # Citation models
        existing_citations = set(map(lambda c: int(c.number), existing_citations))

        add_citations = citations["adds"]  # add_citations is a list of cite dictionaries
        add_citations = set(map(lambda c: c["number"], add_citations.itervalues()))

        # List of cite numbers.
        remove_citations = set(map(lambda c: int(c), citations["removes"]))

        # Accumulate added citations, get rid of removed citations.
        new_citations = existing_citations | add_citations
        new_citations -= remove_citations

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

        # List of models
        existing_options = old_version.__getattribute__(model).all()
        existing_options = set(map(lambda o: o.name, existing_options))

        add_options = set(options["adds"].get(model, []))  # Options being added.
        remove_options = set(options["removes"].get(model, []))  # Options being removed.

        new_options = existing_options | add_options
        new_options -= remove_options

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
                elif model == "licenses":
                    license = License.objects.get(name=new_option)
                    new_version.licenses.add(license)
                elif model == "derived_from":
                    system = System.objects.get(name=new_option)
                    new_version.derived_from.add(system)

    def save_feature_options(self, options, old_version, new_version):
        # Get existing/added/removed feature options which are identified by label.
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
                added_options = [opt for opt in added_options]
                new_options |= set(added_options)
            if removed_options:
                removed_options = [opt for opt in removed_options]
                new_options -= set(removed_options)

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

        citations = eval(data["citations"][0])
        options = eval(data["model_stuff"][0])

        self.save_fields(data, db_version)
        self.save_image(data, db_version)
        self.save_citations(citations, old_version, db_version)
        self.save_model_stuff("written_in", options, old_version, db_version)
        self.save_model_stuff("support_languages", options, old_version, db_version)
        self.save_model_stuff("oses", options, old_version, db_version)
        self.save_model_stuff("licenses", options, old_version, db_version)
        self.save_model_stuff("derived_from", options, old_version, db_version)
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
            existing = System.objects.filter(slug=slugify(name))
            if len(existing) == 0:
                key = util.generateSecretKey()
                db = System(name=name, secret_key=key, current_version=0,
                            slug=slugify(name))
                db.save()

                db_version = SystemVersion(name=name, version_number=0,
                                           system=db)
                db_version.save()
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
            lang = ProgrammingLanguage(slug=slugify(name))
            lang.save()
            return HttpResponseRedirect("/createdb")


class OSCreationView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(OSCreationView, self).dispatch(*args, **kwargs)

    def post(self, request):
        if request.POST.get('name', False):
            name = request.POST.get('name')
            os = OperatingSystem(slug=slugify(name))
            os.save()
            return HttpResponseRedirect("/createdb")


class FetchAllSystems(APIView):
    def get(self, request):
        systems = SystemVersionSerializer(SystemVersion.objects.all(), many=True)
        return Response(systems.data)


class AdvancedSearchView(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(AdvancedSearchView, self).dispatch(*args, **kwargs)

    @staticmethod
    def make_ordered_list(params):
        start_letters = string.digits + string.ascii_lowercase
        ordered_list = [{"letter": letter, "dbs": []} for letter in start_letters]

        # Organize databases based on first letter.
        for db in System.objects.all():

            matches = True
            # Filter databases if there are search parameters.
            if params is not None:
                db_version = SystemVersion.objects.get(system=db,
                                                       version_number=db.current_version)
                matches = AdvancedSearchView.search(db_version, params)

            # Add database if it matches search parameters.
            if matches:
                name = db.name
                slug = db.slug
                letter_idx = start_letters.index(name[0].lower())
                ordered_list[letter_idx]["dbs"].append({"name": name,
                                                        "slug": slug})

        # Arrange each list of databases alphabetically.
        for letter in ordered_list:
            letter['dbs'].sort(cmp=lambda x, y: cmp(x['name'].lower(), y['name'].lower()))

        return ordered_list

    @staticmethod
    def search(db, params):
        # Search if all values in params are in that db's features.
        for field in params:
            feature = Feature.objects.get(label=field)
            search_options = params[field]
            feature_options = [fo.value for fo in db.feature_options.filter(feature=feature)]
            # Set difference of search options with feature options
            if len(set(search_options) - set(feature_options)) > 0:
                return False
        return True

    def post(self, request):
        context = LoadContext.load_base_context(request)
        params = dict(request.POST)
        context["ordered_dbs_list"] = AdvancedSearchView.make_ordered_list(params)
        context["selected"] = params
        return render(request, 'advanced_search.html', context)

    def get(self, request):
        context = LoadContext.load_base_context(request)
        context["ordered_dbs_list"] = AdvancedSearchView.make_ordered_list(None)
        return render(request, 'advanced_search.html', context)


# TODO remove this class and the corresponding url in urls.py
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
    title = "Latest edits to database pages."
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
