# stdlib imports
from functools import reduce
import collections
import datetime
import operator
import json
import time
import urllib.parse
from pprint import pprint
# django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Count, Max, Min
from django.forms import HiddenInput
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.utils.text import smart_split
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
# third-party imports
from django_countries import countries
from haystack.inputs import AutoQuery
from haystack.query import SearchQuerySet
from lxml import etree
import jwt
# project imports
from dbdb.core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm, SystemFeaturesForm, \
    SystemVersionEditForm
from dbdb.core.models import CitationUrl
from dbdb.core.models import Feature
from dbdb.core.models import FeatureOption
from dbdb.core.models import License
from dbdb.core.models import OperatingSystem
from dbdb.core.models import ProgrammingLanguage
from dbdb.core.models import ProjectType
from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemRedirect
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVersionMetadata
from dbdb.core.models import SystemACL
from dbdb.core.models import SystemVisit
from dbdb.core.models import SystemRecommendation

# constants

FILTERGROUP_VISIBLE_LENGTH = 3
SITEMPA_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
SITEMAP_PREFIX = '{%s}' % SITEMPA_NS
SITEMAP_NSMAP = { None : SITEMPA_NS }


# helper classes

FieldSet = collections.namedtuple('FieldSet', ['id','label','choices','description','citation'])
LetterPage = collections.namedtuple('LetterPage', ['id','letter','is_active','is_disabled'])
Stat = collections.namedtuple('Stat', ['label','items', 'search_field', 'systems', 'count'])
StatItem = collections.namedtuple('StatItem', ['label','value','slug'])

class FilterChoice( collections.namedtuple('FilterChoice', ['id','label','checked']) ):

    is_hidden = False

    @property
    def sort_key(self):
        return (
            0 if self.checked else 1,
            self.label,
        )

    pass

class FilterGroup( collections.namedtuple('FieldSet', ['id','label','choices']) ):

    has_checked = False
    has_more = False

    def prepare(self):
        #self.choices.sort(key=lambda fc: fc.sort_key)

        for i,choice in enumerate(self.choices):
            self.has_checked = self.has_checked or choice.checked

            if i >= FILTERGROUP_VISIBLE_LENGTH and not choice.checked:
                choice.is_hidden = True
                self.has_more = True
                pass
            pass
        return

    pass


# class based views

# ==============================================
# EmptyFieldsView
# ==============================================
class EmptyFieldsView(View):

    template_name = 'core/empty-fields.html'

    def build_search_fields(include_citations=False):
        import django.db.models.fields

        IGNORE_TYPES = set([
            django.db.models.fields.AutoField,
            django.db.models.fields.related.ForeignKey,
            #django.db.models.fields.related.ManyToManyField,
        ])
        IGNORE_NAMES = set([
            "ver",
            "comment",
            "features",
            "created",
        ])
        
        version_fields = [ ]
        for f in SystemVersion._meta.get_fields():
            if f.name.endswith("_citations") and not include_citations:
                continue
            
            if not type(f) in IGNORE_TYPES and \
               not f.name in IGNORE_NAMES:
                version_fields.append(f.name)
        ## FOR
        
        meta_fields = [ ]
        for f in SystemVersionMetadata._meta.get_fields():
            if not type(f) in IGNORE_TYPES and \
               not f.name in IGNORE_NAMES:
                meta_fields.append(f.name)
        
        return (version_fields, meta_fields)
    ## DEF

    def get(self, request):
        import django.db.models.fields

        if not request.user.is_authenticated:
            return redirect( settings.LOGIN_URL + '?next=' + reverse('fields') )
        elif not request.user.is_superuser:
            raise Http404()

        version_fields, meta_fields = build_search_fields()
        versions = SystemVersion.objects.filter(is_current=True)

        search_field = request.GET.get('field')
        search_reverse = request.GET.get('reverse', False)
        if search_field:
            query = None
            field = None
            
            if search_field in version_fields:
                field = SystemVersion._meta.get_field(search_field)
                field_name = search_field
                if type(field) == django.db.models.fields.PositiveIntegerField:
                    query = Q(**{search_field: None})
                else:
                    query = Q(**{search_field: ''})
            
            elif search_field in meta_fields:
                field = SystemVersionMetadata._meta.get_field(search_field)
                field_name = "meta__" + search_field
                
                if type(field) in (django.db.models.fields.PositiveIntegerField, django.db.models.fields.related.ManyToManyField):
                    query = Q(**{field_name: None})
                else:
                    query = Q(**{field_name: ''})
            else:
                raise Exception("Invalid field '%s'" % search_field)
            
            if search_reverse:
                versions = versions.filter(~query)
            else:
                versions = versions.filter(query)
                
            # convert query list to regular list
            # and add href/url to each
            versions = list( versions.order_by('system__name') )
            for version in versions:
                version.href = request.build_absolute_uri( version.system.get_absolute_url() )
                if search_field in meta_fields:
                    if type(field) == django.db.models.fields.related.ManyToManyField:
                        method_handle = getattr(version.meta, search_field + "_str")
                        version.value = method_handle()
                    else:
                        version.value = getattr(version.meta, search_field, "XXX")
                else:
                    version.value = getattr(version, field_name, None)
                pass
        ## IF

        num_systems = System.objects.all().count()
        fields = sorted(version_fields + meta_fields)

        return render(request, self.template_name, {
            'activate': 'empty', # NAV-LINKS
            'versions': versions,
            'field': search_field,
            'reverse': search_reverse,
            'fields': fields,
            'match_percent': "%.1f" % (100 * (len(versions) / num_systems)),
            'num_systems': num_systems,
        })

    pass

