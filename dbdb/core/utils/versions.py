from __future__ import annotations

import copy

from dbdb.core.utils.searchtext import generate_searchtext
from dbdb.core.utils.twitter_card import create_twitter_card


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


def finalize_new_version(new_version, *, old_logo=None) -> None:
    """
    Run post-save side effects that must execute after any new SystemVersion
    is saved — regardless of whether it was created from a form or by cloning.

    - Regenerates the twitter card if the logo changed.
    - Updates the SystemSearchText index for the system.
    """
    from dbdb.core.models import SystemSearchText

    if new_version.logo is not None and old_logo != new_version.logo:
        create_twitter_card(new_version)

    ver_search, _ = SystemSearchText.objects.update_or_create(system=new_version.system)
    ver_search.search_text = generate_searchtext(new_version)
    ver_search.save()


def clone_system_version(current_version, *, creator, comment, **field_overrides):
    """
    Clone a SystemVersion, apply scalar overrides, save it, and copy all
    related data (M2M fields, SystemFeature rows, Acquisition rows).

    The pre_save signal on SystemVersion handles ver numbering and flipping
    is_current automatically.

    Does NOT call finalize_new_version — the caller is responsible for any
    additional M2M changes (e.g. adding tags) and then calling finalize.

    Returns the new, saved SystemVersion instance.
    """
    from dbdb.core.models import Acquisition, SystemFeature

    new_version = copy.copy(current_version)
    new_version.pk = None
    new_version.id = None
    new_version.creator = creator
    new_version.comment = comment
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
        sf.options.set(sf_options)
        sf.citations.set(sf_citations)

    # Clone Acquisition rows (no M2M, just FK)
    for acq in current_version.acquisitions.select_related('organization', 'citation'):
        acq.pk = None
        acq.id = None
        acq.version = new_version
        acq.save()

    return new_version
