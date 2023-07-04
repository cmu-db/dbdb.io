# stdlib imports
from functools import reduce
import collections
import datetime
import json
import operator
import time
import urllib.parse
# django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from django.db import transaction
from django.db.models import Q, Count, Max, Min, Func, Value
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
from django.views.decorators.cache import never_cache, cache_control
from django.views.decorators.csrf import csrf_exempt
# third-party imports
from django_countries import countries
from lxml import etree
import jwt
import pytz
# project imports
from dbdb.core.common.searchvector import SearchVector
from dbdb.core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm, SystemFeaturesForm, \
    SystemVersionEditForm
from dbdb.core.models import CitationUrl, SystemSearchText
from dbdb.core.models import Feature
from dbdb.core.models import FeatureOption
from dbdb.core.models import License
from dbdb.core.models import OperatingSystem
from dbdb.core.models import ProgrammingLanguage
from dbdb.core.models import Tag
from dbdb.core.models import ProjectType
from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemRedirect
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVersionMetadata
from dbdb.core.models import SystemACL
from dbdb.core.models import SystemVisit
from dbdb.core.models import SystemRecommendation


UserModel = get_user_model()

# constants
FILTERGROUP_VISIBLE_LENGTH = 3
SITEMPA_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
SITEMAP_PREFIX = '{%s}' % SITEMPA_NS
SITEMAP_NSMAP = { None : SITEMPA_NS }


# helper classes
FieldSet = collections.namedtuple('FieldSet', ['id','label','choices','description','citation'])
LetterPage = collections.namedtuple('LetterPage', ['id','letter','is_active','is_disabled'])
Stat = collections.namedtuple('Stat', ['label','items', 'search_field', 'systems', 'count'])
StatItem = collections.namedtuple('StatItem', ['label','value','slug','url'])

# ==============================================
# FilterChoice
# ==============================================
class FilterChoice( collections.namedtuple('FilterChoice', ['id','label','checked']) ):

    is_hidden = False

    @property
    def sort_key(self):
        return (
            0 if self.checked else 1,
            self.label,
        )

    pass

# ==============================================
# FilterGroup
# ==============================================
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

# ==============================================
# SearchBadge
# ==============================================
class SearchBadge:

    __slots__ = ['query','group_slug','group_name', 'badge_slug', 'badge_name']

    def __init__(self, query, group_slug, group_name, badge_slug, badge_name):
        self.query = query
        self.group_slug = group_slug
        self.group_name = group_name
        self.badge_slug = badge_slug
        self.badge_name = badge_name
        return

    def __repr__(self):
        return repr( tuple( map(str, (self.group_slug, self.group_name, self.badge_slug, self.badge_name)) ) )

    def get_removal_url(self):
        query = []

        for key,values in self.query.lists():
            for value in values:
                if key == self.group_slug and value == self.badge_slug:
                    continue
                query.append((key, value))

        return '?' + urllib.parse.urlencode(query, doseq=False)

    pass


# helper functions

def staff_check(user):
    return user.is_staff

