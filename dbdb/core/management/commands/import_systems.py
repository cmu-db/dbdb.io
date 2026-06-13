"""
import_systems — bulk-create System + SystemVersion entries from a CSV file.

Usage:
    python manage.py import_systems <csv_file> [options]

CSV format:
  - The first row is always a header row.
  - Column 1 (the first column) is always System.name, regardless of its header label.
  - All other columns are matched by header name to SystemVersion fields:

    URL fields (creates/reuses a CitationUrl):
      system_url, docs_url, sourcerepo_url, wikipedia_url, linkedin_url

    Country field (2-char ISO code):
      countries

    Text fields:
      description, history, twitter_handle

    Integer fields:
      start_year, end_year

    Organization field (name; looked up or created):
      developer_orgs

  Unknown header names are skipped with a warning.

Additional behaviour:
  - Logo files are matched by slug in --logos-dir ({slug}.svg/.png/.jpg/.jpeg).
  - If system_url contains "github.com" and no sourcerepo_url column is present,
    system_url is also used as sourcerepo_url.
  - If sourcerepo_url is set, the "Open Source" project type is added.
"""
import csv
import logging
import os
from argparse import ArgumentParser

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.text import slugify

from django.db.models import Q

from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import AttributeOption, CitationUrl, Organization, System, SystemVersion
from dbdb.core.utils.citations import normalize_url, process_citation_url
from dbdb.core.utils.repositories import GitHubCollector

LOG = logging.getLogger(__name__)
User = get_user_model()

_LOGO_EXTENSIONS   = ('svg', 'png', 'jpg', 'jpeg')
_URL_FIELDS        = frozenset({'system_url', 'docs_url', 'sourcerepo_url', 'wikipedia_url', 'linkedin_url'})
_COUNTRY_FIELDS    = frozenset({'countries'})
_TEXT_FIELDS       = frozenset({'description', 'history', 'twitter_handle'})
_INT_FIELDS        = frozenset({'start_year', 'end_year'})
# Maps SystemVersion field name → the Attribute slug that scopes its options.
_ATTR_OPTION_FIELDS: dict[str, str] = {
    'governance':          'governance',
    'tags':                'tag',
    'project_types':       'project-type',
    'licenses':            'license',
    'oses':                'os',
    'supported_languages': 'programming-language',
    'written_in':          'programming-language',
}
# SystemVersion M2M fields that point to other System objects.
_SYSTEM_M2M_FIELDS  = frozenset({'derived_from', 'embedded', 'inspired_by', 'compatible_with', 'hosted_services'})
_ARRAY_FIELDS       = frozenset({'former_names'})
_ORG_FIELDS         = frozenset({'developer_orgs'})
_KNOWN_FIELDS       = (_URL_FIELDS | _COUNTRY_FIELDS | _TEXT_FIELDS | _INT_FIELDS
                       | _ARRAY_FIELDS | _ORG_FIELDS | frozenset(_ATTR_OPTION_FIELDS) | _SYSTEM_M2M_FIELDS)
_OPEN_SOURCE_SLUG  = 'open-source'
_PROJECT_TYPE_SLUG = 'project-type'
_URL_TRUNC         = 45


def _trunc(s: str, n: int = _URL_TRUNC) -> str:
    return s if len(s) <= n else s[:n - 1] + '…'


def _find_logo(logos_dir: str, slug: str) -> str | None:
    for ext in _LOGO_EXTENSIONS:
        path = os.path.join(logos_dir, f'{slug}.{ext}')
        if os.path.isfile(path):
            return path
    return None


def _resolve_attr_options(attr_slug: str, raw: str) -> tuple[list, list[str]]:
    """Split *raw* by comma and match each token to an AttributeOption by name or slug.

    Returns (matched_options, unmatched_tokens).
    """
    opts, unmatched = [], []
    for token in (t.strip() for t in raw.split(',') if t.strip()):
        opt = AttributeOption.objects.filter(
            attribute__slug=attr_slug,
        ).filter(Q(name__iexact=token) | Q(slug__iexact=token)).first()
        if opt:
            opts.append(opt)
        else:
            unmatched.append(token)
    return opts, unmatched


def _resolve_systems(raw: str) -> list:
    """Split *raw* by comma and match each token to a System by name or slug."""
    systems = []
    for token in (t.strip() for t in raw.split(',') if t.strip()):
        sys = System.objects.filter(Q(name__iexact=token) | Q(slug__iexact=token)).first()
        if sys:
            systems.append(sys)
        else:
            LOG.warning("No System found matching %r", token)
    return systems


