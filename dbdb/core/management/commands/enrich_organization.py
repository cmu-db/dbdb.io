"""
enrich_organization — fill missing Organization fields using an LLM.

Usage:
    python manage.py enrich_organization <slug_or_name> [options]

For each empty field on the Organization, the command:
  1. Optionally crawls the org's known URLs (--include-urls)
  2. Builds a prompt via BaseEnricher.build_org_prompt
  3. Calls the LLM with the ORG_ENRICHMENT_TOOL schema (save_org_enrichment)
  4. Validates LLM-suggested citations
  5. Saves directly to the Organization row (no versioning / pending flow)
"""
import logging
import re
import time
from argparse import ArgumentParser
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.core.management.base import CommandError
from django.db import models
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django_countries.fields import CountryField

from dbdb.core.management.base import EnricherBaseCommand
from dbdb.core.models import CitationUrl, Organization, OrgType, StockExchange, SystemVersion
from dbdb.core.utils.citations import crawl_citation_url, normalize_url, process_citation_url
from dbdb.core.utils.enrichment import BaseEnricher, build_org_enrichment_tool, build_url_extraction_tool

LOG = logging.getLogger(__name__)

# Ordered list of all fields the command can enrich.
ORG_ALL_FIELDS = (
    'description', 'stock_symbol',
    'url', 'wikipedia_url', 'linkedin_url', 'crunchbase_url',
    'org_type', 'stock_exchange',
    'countries', 'former_names',
)

# Maps display label → integer value for IntegerChoices fields.
_ORG_CHOICE_MAPS = {
    'org_type':      {label: value for value, label in OrgType.choices},
    'stock_exchange': {label: value for value, label in StockExchange.choices},
}


def _org_field_type(field_name: str) -> str:
    """Return the storage category of an Organization field via reflection."""
    field = Organization._meta.get_field(field_name)
    if isinstance(field, models.ForeignKey):
        return 'url'
    if isinstance(field, models.IntegerField) and field.choices:
        return 'choice'
    if isinstance(field, ArrayField) or (isinstance(field, CountryField) and field.multiple):
        return 'array'
    return 'text'


def _is_org_field_empty(org: Organization, field: str) -> bool:
    ft = _org_field_type(field)
    if ft == 'url':
        return getattr(org, f'{field}_id') is None
    if ft == 'choice':
        return getattr(org, field) is None
    return not getattr(org, field, None)


def _query_orgs_missing_field(field: str):
    """Return a queryset of Organizations that have *field* empty/null."""
    from django.db.models import Q
    ft = _org_field_type(field)
    if ft == 'url':
        return Organization.objects.filter(**{f'{field}_id__isnull': True})
    if ft == 'choice':
        return Organization.objects.filter(**{f'{field}__isnull': True})
    if ft == 'array':
        return Organization.objects.filter(Q(**{f'{field}__isnull': True}) | Q(**{f'{field}': []}))
    # text
    return Organization.objects.filter(Q(**{f'{field}__isnull': True}) | Q(**{field: ''}))


def _get_missing_org_fields(org: Organization, requested: list[str] | None) -> list[str]:
    if requested:
        return list(requested)
    return [f for f in ORG_ALL_FIELDS if _is_org_field_empty(org, f)]


