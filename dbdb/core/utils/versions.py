from __future__ import annotations

import copy
import io

from dbdb.core.models import SystemVersion, SystemVersionCodingAgent
from dbdb.core.utils.searchtext import generate_searchtext
from dbdb.core.utils.twitter_card import create_twitter_card

# ── Citation M2M fields that live directly on SystemVersion ──────────────────
_VERSION_CITATION_M2M = (
    'description_citations',
    'start_year_citations',
    'end_year_citations',
    'history_citations',
)


def _collect_version_deletions(version):
    """
    Inspect *version* and return a plan dict describing every object that
    would be removed if this SystemVersion were deleted.  Does not touch
    the database.

    Returns:
        {
            'version':          SystemVersion,
            'features':         [SystemFeature, ...],
            'acquisitions':     [Acquisition, ...],
            'orphan_citations': [CitationUrl, ...],   # safe to delete after version is gone
            'orphan_orgs':      [Organization, ...],  # safe to delete after version is gone
            'next_version':     SystemVersion | None, # will become is_current
        }
    """
    from dbdb.core.models import (
        Acquisition, CitationUrl, Organization, SystemFeature, SystemVersion,
    )

    features     = list(version.features
                         .select_related('feature')
                         .prefetch_related('citations')
                         .all())
    acquisitions = list(version.acquisitions
                         .select_related('organization', 'citation')
                         .all())

    # ── Gather all CitationUrl PKs referenced by this version ────────────────
    all_cite_ids: set[int] = set()
    for fk in ('system_url_id', 'docs_url_id', 'sourcerepo_url_id', 'wikipedia_url_id'):
        val = getattr(version, fk)
        if val is not None:
            all_cite_ids.add(val)
    for attr in _VERSION_CITATION_M2M:
        all_cite_ids |= set(getattr(version, attr).values_list('pk', flat=True))
    for sf in features:
        all_cite_ids |= set(sf.citations.values_list('pk', flat=True))
    for acq in acquisitions:
        if acq.citation_id is not None:
            all_cite_ids.add(acq.citation_id)

    # ── Gather all Organization PKs referenced by this version ───────────────
    all_org_ids: set[int] = set(version.developer_orgs.values_list('pk', flat=True))
    for acq in acquisitions:
        all_org_ids.add(acq.organization_id)

    # ── Determine which citations are used by OTHER objects ──────────────────
    sf_pks  = [sf.pk  for sf  in features]
    acq_pks = [acq.pk for acq in acquisitions]

    still_cite: set[int] = set()
    if all_cite_ids:
        # FK fields on other SystemVersions
        for fk in ('system_url_id', 'docs_url_id', 'sourcerepo_url_id', 'wikipedia_url_id'):
            still_cite |= set(
                SystemVersion.objects
                .exclude(pk=version.pk)
                .filter(**{f'{fk}__in': all_cite_ids})
                .values_list(fk, flat=True)
            )
        # M2M through tables on other SystemVersions
        for attr in _VERSION_CITATION_M2M:
            Through = getattr(SystemVersion, attr).through
            still_cite |= set(
                Through.objects
                .exclude(systemversion_id=version.pk)
                .filter(citationurl_id__in=all_cite_ids)
                .values_list('citationurl_id', flat=True)
            )
        # SystemFeature.citations on features NOT owned by this version
        Through = SystemFeature.citations.through
        q = Through.objects.filter(citationurl_id__in=all_cite_ids)
        if sf_pks:
            q = q.exclude(systemfeature_id__in=sf_pks)
        still_cite |= set(q.values_list('citationurl_id', flat=True))
        # Acquisition.citation on acquisitions NOT owned by this version
        q = Acquisition.objects.filter(
            citation_id__in=all_cite_ids, citation_id__isnull=False
        )
        if acq_pks:
            q = q.exclude(pk__in=acq_pks)
        still_cite |= set(q.values_list('citation_id', flat=True))

    orphan_cite_ids = all_cite_ids - still_cite

    # ── Determine which Organizations are used by OTHER objects ──────────────
    still_org: set[int] = set()
    if all_org_ids:
        Through = SystemVersion.developer_orgs.through
        still_org |= set(
            Through.objects
            .exclude(systemversion_id=version.pk)
            .filter(organization_id__in=all_org_ids)
            .values_list('organization_id', flat=True)
        )
        q = Acquisition.objects.filter(organization_id__in=all_org_ids)
        if acq_pks:
            q = q.exclude(pk__in=acq_pks)
        still_org |= set(q.values_list('organization_id', flat=True))

    orphan_org_ids = all_org_ids - still_org

    # ── Next version to promote ───────────────────────────────────────────────
    next_version = (
        SystemVersion.objects
        .filter(system=version.system)
        .exclude(pk=version.pk)
        .order_by('-ver')
        .first()
    )

    return {
        'version':          version,
        'features':         features,
        'acquisitions':     acquisitions,
        'orphan_citations': list(CitationUrl.objects.filter(pk__in=orphan_cite_ids)),
        'orphan_orgs':      list(Organization.objects.filter(pk__in=orphan_org_ids)),
        'next_version':     next_version,
    }


