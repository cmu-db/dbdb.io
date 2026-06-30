import logging

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views import View
from meta.views import MetadataMixin

from dbdb.core.forms import SystemSuggestionForm
from dbdb.core.models import CitationUrl, SystemSuggestion, SystemVersion
from dbdb.core.utils.citations import normalize_url

LOG = logging.getLogger(__name__)


class SystemSuggestionView(MetadataMixin, View):

    template_name = 'core/system-suggest.html'
    title = f'Suggest a System{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_NAME}'
    description = f'Suggest a new database system to add to the {settings.DBDB_SITE_NAME} encyclopedia.'
    twitter_type = 'summary'

    def get_meta_image(self, context=None):
        from django.templatetags.static import static
        return self.request.build_absolute_uri(static(settings.DBDB_SITE_OGIMAGE))

    def get(self, request):
        return render(request, self.template_name, {'meta': self.get_meta(), 'form': SystemSuggestionForm()})

    def post(self, request):
        form = SystemSuggestionForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'meta': self.get_meta(), 'form': form})

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
                'meta': self.get_meta(),
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


class SystemSuggestionSuccessView(MetadataMixin, View):

    template_name = 'core/system-suggest-success.html'
    title = f'Suggestion Received{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_NAME}'
    description = f'Thank you for suggesting a database system to the {settings.DBDB_SITE_NAME} encyclopedia.'
    twitter_type = 'summary'

    def get_meta_image(self, context=None):
        from django.templatetags.static import static
        return self.request.build_absolute_uri(static(settings.DBDB_SITE_OGIMAGE))

    def get(self, request):
        return render(request, self.template_name, {'meta': self.get_meta()})
