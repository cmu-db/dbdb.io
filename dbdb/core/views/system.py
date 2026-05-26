import collections
import urllib.parse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms import HiddenInput
from django.http import HttpResponseForbidden
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views import View
from django.views.decorators.cache import cache_control

from dbdb.core.forms import (
    AcquisitionFormSet,
    DeveloperOrgFormSet,
    SystemFeaturesForm,
    SystemForm,
    SystemVersionForm,
)
from dbdb.core.models import (
    Acquisition,
    CitationUrl,
    Feature,
    FeatureOption,
    Organization,
    System,
    SystemACL,
    SystemFeature,
    SystemRecommendation,
    SystemRedirect,
    SystemSearchText,
    SystemVersion,
)
from dbdb.core.utils import logos
from dbdb.core.utils.searchtext import generate_searchtext
from dbdb.core.utils.twitter_card import create_twitter_card
from .api import CounterView


# ==============================================
# SystemView
# ==============================================
class SystemView(View):

    template_name = 'core/system-view.html'

    def process_citations(self, citations):
        citation_offsets = [ ]
        for c in citations:
            offset = None
            try:
                offset = self.all_citations.index(c) + 1
            except:
                self.all_citations.append(c)
                offset = len(self.all_citations)
            citation_offsets.append(offset)
        return citation_offsets

    def get(self, request, slug):
        # try to get system by slug
        try:
            system = System.objects.get(slug=slug)
            pass
        except System.DoesNotExist:
            # if the system doesn't exist, check for a redirect
            try:
                r = SystemRedirect.objects.get(slug=slug)
                return redirect( 'system' , permanent=True, slug=r.system.slug )
                pass
            except SystemRedirect.DoesNotExist:
                # with no redirect, throw 404
                raise Http404( 'system does not exist' )
                pass
            pass

        system_version = system.current()
        system_features = SystemFeature.objects.filter(version=system_version).select_related('feature').order_by('feature__label')

        # if they are logged in, check whether they are allowed to edit
        if not request.user.is_authenticated:
            user_can_edit = False
        elif request.user.is_superuser or request.user.is_staff:
            user_can_edit = True
        else:
            user_can_edit = SystemACL.objects.filter(system=system, user=request.user).exists()
            pass

        # Sections

        self.all_citations = []

        sections = []

        if system_version.description_citations:
            self.process_citations(system_version.description_citations.all())

        if system_version.history:
            sections.append({
                "id": "history",
                "title": "History",
                "body": system_version.history,
                "citations": self.process_citations(system_version.history_citations.all())
            })

        for sf in SystemFeature.objects.filter(version=system_version).select_related('feature').order_by('feature__label'):
            if not sf.system and not sf.description and sf.options.count() == 0: continue

            # If it is linked to another system, then we will get the options
            # from that system instead using this ones
            options = None
            if sf.system:
                try:
                    other_sf = SystemFeature.objects.get(version=sf.system.current(), feature=sf.feature)
                    options = other_sf.options.all()
                except SystemFeature.DoesNotExist:
                    pass
            if options is None:
                options = sf.options.all()

            sections.append({
                "id": sf.feature.slug,
                "title": sf.feature.label,
                "body": sf.description,
                "system": sf.system,
                "citations": self.process_citations(sf.citations.all()),
                "options": options,
            })

        start_year_citations = self.process_citations(system_version.start_year_citations.all())
        end_year_citations = self.process_citations(system_version.end_year_citations.all())

        acquisitions = [
            {
                'organization': acq.organization,
                'year': acq.year,
                'citations': self.process_citations([acq.citation] if acq.citation else []),
            }
            for acq in system_version.acquisitions
                .select_related('organization', 'citation')
                .order_by('year', 'organization__name')
        ]

        # Compatible Systems
        compatible = [
            ver.system for ver in SystemVersion.objects
                                .filter(is_current=True)
                                .filter(compatible_with=system)
                                .order_by("-logo")
                                .select_related()
        ]

        # Derived Systems
        derived = [
            ver.system for ver in SystemVersion.objects
                                .filter(is_current=True)
                                .filter(derived_from=system)
                                .order_by("-logo")
                                .select_related()
        ]

        # Embedding Systems
        embeds = [
            ver.system for ver in SystemVersion.objects
                                .filter(is_current=True)
                                .filter(embedded=system)
                                .order_by("-logo")
                                .select_related()
        ]

        # Systems that host this system as a DBaaS
        hosted_by = [
            ver.system for ver in SystemVersion.objects
                                .filter(is_current=True)
                                .filter(hosted_services=system)
                                .order_by("-logo")
                                .select_related()
        ]

        # Recommendations
        recommendations = [
            rec.recommendation for rec in SystemRecommendation.objects
                                .filter(system=system)
                                .order_by("-score")
                                .select_related()
        ]
        return render(request, self.template_name, {
            'activate': 'system',  # NAV-LINKS
            'system': system,
            'sections': sections,
            'citations': self.all_citations,
            'start_year_citations': start_year_citations,
            'end_year_citations': end_year_citations,
            'acquisitions': acquisitions,
            'system_version': system_version,
            'user_can_edit': user_can_edit,
            'compatible': compatible,
            'derived': derived,
            'embeds': embeds,
            'hosted_by': hosted_by,
            'recommendations': recommendations,
            'counter_token': CounterView.build_token('system', pk=system.id),
            'Status': CitationUrl.Status,
        })

    pass


