# stdlib imports
from functools import reduce
import collections
import datetime
import operator
# django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Count
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
from django.utils.text import smart_split
from django.utils.text import slugify
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
# third-party imports
import jwt
from django_countries import countries
# project imports
from dbdb.core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm, SystemFeaturesForm, \
    SystemVersionEditForm
from dbdb.core.models import System, SystemVersionMetadata
from dbdb.core.models import SystemVersion
from dbdb.core.models import Feature
from dbdb.core.models import FeatureOption
from dbdb.core.models import SystemFeature
from dbdb.core.models import CitationUrl


# helper classes

FieldSet = collections.namedtuple('FieldSet', ['id','label','choices','description','citation'])

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
        self.choices.sort(key=lambda fc: fc.sort_key)

        for i,choice in enumerate(self.choices):
            self.has_checked = self.has_checked or choice.checked

            if i >=4 and not choice.checked:
                choice.is_hidden = True
                self.has_more = True
                pass
            pass
        return

    pass

LetterPage = collections.namedtuple('LetterPage', ['id','letter','is_active','is_disabled'])


# class based views

class AdvancedSearchView(View):

    template_name = 'core/advanced-search.html'

    def build_filter_groups(self, querydict):
        empty_set = set()

        def reduce_feature_options(mapping, option):
            mapping[option.feature_id].choices.append(
                FilterChoice(
                    option.id,
                    option.value,
                    str(option.id) in querydict.getlist( 'fg{0}'.format(option.feature_id), empty_set )
                )
            )
            return mapping

        filtergroups = collections.OrderedDict(
            ( f_id, FilterGroup('fg{}'.format(f_id), f_label, []) )
            for f_id,f_label in Feature.objects.all().order_by().values_list('id','label')
        )

        filtergroups = reduce(
            reduce_feature_options,
            FeatureOption.objects.all().order_by('value').values_list('feature_id','id','value', named=True),
            filtergroups
        )

        filtergroups = filtergroups.values()

        for fg in filtergroups:
            fg.prepare()
            pass

        return filtergroups
    ## DEF

    def get(self, request):
        has_search = False

        # pull search criteria
        search_q = request.GET.get('q', '').strip()
        search_fg = {
            int( k[2:] ) : set( map(int, request.GET.getlist(k)) )
            for k in request.GET.keys()
            if k.startswith('fg')
        }
        search_country = request.GET.get('country', '').strip()

        search_derived = request.GET.get('derived', '').strip()
        derived = None

        search_inspired = request.GET.get('inspired', '').strip()
        inspired = None
        
        search_compatible = request.GET.get('compatible', '').strip()
        compatible = None

        if search_q or search_fg or search_country or \
            search_derived or search_inspired or search_compatible:
            has_search = True

            # only search current versions
            versions = SystemVersion.objects \
                .filter(is_current=True)

            # apply keyword search to name (require all terms)
            if search_q:
                terms = smart_split( search_q.lower() )
                query = [Q(system__name__icontains=t) for t in terms]
                versions = versions.filter( reduce(operator.and_, query) )
                pass

            # search for features
            for feature_id,option_ids in search_fg.items():
                versions = versions.filter(
                    features__feature_id=feature_id,
                    features__options__id__in=option_ids
                )
                pass
            ## FOR
            
            # Country search
            if search_country:
                terms = smart_split( search_country.upper() )
                # query = [Q(system__countries__in=t) for t in terms]
                query = Q(countries__in=terms)
                versions = versions.filter(query)
            # Derived System
            elif search_derived:
                try:
                    derived = System.objects.get(slug=search_derived)
                    versions = versions.filter(meta__derived_from__id=derived.id)
                    search_derived = derived.name
                except:
                    versions = SystemVersion.objects.none()
                    pass
                pass
            # Inspired System
            elif search_inspired:
                try:
                    inspired = System.objects.get(slug=search_inspired)
                    versions = versions.filter(meta__inspired_by__id=inspired.id)
                    search_inspired = inspired.name
                except:
                    versions = SystemVersion.objects.none()
                    pass
                pass
            # Compatible System
            elif search_compatible:
                try:
                    compatible = System.objects.get(slug=search_compatible)
                    versions = versions.filter(meta__compatible_with__id=compatible.id)
                    search_compatible = compatible.name
                except:
                    versions = SystemVersion.objects.none()
                    pass
                pass
            # IF

            # use generated list of PKs to get actual versions with systems
            versions = SystemVersion.objects \
                .filter(id__in=versions.values_list('id', flat=True)) \
                .select_related('system') \
                .order_by('system__name')

            pagination = None
            pass
        else:
            versions = SystemVersion.objects.none()

            pass

        # convert query list to regular list
        versions = list(versions)
        # and add href/url to each
        for version in versions:
            version.href = request.build_absolute_uri( version.system.get_absolute_url() )
            pass

        return render(request, self.template_name, {
            'filtergroups': self.build_filter_groups(request.GET),
            'versions': versions,

            'has_search': has_search,
            'query': search_q,
            'country': search_country,
            'derived': search_derived,
            'derived_system': derived,
            'inspired': search_inspired,
            'inspired_system': inspired,
            'compatible': search_compatible,
            'compatible_system': compatible,
            'no_nav_search': True,
        })

    pass

