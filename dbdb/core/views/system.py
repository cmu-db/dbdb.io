import collections
import urllib.parse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import OuterRef, Subquery
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
    RepositoryInfo,
    System,
    SystemACL,
    SystemFeature,
    SystemRecommendation,
    SystemRedirect,
    SystemSuggestion,
    SystemVersion,
    user_can_edit_system,
)
from dbdb.core.utils.versions import finalize_new_version

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

    def get(self, request, slug, ver=None):
        # try to get system by slug
        try:
            system = System.objects.get(slug=slug)
        except System.DoesNotExist:
            # if the system doesn't exist, check for a redirect
            try:
                r = SystemRedirect.objects.get(slug=slug)
                return redirect( 'system' , permanent=True, slug=r.system.slug )
            except SystemRedirect.DoesNotExist:
                raise Http404( 'system does not exist' )

        # Permission check first — needed to decide which version to show.
        if not request.user.is_authenticated:
            user_can_edit = False
        elif request.user.is_superuser or request.user.is_staff:
            user_can_edit = True
        else:
            user_can_edit = SystemACL.objects.filter(system=system, user=request.user).exists()

        qs = SystemVersion.objects.prefetch_related(
            'tags', 'oses', 'licenses',
            'project_types', 'supported_languages', 'written_in',
        )
        approved_ver = None  # ver of the approved (is_current) version, passed to template when showing a pending default
        version_error = None
        if ver is not None:
            try:
                system_version = qs.get(system=system, ver=ver)
                has_revision = True
            except SystemVersion.DoesNotExist:
                system_version = qs.get(system=system, is_current=True)
                has_revision = False
                version_error = f"Version {ver} does not exist for {system.name}. Showing the current version instead."
        else:
            pending = system.pending_version() if user_can_edit else None
            if pending:
                system_version = qs.get(system=system, ver=pending.ver)
                approved_ver = SystemVersion.objects.filter(system=system, is_current=True).values_list('ver', flat=True).first()
                has_revision = True
            else:
                system_version = qs.get(system=system, is_current=True)
                has_revision = False
        system_features = SystemFeature.objects.filter(version=system_version).select_related('feature').order_by('feature__label')

        # Sections

        self.all_citations = []

        def _url_citation(field):
            obj = getattr(system_version, field)
            return self.process_citations([obj])[0] if obj else None

        system_url_citation     = _url_citation('system_url')
        docs_url_citation       = _url_citation('docs_url')
        sourcerepo_url_citation = _url_citation('sourcerepo_url')
        wikipedia_url_citation  = _url_citation('wikipedia_url')

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

            # Skip if the linked system has no options for this feature and
            # the current SystemFeature contributes nothing of its own.
            if (sf.system
                    and not options
                    and sf.options.count() == 0
                    and not sf.citations.exists()
                    and not sf.description):
                continue

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

        repo_snapshot = None
        if system_version.sourcerepo_url_id:
            repo_info = (
                RepositoryInfo.objects
                .filter(sourcerepo_url_id=system_version.sourcerepo_url_id)
                .select_related('current')
                .first()
            )
            if repo_info:
                repo_snapshot = repo_info.current

        return render(request, self.template_name, {
            'activate': 'system',  # NAV-LINKS
            'system': system,
            'version': system_version,
            'sections': sections,
            'citations': self.all_citations,
            'start_year_citations': start_year_citations,
            'end_year_citations': end_year_citations,
            'acquisitions': acquisitions,
            'user_can_edit': user_can_edit,
            'compatible': compatible,
            'derived': derived,
            'embeds': embeds,
            'hosted_by': hosted_by,
            'recommendations': recommendations,
            'counter_token': CounterView.build_token('system', pk=system.id),
            'Status': CitationUrl.Status,
            'repo_snapshot': repo_snapshot,
            'has_revision': has_revision,
            'approved_ver': approved_ver,
            'system_url_citation':     system_url_citation,
            'docs_url_citation':       docs_url_citation,
            'sourcerepo_url_citation': sourcerepo_url_citation,
            'wikipedia_url_citation':  wikipedia_url_citation,
            'page_error': version_error,
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
            version = SystemVersion(system=system, is_current=True)
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

            # Load in what we need — prefer the pending (unapproved) version if one exists
            pending = system.pending_version()
            if pending:
                version = pending
            else:
                version = SystemVersion.objects.get(system=system, is_current=True)
            system_features = version.features.all()
            pass

        # Load suggestion pre-fill data (only for new-system creation)
        suggestion = None
        if slug is None:
            suggestion_id = request.GET.get('suggestion_id')
            if suggestion_id:
                try:
                    suggestion = SystemSuggestion.objects.get(id=suggestion_id)
                except SystemSuggestion.DoesNotExist:
                    pass

        system_form = SystemForm(
            instance=system,
            initial={'name': suggestion.name} if suggestion else {},
        )

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
            for acq in version.acquisitions.select_related('organization', 'citation').all()
        ] if version.pk else []
        acquisition_formset = AcquisitionFormSet(initial=acquisitions_initial, prefix='acquisitions')

        developer_org_initial = [
            {'organization': org.name}
            for org in version.developer_orgs.all()
        ] if version.pk else []
        developer_org_formset = DeveloperOrgFormSet(initial=developer_org_initial, prefix='developer_orgs')

        version_initial = {
            'system_url':     version.system_url.url     if version.system_url     else '',
            'docs_url':       version.docs_url.url       if version.docs_url       else '',
            'sourcerepo_url': version.sourcerepo_url.url if version.sourcerepo_url else '',
            'wikipedia_url':  version.wikipedia_url.url  if version.wikipedia_url  else '',
        }
        if suggestion:
            version_initial['system_url'] = suggestion.system_url
            if suggestion.sourcerepo_url:
                version_initial['sourcerepo_url'] = suggestion.sourcerepo_url

        return render(request, self.template_name, {
            'activate': 'create' if system.id is None else 'edit', # NAV-LINKS
            'system': system,
            'system_form': system_form,
            'system_version_form': SystemVersionForm(instance=version, initial=version_initial),
            'feature_form': feature_form,
            'features': features,
            'acquisition_formset': acquisition_formset,
            'developer_org_formset': developer_org_formset,
            'pending_version': version if (version.pk and not version.approved) else None,
            'suggestion': suggestion,
        })

    @transaction.atomic
    def post(self, request, slug=None):

        if request.POST.get('action') == 'cancel':
            if slug:
                return redirect('system', slug=slug)
            return redirect('home')

        is_admin = request.user.is_superuser or request.user.is_staff

        prev_version = None
        pending = None
        if slug is None:
            if not request.user.is_superuser:
                raise Http404()

            system = System()
            system_features = SystemFeature.objects.none()
            old_logo = None
        else:
            system = System.objects.get(slug=slug)

            # Permission check (was missing from post())
            if not user_can_edit_system(request.user, system):
                return HttpResponseForbidden()

            try:
                prev_version = SystemVersion.objects.get(system=system, is_current=True)
                system_features = prev_version.features.all()
                old_logo = prev_version.logo
            except SystemVersion.DoesNotExist:
                system_features = SystemFeature.objects.none()
                old_logo = None

            # For non-admins, find any existing unapproved (pending) version
            if not is_admin:
                pending = system.versions.filter(approved=False).first()

        system_form = SystemForm(request.POST, instance=system)
        # Bind the pending instance so save() updates it in-place rather than creating a new row
        system_version_form = SystemVersionForm(
            request.POST, request.FILES,
            instance=pending if pending else None,
        )
        feature_form = SystemFeaturesForm(request.POST, system=system, features=system_features)
        acquisition_formset = AcquisitionFormSet(request.POST, prefix='acquisitions')
        developer_org_formset = DeveloperOrgFormSet(request.POST, prefix='developer_orgs')

        if system_form.is_valid() and \
            system_version_form.is_valid() and \
            feature_form.is_valid() and \
            acquisition_formset.is_valid() and \
            developer_org_formset.is_valid():

            if is_admin:
                original_system_slug = system.slug
                system = system_form.save(commit=False)
                system.slug = slugify(system.name)
                system.save()

                # handle a redirect for a name change
                if system.slug != original_system_slug:
                    SystemRedirect.objects.get_or_create(
                        slug=original_system_slug,
                        defaults=dict(system=system)
                    )

                # If there is already a logo and they do not update it,
                # then we need to make sure it gets copied over.
                try:
                    logo = system.current().logo
                except SystemVersion.DoesNotExist:
                    logo = ''
            else:
                logo = system.current().logo if prev_version else ''

            new_version = system_version_form.save(commit=False)

            if is_admin:
                # Mark as approved and flip all previous versions to not-current
                new_version.approved = True
                new_version.creator = request.user
                new_version.system = system
                system.versions.update(is_current=False)
            else:
                # Pending path: not approved, stays invisible
                new_version.approved = False
                new_version.is_current = False
                if pending is None:
                    # New pending version — set creator/system (update path keeps existing values)
                    new_version.creator = request.user
                    new_version.system = system

            # Resolve CitationUrl FK fields from URL inputs.
            # URLField normalizes bare domains by adding a trailing slash (e.g.
            # "https://mongodb.com" → "https://mongodb.com/").  Try the exact
            # normalized form first, then the slash-stripped form, before creating.
            for fk_field in ('system_url', 'docs_url', 'sourcerepo_url', 'wikipedia_url'):
                url_str = (system_version_form.cleaned_data.get(fk_field) or '').strip()
                if url_str:
                    citation = CitationUrl.objects.filter(url=url_str).first()
                    if citation is None and url_str.endswith('/'):
                        citation = CitationUrl.objects.filter(url=url_str.rstrip('/')).first()
                    if citation is None:
                        citation = CitationUrl.objects.create(
                            url=url_str,
                            status=CitationUrl.Status.UNKNOWN,
                        )
                    setattr(new_version, fk_field, citation)
                else:
                    setattr(new_version, fk_field, None)

            new_version.save()
            system_version_form.save_m2m()
            new_version.hosted_services.remove(system)

            if logo and not new_version.logo:
                new_version.logo = logo

            if is_admin:
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

            new_version.save()

            features = {
                f.label : f
                for f in Feature.objects.all()
            }

            # For pending-update, wipe existing SystemFeature rows so we start fresh
            if pending is not None:
                new_version.features.all().delete()

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

            for f in features.values():
                field_prefix = f.get_sanitized_label()
                sf = None

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
                        FeatureOption.objects.get(feature=f, value=value)
                    )
                else:
                    for v in value:
                        sf = get_systemfeature_obj(f)
                        sf.options.add(
                            FeatureOption.objects.get(feature=f, value=v)
                        )

            for sf in feature_cache.values():
                sf.save()

            # Save acquisitions (clear existing ones for pending-update)
            if pending is not None:
                new_version.acquisitions.all().delete()

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

            finalize_new_version(new_version, old_logo=old_logo)

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

    def get(self, request, slug=None):
        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

        page = request.GET.get("page", 1)
        username = request.GET.get("username", None)
        versions = None
        lookup_user = None
        system = None

        if slug is not None:
            system = get_object_or_404(System, slug=slug)
            versions = SystemVersion.objects.filter(system=system).select_related('system')
        elif username is not None:
            User = get_user_model()
            try:
                lookup_user = User.objects.get(username=username)
                versions = SystemVersion.objects.filter(creator=lookup_user)
            except Exception:
                lookup_user = None

        if versions is None:
            versions = SystemVersion.objects.all()

        # Filter out unapproved (pending) versions based on who is viewing
        if slug is not None:
            # System-specific feed: editors see pending; public does not
            if not user_can_edit_system(request.user, system):
                versions = versions.filter(approved=True)
        else:
            viewing_own = (
                request.user.is_authenticated
                and lookup_user is not None
                and lookup_user == request.user
            )
            if not viewing_own:
                versions = versions.filter(approved=True)

        versions = versions.order_by("-created")
        total_revisions = versions.count()

        can_edit_system = user_can_edit_system(request.user, system) if system else False

        context = {
            "activate": "recent",
            "lookup_user": lookup_user,
            "system": system,
            "total_revisions": total_revisions,
            "revision_list": slug is not None,
            "can_edit_system": can_edit_system,
        }

        if slug is not None:
            version_list = list(versions)
            for i, v in enumerate(version_list):
                v.diff_prev_ver = version_list[i + 1].ver if i + 1 < len(version_list) else None
            context["versions"] = version_list
            context["page_range"] = None
        else:
            prev_ver_sub = SystemVersion.objects.filter(
                system_id=OuterRef('system_id'),
                ver__lt=OuterRef('ver'),
            ).order_by('-ver').values('ver')[:1]
            versions = versions.annotate(diff_prev_ver=Subquery(prev_ver_sub))
            paginator = Paginator(versions, 25)
            page_range = range(1, 2)
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
            context["versions"] = versions
            context["page_range"] = page_range

        return render(request, self.template_name, context)

    @method_decorator(login_required)
    def post(self, request, slug=None):
        if slug is None:
            return HttpResponseForbidden()
        if not (request.user.is_superuser or request.user.is_staff):
            return HttpResponseForbidden()

        system = System.objects.get(slug=slug)
        version = SystemVersion.objects.get(id=request.POST['ver'])
        system.versions.update(is_current=False)
        version.is_current = True
        version.approved = True
        system.ver = version.ver
        system.modified = timezone.now()
        version.save()
        system.save()

        return redirect('system', slug=slug)