# ==============================================
# SystemEditView
# ==============================================
class SystemEditView(LoginRequiredMixin, View):

    template_name = 'core/system-edit.html'

    def build_features(self, feature_form):
        features = Feature.objects.all()
        features = collections.OrderedDict(
            (
                f.id,
                {
                    'id': f'feature_{f.id}',
                    'label': f.label,
                    'choices': None,
                    'description': None,
                    'citation': None,
                }
            )
            for f in features
        )
        for bf in feature_form:
            name = bf.name.split('_')[-1]
            feature_id = bf.field.feature_id

            features[feature_id][name] = bf
            pass
        return features

    @method_decorator(cache_control(private=True))
    def get(self, request, slug=None):

        # If there is no slug, then they are trying to create a new database.
        # Only superusers are allowed to do that.
        if slug is None:
            if not request.user.is_superuser:
                raise Http404()

            # Create a new empty system for the form
            system = System()
            system_version = SystemVersion(system=system, is_current=True)
            system_features = SystemFeature.objects.none()
            pass

        # If there is a slug, then check to see whether they have permission
        # to edit this mofo
        else:
            # You always have to be logged in to edit an entry
            if not request.user.is_authenticated:
                return redirect( settings.LOGIN_URL + '?next=' + reverse('system', args=[slug]))

            system = System.objects.get(slug=slug)

            # Make sure this user has permissions to edit this page
            if not request.user.is_superuser and not request.user.is_staff:
                try:
                    system_acl = SystemACL.objects.get(system=system, user=request.user)
                except SystemACL.DoesNotExist:
                    base_url = reverse('system', args=[slug])
                    query_string =  urllib.parse.urlencode({'noperms': 1})
                    url = f'{base_url}?{query_string}'
                    return redirect(url)
            ## IF

            # Load in what we need
            system_version = SystemVersion.objects.get(system=system, is_current=True)
            system_features = system_version.features.all()
            pass

        system_form = SystemForm(instance=system)

        # Don't allow non-superusers from editing the system name
        # This only really hides it from the UI.
        if request.user.is_superuser:
            system_form.fields['orig_name'].widget = HiddenInput()
        else:
            system_form.fields['name'].widget = HiddenInput()
            system_form.fields['orig_name'].initial = system.name

        feature_form = SystemFeaturesForm(system=system, features=system_features)

        features = self.build_features(feature_form)

        acquisitions_initial = [
            {
                'organization': acq.organization.name,
                'year': acq.year,
                'citation_url': acq.citation.url if acq.citation else '',
            }
            for acq in system_version.acquisitions.select_related('organization', 'citation').all()
        ] if system_version.pk else []
        acquisition_formset = AcquisitionFormSet(initial=acquisitions_initial, prefix='acquisitions')

        developer_org_initial = [
            {'organization': org.name}
            for org in system_version.developer_orgs.all()
        ] if system_version.pk else []
        developer_org_formset = DeveloperOrgFormSet(initial=developer_org_initial, prefix='developer_orgs')

        return render(request, self.template_name, {
            'activate': 'create' if system.id is None else 'edit', # NAV-LINKS
            'system': system,
            'system_form': system_form,
            'system_version_form': SystemVersionForm(instance=system_version, initial={
                'system_url':       system_version.system_url.url       if system_version.system_url       else '',
                'docs_url':         system_version.docs_url.url         if system_version.docs_url         else '',
                'sourcerepo_url':   system_version.sourcerepo_url.url   if system_version.sourcerepo_url   else '',
                'wikipedia_url':    system_version.wikipedia_url.url    if system_version.wikipedia_url    else '',
            }),
            'feature_form': feature_form,
            'features': features,
            'acquisition_formset': acquisition_formset,
            'developer_org_formset': developer_org_formset,
        })

    @transaction.atomic
    def post(self, request, slug=None):

        prev_version = None
        if slug is None:
            if not request.user.is_superuser:
                raise Http404()

            system = System()
            # system_version = SystemVersion(system=system, is_current=True)
            system_features = SystemFeature.objects.none()
            old_logo = None
            pass
        else:
            system = System.objects.get(slug=slug)
            prev_version = SystemVersion.objects.get(system=system, is_current=True)
            system_features = prev_version.features.all()
            old_logo = prev_version.logo
            pass

        system_form = SystemForm(request.POST, instance=system)
        system_version_form = SystemVersionForm(request.POST, request.FILES)
        feature_form = SystemFeaturesForm(request.POST, system=system, features=system_features)
        acquisition_formset = AcquisitionFormSet(request.POST, prefix='acquisitions')
        developer_org_formset = DeveloperOrgFormSet(request.POST, prefix='developer_orgs')

        if system_form.is_valid() and \
            system_version_form.is_valid() and \
            feature_form.is_valid() and \
            acquisition_formset.is_valid() and \
            developer_org_formset.is_valid():

            if request.user.is_superuser:
                original_system_slug = system.slug
                system = system_form.save(commit=False)
                system.slug = slugify(system.name)
                system.save()

                # handle a redirect for a name change
                if system.slug != original_system_slug:
                    SystemRedirect.objects.get_or_create(
                        slug=original_system_slug,
                        defaults=dict(
                            system=system
                        )
                    )
                    pass

                # If there is already a logo and they do not update it,
                # then we need to make sure it gets copied over.
                try:
                    logo = system.current().logo
                except SystemVersion.DoesNotExist:
                    logo = ''
                pass
            else:
                logo = system.current().logo
                pass

            system.versions.update(is_current=False)
            new_version = system_version_form.save(commit=False)
            new_version.creator = request.user
            new_version.system = system

            # Resolve CitationUrl FK fields from URL inputs
            for fk_field in ('system_url', 'docs_url', 'sourcerepo_url', 'wikipedia_url'):
                url_str = (system_version_form.cleaned_data.get(fk_field) or '').strip()
                if url_str:
                    citation, _ = CitationUrl.objects.get_or_create(
                        url=url_str,
                        defaults={'status': CitationUrl.Status.UNKNOWN},
                    )
                    setattr(new_version, fk_field, citation)
                else:
                    setattr(new_version, fk_field, None)

            new_version.save()
            system_version_form.save_m2m()
            new_version.hosted_services.remove(system)

            if logo and not new_version.logo:
                new_version.logo = logo
            # Extract information about the logo that we can use when rendering pages
            if new_version.logo is not None:
                logo_w, logo_h = logos.extract_dimensions(new_version.logo.path)
                new_version.logo_width = logo_w
                new_version.logo_height = logo_h
                new_version.logo_color = logos.color_to_hex(logos.extract_color(new_version.logo.path))

            system.ver = new_version.ver
            system.modified = timezone.now()
            system.save()

            new_version.description_citations.clear()
            for url in system_version_form.cleaned_data.get('description_citations', []):
                new_version.description_citations.add(url)

            new_version.history_citations.clear()
            for url in system_version_form.cleaned_data.get('history_citations', []):
                new_version.history_citations.add(url)

            new_version.start_year_citations.clear()
            for url in system_version_form.cleaned_data.get('start_year_citations', []):
                new_version.start_year_citations.add(url)

            new_version.end_year_citations.clear()
            for url in system_version_form.cleaned_data.get('end_year_citations', []):
                new_version.end_year_citations.add(url)

            # I don't know why we need to do this twice?
            new_version.save()

            features = {
                f.label : f
                for f in Feature.objects.all()
            }

            feature_cache = {}
            def get_systemfeature_obj(feature):
                if feature not in feature_cache:
                    sf, _ = SystemFeature.objects.get_or_create(
                        version=new_version,
                        feature=feature
                    )
                    feature_cache[feature] = sf
                else:
                    sf = feature_cache[feature]
                return sf

            # Old code would create a SystemFeature entry for everything
            # even if the system doesn't include it. So we need to check
            # whether they have previous SystemFeatures
            for f in features.values():
                field_prefix = f.get_sanitized_label()
                sf = None

                # Get the previous version's Feature for this system
                # TODO: Do we need to do this???
                prev_sf = None
                if prev_version is not None:
                    try:
                        prev_sf = SystemFeature.objects.get(
                            version=prev_version,
                            feature=f
                        )
                    except SystemFeature.DoesNotExist:
                        pass

                # Description
                field_name = field_prefix + "_description"
                value = feature_form.cleaned_data[field_name].strip()
                if value:
                    sf = get_systemfeature_obj(f)
                    sf.description = value

                # Citations
                field_name = field_prefix + "_citations"
                value = feature_form.cleaned_data[field_name]
                if value:
                    sf = get_systemfeature_obj(f)
                    sf.citations.set(value)

                # System
                field_name = field_prefix + "_system"
                value = feature_form.cleaned_data[field_name].strip()
                if value:
                    sf = get_systemfeature_obj(f)
                    sf.system = System.objects.get(id=int(value))

                # Options
                field_name = field_prefix + "_choices"
                value = feature_form.cleaned_data[field_name]
                if isinstance(value, str):
                    sf = get_systemfeature_obj(f)
                    sf.options.add(
                        FeatureOption.objects.get(
                            feature=f,
                            value=value
                        )
                    )
                else:
                    for v in value:
                        sf = get_systemfeature_obj(f)
                        sf.options.add(
                            FeatureOption.objects.get(
                                feature=f,
                                value=v
                            )
                        )

            for sf in feature_cache.values():
                print(f"Saving {sf}")
                sf.save()

            # Do this down here to make sure the logo gets uploaded correctly
            if new_version.logo is not None and old_logo != new_version.logo:
                create_twitter_card(new_version)

            # Update the search index too!
            ver_search, created = SystemSearchText.objects.update_or_create(system=system)
            ver_search.search_text = generate_searchtext(new_version)
            ver_search.save()

            # Save acquisitions
            for form in acquisition_formset:
                if not form.has_changed() or form.cleaned_data.get('DELETE'):
                    continue
                if not form.cleaned_data.get('organization', '').strip():
                    continue
                org_name = form.cleaned_data['organization'].strip()
                org_slug = slugify(org_name)[:50]
                org, _ = Organization.objects.get_or_create(
                    name=org_name, defaults={'slug': org_slug}
                )
                citation = None
                citation_url_str = form.cleaned_data.get('citation_url', '').strip()
                if citation_url_str:
                    citation, _ = CitationUrl.objects.get_or_create(url=citation_url_str)
                Acquisition.objects.get_or_create(
                    version=new_version,
                    organization=org,
                    defaults={'year': form.cleaned_data.get('year'), 'citation': citation},
                )

            # Save developer organizations
            developer_orgs = []
            for form in developer_org_formset:
                if not form.has_changed() or form.cleaned_data.get('DELETE'):
                    continue
                org_name = form.cleaned_data.get('organization', '').strip()
                if not org_name:
                    continue
                org, _ = Organization.objects.get_or_create(
                    name=org_name, defaults={'slug': slugify(org_name)[:50]}
                )
                developer_orgs.append(org)
            new_version.developer_orgs.set(developer_orgs)

            return redirect(new_version.system.get_absolute_url())

        features = self.build_features(feature_form)

        return render(request, self.template_name, {
            'activate': 'edit', # NAV-LINKS
            'system_name': system.name,
            'system_form': system_form,
            'system_version_form': system_version_form,
            'feature_form': feature_form,
            'features': features,
            'acquisition_formset': acquisition_formset,
            'developer_org_formset': developer_org_formset,
        })

    pass