# ==============================================
# DatabaseFieldsView
# ==============================================
class DatabaseFieldsView(View):

    template_name = 'core/database-fields.html'

    def build_search_fields(self):
        import django.db.models.fields
        fields = [ ]
        IGNORE_TYPES = set([
            django.db.models.fields.AutoField,
            django.db.models.fields.related.ForeignKey,
            django.db.models.fields.related.ManyToManyField,
        ])
        IGNORE_NAMES = set([
            "ver",
            "comment",
            "features",
            "created",
        ])
        for f in SystemVersion._meta.get_fields():
            if not type(f) in IGNORE_TYPES and \
               not f.name in IGNORE_NAMES:
                fields.append(f.name)
        ## FOR
        return (sorted(fields))
    ## DEF

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect( settings.LOGIN_URL + '?next=' + reverse('fields') )
        elif not request.user.is_superuser:
            raise Http404()
        
        versions = SystemVersion.objects.filter(is_current=True)
        
        search_field = request.GET.get('field')
        search_check = request.GET.get('check')
        if search_field:
            versions = versions.filter(**{search_field: ''})
        
        # convert query list to regular list
        # and add href/url to each
        versions = list( versions.order_by('system__name') )
        for version in versions:
            version.href = request.build_absolute_uri( version.system.get_absolute_url() )
            pass
        
        fields = self.build_search_fields()
        num_systems = System.objects.all().count()
        
        return render(request, self.template_name, {
            'versions': versions,
            'field': search_field,
            'check': search_check,
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

    def get(self, request):
        has_search = False
    
        # Search String
        search_query = request.GET.get('q')
        if search_query is not None and not isinstance(search_query, str):
            search_query = search_query[0]
        
        # Search Letter
        search_letter = request.GET.get('letter', '').strip().upper()

        if search_query:
            versions = SystemVersion.objects \
                .filter(is_current=True) \
                .filter(Q(system__name__icontains=search_query) | \
                        Q(former_names__icontains=search_query))
        elif search_letter == 'ALL' or not search_letter:
            versions = SystemVersion.objects.filter(is_current=True)
            pass
        elif search_letter:
            versions = SystemVersion.objects \
                .filter(is_current=True) \
                .filter( Q(system__name__startswith=search_letter) | Q(system__name__startswith=search_letter.lower()) )
            pass
            #versions = SystemVersion.objects.none()
            #pass
        pagination = self.build_pagination(search_letter)

        # convert query list to regular list
        versions = list( versions.order_by('system__name') )
        # and add href/url to each
        for version in versions:
            version.href = request.build_absolute_uri( version.system.get_absolute_url() )
            pass

        has_results = len(versions) > 0

        return render(request, self.template_name, {
            'has_results': has_results,
            'pagination': pagination,
            'query': search_query,
            'versions': versions,
        })

    pass

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

                with transaction.atomic():
                    system = System.objects.select_for_update().get(pk=pk)
                    system.view_count += 1
                    system.save()
                    pass
                pass
            else:
                return JsonResponse({ 'status':('unrecognized counter: %r' % iss)}, status=400)
            pass
        except jwt.ExpiredSignatureError:
            return JsonResponse({ 'status':'expired counter'}, status=400)

        return JsonResponse({ 'status':'ok' })

    pass

class CreateUser(View):

    template_name = 'registration/create_user.html'

    def get(self, request, *args, **kwargs):
        context = {'form': CreateUserForm()}
        return render(request, context=context, template_name=self.template_name)

    def post(self, request, *args, **kwargs):
        form = CreateUserForm(request.POST)
        User = get_user_model()

        if form.is_valid():
            User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            return redirect('/login/')

        return render(request, context={
            'form': form
        }, template_name=self.template_name)

    pass


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
        if slug is None:

            if not request.user.is_authenticated:
                return redirect( settings.LOGIN_URL + '?next=' + reverse('create_database') )
            elif not request.user.is_superuser:
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

        system_form = SystemForm(instance=system)

        if not request.user.is_superuser:
            system_form.fields['name'].disabled = True

        feature_form = SystemFeaturesForm(features=system_features)

        features = self.build_features(feature_form)

        return render(request, self.template_name, {
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
                system = system_form.save(commit=False)
                system.slug = slugify(system.name)
                system.save()

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
            'system_name': system.name,
            'system_form': system_form,
            'system_version_form': system_version_form,
            'system_version_metadata_form': system_version_metadata_form,
            'feature_form': feature_form,

            'features': features,
        })

    pass

class DatabaseRevisionList(View):

    template_name = 'core/revision_list.html'

    def get(self, request, slug):
        system = get_object_or_404(System, slug=slug)

        versions = SystemVersion.objects \
            .filter(system=system) \
            .select_related('system')

        return render(request, self.template_name, {
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

class DatabaseRevisionView(View):

    template_name = 'core/revision_view.html'

    def get(self, request, slug, ver):
        system_version = get_object_or_404(SystemVersion.objects.select_related('system'), system__slug=slug, ver=ver)

        return render(request, self.template_name, {
            'system': system_version.system,
            'system_version': system_version,
            'system_features': system_version.features.all()
        })

    pass

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


class SystemView(View):

    template_name = 'core/system.html'

    def get(self, request, slug):
        system = get_object_or_404(System, slug=slug)
        system_version = system.current()
        system_features = SystemFeature.objects.filter(system=system_version).select_related('feature').order_by('feature__label')

        return render(request, self.template_name, {
            'system': system,
            'system_features': system_features,
            'system_version': system_version,

            'counter_token': CounterView.build_token('system', pk=system.id),
        })

    pass