def super_user_check(user):
    return user.is_superuser


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

                # SPECIAL!
                # I want to be able to find all the non-SVG logos
                if f.name == "logo": version_fields.append(f.name + "__SVG")
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

        version_fields, meta_fields = EmptyFieldsView.build_search_fields()
        versions = SystemVersion.objects.filter(is_current=True)

        search_field = request.GET.get('field')
        search_reverse = request.GET.get('reverse', False)
        if search_field:
            query = None
            field = None

            if search_field in version_fields:
                # SPECIAL
                if search_field.endswith("__SVG"):
                    field = SystemVersion._meta.get_field(search_field[:-5])
                else:
                    field = SystemVersion._meta.get_field(search_field)
                field_name = field.name
                field_type = type(field)

                # We have to query the different field types a certain way
                if field_type == django.db.models.fields.PositiveIntegerField:
                    query = Q(**{field_name: None})
                elif field_type == django.db.models.fields.related.ManyToManyField:
                    query = Q(**{field_name: None})
                elif search_field.endswith("__SVG"):
                    query = Q(logo__endswith=".svg")
                else:
                    query = Q(**{field_name: ''})

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
                    if type(field) == django.db.models.fields.related.ManyToManyField:
                        method_handle = getattr(version, search_field + "_str")
                        version.value = method_handle()
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
class BrowseView(View):

    template_name = 'core/browse.html'

    def build_filter_group_for_field(self, field, search_field, label, all_systems, querydict):
        empty_set = set()

        values = SystemVersionMetadata.objects \
            .filter(systemversion__is_current=True) \
            .filter(~Q(**{field: None})) \
            .values_list(field)
            #.distinct() \
            #.order_by()
        fg = FilterGroup(search_field, label, sorted([
            FilterChoice(
                all_systems[v[0]].slug,
                all_systems[v[0]].name,
                all_systems[v[0]].slug in querydict.getlist(search_field, empty_set)
            )
            for v in set(values)
            #for sys in System.objects.values_list('id','slug','name', named=True)
        ], key=lambda x: x[1]))
        return fg

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

        # Countries
        def reduce_countries(mapping, item):
            countries = item.countries.split(',')
            for c in countries:
                if c: mapping[c] = mapping.get(c, 0) + 1
            return mapping

        system_countries = SystemVersion.objects \
            .filter(is_current=True) \
            .values_list('countries', named=True)
        system_countries = reduce(reduce_countries, system_countries, {})

        countries_map = dict(countries)

        fg_country = FilterGroup('country', 'Country', sorted([
            FilterChoice(
               code,
               countries_map[code], # name,
               code in querydict.getlist( 'country', empty_set )
            )
            for code in system_countries.keys()
        ], key=lambda x: x[1]))
        other_filtersgroups.append(fg_country)

        all_systems = dict([
            (sys.id, sys)
            for sys in System.objects.values_list('id','slug','name', named=True)
        ])

        # Compatible
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'compatible_with', \
            'compatible', \
            'Compatible With', \
            all_systems, \
            querydict
        ))

        # Embedded
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'embedded', \
            'embeds', \
            'Embeds / Uses', \
            all_systems, \
            querydict
        ))

        # Derived
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'derived_from', \
            'derived', \
            'Derived From', \
            all_systems, \
            querydict
        ))

        # Inspired
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'inspired_by', \
            'inspired', \
            'Inspired By', \
            all_systems, \
            querydict
        ))

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

        # add tags
        fg_tag = FilterGroup('tag', 'Tags', [
            FilterChoice(
                t.slug,
                t.name,
                t.slug in querydict.getlist( 'tag', empty_set )
            )
            for t in Tag.objects.values_list('id','slug','name', named=True)
        ])
        other_filtersgroups.append(fg_tag)

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
            "#" if not name.upper()[0].isalpha() else name.upper()[0]
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

    def slug_to_system(self, slugs):
        slugs = { s.strip() for s in slugs }
        systems = System.objects.filter(slug__in=slugs)
        return { s.slug : s for s in systems }
    ## DEF


    def do_search(self, request, sqs):
        has_search = False

        countries_map = dict(countries)

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
        search_supported = request.GET.getlist('supported')
        search_type = request.GET.getlist('type')
        search_tag = request.GET.getlist('tag')
        search_license = request.GET.getlist('license')
        search_suffix = request.GET.getlist('suffix')

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
            'supported': search_supported,
            'tag': search_tag,
            'type': search_type,
            'license': search_license,
            'suffix': search_suffix,
        }

        if not any(search_mapping.values()) and not any(search_fg):
            return (sqs, { }, [])

        search_badges = []

        # apply keyword search to name (require all terms)
        if search_q:
            search_vector = SearchVector('search_text', config='simple')
            search_query = SearchQuery(search_q, config='simple')
            # search_rank = TrigramSimilarity('search_text', search_q)
            # search_rank = SearchRank(search_vector, search_query)

            # Since we can't pass the rank over to the main search (sqs),
            # we can ignore it for now.
            # It doesn't seem to produce reliable results anyway.
            matches = SystemSearchText.objects \
                .annotate(search=search_vector) \
                .filter(search=search_query) \
                .values('system_id')
                # .annotate(rank=search_rank) \
                # .order_by("-rank") \
                # .values('system_id', 'rank')
            sqs = sqs.filter(system_id__in=[x['system_id'] for x in matches])

        # apply year limits
        if search_start_min.isdigit():
            sqs = sqs.filter(start_year__gte=int(search_start_min))
            pass
        if search_start_max.isdigit():
            sqs = sqs.filter(start_year__lte=int(search_start_max))
            pass
        if search_end_min.isdigit():
            sqs = sqs.filter(end_year__gte=int(search_end_min))
            pass
        if search_end_max.isdigit():
            sqs = sqs.filter(end_year__lte=int(search_end_max))
            pass

        # search - country
        if search_country:
            sqs = sqs.filter(countries__in=search_country)
            search_badges.extend( SearchBadge(request.GET, 'country', 'Country', c, countries_map[c]) for c in search_country )
            pass

        # search - compatible
        if search_compatible:
            sqs = sqs.filter(meta__compatible_with__slug__in=search_compatible)
            systems = self.slug_to_system(search_compatible)
            search_mapping['compatible'] = systems.values()
            search_badges.extend( SearchBadge(request.GET, 'compatible', 'Compatible With', k, v) for k,v in systems.items() )
            pass

        # search - derived from
        if search_derived:
            sqs = sqs.filter(meta__derived_from__slug__in=search_derived)
            systems = self.slug_to_system(search_derived)
            search_mapping['derived'] = systems.values()
            search_badges.extend( SearchBadge(request.GET, 'derived', 'Derived From', k, v) for k,v in systems.items() )
            pass

        # search - embedded
        if search_embeds:
            sqs = sqs.filter(meta__embedded__slug__in=search_embeds)
            systems = self.slug_to_system(search_embeds)
            search_mapping['embeds'] = systems.values()
            search_badges.extend( SearchBadge(request.GET, 'embeds', 'Embeds / Uses', k, v) for k,v in systems.items() )
            pass

        # search - inspired by
        if search_inspired:
            sqs = sqs.filter(meta__inspired_by__slug__in=search_inspired)
            systems = self.slug_to_system(search_inspired)
            search_mapping['inspired'] = systems.values()
            search_badges.extend( SearchBadge(request.GET, 'inspired', 'Inspired By', k, v) for k,v in systems.items() )
            pass

        # search - operating systems
        if search_os:
            sqs = sqs.filter(meta__oses__slug__in=search_os)
            oses = OperatingSystem.objects.filter(slug__in=search_os)
            search_badges.extend( SearchBadge(request.GET, 'os', 'Operating System', os.slug, os.name) for os in oses )
            pass

        # search - programming languages
        if search_programming:
            sqs = sqs.filter(meta__written_in__slug__in=search_programming)
            langs = ProgrammingLanguage.objects.filter(slug__in=search_programming)
            search_badges.extend( SearchBadge(request.GET, 'programming', 'Programming Languages', lang.slug, lang.name) for lang in langs )
            pass

        # search - supported languages
        if search_supported:
            sqs = sqs.filter(meta__supported_languages__slug__in=search_supported)
            langs = ProgrammingLanguage.objects.filter(slug__in=search_supported)
            search_badges.extend( SearchBadge(request.GET, 'supported', 'Supported Languages', lang.slug, lang.name) for lang in langs )
            pass

        # search - tags
        if search_tag:
            sqs = sqs.filter(tags__slug__in=search_tag)
            tags = Tag.objects.filter(slug__in=search_tag)
            search_badges.extend( SearchBadge(request.GET, 'type', 'Tags', t.slug, t.name) for t in tags )
            pass

        # search - project types
        if search_type:
            sqs = sqs.filter(project_types__slug__in=search_type)
            types = ProjectType.objects.filter(slug__in=search_type)
            search_badges.extend( SearchBadge(request.GET, 'type', 'Project Types', type.slug, type.name) for type in types )
            pass

        # search - licenses
        if search_license:
            sqs = sqs.filter(licenses__slug__in=search_license)
            licenses = License.objects.filter(slug__in=search_license)
            search_badges.extend( SearchBadge(request.GET, 'license', 'Licenses', license.slug, license.name) for license in licenses )
            pass

        # search - suffixes
        if search_suffix:
            for suffix in search_suffix:
                sqs = sqs.filter(system__name__icontains=suffix)
            search_badges.extend(SearchBadge(request.GET, 'suffix', 'Suffix', suffix, suffix) for suffix in search_suffix)
            pass

        # convert feature option slugs to IDs to do search by filtering
        filter_option_ids = set()
        for feature_id,option_slugs in search_fg.items():
            option_ids = set( map(lambda option_slug: featuresoptions_map[(feature_id,option_slug)], option_slugs) )
            filter_option_ids.update(option_ids)
            pass

        # if there are filter options to search for, apply filter
        if filter_option_ids:
            # FIXME
            # for option_id in filter_option_ids:
            #     sqs = sqs.filter(feature_options__contains=option_id)

            search_badges.extend(
                SearchBadge(request.GET, *row)
                for row in FeatureOption.objects.filter(id__in=filter_option_ids).values_list('feature__slug','feature__label','slug','value')
            )

        return (sqs, search_mapping, search_badges)

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

        # Search Query
        search_q = request.GET.get('q', '').strip()

        # Search Letter
        search_letter = request.GET.get('letter', '').strip().upper()

        # Perform the search and get back the versions along with a
        # mapping with the search keys
        search_keys = { }
        search_badges = { }
        results = SystemVersion.objects.filter(is_current=True)

        if search_letter and search_letter != 'ALL':
            if search_letter == "#":
                results = results.filter(system__name__regex=r'^\d')
            else:
                results = results.filter(system__name__istartswith=search_letter)
        else:
            results, search_keys, search_badges = self.do_search(request, results)
            search_letter = 'ALL'

        # generate letter pagination
        pagination = self.build_pagination(search_letter)

        # Only get the columns we need for the browse page
        # FIXME results = results.values('system__name', 'system__slug', 'logo', 'created')

        # convert query list to regular list
        results = list( results.order_by('system__name') )
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
            'badges': search_badges,
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

                # And add a SystemVisit entry
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[-1].strip()
                else:
                    ip = request.META.get('REMOTE_ADDR')

                # save visit
                system_visit = SystemVisit.objects.create(
                    system_id=pk,
                    ip_address=ip,
                    user_agent=user_agent[:127]
                )
                pass
            else:
                return JsonResponse({ 'status':('unrecognized counter: %r' % iss) }, status=400)
            pass
        except jwt.ExpiredSignatureError:
            return JsonResponse({ 'status':'expired counter' }, status=400)

        return JsonResponse({ 'status':'ok' })

    pass