def _get_or_create_org(name: str, *, dry_run: bool) -> 'Organization | None':
    """Look up an Organization by name (case-insensitive); create one if not found."""
    org = Organization.objects.filter(name__iexact=name).first()
    if org:
        return org
    slug = slugify(name)
    if not slug:
        LOG.warning("Cannot create Organization with empty slug for name=%r", name)
        return None
    # Resolve slug conflicts by appending a counter.
    base_slug = slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    if dry_run:
        return Organization(name=name, slug=slug)
    return Organization.objects.create(name=name, slug=slug)


def _get_github_start_year(repo_url: str) -> int | None:
    """Clone (or reuse) a GitHub repo and return the year of its first commit."""
    try:
        token = getattr(settings, 'GITHUB_API_TOKEN', None) or None
        collector = GitHubCollector(token=token, delete_on_exit=False)
        collector.clone_url(repo_url, all_branches=True, pull=False)
        ts = collector.get_first_commit_timestamp()
        return ts.year if ts else None
    except Exception:
        LOG.warning("Could not determine start year from %r", repo_url, exc_info=True)
        return None


def _get_or_create_citation(
    url_str: str,
    *,
    dry_run: bool,
    validate: bool = False,
    skip_spamcheck: bool = False,
) -> CitationUrl | None:
    url_str = url_str.strip()
    if not url_str:
        return None
    try:
        norm = normalize_url(url_str)
    except Exception:
        return None
    existing = CitationUrl.objects.filter(url=norm).first()
    if existing:
        return existing
    cite = CitationUrl(url=norm, status=CitationUrl.Status.UNKNOWN)
    if dry_run:
        return cite
    cite.save()
    if validate:
        cite, info = process_citation_url(cite, skip_spamcheck=skip_spamcheck)
        if info is None:
            return cite
        if info['status'] == CitationUrl.Status.VALID:
            cite.save()
            return cite
        LOG.warning("URL unreachable (status=%s): %r", cite.get_status_display(), url_str)
        cite.delete()
        return None
    return cite


def _print_results_table(write, results: list[dict], sv_fields: list[str]):
    fixed_left  = [('name', 'Name'), ('slug', 'Slug')]
    dynamic     = [(f, f) for f in sv_fields]
    fixed_right = [('logo', 'Logo'), ('status', 'Status')]
    columns = fixed_left + dynamic + fixed_right  # [(key, header), ...]

    keys    = [k for k, _ in columns]
    headers = [h for _, h in columns]
    widths  = [len(h) for h in headers]

    for row in results:
        for i, key in enumerate(keys):
            widths[i] = max(widths[i], len(row.get(key, '')))

    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    def fmt(values):
        return '|' + '|'.join(f' {str(v):<{w}} ' for v, w in zip(values, widths)) + '|'

    write(sep)
    write(fmt(headers))
    write(sep)
    for row in results:
        write(fmt([row.get(k, '') for k in keys]))
    write(sep)


def _empty_result(name='(empty)', slug='', status='skipped') -> dict:
    return {'name': name, 'slug': slug, 'logo': '', 'status': status}


