"""
enrich_system — fill missing SystemVersion fields using an LLM.

Usage:
    python manage.py enrich_system <slug> [options]

For each empty field on the current SystemVersion, the command:
  1. Crawls the system's known URLs (system_url, docs_url, sourcerepo_url, wikipedia_url)
  2. Passes crawled text + the full Feature/Attribute taxonomy to an LLM
  3. Validates the LLM-suggested citations via fetch_url_metadata()
  4. Saves a new SystemVersion with approved=False (pending) containing only the
     suggested values for fields that were empty — existing data is never overwritten
"""
import logging
from argparse import ArgumentParser

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.utils import timezone
from dbdb.core.management.base import DbdbBaseCommand
from django.db import transaction

from dbdb.core.models import (
    Attribute, CitationUrl,
    Feature, FeatureOption,
    System, SystemFeature, SystemVersion,
)
from dbdb.core.utils.citations import normalize_url, process_citation_url
from dbdb.core.utils.enrichment import (
    build_feature_prompt,
    build_full_prompt,
    call_llm,
    validate_citations,
)

LOG = logging.getLogger(__name__)
User = get_user_model()


# Fields the command can fill — text, integer, simple char, and URL-FK fields.
# M2M attribute fields (project_types, licenses, oses, written_in) are handled
# separately because they require AttributeOption lookups.
SIMPLE_TEXT_FIELDS = ('description', 'history', 'twitter_handle')
INT_FIELDS = ('start_year', 'end_year')
URL_FK_FIELDS = ('system_url', 'docs_url', 'sourcerepo_url', 'wikipedia_url', 'linkedin_url')
M2M_ATTR_FIELDS = ('project_types', 'licenses', 'oses', 'written_in')
# Maps M2M field name → Attribute slug
M2M_ATTR_SLUGS = {
    'project_types': 'project-type',
    'licenses':      'license',
    'oses':          'os',
    'written_in':    'programming-language',
}
# Maps M2M field name → the M2M citation field on SystemVersion
FIELD_CITATION_MAP = {
    'description': 'description_citations',
    'history':     'history_citations',
    'start_year':  'start_year_citations',
    'end_year':    'end_year_citations',
}


def _is_field_empty(version: SystemVersion, field: str) -> bool:
    """Return True if a targetable field on *version* is empty/null."""
    if field in URL_FK_FIELDS:
        return getattr(version, f'{field}_id') is None
    if field in M2M_ATTR_FIELDS:
        return not getattr(version, field).exists()
    if field == 'features':
        return False  # checked separately per-feature
    val = getattr(version, field, None)
    if val is None:
        return True
    return str(val).strip() == ''


def _get_missing_fields(version: SystemVersion, requested: list[str] | None) -> list[str]:
    """Return the subset of requested fields (or all) that are empty."""
    all_fields = list(SIMPLE_TEXT_FIELDS) + list(INT_FIELDS) + list(URL_FK_FIELDS) + list(M2M_ATTR_FIELDS)
    targets = requested if requested else all_fields
    return [f for f in targets if _is_field_empty(version, f)]


def _crawl_existing_urls(
    version: SystemVersion,
    system: System,
    recrawl_after: int = 7,
) -> dict[str, str]:
    """Crawl the system's known URL fields; return {url: text_excerpt}.

    If a CitationUrl was last checked within *recrawl_after* days and already
    has a CitationUrlContent with text, the cached text is reused and no HTTP
    request is made.
    """
    from dbdb.core.models import CitationUrlContent
    crawled = {}
    cutoff = timezone.now() - timedelta(days=recrawl_after)

    for field in URL_FK_FIELDS:
        citation: CitationUrl | None = getattr(version, field)
        if citation is None:
            continue
        url = citation.url

        # Use cached content if it was fetched recently and has text
        if citation.last_checked and citation.last_checked >= cutoff:
            try:
                content = citation.content
                if content.text:
                    LOG.info(f"  Using cached content for {field}: {url}")
                    crawled[url] = content.text
                    continue
            except CitationUrlContent.DoesNotExist:
                pass

        LOG.info(f"  Crawling {field}: {url}")
        _citation, result = process_citation_url(citation, system=system)
        if result:
            text = result.get('text', '')
            if text:
                crawled[url] = text
    return crawled


def _copy_version(source: SystemVersion) -> SystemVersion:
    """Return an unsaved in-memory copy of *source* with pk=None."""
    copy = SystemVersion()
    skip = {'id', 'ver', 'is_current', 'approved', 'created'}
    for f in source._meta.concrete_fields:
        if f.attname in skip:
            continue
        setattr(copy, f.attname, getattr(source, f.attname))
    return copy


def _get_missing_features(version: SystemVersion) -> list[Feature]:
    """Return Features that have no options set on *version*."""
    existing_feature_ids = set(
        SystemFeature.objects.filter(version=version)
        .exclude(options=None)
        .values_list('feature_id', flat=True)
    )
    return list(Feature.objects.exclude(id__in=existing_feature_ids).prefetch_related('options').order_by('category', 'label'))