# ==============================================
# ==============================================
# _compute_version_diff helper
# ==============================================
def _inline_diff(old_text, new_text):
    """
    Return (old_html, new_html) with word-level changes highlighted inline,
    similar to Wikipedia's diff view.
    Deletions appear wrapped in <del> in old_html; insertions in <ins> in new_html.
    """
    import difflib
    import html as html_module
    import re

    def tokenize(text):
        # Split on whitespace boundaries, keeping the whitespace tokens
        return re.split(r'(\s+)', text)

    old_tokens = tokenize(old_text)
    new_tokens = tokenize(new_text)
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)

    old_parts = []
    new_parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = html_module.escape(''.join(old_tokens[i1:i2]))
        new_chunk = html_module.escape(''.join(new_tokens[j1:j2]))
        if tag == 'equal':
            old_parts.append(old_chunk)
            new_parts.append(new_chunk)
        elif tag == 'replace':
            old_parts.append(f'<del>{old_chunk}</del>')
            new_parts.append(f'<ins>{new_chunk}</ins>')
        elif tag == 'delete':
            old_parts.append(f'<del>{old_chunk}</del>')
        elif tag == 'insert':
            new_parts.append(f'<ins>{new_chunk}</ins>')

    return ''.join(old_parts), ''.join(new_parts)