class Command(DbdbBaseCommand):
    help = 'Bulk-create System + SystemVersion entries from a header-mapped CSV file'

    def add_arguments(self, parser: ArgumentParser):
        super().add_arguments(parser)
        parser.add_argument('csv_file', metavar='CSV_FILE',
                            help='Path to CSV; first row is a header, first column is always System.name')
        parser.add_argument('--logos-dir', default=None, metavar='DIR',
                            help='Directory to search for logo files named {slug}.{svg,png,jpg,jpeg}')
        parser.add_argument('--dry-run', action='store_true',
                            help='Print what would be created without writing to the database')
        parser.add_argument('--pending', action='store_true',
                            help='Create SystemVersions as unapproved/pending (default: approved, immediately live)')
        parser.add_argument('--skip-errors', action='store_true',
                            help='Print per-row errors and continue instead of stopping')
        parser.add_argument('--creator', default=None, metavar='USERNAME',
                            help='Username to use as SystemVersion creator (default: DBDB_BOT_ACCOUNT setting)')
        parser.add_argument('--validate-urls', action='store_true',
                            help='Fetch each URL via process_citation_url(); drop URLs that are unreachable')
        parser.add_argument('--skip-spamcheck', action='store_true',
                            help='Disable spam checking when validating URLs (used with --validate-urls)')

    def handle(self, *args, **options):
        username = options['creator'] or getattr(settings, 'DBDB_BOT_ACCOUNT', None)
        if username:
            try:
                creator = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"Creator user '{username}' not found")
        else:
            creator = User.objects.filter(is_superuser=True).order_by('id').first()
            if not creator:
                raise CommandError("No creator user found — use --creator or set DBDB_BOT_ACCOUNT")

        csv_path = options['csv_file']
        if not os.path.isfile(csv_path):
            raise CommandError(f"CSV file not found: {csv_path}")

        logos_dir = options['logos_dir']
        if logos_dir and not os.path.isdir(logos_dir):
            raise CommandError(f"Logos directory not found: {logos_dir}")

        open_source_opt = AttributeOption.objects.filter(
            attribute__slug=_PROJECT_TYPE_SLUG,
            slug=_OPEN_SOURCE_SLUG,
        ).first()
        if not open_source_opt:
            LOG.warning("AttributeOption '%s' not found — project_type will not be set", _OPEN_SOURCE_SLUG)

        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be saved.\n"))

        results: list[dict] = []
        sv_fields: list[str] = []  # ordered list of SV field names from CSV headers (columns 1+)

        with open(csv_path, newline='', encoding='utf-8-sig') as fh:
            reader = csv.reader(fh)

            # First row is always the header.
            header_row = next(reader, None)
            if not header_row:
                raise CommandError("CSV file is empty or has no header row")

            # Column 0 is always System.name; columns 1+ map by header name to SV fields.
            raw_headers = [h.strip().lower() for h in header_row]
            sv_fields = raw_headers[1:]

            warned_unknown: set[str] = set()
            for fn in sv_fields:
                if fn and fn not in _KNOWN_FIELDS and fn not in warned_unknown:
                    self.stderr.write(self.style.WARNING(f"Unknown header field '{fn}' — column will be ignored"))
                    warned_unknown.add(fn)

            for row in reader:
                if not any(row):
                    continue

                name = row[0].strip() if row else ''

                # Build field_values: only known, non-empty fields.
                field_values: dict[str, str] = {}
                for i, field_name in enumerate(sv_fields):
                    if not field_name or field_name not in _KNOWN_FIELDS:
                        continue
                    val = row[i + 1].strip() if (i + 1) < len(row) else ''
                    if val:
                        field_values[field_name] = val

                if not name:
                    results.append(_empty_result())
                    continue

                try:
                    result = self._import_one(
                        name=name,
                        field_values=field_values,
                        creator=creator,
                        logos_dir=logos_dir,
                        open_source_opt=open_source_opt,
                        options=options,
                    )
                    results.append(result)
                except Exception as exc:
                    if not options['skip_errors']:
                        raise
                    self.stderr.write(self.style.ERROR(f"Error on '{name}': {exc}"))
                    results.append(_empty_result(name=name, slug=slugify(name), status=f'error: {exc}'))

        imported = sum(1 for r in results if r['status'] in ('imported', 'dry-run'))
        skipped  = len(results) - imported

        # Only show SV fields that are known (unknown were warned about, not stored).
        display_fields = [f for f in sv_fields if f in _KNOWN_FIELDS]

        self.stdout.write('')
        sorted_results = sorted(results, key=lambda r: (r.get('logo', '') == '', r.get('logo', '')))
        _print_results_table(self.stdout.write, sorted_results, display_fields)
        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {imported} imported, {skipped} skipped, {len(results)} total rows"
        ))

    def _import_one(self, *, name, field_values: dict[str, str],
                    creator, logos_dir, open_source_opt, options) -> dict:
        dry_run: bool        = options['dry_run']
        approved: bool       = not options['pending']
        validate: bool       = options['validate_urls']
        skip_spamcheck: bool = options['skip_spamcheck']

        slug = slugify(name)
        if not slug:
            return _empty_result(name=name, status='skipped (no slug)')
        if System.objects.filter(slug=slug).exists():
            return _empty_result(name=name, slug=slug, status='skipped (exists)')

        logo_path = _find_logo(logos_dir, slug) if logos_dir else None

        def _cite(url_str):
            return _get_or_create_citation(url_str, dry_run=dry_run,
                                           validate=validate, skip_spamcheck=skip_spamcheck)

        # Resolve CitationUrl objects for all URL fields.
        cite_map: dict[str, CitationUrl | None] = {
            f: _cite(field_values[f]) for f in _URL_FIELDS if f in field_values
        }

        # If system_url is a GitHub URL and no sourcerepo_url column exists, reuse it.
        system_url_str = field_values.get('system_url', '')
        if 'github.com' in system_url_str.lower() and 'sourcerepo_url' not in cite_map:
            cite_map['sourcerepo_url'] = cite_map.get('system_url')

        # If start_year is absent and the source repo is on GitHub, infer it from
        # the first commit in the cloned repository.
        if 'start_year' not in field_values:
            sourcerepo_cite = cite_map.get('sourcerepo_url')
            sourcerepo_url_str = sourcerepo_cite.url if sourcerepo_cite else ''
            if 'github.com' in sourcerepo_url_str.lower():
                year = _get_github_start_year(sourcerepo_url_str)
                if year:
                    field_values = {**field_values, 'start_year': str(year)}
                    self.stdout.write(f"  [{name}] inferred start_year={year} from first commit")

        # Resolve AttributeOption M2M fields — done before the dry-run return so that
        # match errors are always surfaced and the result table shows resolved values.
        attr_opts: dict[str, list] = {}
        for field, attr_slug in _ATTR_OPTION_FIELDS.items():
            if field in field_values:
                opts, unmatched = _resolve_attr_options(attr_slug, field_values[field])
                for token in unmatched:
                    self.stderr.write(self.style.ERROR(
                        f"[{name}] '{field}': no AttributeOption match for {token!r}"
                    ))
                attr_opts[field] = opts

        # Resolve System M2M fields.
        system_m2m: dict[str, list] = {}
        for field in _SYSTEM_M2M_FIELDS:
            if field in field_values:
                system_m2m[field] = _resolve_systems(field_values[field])

        # Resolve developer_orgs.
        dev_org = None
        if 'developer_orgs' in field_values:
            dev_org = _get_or_create_org(field_values['developer_orgs'], dry_run=dry_run)

        # Build the result record.
        result: dict = {'name': name, 'slug': slug,
                        'logo': os.path.basename(logo_path) if logo_path else '',
                        'status': 'dry-run' if dry_run else 'imported'}
        for f in _URL_FIELDS:
            cite = cite_map.get(f)
            result[f] = _trunc(cite.url if cite else '')
        for f in _COUNTRY_FIELDS | _TEXT_FIELDS | _INT_FIELDS:
            result[f] = field_values.get(f, '')
        result['developer_orgs'] = dev_org.name if dev_org else field_values.get('developer_orgs', '')
        for field, opts in attr_opts.items():
            result[field] = ', '.join(o.name for o in opts)
        for field, systems in system_m2m.items():
            result[field] = ', '.join(s.name for s in systems)

        if dry_run:
            return result

        with transaction.atomic():
            system = System.objects.create(name=name, slug=slug)

            sv = SystemVersion(
                system=system,
                creator=creator,
                approved=approved,
                comment=f'Imported via import_systems command',
                **{f: cite_map[f] for f in _URL_FIELDS if f in cite_map},
            )

            # countries: accept a single 2-char code.
            country_code = field_values.get('countries', '').strip().upper()
            if country_code:
                sv.countries = [country_code]

            # Text and integer fields.
            for f in _TEXT_FIELDS:
                if f in field_values:
                    setattr(sv, f, field_values[f])
            for f in _ARRAY_FIELDS:
                if f in field_values:
                    setattr(sv, f, [v.strip() for v in field_values[f].split(',') if v.strip()])
            for f in _INT_FIELDS:
                if f in field_values:
                    try:
                        setattr(sv, f, int(field_values[f]))
                    except ValueError:
                        LOG.warning("Non-integer value for %s: %r", f, field_values[f])

            if logo_path:
                with open(logo_path, 'rb') as fh:
                    sv.logo = File(fh, name=os.path.basename(logo_path))
                    sv.save()
            else:
                sv.save()

            # AttributeOption M2M fields.
            for field, opts in attr_opts.items():
                if opts:
                    getattr(sv, field).set(opts)

            # System M2M fields.
            for field, systems in system_m2m.items():
                if systems:
                    getattr(sv, field).set(systems)

            # developer_orgs.
            if dev_org:
                sv.developer_orgs.set([dev_org])

            # Always add "Open Source" if a source repo is present.
            if sv.sourcerepo_url and open_source_opt:
                sv.project_types.add(open_source_opt)

        return result
