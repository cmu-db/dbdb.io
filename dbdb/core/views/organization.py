import os
from itertools import groupby

from django.conf import settings
from django.db import models
from django.db.models.expressions import RawSQL
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control
from meta.views import MetadataMixin

from dbdb.core.models import CitationUrl, Organization, OrgType
from dbdb.core.views.home import _attach_data_models


@method_decorator(cache_control(public=True, max_age=3600), name='dispatch')
class OrganizationListView(MetadataMixin, View):

    template_name = 'core/organization-list.html'
    title = f'Organizations{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_NAME}'
    twitter_type = 'summary'

    def get_meta_image(self, context=None):
        from django.templatetags.static import static
        return self.request.build_absolute_uri(static(settings.DBDB_SITE_OGIMAGE))

    def get_meta_description(self, context=None):
        return f'A directory of organizations that develop or acquire database systems on {settings.DBDB_SITE_NAME}.'

    def get(self, request):
        orgs = (
            Organization.objects
            .filter(
                models.Q(developed_systems__is_current=True) |
                models.Q(acquisitions__version__is_current=True)
            )
            .distinct()
            .order_by(models.F('org_type').asc(nulls_last=True), 'name')
        )

        org_groups = []
        for org_type_val, group in groupby(orgs, key=lambda o: o.org_type):
            label = OrgType(org_type_val).label if org_type_val is not None else 'Other'
            org_groups.append({'label': label, 'orgs': list(group)})

        total_count = sum(len(g['orgs']) for g in org_groups)

        suggest = None
        suggest_slug = request.GET.get('suggest', '').strip()
        if suggest_slug:
            suggest = Organization.objects.filter(slug=suggest_slug).first()

        return render(request, self.template_name, {
            'meta': self.get_meta(),
            'org_groups': org_groups,
            'total_count': total_count,
            'suggest': suggest,
        })


@method_decorator(cache_control(public=True, max_age=14400), name='dispatch')
class OrganizationView(MetadataMixin, View):

    template_name = 'core/organization-view.html'

    twitter_type = 'summary_large_image'

    def get_meta_image(self, context=None):
        org = getattr(self, '_org', None)
        if org and org.logo:
            card_path = os.path.join(settings.TWITTER_CARD_ROOT, org.get_twitter_card_image())
            if os.path.exists(card_path):
                return self.request.build_absolute_uri(org.twitter_card_url())
        return None

    def get_meta_title(self, context=None):
        name = getattr(self, '_org_name')
        org_type = getattr(self, '_org_type', None)
        if not org_type:
            org_type = 'Organization'
        return f'{name}{settings.DBDB_TITLE_SEPARATOR}{org_type} Profile{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_NAME}'

    def get_meta_description(self, context=None):
        from django.utils.text import Truncator
        if self._org_developed:
            desc = "developer of " + ", ".join([o.system.name for o in self._org_developed]) + " database system"
            if len(self._org_developed) > 1: desc += "s"
        elif self._org_acquisitions:
            desc = "acquirer of " + ", ".join([o['system'].name for o in self._org_acquisitions]) + " database system"
            if len(self._org_acquisitions) > 1: desc += "s"
        else:
            desc = "database systems developer"

        return Truncator(f'Info about the {desc}.').chars(300)

    def get_meta_extra_props(self, context=None):
        org = getattr(self, '_org', None)
        if not org:
            return None
        return {
            'twitter:label1': 'Last Updated',
            'twitter:data1': f'{org.modified:{settings.DBDB_META_DATETIME_FORMAT}}',
            # 'twitter:label2': 'License',
            # 'twitter:data2': sv.licenses.first().name if sv.licenses.exists() else None,
        }

    def get(self, request, slug):
        try:
            org = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist:
            prefix = slug.split('-')[0]
            match = (
                Organization.objects
                .annotate(dist=RawSQL("split_part(slug, '-', 1) <-> %s", [prefix]))
                .filter(dist__lt=0.5)
                .order_by('dist')
                .values('slug')
                .first()
            )
            url = reverse('organization_list')
            if match:
                url += f'?suggest={match["slug"]}'
            return redirect(url)
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

        url_citation        = process(org.url)
        wikipedia_citation  = process(org.wikipedia_url)
        linkedin_citation   = process(org.linkedin_url)
        crunchbase_citation = process(org.crunchbase_url)

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

        self._org = org
        return render(request, self.template_name, {
            'meta': self.get_meta(),
            'org':               org,
            'url_citation':        url_citation,
            'wikipedia_citation':  wikipedia_citation,
            'linkedin_citation':   linkedin_citation,
            'crunchbase_citation': crunchbase_citation,
            'acquisitions':      self._org_acquisitions,
            'developed':         self._org_developed,
            'citations':         all_citations,
            'Status':            CitationUrl.Status,
        })
