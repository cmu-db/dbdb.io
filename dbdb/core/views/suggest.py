import logging

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views import View

from dbdb.core.forms import SystemSuggestionForm
from dbdb.core.models import CitationUrl, SystemSuggestion, SystemVersion
from dbdb.core.utils.citations import normalize_url

LOG = logging.getLogger(__name__)


class SystemSuggestionView(View):

    template_name = 'core/system-suggest.html'

    def get(self, request):
        return render(request, self.template_name, {'form': SystemSuggestionForm()})

    def post(self, request):
        form = SystemSuggestionForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        system_url = normalize_url(form.cleaned_data['system_url'])

        # Check if the URL already exists as a system's website URL
        existing_system = None
        citation = CitationUrl.objects.filter(url=system_url).first()
        if citation:
            sv = (
                SystemVersion.objects
                .filter(system_url=citation, is_current=True)
                .select_related('system')
                .first()
            )
            if sv:
                existing_system = sv.system

        if existing_system:
            return render(request, self.template_name, {
                'form': form,
                'existing_system': existing_system,
            })

        raw_sourcerepo = form.cleaned_data.get('sourcerepo_url', '')
        suggestion = SystemSuggestion.objects.create(
            name=form.cleaned_data['name'],
            system_url=system_url,
            sourcerepo_url=normalize_url(raw_sourcerepo) if raw_sourcerepo else '',
            logo_url=form.cleaned_data.get('logo_url', ''),
            email=form.cleaned_data.get('email', ''),
            is_my_system=form.cleaned_data.get('is_my_system', False),
        )

        if suggestion.email:
            try:
                send_mail(
                    subject='DBDB.IO: System Suggestion Received',
                    message=(
                        f'Hello,\n\n'
                        f'Thank you for suggesting "{suggestion.name}" to DBDB.IO. '
                        f'We have received your submission and will review it shortly.\n\n'
                        f'System Name: {suggestion.name}\n'
                        f'System URL: {suggestion.system_url}\n\n'
                        f'If you have any questions, please contact us at mail@dbdb.io.\n'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@dbdb.io',
                    recipient_list=[suggestion.email],
                    fail_silently=True,
                )
            except Exception:
                LOG.warning('Failed to send suggestion confirmation email', exc_info=True)

        return redirect('system_suggestion_success')


class SystemSuggestionSuccessView(View):

    template_name = 'core/system-suggest-success.html'

    def get(self, request):
        return render(request, self.template_name, {})
