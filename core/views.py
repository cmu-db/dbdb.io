from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.request import QueryDict
from django.http.response import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.contrib.auth import get_user_model

from core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm, SystemFeaturesForm
from core.models import System, SystemVersion, Feature, FeatureOption, SystemFeatures


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


class CreateDatabase(View):
    template_name = 'core/create-database.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise Http404()

        if 'id' not in kwargs:
            self.template_name = 'core/create-database.html'
            context = {
                'system_form': SystemForm(),
                'system_version_form': SystemVersionForm()
            }
        elif kwargs['kind'] == 'meta':
            self.template_name = 'core/create-database-meta.html'
            context = {
                'system_version_metadata_form': SystemVersionMetadataForm()
            }
        elif kwargs['kind'] == 'features':
            self.template_name = 'core/create-database-features.html'
            context = {
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
            db_version .creator = request.user
            db_version .system = db
            db_version .save()

            db_meta = system_version_metadata_form.save()
            db_version.meta = db_meta
            db_version.save()

            for feature, value in form.cleaned_data.items():
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

            return redirect(db.get_absolute_url())
        context = {
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


class EditDatabase(View):
    template_name = 'core/edit-database.html'

    def get(self, request, slug):
        system = System.objects.get(slug=slug)
        system_version = SystemVersion.objects.get(system=system, is_current=True)
        system_meta = system_version.meta
        system_features = system_version.systemfeatures_set.all()

        context = {
            'system_form': SystemForm(instance=system),
            'system_version_form': SystemVersionForm(instance=system_version),
            'system_version_metadata_form': SystemVersionMetadataForm(instance=system_meta),
            'feature_form': SystemFeaturesForm(instance=system_features)
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, slug):
        system = System.objects.get(slug=slug)
        system_form = SystemForm(request.POST, instance=system)
        system_version_form = SystemVersionForm(request.POST, request.FILES)
        system_version_metadata_form = SystemVersionMetadataForm(request.POST)
        form = SystemFeaturesForm(request.POST)

        if system_form.is_valid() and system_version_form.is_valid() and \
                system_version_metadata_form.is_valid() and form.is_valid():

            db = system_form.save()
            db.systemversion_set.update(is_current=False)
            db_version = system_version_form.save(commit=False)
            db_version.creator = request.user
            db_version.system = db
            db_version.save()

            db_meta = system_version_metadata_form.save()
            db_version.meta = db_meta
            db_version.save()

            for feature, value in form.cleaned_data.items():
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
