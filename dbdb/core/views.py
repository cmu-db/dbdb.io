# stdlib imports
from datetime import datetime
from functools import reduce
import collections
# django imports
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
# project imports
from dbdb.core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm, SystemFeaturesForm, \
    AdvancedSearchForm, SystemVersionEditForm
from dbdb.core.models import System, SystemVersionMetadata
from dbdb.core.models import SystemVersion
from dbdb.core.models import Feature
from dbdb.core.models import FeatureOption
from dbdb.core.models import SystemFeature
from dbdb.core.models import CitationUrl


# helper classes

FieldSet = collections.namedtuple('FieldSet', ['id','label','choices','description','citation'])


# class based views

class AdvancedSearchView(View):

    template_name = 'core/advanced-search.html'

    def get(self, request):
        systems = System.objects.order_by('name')

        return render(request, self.template_name, {
            'form': AdvancedSearchForm(),

            'systems': systems
        })

    def post(self, request):
        form = AdvancedSearchForm(request.POST)

        systems = []
        if form.is_valid():
            features = {}

            for key, value in form.cleaned_data.items():
                if not value: continue
        
                options = FeatureOption.objects.filter(value__in=value, feature__label=key)
                feature = Feature.objects.get(label=key)
                features[feature.id] = list( options.values_list('id', flat=True) )
                pass

            system_versions = []
            for feature_id, v in features.items():
                sv = SystemFeature.objects \
                    .filter(feature_id=feature_id, options__id__in=v, system__is_current=True) \
                    .distinct() \
                    .values_list('system', flat=True)
    
                if not sv: continue

                system_versions.append(set(sv))
                pass
            else:
                if system_versions:
                    common_systems = reduce(lambda a, b: a.intersection(b), system_versions)
                    systems = System.objects \
                        .filter(
                            id__in=SystemVersion.objects.filter(id__in=common_systems).values_list('system', flat=True)
                        )
                else:
                    systems = System.objects.all()
            pass

        return render(request, self.template_name, {
            'systems': systems.order_by('name'),
            'form': form,
        })

    pass

