from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import get_user_model

from core.forms import CreateUserForm, SystemForm, SystemVersionForm, SystemVersionMetadataForm
from core.models import SystemVersionMetadata


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
        context = {
            'system_form': SystemForm(),
            'system_version_form': SystemVersionForm(),
            'system_version_metadata_form': SystemVersionMetadataForm()
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        system_form = SystemForm(request.POST)
        system_version_form = SystemVersionForm(request.POST)
        system_version_metadata_form = SystemVersionMetadataForm(request.POST)

        if system_form.is_valid() and system_version_form.is_valid():
            db = system_form.save()
            return redirect(db.get_url())
        context = {
            'system_form': system_form,
            'system_version_form': system_version_form,
            'system_version_metadata_form': system_version_metadata_form
        }
        return render(request, template_name=self.template_name, context=context)