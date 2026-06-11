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
from argparse import ArgumentParser
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.core.management.base import CommandError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_countries.fields import CountryField

from dbdb.core.management.base import EnricherBaseCommand
from dbdb.core.models import CitationUrl, Organization, OrgType, StockExchange
from dbdb.core.utils.citations import crawl_citation_url, normalize_url, process_citation_url
from dbdb.core.utils.enrichment import BaseEnricher, build_org_enrichment_tool

LOG = logging.getLogger(__name__)

# Ordered list of all fields the command can enrich.
ORG_ALL_FIELDS = (
    'description', 'stock_symbol',
    'url', 'wikipedia_url', 'linkedin_url',
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


def _get_missing_org_fields(org: Organization, requested: list[str] | None) -> list[str]:
    targets = requested if requested else list(ORG_ALL_FIELDS)
    return [f for f in targets if _is_org_field_empty(org, f)]


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
        parser.add_argument('keyword', metavar='ORG', type=str,
                            help='Organization slug or name keyword')

    def handle(self, *args, **options):
        keyword = options['keyword']

        orgs = Organization.objects.filter(slug=keyword)
        if not orgs.exists():
            orgs = Organization.objects.filter(slug__icontains=keyword)
        if not orgs.exists():
            orgs = Organization.objects.filter(name__icontains=keyword)
        if not orgs.exists():
            raise CommandError(f"No organization found matching '{keyword}'")

        for org in orgs:
            try:
                self._enrich_one(org, options)
            except Exception as e:
                if not options['skip_errors']:
                    raise
                self.stderr.write(self.style.ERROR(f"Error enriching '{org.slug}': {e}"))

    def _enrich_one(self, org: Organization, options: dict):
        dry_run: bool    = options['dry_run']
        model_override   = options['model']
        include_urls     = options['include_urls']
        requested_fields = (
            [f.strip() for f in options['fields'].split(',')]
            if options['fields'] else None
        )

        self.stdout.write(f"Organization: {org.name} (slug: {org.slug})")
        enricher = BaseEnricher.create(options['enricher'], model_override)

        # --- 2. Identify missing fields ---
        skip_fields = set(options['skip_field'])
        missing_fields = [
            f for f in _get_missing_org_fields(org, requested_fields)
            if f not in skip_fields
        ]
        if not missing_fields:
            self.stdout.write(self.style.SUCCESS("All fields are already filled. Nothing to do."))
            return
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

        if org.get_org_type_display() == 'Individual' and org.description:
            LOG.info("Clearing description: org_type is Individual")
            org.description = ''
            dirty = True

        if dirty:
            org.save()

        fields_filled = [f"{f}={enrichment.get(f)}" for f in missing_fields if enrichment.get(f) not in (None, '')]
        self.stdout.write(self.style.SUCCESS(f"\nUpdated organization '{org.name}'"))
        if fields_filled:
            self.stdout.write(f"Fields filled: {', '.join(fields_filled)}")
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current().domain
        self.stdout.write(self.style.SUCCESS(f"\nhttps://{domain}{reverse('organization', args=[org.slug])}"))
