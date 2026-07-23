# stdlib imports
import datetime
import urllib.parse

import jwt
import tldextract

# django imports
from django import forms as django_forms
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

# project imports
from dbdb.core.forms import CreateUserForm
from dbdb.core.models import CitationUrl, System, SystemACL, SystemVersion

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
        if isinstance(s, bytes):
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


# ==============================================
# SignupRequestView
# ==============================================
class _SignupEmailForm(django_forms.Form):
    email = django_forms.EmailField(label='Your work email address', max_length=254)


class SignupRequestView(View):

    template_name = 'registration/signup_request.html'

    def _build_token(self, email, system_ids):
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            'iss': 'signup_request',
            'sub': email,
            'nbf': datetime.datetime.utcnow(),
            'systems': system_ids,
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        # PyJWT 1.x returns bytes
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token

    def _find_matching_systems(self, email):
        """Return a list of System IDs whose system_url domain matches the email domain."""
        ext = tldextract.extract(email)
        domain = f"{ext.domain}.{ext.suffix}".lower()
        if not domain or domain == '.':
            return []

        matching_citations = CitationUrl.objects.filter(url__icontains=domain)
        system_ids = list(
            SystemVersion.objects
            .filter(is_current=True, system_url__in=matching_citations)
            .values_list('system_id', flat=True)
        )
        return system_ids

    def get(self, request):
        form = _SignupEmailForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = _SignupEmailForm(request.POST)
        error = None

        if form.is_valid():
            email = form.cleaned_data['email'].lower().strip()

            if UserModel.objects.filter(email=email).exists():
                error = 'An account with that email already exists. Please log in instead.'
            else:
                system_ids = self._find_matching_systems(email)
                if not system_ids:
                    error = (
                        'No systems found whose website URL matches your email domain. '
                        'If you believe this is an error, please contact an administrator.'
                    )

            if error is None:
                token = self._build_token(email, system_ids)
                verify_url = request.build_absolute_uri(
                    reverse('create_user') + '?' + urllib.parse.urlencode({'token': token})
                )
                send_mail(
                    subject='DBDB.IO: Verify your email to edit database entries',
                    message=(
                        f'Hello,\n\n'
                        f'Click the link below to create your DBDB.IO account. '
                        f'This link expires in 24 hours.\n\n'
                        f'{verify_url}\n\n'
                        f'If you did not request this, you can ignore this email.\n'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@dbdb.io',
                    recipient_list=[email],
                    fail_silently=False,
                )
                return redirect('signup_pending')

        return render(request, self.template_name, {'form': form, 'error': error})

    pass


# ==============================================
# SignupPendingView
# ==============================================
class SignupPendingView(View):

    template_name = 'registration/signup_pending.html'

    def get(self, request):
        return render(request, self.template_name, {})

    pass


# ==============================================
# ProfileView
# ==============================================
class _EmailChangeForm(django_forms.Form):
    email = django_forms.EmailField(label='New email address', max_length=254)
    current_password = django_forms.CharField(
        label='Current password',
        widget=django_forms.PasswordInput,
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('current_password')
        if password and not authenticate(username=self._user.username, password=password):
            raise django_forms.ValidationError('Current password is incorrect.')
        email = cleaned.get('email', '').lower().strip()
        if email and UserModel.objects.filter(email=email).exclude(pk=self._user.pk).exists():
            raise django_forms.ValidationError('That email address is already in use.')
        return cleaned


class ProfileView(LoginRequiredMixin, View):

    template_name = 'registration/profile.html'

    def _context(self, request, form=None):
        user = request.user
        acl_entries = list(
            SystemACL.objects
            .filter(user=user)
            .select_related('system')
            .annotate(
                ver_count=Count('system__versions'),
                last_edited=Max(
                    'system__versions__created',
                    filter=Q(system__versions__creator=user),
                ),
            )
            .order_by('system__name')
        )
        recent_versions = list(
            SystemVersion.objects
            .filter(creator=user)
            .select_related('system')
            .order_by('-created')[:10]
        )
        revision_count = SystemVersion.objects.filter(creator=user).count()
        return {
            'profile_user': user,
            'acl_entries': acl_entries,
            'recent_versions': recent_versions,
            'revision_count': revision_count,
            'email_form': form or _EmailChangeForm(user=user),
        }

    def get(self, request):
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        form = _EmailChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            request.user.email = form.cleaned_data['email'].lower().strip()
            request.user.save(update_fields=['email'])
            return redirect('user_profile')
        return render(request, self.template_name, self._context(request, form=form))
