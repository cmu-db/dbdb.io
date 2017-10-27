from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import get_user_model

from core.forms import CreateUserForm


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
