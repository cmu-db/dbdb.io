import logging

from dbdb.core.models import OrgType

LOG = logging.getLogger(__name__)

COMPANY_SUFFIXES = frozenset({
    'inc', 'llc', 'ltd', 'corp', 'gmbh', 'ag', 'sa', 'bv', 'plc', 'co', 'lp',
    'group', 'lab', 'labs', 'technology', 'technologies',
})


def _is_individual_name(name: str) -> bool:
    words = name.strip().split()
    if len(words) != 2:
        return False
    return words[-1].lower().rstrip('.') not in COMPANY_SUFFIXES


def maybe_mark_individual(org) -> bool:
    """Set org_type to Individual if the org looks like a person's name. Returns True if updated."""
    if org.org_type is not None:
        return False
    if not _is_individual_name(org.name):
        return False
    org.org_type = OrgType.INDIVIDUAL
    org.save(update_fields=['org_type'])
    LOG.info(f"Marked '{org.name}' as Individual")
    return True


def developer_orgs_changed(sender, instance, action, **kwargs):
    if action not in ('post_add', 'post_set'):
        return
    if not instance.project_types.filter(attribute__slug='project-type', slug='hobby').exists():
        return
    orgs = list(instance.developer_orgs.all())
    if len(orgs) != 1:
        return
    maybe_mark_individual(orgs[0])