class CreateDatabase(View, LoginRequiredMixin):

    template_name = 'core/create-database.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise Http404()

        if 'id' not in kwargs:
            self.template_name = 'core/create-database.html'
            context = {
                'system_form': SystemForm(),
                'system_version_form': SystemVersionForm(),
                'system_version_metadata_form': SystemVersionMetadataForm(),
                'feature_form': SystemFeaturesForm()
            }

        return render(request, template_name=self.template_name, context=context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise Http404()

        system_form = SystemForm(request.POST)
        system_version_form = SystemVersionForm(request.POST)
        system_version_metadata_form = SystemVersionMetadataForm(
            request.POST, request.FILES)
        form = SystemFeaturesForm(request.POST)

        if system_form.is_valid() and system_version_form.is_valid() and \
                system_version_metadata_form.is_valid() and form.is_valid():

            db = system_form.save()
            db_version = system_version_form.save(commit=False)
            db_version.creator = request.user
            db_version.system = db
            db_version.save()

            db_meta = system_version_metadata_form.save()
            db_version.meta = db_meta
            db_version.save()

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
            for field_name, value in form.cleaned_data.items():
                feature_label = '_'.join( field_name.split('_')[:-1] )
                print( 'feature_label', feature_label )
                if '_description' in feature:
                    feature_obj = Feature.objects.get(label=feature[:-12])
                    saved, _ = SystemFeature.objects.get_or_create(
                        system=db_version,
                        feature=feature_obj
                    )
                    saved.description = value
                    saved.save()
                elif '_citation' in feature:
                    feature_obj = Feature.objects.get(label=feature[:-9])
                    saved, _ = SystemFeature.objects.get_or_create(
                        system=db_version,
                        feature=feature_obj
                    )
                    saved.citation.clear()
                    for url in value.split(','):
                        cit_url, _ = CitationUrls.objects.get_or_create(url=url)
                        saved.citation.add(cit_url)

                else:
                    feature_obj = Feature.objects.get(label=feature)
                    saved = SystemFeature.objects.create(
                        system=db_version,
                        feature=feature_obj
                    )
                    if isinstance(value, str):
                        saved.value.add(
                            FeatureOption.objects.get(
                                feature=feature_obj,
                                value=value)
                        )
                    else:
                        for v in value:
                            saved.value.add(
                                FeatureOption.objects.get(
                                    feature=feature_obj,
                                    value=v)
                            )
            return redirect(db_version.system.get_absolute_url())
        context = {
            'system_form': system_form,
            'system_version_form': system_version_form,
            'system_version_metadata_form': system_version_metadata_form,
            'feature_form': form
        }

        return render(request, template_name=self.template_name, context=context)

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

    def get(self, request, slug):
        system = System.objects.get(slug=slug)
        system_version = SystemVersion.objects.get(system=system, is_current=True)
        system_meta = system_version.meta
        system_features = system_version.features.all()

        system_form = SystemForm(instance=system)
        if not request.user.is_superuser:
            system_form.fields['name'].disabled = True

        feature_form = SystemFeaturesForm(features=system_features)
        
        features = Feature.objects.all()
        features = collections.OrderedDict(
            (
                f.id,
                {
                    'id': f'feature_{f.id}',
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

        return render(request, self.template_name, {
            'system_name': system.name,
            'system_form': system_form,
            'system_version_form': SystemVersionForm(instance=system_version),
            'system_version_metadata_form': SystemVersionMetadataForm(instance=system_meta),
            'feature_form': feature_form,
            
            'features': features,
        })

    @transaction.atomic
    def post(self, request, slug):
        system = System.objects.get(slug=slug)
        system_version_form = SystemVersionEditForm(request.POST, request.FILES)
        system_version_metadata_form = SystemVersionMetadataForm(request.POST)
        form = SystemFeaturesForm(request.POST)

        if system_version_form.is_valid() and \
                system_version_metadata_form.is_valid() and \
                form.is_valid():
            logo = system.current().logo

            system.systemversion_set.update(is_current=False)
            db_version = system_version_form.save(commit=False)
            db_version.creator = request.user
            db_version.system = system
            if logo: db_version.logo = logo
            print( 'db_version', db_version.id )
            print( 'db_version', db_version.ver )
            db_version.save()

            db_meta = system_version_metadata_form.save()
            db_version.meta = db_meta
            db_version.save()
            
            system.ver = db_version.ver
            system.modified = datetime.now()
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
            for field_name in form.cleaned_data.keys():
                feature_label = '_'.join( field_name.split('_')[:-1] )

                feature = features[feature_label]
                value = form.cleaned_data[field_name]
                
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
                    for url in value.split(','):
                        cit_url, _ = CitationUrl.objects.get_or_create(url=url)
                        sf.citations.add(cit_url)
                        pass
                    pass
                elif '_choices'in field_name:
                    sf, _ = SystemFeature.objects.get_or_create(
                        system=db_version,
                        feature=feature
                    )
                    if isinstance(value, str):
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
        ## IF
        system_form = SystemForm(instance=system)
        context = {
            'system_form': system_form,
            'system_version_form': system_version_form,
            'system_version_metadata_form': system_version_metadata_form,
            'feature_form': form
        }

        return render(request, template_name=self.template_name, context=context)

    pass

class HomeView(View):

    template_name = 'core/home.html'

    def get(self, request):
        items_to_show = 5
        
        most_edited = System.objects.order_by('-ver', '-name')[:items_to_show]
        most_recent = System.objects.order_by('-modified')[:items_to_show]
        most_views = System.objects.order_by('-view_count')[:items_to_show]

        return render(request, self.template_name, context={
            'most_edited': most_edited,
            'most_recent': most_recent,
            'most_views': most_views
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

class SearchView(View):
    template_name = 'core/search.html'

    def get(self, request):
        query = request.GET.get('q')
        if query is None:
            return redirect('home')
        if not isinstance(query, str):
            query = query[0]

        systems = System.objects.prefetch_related('systemversion_set').filter(name__icontains=query)
        context = {
            'systems': systems,
            'query': query
        }
        return render(request, template_name=self.template_name, context=context)

    pass

class SystemView(View):

    template_name = 'core/system.html'

    def get(self, request, slug):
        system = get_object_or_404(System, slug=slug)

        system_version = system.current()

        return render(request, self.template_name, {
            'system': system,
            'system_version': system_version,
            'system_features': system_version.features.all()
        })

    pass

class UpdateViewCount(View):

    def get(self, request):
        slug = request.META['HTTP_REFERER'].split('/')[-2]
        system = get_object_or_404(System, slug=slug)
        system.view_count += 1
        system.save()

        return HttpResponse(b'Ok', status=200)
    
    pass
