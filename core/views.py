from django.shortcuts import render, redirect
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
        if 'id' not in kwargs:
            system_form = SystemForm(request.POST)
            system_version_form = SystemVersionForm(request.POST)

            if system_form.is_valid() and system_version_form.is_valid():
                db = system_form.save()
                db_version = system_version_form.save(commit=False)
                db_version .creator = request.user
                db_version .system = db
                db_version .save()
                return redirect(reverse('create_db_meta', args=[db.id, 'meta']))
            context = {
                'system_form': system_form,
                'system_version_form': system_version_form,
            }
        elif kwargs['kind'] == 'meta':
            system_version_metadata_form = SystemVersionMetadataForm(
                request.POST, request.FILES)
            if system_version_metadata_form.is_valid():
                db = SystemVersion.objects.get(system_id=kwargs['id'], is_current=True)

                db_meta = system_version_metadata_form.save()
                db.meta = db_meta
                db.save()

                return redirect(reverse('create_db_features', args=[kwargs['id'], 'features']))
            context = {
                'system_version_metadata_form': system_version_metadata_form
            }
        elif kwargs['kind'] == 'features':
            form = SystemFeaturesForm(request.POST)
            if form.is_valid():
                for feature, value in form.cleaned_data.items():
                    feature_obj = Feature.objects.get(label=feature)
                    system = SystemVersion.objects.get(system__id=kwargs['id'], is_current=True)
                    saved = SystemFeatures.objects.create(
                        system=system,
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

                return redirect(system.get_absolute_url())
            context = {
                'feature_form': form
            }

        return render(request, template_name=self.template_name, context=context)


class SystemView(View):
    template_name = 'core/system.html'

    def get(self, request, id):
        system = System.objects.get(id=id)
        context = {
            'system': system,
            'system_version': system.systemversion_set.get(is_current=True),
        }
        return render(request, template_name=self.template_name, context=context)