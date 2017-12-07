from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseForbidden
from django.http.request import QueryDict
from django.http.response import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.contrib.auth import get_user_model
from functools import reduce

from core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm, SystemFeaturesForm, \
    AdvancedSearchForm, SystemVersionEditForm
from core.models import System, SystemVersionMetadata, SystemVersion, Feature, FeatureOption, SystemFeatures, \
    CitationUrls


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
        context = {'form': form}
        return render(request, context=context, template_name=self.template_name)


class CreateDatabase(LoginRequiredMixin, View):
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

            for feature, value in form.cleaned_data.items():
                if '_description' in feature:
                    feature_obj = Feature.objects.get(label=feature[:-12])
                    saved, _ = SystemFeatures.objects.get_or_create(
                        system=db_version,
                        feature=feature_obj
                    )
                    saved.description = value
                    saved.save()
                else:
                    feature_obj = Feature.objects.get(label=feature)
                    saved = SystemFeatures.objects.create(
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


class SystemView(View):
    template_name = 'core/system.html'

    def get(self, request, slug):
        system = get_object_or_404(System, slug=slug)
        system_version = system.current()
        context = {
            'system': system,
            'system_version': system_version,
            'system_features': system_version.systemfeatures_set.all()
        }
        return render(request, template_name=self.template_name, context=context)


class EditDatabase(LoginRequiredMixin, View):
    template_name = 'core/edit-database.html'

    def get(self, request, slug):
        system = System.objects.get(slug=slug)
        system_version = SystemVersion.objects.get(system=system, is_current=True)
        system_meta = system_version.meta
        system_features = system_version.systemfeatures_set.all()
        system_form = SystemForm(instance=system)
        if not request.user.is_superuser:
            system_form.fields['name'].disabled = True


        context = {
            'system_name': system.name,
            'system_form': system_form,
            'system_version_form': SystemVersionForm(instance=system_version),
            'system_version_metadata_form': SystemVersionMetadataForm(instance=system_meta),
            'feature_form': SystemFeaturesForm(instance=system_features)
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, slug):
        system = System.objects.get(slug=slug)
        system_version_form = SystemVersionEditForm(request.POST, request.FILES)
        system_version_metadata_form = SystemVersionMetadataForm(request.POST)
        form = SystemFeaturesForm(request.POST)

        if system_version_form.is_valid() and \
                system_version_metadata_form.is_valid() and form.is_valid():

            system.systemversion_set.update(is_current=False)
            db_version = system_version_form.save(commit=False)
            db_version.creator = request.user
            db_version.system = system
            db_version.save()

            db_meta = system_version_metadata_form.save()
            db_version.meta = db_meta
            db_version.save()

            for feature, value in form.cleaned_data.items():
                if '_description' in feature:
                    feature_obj = Feature.objects.get(label=feature[:-12])
                    saved, _ = SystemFeatures.objects.get_or_create(
                        system=db_version,
                        feature=feature_obj
                    )
                    saved.description = value
                    saved.save()
                elif '_citation'in feature:
                    feature_obj = Feature.objects.get(label=feature[:-9])
                    saved, _ = SystemFeatures.objects.get_or_create(
                        system=db_version,
                        feature=feature_obj
                    )
                    saved.citation.clear()
                    for url in value.split(','):
                        cit_url, _ = CitationUrls.objects.get_or_create(url=url)
                        saved.citation.add(cit_url)

                else:
                    feature_obj = Feature.objects.get(label=feature)
                    saved = SystemFeatures.objects.create(
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
        system_form = SystemForm(instance=system)
        context = {
            'system_form': system_form,
            'system_version_form': system_version_form,
            'system_version_metadata_form': system_version_metadata_form,
            'feature_form': form
        }

        return render(request, template_name=self.template_name, context=context)


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


class AdvancedSearchView(View):
    template_name = 'core/advanced-search.html'

    def get(self, request):
        systems = System.objects.order_by('name')
        context = {
            'form': AdvancedSearchForm(),
            'systems': systems
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request):
        form = AdvancedSearchForm(request.POST)
        systems = []
        if form.is_valid():
            features = {}
            for key, value in form.cleaned_data.items():
                if value:
                    options = FeatureOption.objects.filter(value__in=value, feature__label=key)
                    feature = Feature.objects.get(label=key)
                    features[feature] = options
            system_versions = []
            for k, v in features.items():
                sv = SystemFeatures.objects.filter(
                    feature=k, value__in=v, system__is_current=True
                ).distinct().values_list('system', flat=True)
                if not sv:
                    break
                system_versions.append(set(sv))
            else:
                if system_versions:
                    common_systems = reduce(lambda a, b: a.intersection(b), system_versions)
                    systems = System.objects.filter(id__in=SystemVersion.objects.filter(id__in=common_systems).values_list(
                        'system', flat=True
                    ))
                else:
                    systems = System.objects.order_by('name')

        context = {
            'systems': systems,
            'form': form
        }

        return render(request, template_name=self.template_name, context=context)


class HomeView(View):
    template_name = 'core/home.html'

    def get(self, request):
        context = {}
        most_edited = System.objects.annotate(Count('systemversion')).distinct().order_by('-systemversion__count')[:10]
        most_recent = System.objects.distinct().order_by('-created')[:10]
        most_views = System.objects.distinct().order_by('-view_count')[:10]
        context = {
            'most_edited': most_edited,
            'most_recent': most_recent,
            'most_views': most_views
        }
        return render(request, template_name=self.template_name, context=context)


class UpdateViewCount(View):
    def get(self, request):
        slug = request.META['HTTP_REFERER'].split('/')[-2]
        system = get_object_or_404(System, slug=slug)
        system.view_count += 1
        system.save()

        return HttpResponse(b'Ok', status=200)


class RevisionList(View):
    template_name = 'core/revision_list.html'

    def get(self, request, slug):
        system = System.objects.get(slug=slug)
        versions = system.systemversion_set.all()
        context = {
            'system': system,
            'versions': versions
        }
        return render(request, self.template_name, context)

    def post(self, request, slug):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        system = System.objects.get(slug=slug)
        version = SystemVersion.objects.get(id=request.POST['current_version'])
        system.systemversion_set.update(is_current=False)
        version.is_current = True
        system.current_version = version.version_number
        version.save()
        system.save()
        return redirect('system', slug=slug)


class RevisionView(View):
    template_name = 'core/revision_view.html'

    def get(self, request, slug, id):
        system = get_object_or_404(System, slug=slug)
        system_version = get_object_or_404(SystemVersion, id=id)
        context = {
            'system': system,
            'system_version': system_version,
            'system_features': system_version.systemfeatures_set.all()
        }
        return render(request, template_name=self.template_name, context=context)