def _citation_diff(a_set, b_set):
    """
    Given two sets of URL strings, return a dict with display-ready item lists.

    v1_items: alphabetically sorted list of all v1 citations, each annotated with
              status 'removed' or 'unchanged'.
    v2_items: alphabetically sorted union of both sets, each annotated with
              status 'added', 'removed' (still shown struck), or 'unchanged'.
    """
    removed  = a_set - b_set
    added    = b_set - a_set
    unchanged = a_set & b_set

    v1_items = [
        {'url': u, 'status': 'removed' if u in removed else 'unchanged'}
        for u in sorted(a_set)
    ]
    v2_items = [
        {'url': u,
         'status': 'added' if u in added else ('removed' if u in removed else 'unchanged')}
        for u in sorted(a_set | b_set)
    ]
    return {
        'v1_items': v1_items,
        'v2_items': v2_items,
        'changed': bool(removed or added),
    }


def _citation_set_diff(v1_obj, v2_obj, field_name):
    """Compute citation diff for a named M2M field on a SystemVersion pair."""
    a_set = set(c.url for c in getattr(v1_obj, field_name).all())
    b_set = set(c.url for c in getattr(v2_obj, field_name).all())
    return _citation_diff(a_set, b_set)


def _compute_version_diff(v1, v2):
    """
    Return a list of diff entries comparing two SystemVersion instances.
    Fields are grouped so that citations appear directly below their parent field.
    """
    diffs = []

    def _str(val):
        return str(val) if val is not None else ''

    def _url_str(fk_citation):
        return fk_citation.url if fk_citation else ''

    def _m2m_set(manager, attr='name'):
        return set(getattr(obj, attr) for obj in manager.all())

    def _set_entry(field, label, a_set, b_set):
        return {
            'field': field, 'label': label, 'type': 'set',
            'v1_val': sorted(a_set), 'v2_val': sorted(b_set),
            'added': sorted(b_set - a_set),
            'removed': sorted(a_set - b_set),
            'unchanged': sorted(a_set & b_set),
            'changed': a_set != b_set,
        }

    # --- description + its citations (inline) ---
    for field, label, cite_field in [
        ('description', 'Description', 'description_citations'),
        ('history',     'History',     'history_citations'),
    ]:
        a = getattr(v1, field) or ''
        b = getattr(v2, field) or ''
        old_html, new_html = _inline_diff(a, b) if a != b else ('', '')
        cite = _citation_set_diff(v1, v2, cite_field)
        diffs.append({'field': field, 'label': label, 'type': 'text',
                      'v1_val': a, 'v2_val': b,
                      'v1_html': old_html, 'v2_html': new_html,
                      'changed': a != b or cite['changed'],
                      'citations': cite})

    # --- start_year + citations (inline) ---
    a = _str(v1.start_year)
    b = _str(v2.start_year)
    cite = _citation_set_diff(v1, v2, 'start_year_citations')
    diffs.append({'field': 'start_year', 'label': 'Start Year', 'type': 'scalar',
                  'v1_val': a, 'v2_val': b,
                  'changed': a != b or cite['changed'],
                  'citations': cite})

    # --- end_year + citations (inline) ---
    a = _str(v1.end_year)
    b = _str(v2.end_year)
    cite = _citation_set_diff(v1, v2, 'end_year_citations')
    diffs.append({'field': 'end_year', 'label': 'End Year', 'type': 'scalar',
                  'v1_val': a, 'v2_val': b,
                  'changed': a != b or cite['changed'],
                  'citations': cite})

    # --- remaining scalar fields ---
    for field, label in [
        ('twitter_handle',   'Twitter Handle'),
        ('linkedin_handle',  'LinkedIn Handle'),
        ('former_names',     'Former Names'),
        ('countries',        'Countries'),
    ]:
        a = _str(getattr(v1, field))
        b = _str(getattr(v2, field))
        diffs.append({'field': field, 'label': label, 'type': 'scalar',
                      'v1_val': a, 'v2_val': b, 'changed': a != b})

    # --- URL / CitationUrl FK fields ---
    for field, label in [
        ('system_url',      'Website URL'),
        ('docs_url',        'Docs URL'),
        ('sourcerepo_url',  'Source Repo URL'),
        ('wikipedia_url',   'Wikipedia URL'),
    ]:
        a = _url_str(getattr(v1, field))
        b = _url_str(getattr(v2, field))
        diffs.append({'field': field, 'label': label, 'type': 'url',
                      'v1_val': a, 'v2_val': b, 'changed': a != b})

    # --- M2M attribute fields (AttributeOption — use .name) ---
    attr_fields = [
        ('tags',               'Tags'),
        ('licenses',           'Licenses'),
        ('oses',               'Operating Systems'),
        ('governance',         'Governance'),
        ('project_types',      'Project Types'),
        ('supported_languages','Supported Languages'),
        ('written_in',         'Written In'),
    ]
    for field, label in attr_fields:
        a_set = _m2m_set(getattr(v1, field), 'name')
        b_set = _m2m_set(getattr(v2, field), 'name')
        diffs.append(_set_entry(field, label, a_set, b_set))

    # --- M2M relationship fields (System / Organization — use .name) ---
    rel_fields = [
        ('developer_orgs',  'Developer Orgs'),
        ('derived_from',    'Derived From'),
        ('embedded',        'Embedded Systems'),
        ('inspired_by',     'Inspired By'),
        ('compatible_with', 'Compatible With'),
        ('hosted_services', 'Hosted Services'),
    ]
    for field, label in rel_fields:
        a_set = _m2m_set(getattr(v1, field), 'name')
        b_set = _m2m_set(getattr(v2, field), 'name')
        diffs.append(_set_entry(field, label, a_set, b_set))

    # --- acquisitions ---
    def _acq_tuple(acq):
        return (acq.organization.name, acq.year, acq.citation.url if acq.citation else '')

    v1_acqs = set(_acq_tuple(a) for a in v1.acquisitions.select_related('organization', 'citation').all())
    v2_acqs = set(_acq_tuple(a) for a in v2.acquisitions.select_related('organization', 'citation').all())
    diffs.append({
        'field': 'acquisitions', 'label': 'Acquisitions', 'type': 'acquisitions',
        'v1_val': sorted(v1_acqs), 'v2_val': sorted(v2_acqs),
        'added': sorted(v2_acqs - v1_acqs),
        'removed': sorted(v1_acqs - v2_acqs),
        'unchanged': sorted(v1_acqs & v2_acqs),
        'changed': v1_acqs != v2_acqs,
    })

    # --- SystemFeature rows ---
    def _feature_snapshot(version):
        snap = {}
        for sf in version.features.select_related('feature').prefetch_related('options', 'citations').all():
            snap[sf.feature.label] = {
                'description': sf.description or '',
                'options': sorted(fo.value for fo in sf.options.all()),
                'citations': sorted(c.url for c in sf.citations.all()),
                'system': sf.system.name if sf.system else '',
            }
        return snap

    f1 = _feature_snapshot(v1)
    f2 = _feature_snapshot(v2)
    all_features = sorted(set(f1) | set(f2))
    feature_diffs = []
    for fname in all_features:
        s1 = f1.get(fname, {'description': '', 'options': [], 'citations': [], 'system': ''})
        s2 = f2.get(fname, {'description': '', 'options': [], 'citations': [], 'system': ''})
        changed = s1 != s2
        old_desc_html, new_desc_html = _inline_diff(s1['description'], s2['description']) \
            if s1['description'] != s2['description'] else ('', '')
        cite = _citation_diff(set(s1['citations']), set(s2['citations']))
        feature_diffs.append({
            'name': fname, 'changed': changed,
            'v1': s1, 'v2': s2,
            'v1_desc_html': old_desc_html,
            'v2_desc_html': new_desc_html,
            'options_added': sorted(set(s2['options']) - set(s1['options'])),
            'options_removed': sorted(set(s1['options']) - set(s2['options'])),
            'options_unchanged': sorted(set(s1['options']) & set(s2['options'])),
            'citations': cite,
        })
    diffs.append({
        'field': 'features', 'label': 'Features', 'type': 'features',
        'feature_diffs': feature_diffs,
        'changed': any(fd['changed'] for fd in feature_diffs),
    })

    return diffs


