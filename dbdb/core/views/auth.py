# stdlib imports
import datetime
import urllib.parse

import jwt

# django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

# project imports
from dbdb.core.forms import CreateUserForm
from dbdb.core.models import System, SystemACL

UserModel = get_user_model()


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
            'recaptcha_key': settings.RECAPTCHA_PUBLIC_KEY,
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
            'recaptcha_key': settings.RECAPTCHA_PUBLIC_KEY,
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
        return self.request.user.is_superuser

    pass
