import json
import string

from datetime import date, timedelta
from django.db.models import ObjectDoesNotExist
from django.contrib.syndication.views import Feed
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.template.defaulttags import register
from django.utils.text import slugify
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from systems.forms import SystemVersionForm
from systems.models import Feature, FeatureOption, License, OperatingSystem, ProgrammingLanguage, ProjectType, \
    Publication, SuggestedSystem, System, SystemVersion
from systems.serializers import SystemVersionSerializer
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
            "user": request.user,
            # TODO: don't load all databases when only looking at one. Pass template as argument to load specific context
            "databases": map(lambda db: {'name': db.name, 'slug': db.slug}, System.objects.all()),
            "languages": map(lambda lang: {'name': lang.name, 'slug': lang.slug},
                             ProgrammingLanguage.objects.all()),
            "oses": map(lambda os: {'name': os.name, 'slug': os.slug}, OperatingSystem.objects.all()),
            "licenses": map(lambda license: {'name': license.name, 'slug': license.slug}, License.objects.all()),
            "project_types": map(lambda type: {'name': type.name, 'slug': type.slug}, ProjectType.objects.all()),
            "all_features": LoadContext.get_all_features(),
            "all_feature_options": LoadContext.get_all_feature_options()
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

        db["supported_languages"] = [{'name': lang.name,
                                      'slug': lang.slug}
                                     for lang in db_version.supported_languages.all()]

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

        # # Load database features.
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

        return db


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
                    "name": edit.name,
                    "date": edit.created,
                    "version_message": edit.version_message,
                    "creator": edit.creator,
                    "slug": edit.system.slug
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
        db_article = System.objects.get(slug=slugify(db_name))
        db_version = SystemVersion.objects.get(system=db_article,
                                               version_number=db_article.current_version)
        context = LoadContext.load_base_context(request)
        context["db"] = LoadContext.load_db_data(db_version)
        return render(request, 'database.html',
                      context)


class SearchPage(View):
    def get(self, request, page_type, slug):
        context = LoadContext.load_base_context(request)
        if page_type == "os":
            os = OperatingSystem.objects.get(slug=slug)
            system_versions = os.systems_oses.filter(current=True)
            page_info = {"page_type": "Operating System",
                         "name": "Runs on: " + os.name}
        elif page_type == "written_in":
            lang = ProgrammingLanguage.objects.get(slug=slug)
            system_versions = lang.systems_written.filter(current=True)
            page_info = {"page_type": "Programming Language",
                         "name": "Written in: " + lang.name}
        elif page_type == "supported_lang":
            lang = ProgrammingLanguage.objects.get(slug=slug)
            system_versions = lang.systems_supported.filter(current=True)
            page_info = {"page_type": "Programming Language",
                         "name": "Supports: " + lang.name}
        elif page_type == "license":
            license = License.objects.get(slug=slug)
            system_versions = license.systems_licenses.filter(current=True)
            page_info = {"page_type": "License",
                         "name": "Uses: " + license.name}
        elif page_type == "derived_from":
            system = System.objects.get(slug=slug)
            system_versions = system.systems_derived.filter(current=True)
            page_info = {"page_type": "License",
                         "name": "Derived From: " + system.name}
        else:
            # page_type == "project":
            project_type = ProjectType.objects.get(slug=slug)
            system_versions = project_type.systemversion_set.filter(current=True)
            page_info = {"page_type": "Project Type",
                         "name": "Operates as: " + project_type.name}

        systems_data = []
        # TODO: it's unecessary to load_db_data for each system. All that's needed for the search page is just
        # TODO: the name, slug, description, and features
        for db_version in system_versions:
            data = LoadContext.load_db_data(db_version)
            data["description"] = data["description"][:100] + "..."
            systems_data.append(data)
        systems_data.sort(cmp=lambda x,y: cmp(x['name'], y['name']))
        context["page_data"] = page_info
        context["systems"] = systems_data
        return render(request, 'search_page.html', context)