# ==============================================
# RecentChangesView
# ==============================================
class RecentChangesView(View):
    template_name = "core/recent.html"

    def get(self, request):
        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

        page = request.GET.get("page", 1)
        username = request.GET.get("username", None)
        versions = None
        lookup_user = None

        # Try to get the versions for the given username
        if username is not None:
            User = get_user_model()
            try:
                lookup_user = User.objects.get(username=username)
                versions = SystemVersion.objects.filter(creator=lookup_user)
            except:
                lookup_user = None
                pass
        if versions is None:
            versions = SystemVersion.objects.all()

        # Sort by timestamps
        versions = versions.order_by("-created")

        paginator = Paginator(versions, 25)
        try:
            versions = paginator.get_page(page)
            total_pages = paginator.num_pages
            current_page = versions.number
            DISPLAY_PAGES = 7
            half_window = DISPLAY_PAGES // 2

            start_page = max(current_page - half_window, 1)
            end_page = start_page + DISPLAY_PAGES - 1
            if end_page > total_pages:
                end_page = total_pages
                start_page = max(end_page - DISPLAY_PAGES + 1, 1)

            page_range = range(start_page, end_page + 1)
        except PageNotAnInteger:
            versions = paginator.get_page(1)
        except EmptyPage:
            versions = paginator.get_page(paginator.num_pages)

        return render(
            request,
            self.template_name,
            context={
                "activate": "recent",  # NAV-LINKS
                "versions": versions,
                "page_range": page_range,
                "lookup_user": lookup_user,
                "revision_list": False,
            },
        )

    pass


