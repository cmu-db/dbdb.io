from django.http.response import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View

from dbdb.core.models import CitationUrl, Organization


class OrganizationView(View):

    template_name = 'core/organization-view.html'

    def get(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)

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

        url_citation      = process(org.url)
        linkedin_citation = process(org.linkedin_url)

        # Systems this org has acquired (via Acquisition → SystemVersion → System)
        acquisitions = []
        for acq in (
            org.acquisitions
               .filter(version__is_current=True)
               .select_related('version__system', 'citation')
               .order_by('year', 'version__system__name')
        ):
            acquisitions.append({
                'system':   acq.version.system,
                'version':  acq.version,
                'year':     acq.year,
                'citation': process(acq.citation),
            })

        # Systems this org developed (current SystemVersion only)
        developed = list(
            org.developed_systems
               .filter(is_current=True)
               .select_related('system')
               .order_by('system__name')
        )

        return render(request, self.template_name, {
            'org':               org,
            'url_citation':      url_citation,
            'linkedin_citation': linkedin_citation,
            'acquisitions':      acquisitions,
            'developed':         developed,
            'citations':         all_citations,
            'Status':            CitationUrl.Status,
        })