class DatabaseEditingPage(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(DatabaseEditingPage, self).dispatch(*args, **kwargs)

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

    def create_form(self, db_version, ip):
        # Create the form with blank version message, next version number, and ip address.
        form = SystemVersionForm(instance=db_version, initial={
            'version_message': "",
            'version_number': db_version.version_number + 1,
            'current': True,
            'creator': str(ip)})

        # Hide these fields. See forms.py.
        hidden = [
            'system',
            'version_number',
            'current',
            'creator'
        ]

        intro = [
            'version_message',
            'description',
            'history',
        ]

        features_form = []
        metadata_form = []
        intro_form = []
        hidden_form = []

        for field in list(form):
            if field.html_name.startswith('description_') or field.html_name.startswith('support_') or \
                    field.html_name.startswith('options_'):
                features_form.append(field)
            elif field.html_name in intro:
                intro_form.append(field)
            elif field.html_name in hidden:
                hidden_form.append(field)
            else:
                metadata_form.append(field)
        return {
            'intro_form': intro_form,
            'hidden_form': hidden_form,
            'features_form': features_form,
            'metadata_form': metadata_form
        }

    def post(self, request, db_name, key):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        db_article = System.objects.get(slug=slugify(db_name))
        if db_article.secret_key != key:
            return HttpResponseBadRequest()

        form_data = SystemVersionForm(request.POST, request.FILES)
        if form_data.is_valid():
            instance = form_data.save(commit=True)
            # Update the current version number of the article
            old_version = SystemVersion.objects.get(system=db_article, version_number=db_article.current_version)
            old_version.current = False
            old_version.save()
            db_article.current_version += 1
            db_article.save()
            context = LoadContext.load_base_context(request)
            context["db"] = LoadContext.load_db_data(instance)
            return HttpResponseRedirect('/db/%s' % db_article.slug)
        else:
            print "Invalid form"
            print form_data.errors
            db_version = SystemVersion.objects.get(name=db_article.name,
                                                   version_number=db_article.current_version)
            form = self.create_form(db_version, ip)
            context = LoadContext.load_base_context(request)
            context["key"] = key
            context["intro_form"] = form["intro_form"]
            context["hidden_form"] = form["hidden_form"]
            context["features_form"] = form["features_form"]
            context["metadata_form"] = form["metadata_form"]
            return render(request, 'database_edit.html',
                          context)

    def get(self, request, db_name, key):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        db_article = System.objects.get(slug=slugify(db_name))
        db_version = SystemVersion.objects.get(name=db_article.name,
                                               version_number=db_article.current_version)

        if db_article.secret_key == key:
            form = self.create_form(db_version, ip)
            context = LoadContext.load_base_context(request)
            context["db"] = LoadContext.load_db_data(db_version)
            context["key"] = key
            context["intro_form"] = form["intro_form"]
            context["hidden_form"] = form["hidden_form"]
            context["features_form"] = form["features_form"]
            context["metadata_form"] = form["metadata_form"]
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
            existing = System.objects.filter(name=name)
            if len(existing) == 0:
                key = util.generateSecretKey()
                # TODO slug= should call a helper function that can avoid collisions
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
            lang = ProgrammingLanguage(name=name)
            lang.save()
            return HttpResponseRedirect("/createdb")


class OSCreationView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(OSCreationView, self).dispatch(*args, **kwargs)

    def post(self, request):
        if request.POST.get('name', False):
            name = request.POST.get('name')
            os = OperatingSystem(name=name)
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

        if not params:
            # Return all systems if no search parameters given.
            for db in System.objects.all():
                name = db.name
                slug = db.slug
                letter_idx = start_letters.index(name[0].lower())
                ordered_list[letter_idx]["dbs"].append({"name": name,
                                                        "slug": slug})
        else:
            # Create a set of versions that match ALL search fields.
            matches = set()
            for field in params:
                # Parse the feature name to the actual model field.
                model_field = field.lower().replace(' ', '')
                search_options = params[field]
                for option in search_options:
                    # Get CURRENT db_versions pointing to each feature option using M2M reverse relationship.
                    feature_option = FeatureOption.objects.get(value=option)
                    options = 'options_' + model_field
                    supports = 'support_' + model_field
                    db_versions = feature_option.__getattribute__(options)\
                        .filter(current=True, **{supports: True})
                    # Return intersection which are versions that match ALL search fields.
                    if len(matches) == 0:
                        matches |= set(db_versions)
                    else:
                        matches &= set(db_versions)
            for db in matches:
                name = db.system.name
                slug = db.system.slug
                letter_idx = start_letters.index(name[0].lower())
                ordered_list[letter_idx]["dbs"].append({"name": name,
                                                        "slug": slug})

        # Arrange each list of databases alphabetically.
        for letter in ordered_list:
            letter['dbs'].sort(cmp=lambda x, y: cmp(x['name'].lower(), y['name'].lower()))

        return ordered_list

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