# ==============================================
# SystemRevisionList
# ==============================================
class SystemRevisionList(View):

    template_name = 'core/recent.html'

    def get(self, request, slug):
        system = get_object_or_404(System, slug=slug)

        versions = SystemVersion.objects \
            .filter(system=system) \
            .select_related('system')

        return render(request, self.template_name, {
            'activate': 'revisions', # NAV-LINKS
            'system': system,
            'versions': versions,
            'revision_list': True,
        })

    @method_decorator(login_required)
    def post(self, request, slug):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        system = System.objects.get(slug=slug)
        version = SystemVersion.objects.get(id=request.POST['ver'])
        system.versions.update(is_current=False)
        version.is_current = True
        system.ver = version.ver
        system.modified = timezone.now()
        version.save()
        system.save()

        return redirect('system', slug=slug)

    pass


# ==============================================
# SystemRevisionView
# ==============================================
class SystemRevisionView(View):

    template_name = 'core/system-revision.html'

    def get(self, request, slug, ver):
        system_version = get_object_or_404(SystemVersion.objects.select_related('system'), system__slug=slug, ver=ver)

        return render(request, self.template_name, {
            'activate': 'revisions', # NAV-LINKS
            'system': system_version.system,
            'system_version': system_version,
            'has_revision': True,
            'system_features': system_version.features.all()
        })

    pass