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
import re
import sys
import time
from argparse import ArgumentParser

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db.models import Q
from django.utils import timezone
from dbdb.core.management.base import EnricherBaseCommand
from django.db import transaction

from dbdb.core.models import (
    Attribute, CitationUrl,
    Feature, FeatureOption,
    System, SystemFeature, SystemVersion, AttributeOption,
)
from dbdb.core.utils.citations import crawl_citation_url, normalize_url, process_citation_url
from dbdb.core.utils.enrichment import BaseEnricher, SYSTEM_ENRICHMENT_TOOL, build_url_extraction_tool
from dbdb.core.utils.repositories import GitHubCollector
from dbdb.core.utils.versions import clone_system_version, finalize_new_version

LOG = logging.getLogger(__name__)
User = get_user_model()


# Fields the command can fill — text, integer, simple char, and URL-FK fields.
# M2M attribute fields (project_types, licenses, oses, written_in) are handled
# separately because they require AttributeOption lookups.
SIMPLE_TEXT_FIELDS = ('description', 'history', 'twitter_handle')
INT_FIELDS = ('start_year', 'end_year')
URL_FK_FIELDS = ('system_url', 'docs_url', 'sourcerepo_url', 'wikipedia_url')
M2M_ATTR_FIELDS = ('project_types', 'licenses', 'oses', 'written_in', 'tags')
# Maps M2M field name → Attribute slug
M2M_ATTR_SLUGS = {
    'project_types': 'project-type',
    'licenses':      'license',
    'oses':          'os',
    'written_in':    'programming-language',
    'tags':          'tag'
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
    if requested:
        return list(requested)
    all_fields = list(SIMPLE_TEXT_FIELDS) + list(INT_FIELDS) + list(URL_FK_FIELDS) + list(M2M_ATTR_FIELDS)
    return [f for f in all_fields if _is_field_empty(version, f)]


def _extract_twitter_handle(val: str) -> str | None:
    """Return '@handle' from a twitter.com/x.com URL or bare handle string."""
    m = re.match(r'https?://(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]{1,50})', val)
    if m:
        return f'@{m.group(1)}'
    if re.match(r'^@?[A-Za-z0-9_]{1,50}$', val.strip()):
        return f'@{val.strip().lstrip("@")}'
    return None


def _crawl_existing_urls(
    version: SystemVersion,
    system: System,
    recrawl_after: int = 7,
    skip_spamcheck: bool = False,
) -> dict[str, str]:
    """Crawl the system's known URL fields; return {url: text_excerpt}."""
    crawled = {}
    cutoff = timezone.now() - timedelta(days=recrawl_after)
    for field in URL_FK_FIELDS:
        citation: CitationUrl | None = getattr(version, field)
        if citation is None:
            continue
        text = crawl_citation_url(citation, system=system, recrawl_cutoff=cutoff, skip_spamcheck=skip_spamcheck)
        if text:
            crawled[citation.url] = text
    return crawled



def _query_systems_missing_field(field: str):
    """Return a queryset of Systems whose current version has *field* empty/null."""
    from django.db.models import Q
    sv_qs = SystemVersion.objects.filter(is_current=True)
    if field in URL_FK_FIELDS:
        sv_qs = sv_qs.filter(**{f'{field}_id__isnull': True})
    elif field in M2M_ATTR_FIELDS:
        sv_qs = sv_qs.filter(**{f'{field}__isnull': True})
    elif field in SIMPLE_TEXT_FIELDS:
        sv_qs = sv_qs.filter(Q(**{f'{field}__isnull': True}) | Q(**{field: ''}))
    else:  # INT_FIELDS
        sv_qs = sv_qs.filter(**{f'{field}__isnull': True})
    return System.objects.filter(versions__in=sv_qs).order_by('name')


def _get_missing_features(version: SystemVersion) -> list[Feature]:
    """Return Features that have no options set on *version*."""
    existing_feature_ids = set(
        SystemFeature.objects.filter(version=version)
        .exclude(options=None)
        .values_list('feature_id', flat=True)
    )
    features = Feature.objects.exclude(id__in=existing_feature_ids).prefetch_related('options').order_by('category', 'label')
    return list(features)


class Command(EnricherBaseCommand):
    help = 'Fill missing SystemVersion fields using an LLM and save a pending version'

    def add_arguments(self, parser: ArgumentParser):
        super().add_arguments(parser)
        parser.add_argument('--per-feature', action='store_true',
                            help='One LLM call per missing Feature (slower, more targeted)')
        all_fields = list(SIMPLE_TEXT_FIELDS) + list(INT_FIELDS) + list(URL_FK_FIELDS) + list(M2M_ATTR_FIELDS)
        parser.add_argument('--missing', metavar='FIELD', default=None,
                            choices=all_fields,
                            help=f'Process every system whose current version is missing FIELD '
                                 f'(instead of providing KEYWORDs). '
                                 f'Valid fields: {", ".join(all_fields)}')
        parser.add_argument('--add-tag', metavar='TAG', default=None,
                            help='Create a new approved SystemVersion adding TAG to the target '
                                 'systems (matched by name or slug). Skips LLM enrichment.')

    def handle(self, *args, **options):
        seen = {}
        missing_field = options.get('missing')
        add_tag = options.get('add_tag')

        # Resolve tag option before building the system list
        tag_option = None
        if add_tag:
            tag_option = (
                AttributeOption.objects
                .filter(attribute__slug='tag')
                .filter(Q(name=add_tag) | Q(slug=add_tag))
                .first()
            )
            if tag_option is None:
                raise CommandError(f"No tag found with name or slug '{add_tag}'")
            self.stdout.write(f"Tag: {tag_option.name} (slug={tag_option.slug})")

        if missing_field:
            for system in _query_systems_missing_field(missing_field):
                seen[system.pk] = system
        else:
            if not options['keywords']:
                raise CommandError("Provide at least one KEYWORD or use --missing=FIELD")
            for keyword in options['keywords']:
                if keyword.isdigit():
                    qs = System.objects.filter(id=int(keyword))
                else:
                    qs = System.objects.filter(slug__icontains=keyword)
                if not qs.exists():
                    raise CommandError(f"No system found with keyword '{keyword}'")
                for system in qs:
                    seen.setdefault(system.pk, system)
        systems = list(seen.values())

        mode = options['mode']
        do_enrich = mode in ('enrich', 'both')
        do_extract_urls = mode in ('extract-urls', 'both')

        limit = options['limit']
        sleep_secs = options['sleep']
        processed = 0
        prev_did_work = False
        for system in systems:
            if limit is not None and processed >= limit:
                break
            if do_enrich and system.pending_version():
                LOG.warning("Skipping '%s': has a pending (unapproved) SystemVersion", system.slug)
                continue
            if sleep_secs and prev_did_work:
                time.sleep(sleep_secs)
            did_work = False
            try:
                if add_tag:
                    did_work = self._add_tag_one(system, tag_option, options)
                else:
                    if do_enrich:
                        did_work |= self._enrich_one(system, options)
                    if do_extract_urls:
                        did_work |= self._extract_urls_one(system, options)
                processed += 1
            except Exception as e:
                did_work = True  # work was started before the failure
                if not options['skip_errors']:
                    raise
                self.stderr.write(self.style.ERROR(f"Error enriching '{system.slug}': {e}"))
            prev_did_work = did_work

    def _add_tag_one(self, system: System, tag_option: AttributeOption, options: dict) -> bool:
        system.refresh_from_db()
        dry_run: bool = options['dry_run']

        try:
            current = SystemVersion.objects.get(system=system, is_current=True)
        except SystemVersion.DoesNotExist:
            raise CommandError(f"No current SystemVersion for '{system.slug}'")

        if current.tags.filter(pk=tag_option.pk).exists():
            self.stdout.write(f"  '{system.name}' already has tag '{tag_option.name}', skipping")
            return False

        self.stdout.write(f"  Adding tag '{tag_option.name}' to '{system.name}'...")

        if dry_run:
            self.stdout.write(self.style.WARNING("  [DRY RUN] Would create new approved SystemVersion"))
            return True

        with transaction.atomic():
            new_sv = clone_system_version(
                current,
                username=settings.DBDB_BOT_ACCOUNT,
                comment=f"Added tag '{tag_option.name}'",
                approved=True,
                attribute_options=[tag_option],
            )
            finalize_new_version(new_sv)

        self.stdout.write(self.style.SUCCESS(
            f"  Created SystemVersion #{new_sv.ver} for '{system.name}'"
        ))
        return True

    def _extract_urls_one(self, system: System, options: dict, *, enricher=None) -> bool:
        system.refresh_from_db()
        dry_run: bool = options['dry_run']

        try:
            current = SystemVersion.objects.get(system=system, is_current=True)
        except SystemVersion.DoesNotExist:
            raise CommandError(f"No current SystemVersion for '{system.slug}'")

        if current.system_url_id is None:
            LOG.info("Skipping '%s': no system_url to crawl", system.slug)
            return False

        if current.system_url.status in (CitationUrl.Status.DEAD, CitationUrl.Status.SPAM):
            LOG.info("Skipping '%s': system_url status is %s", system.slug, current.system_url.status.name)
            return False

        # Determine which URL fields are missing on the current version.
        # Also check the existing pending version so we don't overwrite fields
        # that were already filled by a prior _enrich_one() call.
        url_fields = ['docs_url', 'twitter_handle']
        missing = [f for f in url_fields if _is_field_empty(current, f)]
        pending = system.pending_version()
        if pending:
            missing = [f for f in missing if _is_field_empty(pending, f)]
        if not missing:
            self.stdout.write(f"  '{system.name}': all URL fields already set, skipping extraction")
            return False

        # Past this point we crawl the homepage and call the LLM.
        cutoff = timezone.now() - timedelta(days=options['recrawl_after'])
        crawl_citation_url(
            current.system_url,
            system=system,
            recrawl_cutoff=cutoff,
            skip_spamcheck=options['skip_spamcheck'],
        )

        try:
            raw_html = current.system_url.content.raw
        except AttributeError:
            raw_html = ''

        if not raw_html:
            # crawl_citation_url may have served cached text without saving raw HTML
            # (e.g. URLs crawled before the raw field existed). Force a fresh fetch.
            _, info = process_citation_url(
                current.system_url,
                system=system,
                skip_spamcheck=options['skip_spamcheck'],
            )
            raw_html = (info or {}).get('raw') or ''

        if not raw_html:
            LOG.info("Skipping '%s': could not retrieve homepage content", system.slug)
            return True  # crawling was attempted; count as work to avoid rapid retries

        if enricher is None:
            enricher = BaseEnricher.create(options['enricher'])
        enricher.set_context(name=system.name)

        tool = build_url_extraction_tool(system, missing)
        expected_keys = set(tool['input_schema']['properties'].keys())
        prompts = enricher.build_homepage_url_prompt(system.name, raw_html, missing)
        result = {}
        for prompt in prompts:
            chunk_result = enricher.call_llm(prompt, tool, model_override=options.get('model'), dry_run=dry_run)
            for key, val in chunk_result.items():
                if val and key not in result:
                    result[key] = val
            if all(result.get(k) for k in expected_keys):
                break

        new_docs_url = None
        new_twitter_handle = None

        if 'docs_url' in missing:
            url_str = (result.get('docs_url') or '').strip()
            if url_str:
                try:
                    norm = normalize_url(url_str)
                    existing = CitationUrl.objects.filter(url=norm).first()
                    if existing:
                        new_docs_url = existing
                    else:
                        citation = CitationUrl.objects.create(url=norm, status=CitationUrl.Status.UNKNOWN)
                        citation, info = process_citation_url(citation, system=system, skip_spamcheck=options['skip_spamcheck'])
                        if info is None or info['status'] == CitationUrl.Status.VALID:
                            if info is not None:
                                citation.save()
                            new_docs_url = citation
                        else:
                            LOG.warning("docs_url: %r is unreachable, skipping", url_str)
                            citation.delete()
                except Exception as e:
                    LOG.warning("docs_url: could not validate %r: %s", url_str, e)

        if 'twitter_handle' in missing:
            raw_twitter = (result.get('twitter_url') or '').strip()
            if raw_twitter:
                new_twitter_handle = _extract_twitter_handle(raw_twitter)

        if dry_run:
            self.stdout.write(
                f"  [DRY RUN] docs_url={new_docs_url!r}, twitter_handle={new_twitter_handle!r}"
            )
            return True

        if new_docs_url is None and new_twitter_handle is None:
            self.stdout.write(f"  '{system.name}': nothing extracted from homepage")
            return True

        bot_user = User.objects.get(username=settings.DBDB_BOT_ACCOUNT)
        with transaction.atomic():
            pending = system.pending_version()
            if pending:
                new_sv = pending
                self.stdout.write(f"  Reusing existing pending SystemVersion #{new_sv.ver}")
            else:
                new_sv = clone_system_version(
                    current,
                    approved=False,
                    creator=bot_user,
                    comment='Auto URL extraction by enrich_system command',
                )
            if new_docs_url is not None:
                new_sv.docs_url = new_docs_url
            if new_twitter_handle is not None:
                new_sv.twitter_handle = new_twitter_handle
            new_sv.save()

        self.stdout.write(self.style.SUCCESS(
            f"  Extracted for '{system.name}': "
            f"docs_url={new_docs_url}, twitter_handle={new_twitter_handle}"
        ))
        return True

    def _enrich_one(self, system: System, options: dict) -> bool:
        system.refresh_from_db()

        dry_run: bool = options['dry_run']
        model_override: str | None = options['model']
        per_feature: bool = options['per_feature']
        requested_fields: list[str] | None = (
            [f.strip() for f in options['fields'].split(',')]
            if options['fields'] else None
        )

        # --- 1. Load current version ---
        try:
            current = SystemVersion.objects.prefetch_related(
                'project_types', 'licenses', 'oses', 'written_in',
                'features', 'features__options',
            ).get(system=system, is_current=True)
        except SystemVersion.DoesNotExist:
            raise CommandError(f"No current SystemVersion for '{system.slug}'")

        self.stdout.write(f"System: {system.name} (current ver #{current.ver})")
        enricher = BaseEnricher.create(options['enricher'])

        # --- 2. Identify missing fields ---
        skip_fields = set(options['skip_field'])
        missing_fields = [f for f in _get_missing_fields(current, requested_fields) if f not in skip_fields]
        missing_features = [f for f in _get_missing_features(current) if f.slug not in skip_fields]

        if not missing_fields and not missing_features:
            self.stdout.write(self.style.SUCCESS("All fields are already filled. Nothing to do."))
            return False

        if missing_fields:
            self.stdout.write(f"Missing fields: {', '.join(missing_fields)}")
        if missing_features:
            self.stdout.write(f"Missing features: {len(missing_features)} of {Feature.objects.count()}")

        # --- 3. Crawl existing URLs (opt-in via --include-urls) ---
        crawled_pages: dict[str, str] = {}
        if options['include_urls']:
            self.stdout.write("Crawling existing URLs...")
            crawled_pages = _crawl_existing_urls(current, system, recrawl_after=options['recrawl_after'], skip_spamcheck=options['skip_spamcheck'])
            self.stdout.write(f"  Crawled {len(crawled_pages)} page(s)")

        # --- 3b. Fetch README from GitHub source repo ---
        sourcerepo: CitationUrl | None = current.sourcerepo_url
        if sourcerepo and 'github.com' in sourcerepo.url.lower():
            try:
                token = getattr(settings, 'GITHUB_API_TOKEN', None) or None
                collector = GitHubCollector(token=token, delete_on_exit=False)
                collector.clone_url(sourcerepo.url, pull=False)
                readme = collector.get_readme()
                if readme:
                    crawled_pages[f"{sourcerepo.url}/README.md"] = readme
                    self.stdout.write(f"  Fetched README.md from {sourcerepo.url} ({len(readme):,} chars)")
                else:
                    self.stdout.write(f"  No README.md found in {sourcerepo.url}")
            except Exception:
                LOG.warning("Could not fetch README from %s", sourcerepo.url, exc_info=True)
        else:
            LOG.warning(f"Not retrieving {system.name} README [sourcerepo={sourcerepo}]")

        # --- 4. Load taxonomy ---
        features = list(Feature.objects.prefetch_related('options').order_by('category', 'label'))
        missing_sv_fields = [f for f in missing_fields if f in M2M_ATTR_SLUGS]
        attributes = list(
            Attribute.objects
            .filter(sv_field__in=missing_sv_fields)
            .prefetch_related('options')
            .order_by('name')
        )

        # --- 5. Call LLM ---
        enrichment: dict = {}

        org_names = [o.name for o in current.developer_orgs.all()]
        enricher.set_context(name=system.name, organization=org_names[0] if org_names else '')

        if not per_feature:
            # Single comprehensive call
            self.stdout.write("Calling LLM (single call)...")
            prompt = enricher.build_system_prompt(system=system, current_version=current,
                                                  fields=missing_fields + (['features'] if missing_features else []),
                                                  features=missing_features, attributes=attributes,
                                                  crawled_pages=crawled_pages)
            LOG.debug(prompt)
            # sys.exit(1)
            try:
                enrichment = enricher.call_llm(prompt, SYSTEM_ENRICHMENT_TOOL, model_override, dry_run=dry_run)
            except Exception as e:
                raise CommandError(f"LLM call failed: {e}")
        else:
            # Per-feature calls — merge results into enrichment dict
            if missing_fields:
                self.stdout.write("Calling LLM for metadata fields...")
                prompt = enricher.build_system_prompt(system=system, current_version=current, fields=missing_fields,
                                                      features=[], attributes=attributes, crawled_pages=crawled_pages)
                try:
                    enrichment = enricher.call_llm(prompt, SYSTEM_ENRICHMENT_TOOL, model_override, dry_run=dry_run)
                except Exception as e:
                    raise CommandError(f"LLM call failed: {e}")

            enrichment.setdefault('features', {})
            enrichment.setdefault('citations', [])
            for feature in missing_features:
                self.stdout.write(f"  Calling LLM for feature: {feature.label}")
                prompt = enricher.build_feature_prompt(system, feature, crawled_pages)
                try:
                    result = enricher.call_llm(prompt, SYSTEM_ENRICHMENT_TOOL, model_override, dry_run=dry_run)
                    enrichment['features'].update(result.get('features', {}))
                    enrichment['citations'].extend(result.get('citations', []))
                except Exception as e:
                    LOG.warning(f"LLM call failed for feature {feature.slug}: {e}")

        # --- 6. Validate citations ---
        self.stdout.write("Validating citations...")
        raw_citations = enrichment.get('citations', [])
        valid_citations = enricher.validate_citations(raw_citations, system, skip_spamcheck=options['skip_spamcheck'])
        self.stdout.write(f"  {len(valid_citations)}/{len(raw_citations)} citations valid")

        # Drop citations that are simply the system's own known URLs — those are
        # already stored as FK fields and should not also appear as free citations.
        known_urls = {
            c.url
            for field in URL_FK_FIELDS
            if (c := getattr(current, field)) is not None
        }
        before = len(valid_citations)
        valid_citations = {url: val for url, val in valid_citations.items() if url not in known_urls}
        if len(valid_citations) < before:
            self.stdout.write(f"  Excluded {before - len(valid_citations)} known system URL(s) from citations")

        # --- 7. Dry-run exit ---
        if dry_run:
            return

        # --- 8. Build and save pending SystemVersion ---
        bot_user = User.objects.get(username=settings.DBDB_BOT_ACCOUNT)

        with transaction.atomic():
            last_model = enricher.get_last_model()
            enrichment_comment = f"Auto-enriched by enrich_system command (model: {last_model})"
            existing_pending = system.pending_version()
            if existing_pending:
                new_sv = existing_pending
                new_sv.comment = enrichment_comment
                self.stdout.write(f"Reusing existing pending SystemVersion #{new_sv.ver}")
            else:
                new_sv = clone_system_version(
                    current,
                    approved=False,
                    creator=bot_user,
                    comment=enrichment_comment,
                )

            # Apply simple text / int fields
            dirty = False
            for field in SIMPLE_TEXT_FIELDS:
                if field in missing_fields:
                    val = enrichment.get(field, '')
                    if val:
                        if field == 'twitter_handle' and field[0] != '@':
                            val = f"@{val}"
                        setattr(new_sv, field, val)
                        dirty = True

            for field in INT_FIELDS:
                if field in missing_fields:
                    val = enrichment.get(field)
                    if val:
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
                    citation, info = process_citation_url(citation, system=system, skip_spamcheck=options['skip_spamcheck'])
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
                    self.stdout.write(f"  attr  {field}: (empty, skipping)")
                    continue
                opts = list(
                    AttributeOption.objects.filter(
                        attribute__slug=attr_slug,
                        slug__in=slugs,
                    )
                )
                if opts:
                    getattr(new_sv, field).add(*opts)
                    self.stdout.write(f"  attr  {field}: {', '.join(o.name for o in opts)}")
                else:
                    self.stdout.write(f"  attr  {field}: no matching options for slugs {slugs}")

            # Attach citations to citation M2M fields
            for norm_url, (cite_obj, fields) in valid_citations.items():
                for field in fields:
                    cite_m2m = FIELD_CITATION_MAP.get(field)
                    if cite_m2m:
                        getattr(new_sv, cite_m2m).add(cite_obj)
                        self.stdout.write(f"  cite  {field}: {norm_url}")

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
                    self.stdout.write(f"  feat  {feat_slug}: no matching options for slugs {option_slugs}")
                    LOG.warning(f"No matching options for feature {feat_slug}: {option_slugs}")
                    continue
                sf, _ = SystemFeature.objects.get_or_create(
                    version=new_sv,
                    feature=feature,
                    defaults={'system': None},
                )
                sf.options.set(opts)
                self.stdout.write(f"  feat  {feature.label}: {', '.join(o.value for o in opts)}")

        verb = "Updated" if existing_pending else "Created"
        self.stdout.write(self.style.SUCCESS(
            f"\n{verb} pending SystemVersion #{new_sv.ver} for '{system.name}'"
        ))
        fields_filled = [
            f for f in missing_fields
            if enrichment.get(f) not in (None, '', [], {})
        ]
        if fields_filled:
            self.stdout.write(f"Fields filled: {', '.join(fields_filled)}")
        if feat_suggestions:
            self.stdout.write(f"Features set: {', '.join(feat_suggestions.keys())}")
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current().domain
        self.stdout.write(f"Review and approve: http://{domain}{new_sv.get_diff_url()}")
        return True
