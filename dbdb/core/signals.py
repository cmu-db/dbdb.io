import logging

from dbdb.core.models import Organization, OrgType

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


def _org_capture_logo(sender, instance, **kwargs):
    """Store the current DB logo value on the instance before save."""
    if instance.pk:
        instance._original_logo = (
            Organization.objects.filter(pk=instance.pk)
            .values_list('logo', flat=True)
            .first()
        )
    else:
        instance._original_logo = None


def _org_regen_card_on_logo_change(sender, instance, created, **kwargs):
    """Regenerate twitter card if the logo field changed."""
    original = getattr(instance, '_original_logo', None)
    current = instance.logo.name if instance.logo else None
    if current and original != current:
        from dbdb.core.utils.twitter_card import create_twitter_card
        try:
            create_twitter_card(instance)
        except Exception:
            LOG.exception('Failed to regenerate twitter card for Organization pk=%s', instance.pk)


def developer_orgs_changed(sender, instance, action, **kwargs):
    if action not in ('post_add', 'post_set'):
        return
    if not instance.project_types.filter(attribute__slug='project-type', slug='hobby').exists():
        return
    orgs = list(instance.developer_orgs.all())
    if len(orgs) != 1:
        return
    maybe_mark_individual(orgs[0])