## CLASS

# ==============================================
# DatabaseBrowseView
# ==============================================
class DatabaseBrowseView(View):

    template_name = 'core/database-browse.html'

    def build_filter_groups(self, querydict):
        empty_set = set()

        def reduce_feature_options(mapping, option):
            mapping[option.feature_id].choices.append(
                FilterChoice(
                    option.slug,
                    option.value,
                    option.slug in querydict.getlist( option.feature__slug, empty_set )
                )
            )
            return mapping

        other_filtersgroups = []
        
        # add countries
        fg_country = FilterGroup('country', 'Country', [
            FilterChoice(
               code,
               name,
               code in querydict.getlist( 'country', empty_set )
            )
            for code,name in list(countries)
        ])
        other_filtersgroups.append(fg_country)

        # add compatible
        fg_compatible = FilterGroup('compatible', 'Compatible With', [
            FilterChoice(
                sys.slug,
                sys.name,
                sys.slug in querydict.getlist( 'compatible', empty_set )
            )
            for sys in System.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_compatible)

        # add embedded
        fg_embedded = FilterGroup('embeds', 'Embeds / Uses', [
            FilterChoice(
                sys.slug,
                sys.name,
                sys.slug in querydict.getlist( 'embeds', empty_set )
            )
            for sys in System.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_embedded)

        # add derived from
        fg_derived = FilterGroup('derived', 'Derived From', [
            FilterChoice(
                sys.slug,
                sys.name,
                sys.slug in querydict.getlist( 'derived', empty_set )
            )
            for sys in System.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_derived)

        # add inspired by
        fg_inspired = FilterGroup('inspired', 'Inspired By', [
            FilterChoice(
                sys.slug,
                sys.name,
                sys.slug in querydict.getlist( 'inspired', empty_set )
            )
            for sys in System.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_inspired)

        # add operating system
        fg_os = FilterGroup('os', 'Operating System', [
            FilterChoice(
                os.slug,
                os.name,
                os.slug in querydict.getlist( 'os', empty_set )
            )
            for os in OperatingSystem.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_os)

        # add programming languages
        fg_programming = FilterGroup('programming', 'Programming Languages', [
            FilterChoice(
                p.slug,
                p.name,
                p.slug in querydict.getlist( 'programming', empty_set )
            )
            for p in ProgrammingLanguage.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_programming)

        # add project types
        fg_project_type = FilterGroup('type', 'Project Types', [
            FilterChoice(
                pt.slug,
                pt.name,
                pt.slug in querydict.getlist( 'type', empty_set )
            )
            for pt in ProjectType.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_project_type)

        # add licenses
        fg_license = FilterGroup('license', 'Licenses', [
            FilterChoice(
                l.slug,
                l.name,
                l.slug in querydict.getlist( 'license', empty_set )
            )
            for l in License.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_license)

        # build from list of features (alphabetical order)
        filtergroups = collections.OrderedDict(
            (
                f_id,
                FilterGroup(f_slug, f_label, []),
            )
            for f_id,f_slug,f_label in Feature.objects.all().order_by('label').values_list('id','slug','label')
        )

        # add feature options to features
        filtergroups = reduce(
            reduce_feature_options,
            FeatureOption.objects.all().order_by('value').values_list('feature_id','feature__slug','id','slug','value', named=True),
            filtergroups
        )

        filtergroups = other_filtersgroups + list( filtergroups.values() )

        for fg in filtergroups:
            fg.prepare()
            pass

        return filtergroups

    def build_pagination(self, letter):
        letters_alphabet = set(
            chr(i)
            for i in range( ord('A') , ord('Z')+1 )
        )
        letters_available = set(
            name.upper()[0]
            for name in System.objects.all().values_list('name', flat=True)
        )
        letters_missing = letters_alphabet.difference( letters_available )
        letters_all = letters_alphabet.union( letters_available )

        pagination = list(
            LetterPage(
                l,
                l,
                l == letter,
                l not in letters_available
            )
            for l in sorted(letters_all)
        )
        pagination.append(
            LetterPage(
                'ALL',
                'All',
                'ALL' == letter,
                False
            )
        )

        return pagination
    
    def convert_slugs(self, slugs):
        full_systems = [ ]
        for slug in slugs:
            try:
                full_systems.append(System.objects.get(slug=slug))
            except:
                # Ignore any invalid slugs 
                pass
        return full_systems
    ## DEF
        

    def do_search(self, request):
        has_search = False

        # map feature slugs to ids
        features_map = {
            f_slug : f_id
            for f_id,f_slug in Feature.objects.all().order_by().values_list('id','slug')
        }

        # map feature options slugs to ids
        featuresoptions_map = {
            (f_id,fo_slug) : fo_id
            for f_id,fo_id,fo_slug in FeatureOption.objects.all().order_by().values_list('feature_id','id','slug')
        }

        # pull search criteria
        search_q = request.GET.get('q', '').strip()
        search_fg = {
            features_map[k] : set( request.GET.getlist(k) )
            for k in request.GET.keys()
            if k in features_map
        }

        # define date filters
        search_start_min = request.GET.get('start-min', '').strip()
        search_start_max = request.GET.get('start-max', '').strip()
        search_end_min = request.GET.get('end-min', '').strip()
        search_end_max = request.GET.get('end-max', '').strip()

        # define static filters
        search_compatible = request.GET.getlist('compatible')
        search_country = request.GET.getlist('country')
        search_derived = request.GET.getlist('derived')
        search_embeds = request.GET.getlist('embeds')
        search_inspired = request.GET.getlist('inspired')
        search_os = request.GET.getlist('os')
        search_programming = request.GET.getlist('programming')
        search_type = request.GET.getlist('type')
        search_license = request.GET.getlist('license')

        # collect filters
        search_mapping = {
            'query': search_q,

            'start_min': search_start_min,
            'start_max': search_start_max,
            'end_min': search_end_min,
            'end_max': search_end_max,

            'compatible': search_compatible,
            'country': search_country,
            'derived': search_derived,
            'embeds': search_embeds,
            'inspired': search_inspired,
            'os': search_os,
            'programming': search_programming,
            'type': search_type,
            'license': search_license,
        }

        if not any(search_mapping.values()) and not any(search_fg):
            return (None, { })

        # create new search query
        sqs = SearchQuerySet()

        # apply keyword search to name (require all terms)
        if search_q:
            sqs = sqs.filter(content=AutoQuery(search_q))

        # apply year limits
        if all((search_start_min, search_start_max)):
            search_start_min = int(search_start_min)
            search_start_max = int(search_start_max)
            sqs = sqs.filter(start_year__gte=search_start_min, start_year__lte=search_start_max)
            pass

        if all((search_end_min, search_end_max)):
            search_end_min = int(search_end_min)
            search_end_max = int(search_end_max)
            sqs = sqs.filter(end_year__gte=search_end_min, end_year__lte=search_end_max)
            pass

        # search - compatible
        if search_compatible:
            sqs = sqs.filter(compatible_with__in=search_compatible)
            search_mapping['compatible'] = self.convert_slugs(search_compatible)
            pass

        # search - country
        if search_country:
            sqs = sqs.filter(countries__in=search_country)
            pass

        # search - derived from
        if search_derived:
            sqs = sqs.filter(derived_from__in=search_derived)
            search_mapping['derived'] = self.convert_slugs(search_derived)
            pass
        
        # search - embedded
        if search_embeds:
            sqs = sqs.filter(embedded__in=search_embeds)
            print(sqs)
            search_mapping['embeds'] = self.convert_slugs(search_embeds)
            pass

        # search - inspired by
        if search_inspired:
            sqs = sqs.filter(inspired_by__in=search_inspired)
            search_mapping['inspired'] = self.convert_slugs(search_inspired)
            pass

        # search - operating systems
        if search_os:
            sqs = sqs.filter(oses__in=search_os)
            pass

        # search - programming languages
        if search_programming:
            sqs = sqs.filter(written_langs__in=search_programming)
            pass

        # search - project types
        if search_type:
            sqs = sqs.filter(project_types__in=search_type)
            pass

        # search - licenses
        if search_license:
            sqs = sqs.filter(licenses__in=search_license)
            pass

        # convert feature option slugs to IDs to do search by filtering
        filter_option_ids = set()
        for feature_id,option_slugs in search_fg.items():
            option_ids = set( map(lambda option_slug: featuresoptions_map[(feature_id,option_slug)], option_slugs) )
            filter_option_ids.update(option_ids)
            pass

        # if there are filter options to search for, apply filter
        if filter_option_ids:
            for option_id in filter_option_ids:
                sqs = sqs.filter(feature_options__contains=option_id)

        return (sqs, search_mapping)

    def handle_old_urls(self, request):
        query = []

        # get mapping of feature options
        featuresoptions_map = {
            str(fo_id): (f_slug, fo_slug)
            for fo_id,fo_slug,f_slug in FeatureOption.objects.all().order_by().values_list('id','slug','feature__slug')
        }

        for k in request.GET.keys():
            for v in request.GET.getlist(k):
                if k.startswith('fg'):
                    query.append( featuresoptions_map[v] )
                    pass
                elif v:
                    query.append((k,v))
                    pass
                pass
            pass

        return redirect( request.path + '?' + urllib.parse.urlencode(query) )

    def get(self, request):
        # handle older filter group urls
        if any( filter(lambda k: k.startswith('fg'), request.GET.keys()) ):
           return self.handle_old_urls(request)

        # Perform the search and get back the versions along with a
        # mapping with the search keys
        results, search_keys = self.do_search(request)

        search_q = request.GET.get('q', '').strip()

        # Search Letter
        search_letter = request.GET.get('letter', '').strip().upper()

        if results is not None:
            pass
        elif search_letter == 'ALL' or not search_letter:
            results = SearchQuerySet()
            search_letter = 'ALL'
            pass
        elif search_letter:
            results = SearchQuerySet().filter(letter__exact=search_letter.lower()).filter(name__startswith=search_letter)
            pass

        # generate letter pagination
        pagination = self.build_pagination(search_letter)

        # convert query list to regular list
        results = list( results.order_by('name') )
        # check if there are results
        has_results = len(results) > 0

        # get year ranges
        years_start = SystemVersion.objects.filter(is_current=True).filter(start_year__gt=0).aggregate(
            min_start_year=Min('start_year'),
            max_start_year=Max('start_year')
        )
        years_end = SystemVersion.objects.filter(is_current=True).filter(end_year__gt=0).aggregate(
            min_end_year=Min('end_year'),
            max_end_year=Max('end_year')
        )

        years = {}
        years.update(years_start)
        years.update(years_end)

        return render(request, self.template_name, {
            'activate': 'browse', # NAV-LINKS
            'filtergroups': self.build_filter_groups(request.GET),

            'has_results': has_results,
            'pagination': pagination,
            'query': search_q,
            'results': results,
            'years': years,
            'has_search': len(search_keys) != 0,
            'search': search_keys,
        })

    pass


# ==============================================
# CounterView
# ==============================================
@method_decorator(csrf_exempt, name='dispatch')
class CounterView(View):

    @staticmethod
    def build_token(origin, **kwargs):
        payload = dict(kwargs)
        payload.update( {
            #'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=15), # +15 seconds ## disabled expatriation to allow caching
            'iss': 'counter:{}'.format(origin),
            'nbf': datetime.datetime.utcnow(),
        })

        s = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        s = s.decode('utf-8')

        return s

    def post(self, request):
        token = request.POST.get('token')

        if not token:
            return JsonResponse({ 'status':'missing token'}, status=400)

        try:
            payload = jwt.decode(
                token.encode('utf-8'),
                 settings.SECRET_KEY,
                 algorithms=['HS256']
            )

            iss = payload.get('iss')

            if iss == 'counter:system':
                pk = payload['pk']
                
                # Skip bots
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                if user_agent.lower().find("bot") != -1:
                    return JsonResponse({ 'status':'bot' })

                ## Update the system's counter
                system = None
                with transaction.atomic():
                    system = System.objects.select_for_update().get(pk=pk)
                    system.view_count += 1
                    system.save()
                #pass
                
                # And add a SystemVisit entry
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[-1].strip()
                else:
                    ip = request.META.get('REMOTE_ADDR')
                
                system_visit = SystemVisit(system=system, ip_address=ip, user_agent=user_agent[:127])
                system_visit.save()
                
            else:
                return JsonResponse({ 'status':('unrecognized counter: %r' % iss)}, status=400)
            pass
        except jwt.ExpiredSignatureError:
            return JsonResponse({ 'status':'expired counter'}, status=400)

        return JsonResponse({ 'status':'ok' })

    pass

# ==============================================
# CreateUser
# ==============================================
class CreateUser(View):

    template_name = 'registration/create_user.html'

    def get(self, request, *args, **kwargs):
        context = {
            'form': CreateUserForm(auto_id='%s'),
            'recaptcha_key': getattr(settings, 'NORECAPTCHA_SITE_KEY'),
        }
        return render(request, context=context, template_name=self.template_name)

    def post(self, request, *args, **kwargs):
        form = CreateUserForm(request.POST, auto_id='%s')
        User = get_user_model()

        if form.is_valid():
            User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            return redirect('/login/?status=success')

        return render(request, context={
            'form': form,
            'recaptcha_key': getattr(settings, 'NORECAPTCHA_SITE_KEY'),
        }, template_name=self.template_name)

    pass

# ==============================================
# DatabasesEditView
# ==============================================
class DatabasesEditView(View, LoginRequiredMixin):

    template_name = 'core/databases-edit.html'

    def build_features(self, feature_form):
        features = Feature.objects.all()
        features = collections.OrderedDict(
            (
                f.id,
                {
                    'id': 'feature_{}'.format(f.id),
                    'label': f.label,
                    'choices': None,
                    'description': None,
                    'citation': None,
                }
            )
            for f in features
        )
        for bf in feature_form:
            name = bf.name.split('_')[-1]
            feature_id = bf.field.feature_id

            features[feature_id][name] = bf
            pass
        return features

    @never_cache
    def get(self, request, slug=None):
                
        # If there is no slug, then they are trying to create a new database.
        # Only superusers are allowed to do that.
        if slug is None:
            if not request.user.is_superuser:
                raise Http404()

            # Create a new empty system for the form
            system = System()
            system_version = SystemVersion(system=system, is_current=True)
            system_meta = SystemVersionMetadata()
            system_features = SystemFeature.objects.none()
            pass
        
        # If there is a slug, then check to see whether they have permission
        # to edit this mofo
        else:
            # You always have to be logged in to edit an entry
            if not request.user.is_authenticated:
                return redirect( settings.LOGIN_URL + '?next=' + reverse('system', args=[slug]))
            
            system = System.objects.get(slug=slug)
            
            # Make sure this user has permissions to edit this page
            if not request.user.is_superuser:
                try:
                    system_acl = SystemACL.objects.get(system=system, user=request.user)
                except SystemACL.DoesNotExist:
                    base_url = reverse('system', args=[slug])
                    query_string =  urllib.parse.urlencode({'noperms': 1})
                    url = '{}?{}'.format(base_url, query_string)
                    return redirect(url)
            ## IF
                    
            # Load in what we need
            system_version = SystemVersion.objects.get(system=system, is_current=True)
            system_meta = system_version.meta
            system_features = system_version.features.all()
            pass

        system_form = SystemForm(instance=system)

        # Don't allow non-superusers from editting the system name
        # This only really hides it from the UI.
        if request.user.is_superuser:
            system_form.fields['orig_name'].widget = HiddenInput()
        else:
            system_form.fields['name'].widget = HiddenInput()
            system_form.fields['orig_name'].initial = system.name

        feature_form = SystemFeaturesForm(features=system_features)

        features = self.build_features(feature_form)

        return render(request, self.template_name, {
            'activate': 'create' if system.id is None else 'edit', # NAV-LINKS
            'system_name': system.name,
            'system_form': system_form,
            'system_version_form': SystemVersionForm(instance=system_version),
            'system_version_metadata_form': SystemVersionMetadataForm(instance=system_meta),
            'feature_form': feature_form,

            'features': features,
        })

    @transaction.atomic
    def post(self, request, slug=None):
        if slug is None:
            if not request.user.is_superuser:
                raise Http404()

            system = System()
            system_version = SystemVersion(system=system, is_current=True)
            system_meta = SystemVersionMetadata()
            system_features = SystemFeature.objects.none()
            pass
        else:
            system = System.objects.get(slug=slug)
            system_version = SystemVersion.objects.get(system=system, is_current=True)
            system_meta = system_version.meta
            system_features = system_version.features.all()
            pass

        system_form = SystemForm(request.POST, instance=system)
        system_version_form = SystemVersionEditForm(request.POST, request.FILES)
        system_version_metadata_form = SystemVersionMetadataForm(request.POST)
        feature_form = SystemFeaturesForm(request.POST, features=system_features)

        if system_form.is_valid() and \
            system_version_form.is_valid() and \
            system_version_metadata_form.is_valid() and \
            feature_form.is_valid():

            if request.user.is_superuser:
                original_system_slug = system.slug
                system = system_form.save(commit=False)
                system.slug = slugify(system.name)
                system.save()

                # handle a redirect for a name change
                if system.slug != original_system_slug:
                    SystemRedirect.objects.get_or_create(
                        slug=original_system_slug,

                        defaults=dict(
                            system=system
                        )
                    )
                    pass

                try:
                    logo = system.current().logo
                except SystemVersion.DoesNotExist:
                    logo = ''
                pass
            else:
                logo = system.current().logo
                pass

            system.systemversion_set.update(is_current=False)
            db_version = system_version_form.save(commit=False)
            db_version.creator = request.user
            db_version.system = system

            if logo and not db_version.logo: db_version.logo = logo

            db_version.save()
            system_version_form.save_m2m()

            db_meta = system_version_metadata_form.save()
            db_version.meta = db_meta
            db_version.save()

            system.ver = db_version.ver
            system.modified = timezone.now()
            system.save()

            db_version.description_citations.clear()
            for url in system_version_form.cleaned_data.get('description_citations', []):
                db_version.description_citations.add(url)

            db_version.history_citations.clear()
            for url in system_version_form.cleaned_data.get('history_citations', []):
                db_version.history_citations.add(url)

            db_version.start_year_citations.clear()
            for url in system_version_form.cleaned_data.get('start_year_citations', []):
                db_version.start_year_citations.add(url)

            db_version.end_year_citations.clear()
            for url in system_version_form.cleaned_data.get('end_year_citations', []):
                db_version.end_year_citations.add(url)

            features = {
                f.label : f
                for f in Feature.objects.all()
            }
            for field_name in feature_form.cleaned_data.keys():
                feature_label = '_'.join( field_name.split('_')[:-1] )

                feature = features[feature_label]
                value = feature_form.cleaned_data[field_name]

                if '_description' in field_name:
                    sf, _ = SystemFeature.objects.get_or_create(
                        system=db_version,
                        feature=feature
                    )

                    sf.description = value
                    sf.save()
                    pass
                elif '_citation'in field_name:
                    sf, _ = SystemFeature.objects.get_or_create(
                        system=db_version,
                        feature=feature
                    )

                    sf.citations.clear()
                    for url in filter(None, value.split(',')):
                        cit_url, _ = CitationUrl.objects.get_or_create(url=url)
                        sf.citations.add(cit_url)
                        pass
                    pass
                elif '_choices'in field_name:
                    sf, _ = SystemFeature.objects.get_or_create(
                        system=db_version,
                        feature=feature
                    )
                    if not value:
                        pass
                    elif isinstance(value, str):
                        sf.options.add(
                            FeatureOption.objects.get(
                                feature=feature,
                                value=value
                            )
                        )
                    else:
                        for v in value:
                            sf.options.add(
                                FeatureOption.objects.get(
                                    feature=feature,
                                    value=v
                                )
                            )
                        pass
                    pass
                pass

            return redirect(db_version.system.get_absolute_url())

        features = self.build_features(feature_form)

        return render(request, self.template_name, {
            'activate': 'edit', # NAV-LINKS
            'system_name': system.name,
            'system_form': system_form,
            'system_version_form': system_version_form,
            'system_version_metadata_form': system_version_metadata_form,
            'feature_form': feature_form,

            'features': features,
        })

    pass

# ==============================================
# DatabaseRevisionList
# ==============================================
class DatabaseRevisionList(View):

    template_name = 'core/revision_list.html'

    def get(self, request, slug):
        system = get_object_or_404(System, slug=slug)

        versions = SystemVersion.objects \
            .filter(system=system) \
            .select_related('system')

        return render(request, self.template_name, {
            'activate': 'revisions', # NAV-LINKS
            'system': system,
            'versions': versions,
        })

    @method_decorator(login_required)
    def post(self, request, slug):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        system = System.objects.get(slug=slug)
        version = SystemVersion.objects.get(id=request.POST['ver'])
        system.systemversion_set.update(is_current=False)
        version.is_current = True
        system.ver = version.ver
        system.modified = timezone.now()
        version.save()
        system.save()

        return redirect('system', slug=slug)

    pass

# ==============================================
# DatabaseRevisionView
# ==============================================
class DatabaseRevisionView(View):

    template_name = 'core/revision_view.html'

    def get(self, request, slug, ver):
        system_version = get_object_or_404(SystemVersion.objects.select_related('system'), system__slug=slug, ver=ver)

        return render(request, self.template_name, {
            'activate': 'revisions', # NAV-LINKS
            'system': system_version.system,
            'system_version': system_version,
            'has_revision': True,
            'system_features': system_version.features.all()
        })

    pass

# ==============================================
# RecentChangesView
# ==============================================
class RecentChangesView(View):

    template_name = 'core/recent.html'

    def get(self, request):
        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
        page = request.GET.get('page', 1)
        username = request.GET.get('username', None)
        versions = None
        lookup_user = None

        # Try to get the versions for the given username
        if not username is None:
            User = get_user_model()
            try:
                lookup_user = User.objects.get(username=username)
                versions = SystemVersion.objects.filter(creator=lookup_user)
            except:
                lookup_user = None
                pass
        if versions is None:
            versions = SystemVersion.objects.all()

        # Sort by timestamps
        versions = versions.order_by('-created')

        paginator = Paginator(versions, 25)
        try:
            versions = paginator.get_page(page)
        except PageNotAnInteger:
            versions = paginator.get_page(1)
        except EmptyPage:
            versions = paginator.get_page(paginator.num_pages)

        return render(request, self.template_name, context={
            'activate': 'recent', # NAV-LINKS
            'versions': versions,
            'lookup_user': lookup_user,
        })

    pass

# ==============================================
# HomeView
# ==============================================
class HomeView(View):

    template_name = 'core/home.html'

    def get(self, request):
        items_to_show = 5

        num_systems = System.objects.all().count()


        most_edited = System.objects.order_by('-ver', '-name')[:items_to_show]
        most_recent = System.objects.order_by('-modified')[:items_to_show]
        most_views = System.objects.order_by('-view_count')[:items_to_show]

        return render(request, self.template_name, context={
            'num_systems': num_systems,
            'most_edited': most_edited,
            'most_recent': most_recent,
            'most_views': most_views,

            'no_nav_search': True,
        })

    pass

# ==============================================
# StatsView
# ==============================================
class StatsView(View):

    template_name = 'core/stats.html'
    default_limit = 10

    def get_bycountries(self, limit):
        def reduce_countries(mapping, item):
            countries = item.countries.split(',')
            for c in countries:
                if c:
                    mapping[c] = mapping.get(c, 0) + 1
            return mapping

        system_countries = SystemVersion.objects \
            .filter(is_current=True) \
            .values_list('system_id', 'countries', named=True)
        system_countries = reduce(reduce_countries, system_countries, {})
        
        system_countries = [
            StatItem(k, v, k)
            for k,v in system_countries.items()
        ]
        system_countries.sort(key=lambda i: i.value, reverse=True)

        stat = Stat(
            'Country of Origin',
            system_countries[:limit],
            'country',
            False,
            len(system_countries)
        )

        return stat
    
    def get_by_field(self, title, field, search_field, labels, slugs, is_systems, limit):
        def reduce_counts(mapping, item):
            assert not mapping is None
            if item is not None:
                mapping[item] = mapping.get(item, 0) + 1
        
        values = SystemVersionMetadata.objects \
            .filter(systemversion__is_current=True) \
            .filter(~Q(**{field: None})) \
            .values_list('systemversion__system_id', field, named=True)
        #pprint(values)
        counts = { }
        for v in values:
            #print(v[0])
            counts[v[1]] = counts.get(v[1], 0) + 1
        #counts = reduce(reduce_counts, values, { })
        pprint(counts)
        
        stat_items = [ ]
        
        if is_systems:
            stat_items = [
                StatItem(System.objects.get(id=k), v, slugs[k])
                for k,v in counts.items()
            ]
        else:
            stat_items = [
                StatItem(labels[k], v, slugs[k])
                for k,v in counts.items()
            ]
            
        stat_items.sort(key=lambda i: i.value, reverse=True)
        stat = Stat(
            title,
            stat_items[:limit],
            search_field,
            is_systems,
            len(stat_items)
        )

        return stat
        

    def get(self, request, stats_type=None):
        stats = []

        # Countries
        if stats_type is None or stats_type == "country":
            limit = -1 if stats_type == "country" else self.default_limit
            stats.append( self.get_bycountries(limit) )

        # Licenses
        if stats_type is None or stats_type == "license":
            limit = -1 if stats_type == "license" else self.default_limit
            labels = dict(License.objects.all().values_list('id', 'name'))
            slugs = dict(License.objects.all().values_list('id', 'slug'))
            stats.append( self.get_by_field('License', 'licenses', 'license', labels, slugs, False, limit) )

        # Implementation Language
        if stats_type is None or stats_type == "programming":
            limit = -1 if stats_type == "programming" else self.default_limit
            all_values = ProgrammingLanguage.objects.all()
            labels = dict(all_values.values_list('id', 'name'))
            slugs = dict(all_values.values_list('id', 'slug'))
            stats.append( self.get_by_field('Programming Lang.', 'written_in', 'programming', labels, slugs, False, limit) )
        
        all_values = System.objects.all()
        labels = dict(all_values.values_list('id', 'name'))
        slugs = dict(all_values.values_list('id', 'slug'))
        
        # Compatibility
        if stats_type is None or stats_type == "compatible":
            stats.append( self.get_by_field('Compatibility', 'compatible_with', 'compatible', labels, slugs, True, self.default_limit) )
        
        # Derived From
        if stats_type is None or stats_type == "derived":
            stats.append( self.get_by_field('Derived From', 'derived_from', 'derived', labels, slugs, True, self.default_limit) )
        
        # Embeds
        if stats_type is None or stats_type == "embeds":
            stats.append( self.get_by_field('Embeds / Uses', 'embedded', 'embeds', labels, slugs, True, self.default_limit ) )

        return render(request, self.template_name, context={
            'activate': 'stats', # NAV-LINKS
            'stats': stats,
            'stats_type': stats_type,
        })

    pass

# ==============================================
# SitemapView
# ==============================================
class SitemapView(View):

    def get(self, request):
        response = HttpResponse(content_type='text/xml; charset=utf-8')

        root = etree.Element(SITEMAP_PREFIX+'urlset', nsmap=SITEMAP_NSMAP)
        tree = etree.ElementTree(root)

        for system in System.objects.order_by('name').iterator():
            url = etree.SubElement(root, 'url')
            loc = etree.SubElement(url, 'loc')
            loc.text = request.build_absolute_uri( reverse('system', args=[system.slug]) )
            lastmod = etree.SubElement(url, 'lastmod')
            lastmod.text = system.modified.date().isoformat()
            changefreq = etree.SubElement(url, 'changefreq')
            changefreq.text = 'daily'
            pass

        tree.write(response, encoding='UTF-8', pretty_print=True, xml_declaration=True)

        return response

    pass

# ==============================================
# SystemView
# ==============================================
class SystemView(View):

    template_name = 'core/system.html'

    def get(self, request, slug):
        # try to get system by slug
        try:
            system = System.objects.get(slug=slug)
            pass
        except System.DoesNotExist:
            # if the system doesn't exist, check for a redirect
            try:
                r = SystemRedirect.objects.get(slug=slug)
                return redirect( 'system' , permanent=True, slug=r.system.slug )
                pass
            except SystemRedirect.DoesNotExist:
                # with no redirect, throw 404
                raise Http404( 'system does not exist' )
                pass
            pass

        system_version = system.current()
        system_features = SystemFeature.objects.filter(system=system_version).select_related('feature').order_by('feature__label')

        # If they are logged in, check whether they are allowed to edit
        user_can_edit = False
        if request.user.is_authenticated:
            if request.user.is_superuser:
                user_can_edit = True
            else:
                try:
                    SystemACL.objects.get(system=system, user=request.user)
                    user_can_edit = True
                except SystemACL.DoesNotExist:
                    pass
        ## IF
        
        # Recommendations
        recommendations = [ ]
        for rec in SystemRecommendation.objects.filter(system=system).order_by("-recommendation__name").select_related():
            recommendations.append(rec.recommendation)
        

        return render(request, self.template_name, {
            'activate': 'system', # NAV-LINKS
            'system': system,
            'system_features': system_features,
            'system_version': system_version,
            'user_can_edit': user_can_edit,
            'recommendations': recommendations,
            'counter_token': CounterView.build_token('system', pk=system.id),
        })

    pass


# ==============================================
# System Name AutoComplete 
# ==============================================
def search_autocomplete(request):
    search_q = request.GET.get('q', '').strip()
    if search_q:
        sqs = SearchQuerySet().autocomplete(autocomplete_name=request.GET.get('q', ''))[:5]
        suggestions = [system.name for system in sqs]
    else:
        suggestions = [ ]
        
    data = json.dumps(suggestions)
    return HttpResponse(data, content_type='application/json')