def delete_latest_version(system, *, dry_run: bool = False, out=None) -> None:
    """
    Delete the most recent SystemVersion for *system*, clean up exclusively
    owned shared objects, and promote the next newest version as current.

    Args:
        system:   System instance.
        dry_run:  If True, print what would happen without modifying the DB.
        out:      File-like object for output (defaults to stdout).
    """
    from dbdb.core.models import CitationUrl, Organization, SystemVersion
    from django.db import transaction

    if out is None:
        import sys
        out = sys.stdout

    prefix = '[DRY RUN] ' if dry_run else ''

    def log(msg: str) -> None:
        out.write(prefix + msg + '\n')

    # ── Validate ──────────────────────────────────────────────────────────────
    total = SystemVersion.objects.filter(system=system).count()
    if total == 0:
        out.write(f'No versions found for {system.name}.\n')
        return
    if total == 1:
        out.write(
            f'Cannot delete: {system.name} v{system.ver} is the only version.\n'
        )
        return

    target = (
        SystemVersion.objects
        .filter(system=system)
        .order_by('-ver')
        .first()
    )

    out.write(
        f"{'[DRY RUN] ' if dry_run else ''}Target: {system.name} v{target.ver} "
        f"(approved={'yes' if target.approved else 'no'}, "
        f"is_current={'yes' if target.is_current else 'no'})\n"
    )

    # ── Collect plan ──────────────────────────────────────────────────────────
    plan = _collect_version_deletions(target)

    log(f'Delete  SystemVersion : {target}')
    for sf in plan['features']:
        log(f'Delete  SystemFeature  : {sf}')
    for acq in plan['acquisitions']:
        log(f'Delete  Acquisition    : {acq}')
    for cite in sorted(plan['orphan_citations'], key=lambda c: c.url):
        log(f'Delete  CitationUrl    : {cite}')
    for org in sorted(plan['orphan_orgs'], key=lambda o: o.name):
        log(f'Delete  Organization   : {org}')
    if plan['next_version']:
        nv = plan['next_version']
        log(f'Promote SystemVersion  : {nv} → is_current=True, system.ver={nv.ver}')
    else:
        out.write('WARNING: no remaining version to promote.\n')

    if dry_run:
        return

    # ── Execute ───────────────────────────────────────────────────────────────
    with transaction.atomic():
        # Delete the version; CASCADE removes SystemFeature + Acquisition rows.
        target.delete()

        # Remove exclusively owned CitationUrls.
        if plan['orphan_citations']:
            CitationUrl.objects.filter(
                pk__in=[c.pk for c in plan['orphan_citations']]
            ).delete()

        # Remove exclusively owned Organizations.
        if plan['orphan_orgs']:
            Organization.objects.filter(
                pk__in=[o.pk for o in plan['orphan_orgs']]
            ).delete()

        # Promote next version.
        if plan['next_version']:
            nv = plan['next_version']
            SystemVersion.objects.filter(system=system).update(is_current=False)
            nv.is_current = True
            nv.save(update_fields=['is_current'])
            system.ver = nv.ver
            system.save(update_fields=['ver', 'modified'])


_VERSION_M2M = (
    'description_citations',
    'start_year_citations',
    'end_year_citations',
    'history_citations',
    'developer_orgs',
    'derived_from',
    'embedded',
    'inspired_by',
    'compatible_with',
    'hosted_services',
    'governance',
    'tags',
    'project_types',
    'licenses',
    'oses',
    'supported_languages',
    'written_in',
)


def is_spotlight_eligible(version) -> bool:
    """
    Return True if the SystemVersion is complete enough to be featured as the
    weekly spotlight system on the homepage.

    Checks (all must pass):
    1. Basic fields: logo, system_url, docs_url, start_year, description, history
    2. Core AttributeOption M2M fields: developer_orgs, tags, licenses, project_types
    3. Every Feature in the database has a SystemFeature for this version with at
       least one FeatureOption (or an inherited system) and at least one citation.
    """
    from dbdb.core.models import Feature

    # 1. Basic scalar / FK fields
    if not version.logo:
        return False
    if not version.system_url_id:
        return False
    if not version.docs_url_id:
        return False
    if version.start_year is None:
        return False
    if not (version.description and version.description.strip()):
        return False
    if not (version.history and version.history.strip()):
        return False

    # 2. Required M2M fields
    if not version.developer_orgs.exists():
        return False
    if not version.tags.exists():
        return False
    if not version.licenses.exists():
        return False
    if not version.project_types.exists():
        return False

    # 3. At least 50% of Features must have a SystemFeature with options/system + citation
    total_features = Feature.objects.count()
    if total_features == 0:
        return True
    sf_map = {
        sf.feature_id: sf
        for sf in version.features.prefetch_related('options', 'citations').all()
    }
    complete = 0
    for sf in sf_map.values():
        options   = list(sf.options.all())    # consumes prefetch cache
        citations = list(sf.citations.all())  # consumes prefetch cache
        if (options or sf.system_id is not None) and citations and sf.description.strip():
            complete += 1
    if complete < total_features / 2:
        return False

    return True


