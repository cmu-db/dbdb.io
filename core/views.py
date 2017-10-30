from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.contrib.auth import get_user_model

from core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm
from core.models import System, SystemVersion


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
            }

        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        if 'id' not in kwargs:
            system_form = SystemForm(request.POST)
            system_version_form = SystemVersionForm(request.POST)

            if system_form.is_valid() and system_version_form.is_valid():
                db = system_form.save()
                db_version  = system_version_form.save(commit=False)
                db_version .creator = request.user
                db_version .system = db
                db_version .save()
                return redirect(reverse('create_db_meta', args=[db.id, 'meta']))
            context = {
                'system_form': system_form,
                'system_version_form': system_version_form,
            }
        elif kwargs['kind'] == 'meta':
            system_version_metadata_form = SystemVersionMetadataForm(request.POST)
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
            context = {}

        return render(request, template_name=self.template_name, context=context)