# ==============================================
# CreateUserView
# ==============================================
class CreateUserView(View):

    TOKEN_QUERY_NAME = 'token'

    template_name = 'registration/create_user.html'

    def decode_token(self, request):
        token = request.GET.get(CreateUserView.TOKEN_QUERY_NAME)

        if not token:
            return None

        try:
            payload = jwt.decode(
                token.encode('utf-8'),
                settings.SECRET_KEY,
                algorithms=['HS256'],
                verify=True
            )
            pass
        except jwt.exceptions.ExpiredSignatureError:
            payload = False
        except:
            payload = None

        return payload

    def get(self, request, *args, **kwargs):
        expired_token = False
        initial = { }

        reg_info = self.decode_token(request)
        if reg_info == False:
            expired_token = True
            pass
        elif reg_info and 'sub' in reg_info:
            initial['email'] = reg_info['sub']

        form = CreateUserForm(auto_id='%s', initial=initial)

        return render(request, self.template_name, {
            'title': 'User Registration',

            'expired_token': expired_token,
            'form': form,
            'recaptcha_key': getattr(settings, 'RECAPTCHA_PUBLIC_KEY'),
        })

    def post(self, request, *args, **kwargs):
        expired_token = False
        initial = { }

        # check for a registration info
        reg_info = self.decode_token(request)
        # if the registration expired `False` then return to login page
        if reg_info == False:
            return redirect(settings.LOGIN_URL + '?status=failed')
            pass
        # if the registration included a subject, use as email address
        elif reg_info and 'sub' in reg_info:
            initial['email'] = reg_info['sub']
            pass

        # create form class (it handles enforcing initial email)
        form = CreateUserForm(request.POST, auto_id='%s', initial=initial)

        if form.is_valid():
            with transaction.atomic():
                # create user with provided info
                user = UserModel.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password']
                )

                # associate the user with various systems if specified in registration info
                if reg_info and 'systems' in reg_info:
                    system_ids = list( map(int, reg_info['systems']) )

                    # NOTE: if registration contained no longer valid system IDs, this will error out
                    SystemACL.objects.bulk_create([
                        SystemACL(
                            system_id=system_id,
                            user_id=user.id
                        )
                        for system_id in system_ids
                    ])
                    pass
                pass

            # end successfully with a redirect to login page
            return redirect(settings.LOGIN_URL + '?status=success')

        return render(request, self.template_name, {
            'form': form,
            'recaptcha_key': getattr(settings, 'RECAPTCHA_PUBLIC_KEY'),
        })

    pass

