import logging
import re

from django.core.management import BaseCommand
from django.utils.text import slugify

from dbdb.core.models import Organization, SystemVersion

LOG = logging.getLogger(__name__)

# Tokens that indicate a company-name suffix rather than a list separator.
_COMPANY_SUFFIXES = frozenset({
    'LLC', 'L.L.C.', 'Inc', 'Inc.', 'Ltd', 'Ltd.', 'Limited',
    'Corp', 'Corp.', 'Corporation', 'Co', 'Co.', 'Company',
    'GmbH', 'AG', 'SA', 'S.A.', 'PLC', 'plc',
    'LP', 'L.P.', 'LLP', 'L.L.P.',
})

_SKIP_URLS = frozenset(map(str.lower, [
    'Codernity.com',
    'Crate.io',
    'JSONbin.io',
    'JD.com',
    'Visual Objects.Net',
    'Wakanda.io',
    'ZippyDB.com'
]))

# Matches strings that look like URLs rather than organization names.
_URL_RE = re.compile(
    r'^(https?://|www\.)|://|\.(com|org|net|io|edu|gov|co|uk|de|fr|info|biz)\b',
    re.IGNORECASE,
)


def _looks_like_url(name):
    # Special Case: Company names as URLs
    if name.lower() in _SKIP_URLS:
        return False
    return bool(_URL_RE.search(name))


def _extract_names(value):
    """Split a free-text field into individual organization names.

    Commas that precede a known company suffix (e.g. ', Inc.', ', LLC') are
    treated as part of the name rather than list separators.  When no commas
    are present the string is split on ' and '.
    """
    if ',' not in value:
        return [n.strip() for n in value.split(' and ') if n.strip()]

    parts = [p.strip() for p in value.split(',')]
    names = []
    for part in parts:
        if part in _COMPANY_SUFFIXES and names:
            names[-1] = f"{names[-1]}, {part}"
        else:
            names.append(part)
    return [n for n in names if n]


def _canonical_name(name):
    """Strip a trailing company suffix to produce a deduplicated canonical name.

    "ApolloDB, Inc." and "ApolloDB" both become "ApolloDB".
    Suffixes are tried longest-first so "L.L.C." is matched before "LLC".
    """
    for suffix in sorted(_COMPANY_SUFFIXES, key=len, reverse=True):
        for sep in (', ', ' '):
            tail = sep + suffix
            if name.endswith(tail):
                return name[: -len(tail)].strip()
    return name


def _get_or_create_org(name):
    canonical = _canonical_name(name)
    slug = slugify(canonical) or slugify(canonical.encode('ascii', 'ignore').decode())
    if not slug:
        return None
    if len(slug) > 50: slug = slug[:50]

    # 1. Exact canonical-name match.
    org = Organization.objects.filter(name=canonical).first()
    if org:
        return org

    # 2. Slug match — catches names that differ only in punctuation/spacing.
    org = Organization.objects.filter(slug=slug).first()
    if org:
        LOG.info(f"Matched '{name}' → existing '{org.name}' via slug '{slug}'")
        return org

    # 3. Nothing found — create using the canonical name.
    org = Organization(name=canonical, slug=slug)
    org.save()
    LOG.info(f"Created Organization: {org}")
    return org


def _process_field(ver, field_value, field_name):
    """Return list of Organization instances parsed from field_value, printing errors."""
    orgs = []
    for name in _extract_names(field_value):
        if _looks_like_url(name):
            print(f"SKIP (URL): {ver} | {field_name}={name!r}")
            continue
        try:
            org = _get_or_create_org(name)
        except Exception as exc:
            print(f"ERROR: {ver} | {field_name}={name!r} → {exc}")
            raise
        if org:
            orgs.append(org)
    return orgs

class Command(BaseCommand):
    help = "Populate Organization records from SystemVersion.developer and acquired_by text fields"

    def add_arguments(self, parser):
        parser.add_argument(
            'system', metavar='S', type=str, nargs='?',
            help='Limit to a specific system name or ID',
        )

    def handle(self, *args, **options):
        versions = SystemVersion.objects.select_related('system').order_by('system__name', 'ver')
        if options.get('system'):
            keyword = options['system']
            if keyword.isdigit():
                versions = versions.filter(system__id=int(keyword))
            else:
                versions = versions.filter(system__name__icontains=keyword)

        created_total = 0
        linked_total = 0

        for ver in versions:
            if ver.developer:
                orgs = _process_field(ver, ver.developer, 'developer')
                if orgs:
                    ver.developer_orgs.set(orgs)
                    created_total += len(orgs)
                    linked_total += len(orgs)

            if ver.acquired_by:
                orgs = _process_field(ver, ver.acquired_by, 'acquired_by')
                created_total += len(orgs)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Processed {versions.count()} versions, "
            f"created/found {created_total} organizations, "
            f"linked {linked_total} developer org relationships."
        ))