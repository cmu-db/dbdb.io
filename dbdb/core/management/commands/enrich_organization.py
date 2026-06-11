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

from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from dbdb.core.management.base import EnricherBaseCommand
from dbdb.core.models import CitationUrl, Organization, OrgType, StockExchange
from dbdb.core.utils.citations import crawl_citation_url, normalize_url, process_citation_url
from dbdb.core.utils.enrichment import BaseEnricher, build_org_enrichment_tool

LOG = logging.getLogger(__name__)

ORG_URL_FIELDS    = ('url', 'wikipedia_url', 'linkedin_url')
ORG_TEXT_FIELDS   = ('description', 'stock_symbol')
ORG_CHOICE_FIELDS = ('org_type', 'stock_exchange')
ORG_ALL_FIELDS    = ORG_TEXT_FIELDS + ORG_URL_FIELDS + ORG_CHOICE_FIELDS

# Maps display label → integer value for each IntegerChoices field.
_ORG_TYPE_BY_LABEL      = {label: value for value, label in OrgType.choices}
_STOCK_EXCHANGE_BY_LABEL = {label: value for value, label in StockExchange.choices}


def _is_org_field_empty(org: Organization, field: str) -> bool:
    if field in ORG_URL_FIELDS:
        return getattr(org, f'{field}_id') is None
    if field in ORG_CHOICE_FIELDS:
        return getattr(org, field) is None
    val = getattr(org, field, None)
    return not val or str(val).strip() == ''


def _get_missing_org_fields(org: Organization, requested: list[str] | None) -> list[str]:
    targets = requested if requested else list(ORG_ALL_FIELDS)
    return [f for f in targets if _is_org_field_empty(org, f)]


def _crawl_org_urls(org: Organization, recrawl_after: int = 7) -> dict[str, str]:
    """Crawl the org's known URL fields; return {url: text_excerpt}."""
    crawled: dict[str, str] = {}
    cutoff = timezone.now() - timedelta(days=recrawl_after)
    for field in ORG_URL_FIELDS:
        citation: CitationUrl | None = getattr(org, field)
        if citation is None:
            continue
        text = crawl_citation_url(citation, recrawl_cutoff=cutoff)
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
        keyword          = options['keyword']
        dry_run: bool    = options['dry_run']
        model_override   = options['model']
        include_urls     = options['include_urls']
        requested_fields = (
            [f.strip() for f in options['fields'].split(',')]
            if options['fields'] else None
        )

        # --- 1. Load organization ---
        org = (
            Organization.objects.filter(slug=keyword).first()
            or Organization.objects.filter(slug__icontains=keyword).first()
            or Organization.objects.filter(name__icontains=keyword).first()
        )
        if org is None:
            raise CommandError(f"No organization found matching '{keyword}'")

        self.stdout.write(f"Organization: {org.name} (slug: {org.slug})")
        enricher = BaseEnricher.create(options['enricher'], model_override)

        # --- 2. Identify missing fields ---
        missing_fields = _get_missing_org_fields(org, requested_fields)
        if not missing_fields:
            self.stdout.write(self.style.SUCCESS("All fields are already filled. Nothing to do."))
            return
        self.stdout.write(f"Missing fields: {', '.join(missing_fields)}")

        # --- 3. Crawl existing URLs (opt-in via --include-urls) ---
        crawled_pages: dict[str, str] = {}
        if include_urls:
            self.stdout.write("Crawling existing URLs...")
            crawled_pages = _crawl_org_urls(org, recrawl_after=options['recrawl_after'])
            self.stdout.write(f"  Crawled {len(crawled_pages)} page(s)")

        # --- 4. Call LLM ---
        self.stdout.write("Calling LLM...")
        prompt = enricher.build_org_prompt(org, missing_fields, crawled_pages)
        LOG.debug(prompt)
        tool = build_org_enrichment_tool(missing_fields)
        try:
            enrichment: dict = enricher.call_llm(prompt, tool, model_override)
        except Exception as e:
            raise CommandError(f"LLM call failed: {e}")

        # --- 5. Validate citations ---
        self.stdout.write("Validating citations...")
        raw_citations = enrichment.get('citations', [])
        valid_citations = enricher.validate_citations(raw_citations, system=None)
        self.stdout.write(f"  {len(valid_citations)}/{len(raw_citations)} citations valid")

        # --- 6. Dry-run output ---
        if dry_run:
            self.stdout.write(self.style.WARNING("\n--- DRY RUN (no changes saved) ---"))
            for field in missing_fields:
                val = enrichment.get(field)
                if val not in (None, ''):
                    self.stdout.write(f"  {field}: {str(val)[:120]}")
            self.stdout.write(f"  valid citations: {list(valid_citations.keys())}")
            return

        # --- 7. Apply enrichment ---
        dirty = False

        for field in ORG_TEXT_FIELDS:
            if field in missing_fields:
                val = enrichment.get(field, '')
                if val:
                    setattr(org, field, val)
                    dirty = True

        _choice_maps = {
            'org_type':       _ORG_TYPE_BY_LABEL,
            'stock_exchange':  _STOCK_EXCHANGE_BY_LABEL,
        }
        for field in ORG_CHOICE_FIELDS:
            if field not in missing_fields:
                continue
            label = (enrichment.get(field) or '').strip()
            if not label:
                continue
            int_val = _choice_maps[field].get(label)
            if int_val is not None:
                setattr(org, field, int_val)
                dirty = True
            else:
                LOG.warning(f"  {field}: unrecognised value {label!r}, skipping")

        for field in ORG_URL_FIELDS:
            if field not in missing_fields:
                continue
            url_str = (enrichment.get(field) or '').strip()
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
                citation, info = process_citation_url(citation)
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

        if dirty:
            org.save()

        fields_filled = [f"{f}={enrichment.get(f)}" for f in missing_fields if enrichment.get(f) not in (None, '')]
        self.stdout.write(self.style.SUCCESS(f"\nUpdated organization '{org.name}'"))
        if fields_filled:
            self.stdout.write(f"Fields filled: {', '.join(fields_filled)}")
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current().domain
        self.stdout.write(self.style.SUCCESS(f"\nhttps://{domain}{reverse('organization', args=[org.slug])}"))