# ==============================================
# DatabasesEditView
# ==============================================
class DatabasesEditView(LoginRequiredMixin, View):

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

    @method_decorator(cache_control(private=True))
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
            old_logo = None
            pass
        else:
            system = System.objects.get(slug=slug)
            system_version = SystemVersion.objects.get(system=system, is_current=True)
            system_meta = system_version.meta
            system_features = system_version.features.all()
            old_logo = system_version.logo
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

            system.versions.update(is_current=False)
            db_version = system_version_form.save(commit=False)
            db_version.creator = request.user
            db_version.system = system

            if logo and not db_version.logo:
                db_version.logo = logo

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
                        version=db_version,
                        feature=feature
                    )

                    sf.description = value
                    sf.save()
                    pass
                elif '_citation'in field_name:
                    sf, _ = SystemFeature.objects.get_or_create(
                        version=db_version,
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
                        version=db_version,
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

            # Do this down here to make sure the logo gets uploaded correctly
            if db_version.logo is not None and old_logo != db_version.logo:
                db_version.create_twitter_card()

            # Update the search index too!
            ver_search, created = SystemSearchText.objects.update_or_create(
                system=system,
                search_text=db_version.generate_searchtext())
            ver_search.save()

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
        system.versions.update(is_current=False)
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

    template_name = 'core/system-revision.html'

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

    ITEMS_TO_SHOW = 5

    template_name = 'core/home.html'

    def get(self, request):
        # calculate date window
        start_date = timezone.now().astimezone(pytz.utc) - datetime.timedelta(days=30) # rolling 30 days
        start_date = datetime.datetime.combine(start_date.date(), datetime.time(0, 0, 0))
        start_date = pytz.utc.localize(start_date)

        # get top systems by modified date
        most_recent = System.objects \
            .order_by('-modified')
        most_recent = most_recent[:HomeView.ITEMS_TO_SHOW]

        # get top systems by number of (windowed) versions
        most_versions = System.objects \
            .annotate(num_versions=Count('versions__id', filter=Q(versions__created__gte=start_date))) \
            .order_by('-num_versions', 'name') \
            .filter(num_versions__gt=0)
        most_versions = most_versions[:HomeView.ITEMS_TO_SHOW]

        # get top systems by number of (windowed) visits
        most_visits = System.objects \
            .annotate(num_visits=Count('visits__id', filter=Q(visits__created__gte=start_date))) \
            .order_by('-num_visits', 'name') \
            .filter(num_visits__gt=0)
        most_visits = most_visits[:HomeView.ITEMS_TO_SHOW]

        # count numb systems
        num_systems = System.objects.all().count()

        return render(request, self.template_name, {
            'most_recent': most_recent,
            'most_versions': most_versions,
            'most_visits': most_visits,

            'no_nav_search': True,
            'num_systems': num_systems,
        })

    pass

# ==============================================
# SetupUserView
# ==============================================
class SetupUserView(UserPassesTestMixin, View):

    TOKEN_QUERY_NAME = 'token'

    template_name = 'registration/setup_user.html'

    def build_token(self, email, systems):
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
            'iss': 'setup_user',
            'sub': email,
            'nbf': datetime.datetime.utcnow(),
            'systems': list( map(int, systems) ),
        }

        s = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        s = s.decode('utf-8')

        return s

    def get(self, request, *args, **kwargs):
        if request.GET.get('action') == 'url' and request.GET.get('email') and request.GET.getlist('systems'):
            email = request.GET.get('email').lower().strip()
            systems = request.GET.getlist('systems')

            response = None

            if UserModel.objects.filter(email=email).exists():
                response = { 'error':'Email already exists' }
                pass
            else:
                url = reverse('create_user') + '?' + urllib.parse.urlencode({ SetupUserView.TOKEN_QUERY_NAME:self.build_token(email, systems) })
                url = request.build_absolute_uri(url)

                response = { 'url':url }
                pass

            return JsonResponse(response)

        return render(request, self.template_name, {
            'title': 'User Registration Setup',

            'systems': System.objects.all(),
        })

    def test_func(self):
        return super_user_check(self.request.user)

    pass