# ==============================================
# SystemVersionDiffView
# ==============================================
class SystemVersionDiffView(View):

    template_name = 'core/system-diff.html'

    def get(self, request, slug, ver1, ver2):
        from django.contrib import messages

        system = get_object_or_404(System, slug=slug)
        try:
            v1 = SystemVersion.objects.get(system=system, ver=ver1)
        except SystemVersion.DoesNotExist:
            messages.error(request, f'{system.name} does not have a version #{ver1}.')
            return redirect('system_revision', slug=slug)
        try:
            v2 = SystemVersion.objects.get(system=system, ver=ver2)
        except SystemVersion.DoesNotExist:
            messages.error(request, f'{system.name} does not have a version #{ver2}.')
            return redirect('system_revision', slug=slug)

        can_approve = (
            request.user.is_authenticated
            and (request.user.is_superuser or request.user.is_staff)
            and not v2.approved
        )
        diffs = _compute_version_diff(v1, v2)

        return render(request, self.template_name, {
            'activate': 'revisions',
            'system': system,
            'v1': v1,
            'v2': v2,
            'diffs': diffs,
            'can_approve': can_approve,
        })

    @method_decorator(login_required)
    def post(self, request, slug, ver1, ver2):
        if not (request.user.is_superuser or request.user.is_staff):
            return HttpResponseForbidden()

        system = get_object_or_404(System, slug=slug)
        v = get_object_or_404(SystemVersion, system=system, ver=ver2)

        if not v.approved:
            with transaction.atomic():
                system.versions.update(is_current=False)
                v.approved = True
                v.is_current = True
                v.save()
                system.ver = v.ver
                system.modified = timezone.now()
                system.save()
                finalize_new_version(v)

        return redirect('system', slug=slug)