from django.conf import settings
from django.http.response import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control
from meta.views import MetadataMixin

from dbdb.core.models import CitationUrl, Organization
from dbdb.core.views.home import _attach_data_models


@method_decorator(cache_control(public=True, max_age=14400), name='dispatch')
class OrganizationView(MetadataMixin, View):

    template_name = 'core/organization-view.html'

    twitter_type = 'summary'

    def get_meta_title(self, context=None):
        name = getattr(self, '_org_name')
        org_type = getattr(self, '_org_type', 'Organization')
        return f'{org_type} Profile for {name}{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_NAME}'

    def get_meta_description(self, context=None):
        if self._org_developed:
            desc = "developer of " + ", ".join([o.system.name for o in self._org_developed]) + " database system"
            if len(self._org_developed) > 1: desc += "s"
        elif self._org_acquisitions:
            desc = "acquirer of " + ", ".join([o.system.name for o in self._org_acquisitions]) + " database system"
            if len(self._org_acquisitions) > 1: desc += "s"
        else:
            desc = "database systems developer"

        return f'Information about the {desc}.'

    def get(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        # django-meta fields
        self._org_name = org.name
        self._org_type = org.get_org_type_display()

        # Build a numbered citation list (same mechanic as SystemView)
        all_citations = []

        def process(c):
            if c is None:
                return None
            try:
                return all_citations.index(c) + 1
            except ValueError:
                all_citations.append(c)
                return len(all_citations)

        url_citation       = process(org.url)
        wikipedia_citation = process(org.wikipedia_url)
        linkedin_citation  = process(org.linkedin_url)

        # Systems this org has acquired (via Acquisition → SystemVersion → System)
        self._org_acquisitions = []
        for acq in (
            org.acquisitions
               .filter(version__is_current=True)
               .select_related('version__system', 'citation')
               .order_by('year', 'version__system__name')
        ):
            self._org_acquisitions.append({
                'system':   acq.version.system,
                'version':  acq.version,
                'year':     acq.year,
                'citation': process(acq.citation),
            })

        # Systems this org developed (current SystemVersion only)
        self._org_developed = list(
            org.developed_systems
               .filter(is_current=True)
               .select_related('system')
               .order_by('system__name')
        )
        _attach_data_models(self._org_developed)

        return render(request, self.template_name, {
            'meta': self.get_meta(),
            'org':               org,
            'url_citation':       url_citation,
            'wikipedia_citation': wikipedia_citation,
            'linkedin_citation':  linkedin_citation,
            'acquisitions':      self._org_acquisitions,
            'developed':         self._org_developed,
            'citations':         all_citations,
            'Status':            CitationUrl.Status,
        })