class Command(DbdbBaseCommand):
    help = 'Fill missing SystemVersion fields using an LLM and save a pending version'

    def add_arguments(self, parser: ArgumentParser):
        super().add_arguments(parser)
        parser.add_argument('keyword', metavar='S', type=str, help='System id or slug keyword')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be filled without saving')
        parser.add_argument('--fields', default=None,
                            help='Comma-separated list of field names to target')
        parser.add_argument('--model', default=None,
                            help='Override LLM model name')
        parser.add_argument('--per-feature', action='store_true',
                            help='One LLM call per missing Feature (slower, more targeted)')
        parser.add_argument('--recrawl-after', type=int, default=7, metavar='DAYS',
                            help='Re-fetch a URL only if its cached content is older than N days (default: 7)')

    def handle(self, *args, **options):
        keyword = options['keyword']
        dry_run: bool = options['dry_run']
        model_override: str | None = options['model']
        per_feature: bool = options['per_feature']
        requested_fields: list[str] | None = (
            [f.strip() for f in options['fields'].split(',')]
            if options['fields'] else None
        )

        # --- 1. Load system and current version ---
        try:
            if keyword.isdigit():
                system = System.objects.filter(id=int(keyword)).first()
            else:
                system = System.objects.filter(slug__icontains=keyword).first()
        except System.DoesNotExist:
            raise CommandError(f"No system found with keyword '{keyword}'")

        try:
            current = SystemVersion.objects.prefetch_related(
                'project_types', 'licenses', 'oses', 'written_in',
                'features', 'features__options',
            ).get(system=system, is_current=True)
        except SystemVersion.DoesNotExist:
            raise CommandError(f"No current SystemVersion for '{keyword}'")

        self.stdout.write(f"System: {system.name} (current ver #{current.ver})")

        # --- 2. Identify missing fields ---
        missing_fields = _get_missing_fields(current, requested_fields)
        missing_features = _get_missing_features(current)

        if not missing_fields and not missing_features:
            self.stdout.write(self.style.SUCCESS("All fields are already filled. Nothing to do."))
            return

        if missing_fields:
            self.stdout.write(f"Missing fields: {', '.join(missing_fields)}")
        if missing_features:
            self.stdout.write(f"Missing features: {len(missing_features)} of {Feature.objects.count()}")

        # --- 3. Crawl existing URLs ---
        self.stdout.write("Crawling existing URLs...")
        crawled_pages = _crawl_existing_urls(current, system, recrawl_after=options['recrawl_after'])
        self.stdout.write(f"  Crawled {len(crawled_pages)} page(s)")

        # --- 4. Load taxonomy ---
        features = list(Feature.objects.prefetch_related('options').order_by('category', 'label'))
        attributes = list(
            Attribute.objects
            .filter(sv_field__in=M2M_ATTR_SLUGS.values())
            .prefetch_related('options')
            .order_by('name')
        )

        # --- 5. Call LLM ---
        enrichment: dict = {}

        if not per_feature:
            # Single comprehensive call
            self.stdout.write("Calling LLM (single call)...")
            prompt = build_full_prompt(
                system=system,
                current_version=current,
                missing_fields=missing_fields + (['features'] if missing_features else []),
                crawled_pages=crawled_pages,
                features=features,
                attributes=attributes,
            )
            try:
                enrichment = call_llm(prompt, model_override=model_override)
            except Exception as e:
                raise CommandError(f"LLM call failed: {e}")
        else:
            # Per-feature calls — merge results into enrichment dict
            if missing_fields:
                self.stdout.write("Calling LLM for metadata fields...")
                prompt = build_full_prompt(
                    system=system,
                    current_version=current,
                    missing_fields=missing_fields,
                    crawled_pages=crawled_pages,
                    features=[],
                    attributes=attributes,
                )
                try:
                    enrichment = call_llm(prompt, model_override=model_override)
                except Exception as e:
                    raise CommandError(f"LLM call failed: {e}")

            enrichment.setdefault('features', {})
            enrichment.setdefault('citations', [])
            for feature in missing_features:
                self.stdout.write(f"  Calling LLM for feature: {feature.label}")
                prompt = build_feature_prompt(system, feature, crawled_pages)
                try:
                    result = call_llm(prompt, model_override=model_override)
                    enrichment['features'].update(result.get('features', {}))
                    enrichment['citations'].extend(result.get('citations', []))
                except Exception as e:
                    LOG.warning(f"LLM call failed for feature {feature.slug}: {e}")

        # --- 6. Validate citations ---
        self.stdout.write("Validating citations...")
        raw_citations = enrichment.get('citations', [])
        valid_citations = validate_citations(raw_citations, system)
        self.stdout.write(f"  {len(valid_citations)}/{len(raw_citations)} citations valid")

        # --- 7. Dry-run output ---
        if dry_run:
            self.stdout.write(self.style.WARNING("\n--- DRY RUN (no changes saved) ---"))
            for field in missing_fields:
                val = enrichment.get(field)
                if val is not None and val != '' and val != [] and val != {}:
                    self.stdout.write(f"  {field}: {str(val)[:120]}")
            feat_suggestions = enrichment.get('features', {})
            if feat_suggestions:
                self.stdout.write(f"  features: {feat_suggestions}")
            self.stdout.write(f"  valid citations: {list(valid_citations.keys())}")
            return

        # --- 8. Build and save pending SystemVersion ---
        bot_user = User.objects.get(username=settings.DBDB_BOT_ACCOUNT)

        with transaction.atomic():
            new_sv = _copy_version(current)
            new_sv.approved = False
            new_sv.is_current = False
            new_sv.creator = bot_user
            new_sv.comment = f"Auto-enriched by enrich_system command (model: {model_override or settings.ENRICHMENT_LLM_MODEL})"
            new_sv.save()  # pre-save signal assigns ver number

            # Apply simple text / int fields
            dirty = False
            for field in SIMPLE_TEXT_FIELDS:
                if field in missing_fields:
                    val = enrichment.get(field, '')
                    if val:
                        setattr(new_sv, field, val)
                        dirty = True

            for field in INT_FIELDS:
                if field in missing_fields:
                    val = enrichment.get(field)
                    if val is not None:
                        try:
                            setattr(new_sv, field, int(val))
                            dirty = True
                        except (TypeError, ValueError):
                            LOG.warning(f"  {field}: LLM returned non-integer {val!r}, skipping")

            # Apply URL FK fields — validate each LLM-suggested URL before use
            for field in URL_FK_FIELDS:
                if field not in missing_fields:
                    continue
                url_str = (enrichment.get(field) or '').strip()
                if not url_str:
                    continue
                try:
                    norm = normalize_url(url_str)
                    existing = CitationUrl.objects.filter(url=norm).first()
                    if existing:
                        setattr(new_sv, field, existing)
                        dirty = True
                        continue
                    # New URL: create, validate, keep only if reachable
                    citation = CitationUrl.objects.create(url=norm, status=CitationUrl.Status.UNKNOWN)
                    citation, info = process_citation_url(citation, system=system)
                    if info is None:
                        # Merged into an existing CitationUrl
                        setattr(new_sv, field, citation)
                        dirty = True
                    elif info['status'] == CitationUrl.Status.VALID:
                        citation.save()
                        setattr(new_sv, field, citation)
                        dirty = True
                    else:
                        LOG.warning(f"  {field}: {url_str!r} is unreachable (status={citation.get_status_display()}), skipping")
                        citation.delete()
                except Exception as e:
                    LOG.warning(f"  {field}: could not validate {url_str!r}: {e}")

            if dirty:
                new_sv.save()

            # Apply M2M attribute fields
            for field, attr_slug in M2M_ATTR_SLUGS.items():
                if field not in missing_fields:
                    continue
                slugs = enrichment.get(field, [])
                if not slugs:
                    continue
                opts = list(
                    AttributeOption.objects.filter(
                        attribute__slug=attr_slug,
                        slug__in=slugs,
                    )
                )
                if opts:
                    getattr(new_sv, field).set(opts)

            # Attach citations to citation M2M fields
            for norm_url, (cite_obj, fields) in valid_citations.items():
                for field in fields:
                    cite_m2m = FIELD_CITATION_MAP.get(field)
                    if cite_m2m:
                        getattr(new_sv, cite_m2m).add(cite_obj)

            # Create SystemFeature rows for suggested features
            feat_suggestions = enrichment.get('features', {})
            if not isinstance(feat_suggestions, dict):
                LOG.warning(f"LLM returned non-dict for 'features': {type(feat_suggestions).__name__} — skipping")
                feat_suggestions = {}
            features_by_slug = {f.slug: f for f in features}
            for feat_slug, option_slugs in feat_suggestions.items():
                feature = features_by_slug.get(feat_slug)
                if feature is None:
                    LOG.warning(f"Unknown feature keyword from LLM: {feat_slug}")
                    continue
                opts = list(
                    FeatureOption.objects.filter(
                        feature=feature,
                        slug__in=option_slugs,
                    )
                )
                if not opts:
                    LOG.warning(f"No matching options for feature {feat_slug}: {option_slugs}")
                    continue
                sf, _ = SystemFeature.objects.get_or_create(
                    version=new_sv,
                    feature=feature,
                    defaults={'system': None},
                )
                sf.options.set(opts)

        self.stdout.write(self.style.SUCCESS(
            f"\nCreated pending SystemVersion #{new_sv.ver} for '{system.name}'"
        ))
        fields_filled = [
            f for f in missing_fields
            if enrichment.get(f) not in (None, '', [], {})
        ]
        if fields_filled:
            self.stdout.write(f"Fields filled: {', '.join(fields_filled)}")
        if feat_suggestions:
            self.stdout.write(f"Features set: {', '.join(feat_suggestions.keys())}")
        self.stdout.write("Review and approve at /admin/core/systemversion/")