# ==============================================
# StatsView
# ==============================================
class StatsView(View):

    template_name = 'core/stats.html'
    default_limit = 10
    is_superuser = False

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
            StatItem(k, v, k, None)
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

    def get_versionmeta_stat(self, title, field, search_field, labels, slugs, is_systems, limit):

        def reduce_counts(mapping, item):
            assert not mapping is None
            if item is not None:
                mapping[item] = mapping.get(item, 0) + 1

        values = SystemVersionMetadata.objects \
            .filter(systemversion__is_current=True) \
            .filter(~Q(**{field: None})) \
            .values_list('systemversion__system_id', field, named=True)

        counts = { }
        for v in values:
            counts[v[1]] = counts.get(v[1], 0) + 1
        #counts = reduce(reduce_counts, values, { })

        stat_items = [ ]

        if is_systems:
            stat_items = [
                StatItem(System.objects.get(id=k), v, slugs[k], None)
                for k,v in counts.items()
            ]
        else:
            stat_items = [
                StatItem(labels[k], v, slugs[k], None)
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

    def get_version_stat(self, title, field, search_field, labels, slugs, is_systems, limit):

        def reduce_counts(mapping, item):
            assert not mapping is None
            if item is not None:
                mapping[item] = mapping.get(item, 0) + 1

        values = SystemVersion.objects \
            .filter(is_current=True) \
            .filter(~Q(**{field: None})) \
            .values_list('system_id', field, named=True)

        counts = { }
        for v in values:
            counts[v[1]] = counts.get(v[1], 0) + 1
        #counts = reduce(reduce_counts, values, { })

        stat_items = [ ]

        if is_systems:
            stat_items = [
                StatItem(System.objects.get(id=k), v, slugs[k], None)
                for k,v in counts.items()
            ]
        else:
            stat_items = [
                StatItem(labels[k], v, slugs[k], None)
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

    def get_system_stat(self, title, field, labels, slugs, limit):
        values = System.objects \
            .order_by('-'+field)[:limit]
            #.values_list('id', field, named=True)

        stat_items = [ ]
        for s in values:
            if field == 'view_count' and self.is_superuser == False:
                value = "#%02d" % (len(stat_items)+1)
            else:
                value = getattr(s, field)
            stat_items.append(StatItem(s, value, s.slug, s.get_absolute_url))
        # FOR

        # stat_items.sort(key=lambda i: i.value, reverse=True)
        stat = Stat(
            title,
            stat_items[:limit],
            None,
            True,
            len(stat_items)
        )

        return stat


    def get(self, request, stats_type=None):
        self.is_superuser = request.user.is_superuser
        stats = []

        # Countries
        if stats_type is None or stats_type == "country":
            limit = -1 if stats_type == "country" else self.default_limit
            stats.append( self.get_bycountries(limit) )

        all_values = System.objects.all()
        labels = dict(all_values.values_list('id', 'name'))
        slugs = dict(all_values.values_list('id', 'slug'))

        # Compatibility
        if stats_type is None or stats_type == "compatible":
            stats.append( self.get_versionmeta_stat('Compatibility', 'compatible_with', 'compatible', labels, slugs, True, self.default_limit) )

        # Derived From
        if stats_type is None or stats_type == "derived":
            stats.append( self.get_versionmeta_stat('Derived From', 'derived_from', 'derived', labels, slugs, True, self.default_limit) )

        # Embeds
        if stats_type is None or stats_type == "embeds":
            stats.append( self.get_versionmeta_stat('Embeds / Uses', 'embedded', 'embeds', labels, slugs, True, self.default_limit ) )

        # Versions
        if stats_type is None or stats_type == "revisions":
            stats.append( self.get_system_stat('Revisions', 'ver', labels, slugs, self.default_limit ) )

        # Views
        if stats_type is None or stats_type == "views":
            stats.append( self.get_system_stat('Views', 'view_count', labels, slugs, self.default_limit ) )

        # Licenses
        if stats_type is None or stats_type == "license":
            limit = -1 if stats_type == "license" else self.default_limit
            labels = dict(License.objects.all().values_list('id', 'name'))
            slugs = dict(License.objects.all().values_list('id', 'slug'))
            stats.append( self.get_versionmeta_stat('License', 'licenses', 'license', labels, slugs, False, limit) )

        # Implementation Language
        if stats_type is None or stats_type == "programming":
            limit = -1 if stats_type == "programming" else self.default_limit
            all_values = ProgrammingLanguage.objects.all()
            labels = dict(all_values.values_list('id', 'name'))
            slugs = dict(all_values.values_list('id', 'slug'))
            stats.append( self.get_versionmeta_stat('Implementation', 'written_in', 'programming', labels, slugs, False, limit) )

        # Project Type
        if stats_type is None or stats_type == "project_type":
            limit = -1 if stats_type == "project_type" else self.default_limit
            labels = dict(ProjectType.objects.all().values_list('id', 'name'))
            slugs = dict(ProjectType.objects.all().values_list('id', 'slug'))
            stats.append( self.get_version_stat('Project Type', 'project_types', 'type', labels, slugs, False, limit) )

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

        # Stats Page
        url = etree.SubElement(root, 'url')
        loc = etree.SubElement(url, 'loc')
        loc.text = request.build_absolute_uri( reverse('stats') )
        lastmod = etree.SubElement(url, 'lastmod')
        lastmod.text = datetime.date.today().isoformat()
        changefreq = etree.SubElement(url, 'changefreq')
        changefreq.text = 'weekly'

        # Systems
        for system in System.objects.order_by('name').iterator():
            url = etree.SubElement(root, 'url')
            loc = etree.SubElement(url, 'loc')
            loc.text = request.build_absolute_uri( reverse('system', args=[system.slug]) )
            lastmod = etree.SubElement(url, 'lastmod')
            lastmod.text = system.modified.date().isoformat()
            changefreq = etree.SubElement(url, 'changefreq')
            changefreq.text = 'weekly'
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
        system_features = SystemFeature.objects.filter(version=system_version).select_related('feature').order_by('feature__label')

        # if they are logged in, check whether they are allowed to edit
        if not request.user.is_authenticated:
            user_can_edit = False
        elif request.user.is_superuser:
            user_can_edit = True
        else:
            user_can_edit = SystemACL.objects.filter(system=system, user=request.user).exists()
            pass

        # Citations
        #citations = [ ]
        #citations.append(system_version.description_citations)
        #citations.append(

        # Compatible Systems
        compatible = [
            ver.system for ver in SystemVersion.objects
                                .filter(is_current=True)
                                .filter(meta__compatible_with=system)
                                .order_by("-logo")
                                .select_related()
        ]

        # Derived Systems
        derived = [
            ver.system for ver in SystemVersion.objects
                                .filter(is_current=True)
                                .filter(meta__derived_from=system)
                                .order_by("-logo")
                                .select_related()
        ]

        # Embedding Systems
        embeds = [
            ver.system for ver in SystemVersion.objects
                                .filter(is_current=True)
                                .filter(meta__embedded=system)
                                .order_by("-logo")
                                .select_related()
        ]

        # Recommendations
        recommendations = [
            rec.recommendation for rec in SystemRecommendation.objects
                                .filter(system=system)
                                .order_by("-score")
                                .select_related()
        ]

        return render(request, self.template_name, {
            'activate': 'system', # NAV-LINKS
            'system': system,
            'system_features': system_features,
            'system_version': system_version,
            'user_can_edit': user_can_edit,
            'compatible': compatible,
            'derived': derived,
            'embeds': embeds,
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
        sqs = System.objects.filter(name__icontains=search_q).order_by('name')
        sqs = sqs.values('name')[:6]
        suggestions = [system["name"] for system in sqs]
    else:
        suggestions = [ ]

    data = json.dumps(suggestions)
    return HttpResponse(data, content_type='application/json')