def _generate_unique_org_slug(name: str, exclude_pk: int | None = None) -> str:
    base = slugify(name)
    slug = base
    counter = 1
    while True:
        qs = Organization.objects.filter(slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _get_full_company_name(org: Organization, enricher, model_override, dry_run: bool) -> str | None:
    prompt = (
        f"# Organization: {org.name}\n\n"
        f"What is the full legal name of this company, including its corporate suffix "
        f"(e.g. 'Inc.', 'Corporation', 'Ltd.', 'GmbH')?\n"
        f"If '{org.name}' is already the complete legal name, return it unchanged. "
        f"Return null if unknown."
    )
    tool = {
        "name": "save_full_name",
        "description": "Save the full legal company name with its corporate suffix",
        "input_schema": {
            "type": "object",
            "properties": {
                "full_name": {
                    "type": "string",
                    "description": (
                        "Full legal name including suffix such as 'Inc.', 'Corporation', "
                        "'Ltd.', 'GmbH'. Return null if unknown."
                    ),
                }
            },
        },
    }
    result = enricher.call_llm(prompt, tool, model_override, dry_run=dry_run)
    return (result.get("full_name") or "").strip() or None


_LINKEDIN_RE = re.compile(
    r'^https?://(?:www\.)?linkedin\.com/(company|in|school)/([A-Za-z0-9_\-\.%]+)/?$'
)


def _validate_linkedin_url(url: str) -> str | None:
    """Return a canonical LinkedIn URL, or None if the format is not recognized."""
    m = _LINKEDIN_RE.match(url.strip())
    if m:
        return f'https://www.linkedin.com/{m.group(1)}/{m.group(2)}'
    return None


_CRUNCHBASE_RE = re.compile(
    r'^https?://(?:www\.)?crunchbase\.com/(organization|person)/([A-Za-z0-9_\-\.]+)/?$'
)


def _validate_crunchbase_url(url: str) -> str | None:
    """Return a canonical Crunchbase URL, or None if the format is not recognized."""
    m = _CRUNCHBASE_RE.match(url.strip())
    if m:
        return f'https://www.crunchbase.com/{m.group(1)}/{m.group(2)}'
    return None


def _crawl_org_urls(org: Organization, recrawl_after: int = 7, skip_spamcheck: bool = False) -> dict[str, str]:
    """Crawl the org's CitationUrl FK fields; return {url: text_excerpt}."""
    crawled: dict[str, str] = {}
    cutoff = timezone.now() - timedelta(days=recrawl_after)
    for field in ORG_ALL_FIELDS:
        if _org_field_type(field) != 'url':
            continue
        citation: CitationUrl | None = getattr(org, field)
        if citation is None:
            continue
        text = crawl_citation_url(citation, recrawl_cutoff=cutoff, skip_spamcheck=skip_spamcheck)
        if text:
            crawled[citation.url] = text
    return crawled


class Command(EnricherBaseCommand):
    help = 'Fill missing Organization fields using an LLM'

    def add_arguments(self, parser: ArgumentParser):
        super().add_arguments(parser)
        org_type_choices = [m.name.lower() for m in OrgType]
        parser.add_argument('--search-type', choices=org_type_choices, default=None,
                            metavar='TYPE',
                            help=f'Only search for organizations with this type. '
                                 f'Choices: {", ".join(org_type_choices)}')
        parser.add_argument('--set-type', choices=org_type_choices, default=None,
                            metavar='TYPE',
                            help=f'Directly set org_type without invoking the LLM. '
                                 f'Choices: {", ".join(org_type_choices)}')
        parser.add_argument('--missing', metavar='FIELD', default=None,
                            choices=list(ORG_ALL_FIELDS),
                            help=f'Select organizations where FIELD is empty. '
                                 f'Can be combined with --search-type. '
                                 f'Valid fields: {", ".join(ORG_ALL_FIELDS)}')

    def handle(self, *args, **options):
        seen = {}
        missing_field = options.get('missing')

        if options.get('search_type'):
            org_type = OrgType[options['search_type'].upper()]
            qs = Organization.objects.filter(org_type=org_type)
            if missing_field:
                qs = qs & _query_orgs_missing_field(missing_field)
            for org in qs:
                seen.setdefault(org.pk, org)
        elif missing_field:
            for org in _query_orgs_missing_field(missing_field):
                seen.setdefault(org.pk, org)
        else:
            if not options['keywords']:
                raise CommandError("Provide at least one KEYWORD, --search-type, or --missing=FIELD")
            for keyword in options['keywords']:
                qs = Organization.objects.filter(slug=keyword)
                if not qs.exists():
                    qs = Organization.objects.filter(slug__icontains=keyword)
                if not qs.exists():
                    qs = Organization.objects.filter(name__icontains=keyword)
                if not qs.exists():
                    raise CommandError(f"No organization found matching '{keyword}'")
                for org in qs:
                    seen.setdefault(org.pk, org)
        import random
        orgs = list(seen.values())
        random.shuffle(orgs)

        if options['set_type']:
            member = OrgType[options['set_type'].upper()]
            Organization.objects.filter(pk__in=[o.pk for o in orgs]).update(org_type=member)
            self.stdout.write(self.style.SUCCESS(
                f"Set org_type='{member.label}' on {len(orgs)} organization(s)"
            ))
            return

        if not options['enricher']:
            raise CommandError("--enricher is required when --set-type is not used")

        mode = options['mode']
        do_enrich = mode in ('enrich', 'both')
        do_extract_urls = mode in ('extract-urls', 'both')

        limit = options['limit']
        sleep_secs = options['sleep']
        processed = 0
        prev_did_work = False
        for org in orgs:
            if limit is not None and processed >= limit:
                break
            if sleep_secs and prev_did_work:
                time.sleep(sleep_secs)
            did_work = False
            try:
                if do_enrich:
                    did_work |= self._enrich_one(org, options)
                if do_extract_urls:
                    did_work |= self._extract_urls_one(org, options)
                processed += 1
            except Exception as e:
                did_work = True  # work was started before the failure
                if not options['skip_errors']:
                    raise
                self.stderr.write(self.style.ERROR(f"Error enriching '{org.slug}': {e}"))
            prev_did_work = did_work

    def _enrich_one(self, org: Organization, options: dict) -> bool:
        org.refresh_from_db()

        dry_run: bool    = options['dry_run']
        model_override   = options['model']
        include_urls     = options['include_urls']
        requested_fields = (
            [f.strip() for f in options['fields'].split(',')]
            if options['fields'] else None
        )

        self.stdout.write(f"Organization: {org.name} (slug: {org.slug})")
        enricher = BaseEnricher.create(options['enricher'])

        # --- 2. Identify missing fields ---
        skip_fields = set(options['skip_field'])
        missing_fields = [
            f for f in _get_missing_org_fields(org, requested_fields)
            if f not in skip_fields
        ]
        if not missing_fields:
            self.stdout.write(self.style.SUCCESS("All fields are already filled. Nothing to do."))
            return False
        self.stdout.write(f"Missing fields: {', '.join(missing_fields)}")

        # --- 3. Crawl existing URLs (opt-in via --include-urls) ---
        crawled_pages: dict[str, str] = {}
        if include_urls:
            self.stdout.write("Crawling existing URLs...")
            crawled_pages = _crawl_org_urls(org, recrawl_after=options['recrawl_after'], skip_spamcheck=options['skip_spamcheck'])
            self.stdout.write(f"  Crawled {len(crawled_pages)} page(s)")

        # --- 4. Call LLM ---
        self.stdout.write("Calling LLM...")
        prompt = enricher.build_org_prompt(org, missing_fields, crawled_pages)
        LOG.debug(prompt)
        tool = build_org_enrichment_tool(missing_fields)
        try:
            enrichment: dict = enricher.call_llm(prompt, tool, model_override, dry_run=dry_run)
        except Exception as e:
            raise CommandError(f"LLM call failed: {e}")
        if dry_run:
            return

        # --- 5. Validate citations ---
        self.stdout.write("Validating citations...")
        raw_citations = enrichment.get('citations', [])
        valid_citations = enricher.validate_citations(raw_citations, system=None, skip_spamcheck=options['skip_spamcheck'])
        self.stdout.write(f"  {len(valid_citations)}/{len(raw_citations)} citations valid")

        # --- 6. Apply enrichment ---
        dirty = False

        for field in missing_fields:
            val = enrichment.get(field)
            ft = _org_field_type(field)

            if ft == 'text':
                if val:
                    setattr(org, field, val)
                    dirty = True

            elif ft == 'choice':
                label = (val or '').strip()
                int_val = _ORG_CHOICE_MAPS.get(field, {}).get(label)
                if int_val is not None:
                    setattr(org, field, int_val)
                    dirty = True
                elif label:
                    LOG.warning(f"  {field}: unrecognised value {label!r}, skipping")

            elif ft == 'array':
                if isinstance(val, list) and val:
                    setattr(org, field, val)
                    dirty = True

            elif ft == 'url':
                url_str = (val or '').strip()
                if not url_str:
                    continue
                try:
                    norm = normalize_url(url_str)
                    existing = CitationUrl.objects.filter(url=norm).first()
                    if existing:
                        if existing.status in (CitationUrl.Status.DEAD, CitationUrl.Status.SPAM):
                            LOG.warning(f"  {field}: existing citation {url_str!r} has status {CitationUrl.Status(existing.status).name}, skipping")
                        else:
                            setattr(org, field, existing)
                            dirty = True
                        continue
                    citation = CitationUrl.objects.create(url=norm, status=CitationUrl.Status.UNKNOWN)
                    citation, info = process_citation_url(citation, skip_spamcheck=options['skip_spamcheck'])
                    if info is None:
                        setattr(org, field, citation)
                        dirty = True
                    elif info['status'] == CitationUrl.Status.VALID:
                        citation.save()
                        setattr(org, field, citation)
                        dirty = True
                    else:
                        LOG.warning(
                            f"  {field}: {url_str!r} unreachable "
                            f"(status={citation.get_status_display()}), skipping"
                        )
                        citation.delete()
                except Exception as e:
                    LOG.warning(f"  {field}: could not validate {url_str!r}: {e}")

        if org.url_id and 'linkedin.com' in org.url.url:
            LOG.info(f"Moving LinkedIn URL from url to linkedin_url: {org.url.url}")
            if not org.linkedin_url_id:
                org.linkedin_url = org.url
            org.url = None
            dirty = True

        if org.get_org_type_display() == 'Individual' and org.description:
            LOG.info("Clearing description: org_type is Individual")
            org.description = ''
            dirty = True

        # If the org has no country, look for a current SystemVersion where this
        # org is the only developer and that SV has exactly one country — if found,
        # copy that country to the org.
        if not org.countries:
            sv = (
                SystemVersion.objects
                .filter(is_current=True, developer_orgs=org)
                .annotate(dev_org_count=Count('developer_orgs'))
                .filter(dev_org_count=1)
                .first()
            )
            if sv and len(sv.countries) == 1:
                org.countries = list(sv.countries)
                dirty = True
                self.stdout.write(
                    f"  Inferred countries={list(org.countries)} "
                    f"from SystemVersion '{sv.system.name}'"
                )

        if dirty:
            org.save()

        # --- Full legal name (Company orgs only) ---
        if org.org_type == OrgType.COMPANY:
            full_name = _get_full_company_name(org, enricher, model_override, dry_run)
            if full_name and full_name != org.name:
                old_name = org.name
                new_slug = _generate_unique_org_slug(full_name, exclude_pk=org.pk)
                org.name = full_name
                org.slug = new_slug
                if not dry_run:
                    org.save()
                self.stdout.write(
                    self.style.SUCCESS(f"  Renamed: {old_name!r} → {full_name!r} (slug: {new_slug!r})")
                )

        fields_filled = [f"{f}={enrichment.get(f)}" for f in missing_fields if enrichment.get(f) not in (None, '')]
        self.stdout.write(self.style.SUCCESS(f"\nUpdated organization '{org.name}'"))
        if fields_filled:
            self.stdout.write(f"Fields filled: {', '.join(fields_filled)}")
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current().domain
        self.stdout.write(self.style.SUCCESS(f"\nhttps://{domain}{reverse('organization', args=[org.slug])}"))
        return True

    def _extract_urls_one(self, org: Organization, options: dict, *, enricher=None) -> bool:
        org.refresh_from_db()
        dry_run: bool = options['dry_run']

        if org.url_id is None:
            LOG.info("Skipping '%s': no url set", org.slug)
            return False

        if org.url.status in (CitationUrl.Status.DEAD, CitationUrl.Status.SPAM):
            LOG.info("Skipping '%s': url status is %s", org.slug, org.url.status.name)
            return False

        url_fields = ['linkedin_url', 'crunchbase_url']
        missing = [f for f in url_fields if getattr(org, f'{f}_id') is None]
        if not missing:
            LOG.info("Skipping '%s': all URL fields already set", org.slug)
            return False

        # Past this point we crawl the homepage and call the LLM.
        cutoff = timezone.now() - timedelta(days=options['recrawl_after'])
        crawl_citation_url(org.url, recrawl_cutoff=cutoff, skip_spamcheck=options['skip_spamcheck'])

        try:
            raw_html = org.url.content.raw
        except AttributeError:
            raw_html = ''

        if not raw_html:
            # crawl_citation_url may have served cached text without saving raw HTML
            # (e.g. URLs crawled before the raw field existed). Force a fresh fetch.
            _, info = process_citation_url(
                org.url,
                skip_spamcheck=options['skip_spamcheck'],
            )
            raw_html = (info or {}).get('raw') or ''

        if not raw_html:
            LOG.info("Skipping '%s': could not retrieve homepage content", org.slug)
            return True  # crawling was attempted; count as work to avoid rapid retries

        if enricher is None:
            enricher = BaseEnricher.create(options['enricher'])

        tool = build_url_extraction_tool(org, missing)
        expected_keys = set(tool['input_schema']['properties'].keys())
        prompts = enricher.build_homepage_url_prompt(org.name, raw_html, missing)
        result = {}
        for prompt in prompts:
            try:
                chunk_result = enricher.call_llm(prompt, tool, model_override=options.get('model'), dry_run=dry_run)
            except Exception as e:
                LOG.warning(f"Unexpected error: {e}")
                if not options['skip_errors']:
                    raise
                continue

            for key, val in chunk_result.items():
                if val and key not in result:
                    result[key] = val
            if all(result.get(k) for k in expected_keys):
                break

        if dry_run:
            self.stdout.write(
                f"  [DRY RUN] linkedin_url={result.get('linkedin_url')!r}, "
                f"crunchbase_url={result.get('crunchbase_url')!r}"
            )
            return True

        if 'linkedin_url' in missing:
            linkedin_url = _validate_linkedin_url(result.get('linkedin_url') or '')
            if not linkedin_url:
                LOG.warning("Skipping '%s': extracted linkedin_url is invalid: %r", org.slug, result.get('linkedin_url'))
            else:
                try:
                    norm = normalize_url(linkedin_url)
                    existing = CitationUrl.objects.filter(url=norm).first()
                    if existing:
                        if existing.status in (CitationUrl.Status.DEAD, CitationUrl.Status.SPAM):
                            LOG.warning("linkedin_url: %r has status %s, skipping", linkedin_url, CitationUrl.Status(existing.status).name)
                            citation = None
                        else:
                            citation = existing
                    else:
                        citation = CitationUrl.objects.create(url=norm, status=CitationUrl.Status.UNKNOWN)
                        citation, info = process_citation_url(citation, skip_spamcheck=options['skip_spamcheck'])
                        if info is not None and info['status'] != CitationUrl.Status.VALID:
                            LOG.warning("linkedin_url: %r is unreachable, skipping", linkedin_url)
                            citation.delete()
                            citation = None
                        elif info is not None:
                            citation.save()
                    if citation is not None:
                        org.linkedin_url = citation
                        org.save(update_fields=['linkedin_url'])
                        self.stdout.write(self.style.SUCCESS(f"  Set linkedin_url={linkedin_url} for '{org.name}'"))
                except Exception as e:
                    LOG.warning("linkedin_url: could not validate %r: %s", linkedin_url, e)

        if 'crunchbase_url' in missing:
            # crunchbase.com is in SKIP_DOMAINS so process_citation_url returns IGNORE.
            # Validate URL format only; get-or-create the CitationUrl without HTTP fetch.
            crunchbase_url = _validate_crunchbase_url(result.get('crunchbase_url') or '')
            if not crunchbase_url:
                LOG.warning("Skipping '%s': extracted crunchbase_url is invalid: %r", org.slug, result.get('crunchbase_url'))
            else:
                try:
                    norm = normalize_url(crunchbase_url)
                    citation, created = CitationUrl.objects.get_or_create(
                        url=norm,
                        defaults={'status': CitationUrl.Status.IGNORE},
                    )
                    org.crunchbase_url = citation
                    org.save(update_fields=['crunchbase_url'])
                    self.stdout.write(self.style.SUCCESS(f"  Set crunchbase_url={crunchbase_url} for '{org.name}'"))
                except Exception as e:
                    LOG.warning("crunchbase_url: could not save %r: %s", crunchbase_url, e)

        return True
