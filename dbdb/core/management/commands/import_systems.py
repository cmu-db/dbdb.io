"""
import_systems — bulk-create System + SystemVersion entries from a CSV file.

Usage:
    python manage.py import_systems <csv_file> [options]

CSV columns (positional, header row skipped by default):
  1. System Name
  2. System URL
  3. Source Repository URL

For each row the command:
  1. Derives a slug from the name and skips the row if a System with that slug exists.
  2. Optionally finds a logo in --logos-dir by matching {slug}.svg / .png / .jpg / .jpeg.
  3. Creates CitationUrl rows for non-empty URLs (reuses existing ones).
     With --validate-urls each URL is fetched; unreachable URLs are dropped.
  4. Any URL from wikipedia.org is routed to SystemVersion.wikipedia_url.
  5. Creates a System + SystemVersion (approved=True by default, making it live immediately).
     If a logo was found, it is attached before save so LogoMixin auto-extracts dimensions/color.
  6. If the source repository URL is set (and reachable when --validate-urls), the
     "Open Source" project type is added to the SystemVersion.
  7. Prints a formatted summary table at the end.
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

from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import AttributeOption, CitationUrl, System, SystemVersion
from dbdb.core.utils.citations import normalize_url, process_citation_url

LOG = logging.getLogger(__name__)
User = get_user_model()

_LOGO_EXTENSIONS = ('svg', 'png', 'jpg', 'jpeg')
_OPEN_SOURCE_ATTR_SLUG = 'open-source'
_PROJECT_TYPE_ATTR_SLUG = 'project-type'
_URL_TRUNC = 45


def _trunc(s: str, n: int = _URL_TRUNC) -> str:
    return s if len(s) <= n else s[:n - 1] + '…'


def _find_logo(logos_dir: str, slug: str) -> str | None:
    for ext in _LOGO_EXTENSIONS:
        path = os.path.join(logos_dir, f'{slug}.{ext}')
        if os.path.isfile(path):
            return path
    return None


def _is_wikipedia_url(url: str) -> bool:
    return 'wikipedia.org' in url.lower()


def _get_or_create_citation(
    url_str: str,
    *,
    dry_run: bool,
    validate: bool = False,
    system=None,
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
        return cite  # unsaved placeholder

    cite.save()

    if validate:
        cite, info = process_citation_url(cite, system=system, skip_spamcheck=skip_spamcheck)
        if info is None:
            return cite  # merged into an existing CitationUrl
        if info['status'] == CitationUrl.Status.VALID:
            cite.save()
            return cite
        LOG.warning(f"  URL unreachable (status={cite.get_status_display()}): {url_str!r}")
        cite.delete()
        return None

    return cite


def _print_results_table(write, results: list[dict]):
    headers = ['Name', 'Slug', 'System URL', 'Repo URL', 'Wikipedia URL', 'Logo', 'Status']
    keys    = ['name', 'slug', 'system_url', 'sourcerepo_url', 'wikipedia_url', 'logo', 'status']

    widths = [len(h) for h in headers]
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


class Command(DbdbBaseCommand):
    help = 'Bulk-create System + SystemVersion entries from a CSV file'

    def add_arguments(self, parser: ArgumentParser):
        super().add_arguments(parser)
        parser.add_argument('csv_file', metavar='CSV_FILE',
                            help='Path to CSV file (columns: Name, System URL, Source Repo URL)')
        parser.add_argument('--logos-dir', default=None, metavar='DIR',
                            help='Directory to search for logo files named {slug}.{svg,png,jpg,jpeg}')
        parser.add_argument('--dry-run', action='store_true',
                            help='Print what would be created without writing to the database')
        parser.add_argument('--pending', action='store_true',
                            help='Create SystemVersions as unapproved/pending (default: approved, immediately live)')
        parser.add_argument('--no-header', action='store_true',
                            help='Treat the first CSV row as data (default: skip header row)')
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
            attribute__slug=_PROJECT_TYPE_ATTR_SLUG,
            slug=_OPEN_SOURCE_ATTR_SLUG,
        ).first()
        if not open_source_opt:
            LOG.warning(f"AttributeOption '{_OPEN_SOURCE_ATTR_SLUG}' not found — "
                        "project_type will not be set automatically")

        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be saved.\n"))

        results: list[dict] = []

        with open(csv_path, newline='', encoding='utf-8-sig') as fh:
            reader = csv.reader(fh)
            if not options['no_header']:
                next(reader, None)

            for row in reader:
                if not any(row):
                    continue
                name = row[0].strip() if len(row) > 0 else ''
                system_url_str = row[1].strip() if len(row) > 1 else ''
                sourcerepo_url_str = row[2].strip() if len(row) > 2 else ''

                if not name:
                    results.append({'name': '(empty)', 'slug': '', 'system_url': '',
                                    'sourcerepo_url': '', 'wikipedia_url': '', 'logo': '',
                                    'status': 'skipped'})
                    continue

                try:
                    result = self._import_one(
                        name=name,
                        system_url_str=system_url_str,
                        sourcerepo_url_str=sourcerepo_url_str,
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
                    results.append({'name': name, 'slug': slugify(name), 'system_url': '',
                                    'sourcerepo_url': '', 'wikipedia_url': '', 'logo': '',
                                    'status': f'error: {exc}'})

        imported = sum(1 for r in results if r['status'] == 'imported')
        skipped  = sum(1 for r in results if r['status'] != 'imported')

        self.stdout.write('')
        _print_results_table(self.stdout.write, results)
        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {imported} imported, {skipped} skipped, {len(results)} total rows"
        ))

    def _import_one(self, *, name, system_url_str, sourcerepo_url_str,
                    creator, logos_dir, open_source_opt, options) -> dict:
        dry_run: bool      = options['dry_run']
        approved: bool     = not options['pending']
        validate: bool     = options['validate_urls']
        skip_spamcheck: bool = options['skip_spamcheck']

        slug = slugify(name)
        if not slug:
            return {'name': name, 'slug': '', 'system_url': '', 'sourcerepo_url': '',
                    'wikipedia_url': '', 'logo': '', 'status': 'skipped (no slug)'}

        if System.objects.filter(slug=slug).exists():
            return {'name': name, 'slug': slug, 'system_url': '', 'sourcerepo_url': '',
                    'wikipedia_url': '', 'logo': '', 'status': 'skipped (exists)'}

        logo_path = _find_logo(logos_dir, slug) if logos_dir else None

        # Route Wikipedia URLs to wikipedia_url regardless of source column.
        raw_urls = {'system_url': system_url_str, 'sourcerepo_url': sourcerepo_url_str}
        field_map: dict[str, str] = {}
        wikipedia_url_str = ''
        for field, url in raw_urls.items():
            if not url:
                continue
            if _is_wikipedia_url(url):
                if wikipedia_url_str:
                    self.stderr.write(self.style.WARNING(
                        f"  '{name}': multiple Wikipedia URLs; using first, ignoring {url!r}"
                    ))
                else:
                    wikipedia_url_str = url
            else:
                field_map[field] = url

        def _cite(url_str):
            return _get_or_create_citation(
                url_str, dry_run=dry_run,
                validate=validate, skip_spamcheck=skip_spamcheck,
            )

        system_cite     = _cite(field_map.get('system_url', ''))
        sourcerepo_cite = _cite(field_map.get('sourcerepo_url', ''))
        wikipedia_cite  = _cite(wikipedia_url_str)

        # Build the result record using resolved URLs (dropped if validation failed).
        result = {
            'name':           name,
            'slug':           slug,
            'system_url':     _trunc(system_cite.url if system_cite else ''),
            'sourcerepo_url': _trunc(sourcerepo_cite.url if sourcerepo_cite else ''),
            'wikipedia_url':  _trunc(wikipedia_cite.url if wikipedia_cite else ''),
            'logo':           os.path.basename(logo_path) if logo_path else '',
            'status':         'dry-run' if dry_run else 'imported',
        }

        if dry_run:
            return result

        with transaction.atomic():
            system = System.objects.create(name=name, slug=slug)

            sv = SystemVersion(
                system=system,
                creator=creator,
                approved=approved,
                comment='Imported via import_systems command',
                system_url=system_cite,
                sourcerepo_url=sourcerepo_cite,
                wikipedia_url=wikipedia_cite,
            )

            if logo_path:
                with open(logo_path, 'rb') as f:
                    sv.logo = File(f, name=os.path.basename(logo_path))
                    sv.save()
            else:
                sv.save()

            if sv.sourcerepo_url and open_source_opt:
                sv.project_types.add(open_source_opt)

        return result