def finalize_new_version(new_version, *, old_logo=None) -> None:
    """
    Run post-save side effects that must execute after any new SystemVersion
    is saved — regardless of whether it was created from a form or by cloning.

    - Regenerates the twitter card if the logo changed.
    - Updates the SystemSearchText index for the system.
    - Recomputes System.spotlight_enabled based on version completeness.
    """
    from dbdb.core.models import SystemSearchText

    if new_version.logo is not None and old_logo != new_version.logo:
        create_twitter_card(new_version)

    ver_search, _ = SystemSearchText.objects.update_or_create(system=new_version.system)
    ver_search.search_text = generate_searchtext(new_version)
    ver_search.save()

    eligible = is_spotlight_eligible(new_version)
    system = new_version.system
    if system.spotlight_eligible != eligible:
        system.spotlight_eligible = eligible
        system.save(update_fields=['spotlight_eligible'])


def clone_system_version(
    current_version: SystemVersion, *, creator=None, username=None, comment,
    approved: bool = True,
    attribute_options=None, feature_options=None,
    **field_overrides,
) -> SystemVersion:
    """
    Clone a SystemVersion, apply scalar overrides, save it, and copy all
    related data (M2M fields, SystemFeature rows, Acquisition rows).

    The pre_save signal on SystemVersion handles ver numbering and flipping
    is_current automatically.

    creator:   User instance to record as the version creator.
    username:  Username string alternative to creator.  If creator is None,
               the user is resolved by username; if both are None the first
               superuser is used.
    approved:  True (default) makes the clone the live version immediately.
               False creates a pending version awaiting approval.

    attribute_options: optional list of AttributeOption instances to add to the
    new version.  Each option's Attribute.sv_field must be set to the
    SystemVersion M2M field name (e.g. 'tags', 'licenses').

    feature_options: optional list of FeatureOption instances to add to the
    new version.  The corresponding SystemFeature row is located by feature;
    if none exists one is created.

    Does NOT call finalize_new_version — the caller is responsible for any
    additional M2M changes (e.g. adding tags) and then calling finalize.

    Returns the new, saved SystemVersion instance.
    """
    from django.contrib.auth import get_user_model
    from dbdb.core.models import Acquisition, SystemFeature

    if creator is None:
        User = get_user_model()
        if username:
            creator = User.objects.get(username=username)
        else:
            creator = User.objects.filter(is_superuser=True).order_by('pk').first()
            if creator is None:
                raise ValueError('No creator specified and no superuser found.')

    new_version = copy.copy(current_version)
    new_version.pk = None
    new_version.id = None
    new_version.creator = creator
    new_version.comment = comment
    new_version.approved = approved
    for field, value in field_overrides.items():
        setattr(new_version, field, value)

    new_version.save()

    # Copy all M2M relationships from the previous version
    for field_name in _VERSION_M2M:
        getattr(new_version, field_name).set(
            getattr(current_version, field_name).all()
        )

    # Clone SystemFeature rows (each has options + citations M2M)
    for sf in (
        current_version.features
        .select_related('feature')
        .prefetch_related('options', 'citations')
    ):
        sf_options = list(sf.options.all())
        sf_citations = list(sf.citations.all())
        sf.pk = None
        sf.id = None
        sf.version = new_version
        sf.save()
        # After reassigning pk via save(), the prefetch cache is stale: it
        # was populated for the old pk, so set() would treat the old entries
        # as "already present" and skip all inserts for the new row.
        sf._prefetched_objects_cache = {}
        sf.options.set(sf_options)
        sf.citations.set(sf_citations)

    # Clone Acquisition rows (no M2M, just FK)
    for acq in current_version.acquisitions.select_related('organization', 'citation'):
        acq.pk = None
        acq.id = None
        acq.version = new_version
        acq.save()

    # Clone CodingAgent entries (through model, can't use .set())
    for entry in current_version.coding_agent_entries.select_related('agent', 'citation').all():
        SystemVersionCodingAgent.objects.create(
            system_version=new_version,
            agent=entry.agent,
            citation=entry.citation,
        )

    # Add any extra AttributeOptions requested by the caller
    if attribute_options:
        for option in attribute_options:
            sv_field = option.attribute.sv_field
            if sv_field:
                getattr(new_version, sv_field).add(option)

    # Add any extra FeatureOptions requested by the caller
    if feature_options:
        for fo in feature_options:
            sf, _ = SystemFeature.objects.get_or_create(
                version=new_version,
                feature=fo.feature,
            )
            sf.options.add(fo)

    return new_version
