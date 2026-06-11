"""
BaseEnricher ABC — prompt builders, citation validator, and provider factory.
"""
import logging
from abc import ABC, abstractmethod

from dbdb.core.models import Attribute, CitationUrl, Feature, System, SystemVersion
from dbdb.core.utils.citations import normalize_url, process_citation_url

LOG = logging.getLogger(__name__)

# Fields we never ask the LLM to fill — either too risky to auto-populate
# or expected to be set by other means (e.g. crawling, manual entry).
_PROMPT_EXCLUDED_FIELDS = frozenset({
    'system_url', 'wikipedia_url', 'sourcerepo_url', 'hosted_services',
})


class BaseEnricher(ABC):

    @abstractmethod
    def call_llm(
        self,
        user_prompt: str,
        tool_schema: dict,
        model_override: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Invoke the provider LLM; return the parsed result dict.

        If *dry_run* is True, print the prompt that would be sent and return {}
        without making any API call.
        """

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def build_system_prompt(
        self,
        system: System,
        current_version: SystemVersion,
        fields: list[str],
        features: list[Feature],
        attributes: list[Attribute],
        crawled_pages: dict[str, str],
    ) -> str:
        LOG.debug(f"fields={fields}, features={features}, attributes={attributes}")

        # Strip fields we never populate via LLM.
        active_fields = [f for f in fields if f not in _PROMPT_EXCLUDED_FIELDS]

        parts = [f"# System: {system.name}\n"]

        if current_version.description:
            parts.append(f"## Existing Description\n{current_version.description[:500]}\n")
        if current_version.start_year:
            parts.append(f"Existing Start Year: {current_version.start_year}\n")

        if crawled_pages:
            parts.append("## Crawled Pages\n")
            for url, text in crawled_pages.items():
                parts.append(f"### {url}\n{text[:3000]}\n")

        if active_fields:
            parts.append(f"## Missing Fields to Fill\n{', '.join(active_fields)}\n")

        if features:
            parts.append("## Feature Taxonomy (slug → label → options)\n")
            for feature in features:
                opts = [f"{o.slug}={o.value!r}" for o in feature.options.all()]
                parts.append(f"- {feature.slug} ({feature.label}): {', '.join(opts)}\n")

        if attributes:
            parts.append("## Attribute Taxonomy (slug → name → options)\n")
            for attr in attributes:
                opts = [f"{o.slug}={o.name!r}" for o in attr.options.all()]
                parts.append(f"- {attr.sv_field} ({attr.name}): {', '.join(opts)}\n")

        parts.append(
            "\nUse the save_enrichment tool to return your answer. "
            "Only fill the missing fields listed above. "
            "Provide citations for every claim you make. "
            "Use only neutral, factual language — no marketing copy or subjective assessments."
        )
        return "".join(parts)

    def build_feature_prompt(
        self,
        system: System,
        feature: Feature,
        crawled_pages: dict[str, str],
    ) -> str:
        opts = [f"{o.slug}={o.value!r}" for o in feature.options.all()]
        parts = [
            f"# System: {system.name}\n",
            f"## Feature: {feature.label} (slug: {feature.slug})\n",
            f"Options: {', '.join(opts)}\n",
        ]
        if crawled_pages:
            parts.append("## Crawled Pages\n")
            for url, text in crawled_pages.items():
                parts.append(f"### {url}\n{text[:3000]}\n")
        parts.append(
            "\nUse the save_enrichment tool. Only fill the 'features' key for this feature, "
            "provide citations, and use only neutral, factual language."
        )
        return "".join(parts)

    def build_org_prompt(
        self,
        org,
        missing_fields: list[str],
        crawled_pages: dict[str, str],
    ) -> str:
        parts = [f"# Organization: {org.name}\n"]
        if crawled_pages:
            parts.append("## Crawled Pages\n")
            for url, text in crawled_pages.items():
                parts.append(f"### {url}\n{text[:3000]}\n")
        parts.append(f"## Missing Fields to Fill\n{', '.join(missing_fields)}\n")
        parts.append(
            "\nUse the save_org_enrichment tool to return your answer. "
            "Only fill the missing fields listed above. "
            # "Provide citations for every claim you make. "
            "Use only neutral, factual language — no marketing copy or subjective assessments."
        )
        return "".join(parts)

    def build_doc_prompt(
        self,
        entity,
        crawled_pages: dict[str, str],
    ) -> str:
        parts = [f"# Entity: {entity}\n"]
        if crawled_pages:
            parts.append("## Crawled Pages\n")
            for url, text in crawled_pages.items():
                parts.append(f"### {url}\n{text[:3000]}\n")
        parts.append(
            "\nUse the save_doc_enrichment tool to return a clear description "
            "with concrete examples and citations. "
            "Use only neutral, factual language — no marketing copy or subjective assessments."
        )
        return "".join(parts)

    # ------------------------------------------------------------------
    # Citation validation
    # ------------------------------------------------------------------

    def validate_citations(
        self,
        raw_citations: list[dict],
        system: System,
        skip_spamcheck: bool = False,
    ) -> dict[str, tuple[CitationUrl, list[str]]]:
        valid: dict[str, tuple[CitationUrl, list[str]]] = {}

        for entry in raw_citations:
            raw_url = entry.get("url", "").strip()
            fields = entry.get("fields", [])
            if not raw_url:
                continue

            try:
                norm_url = normalize_url(raw_url)
            except Exception:
                norm_url = raw_url

            citation_obj, _ = CitationUrl.objects.get_or_create(url=norm_url)

            if citation_obj.status == CitationUrl.Status.UNKNOWN or citation_obj.last_checked is None:
                try:
                    citation_obj, result = process_citation_url(citation_obj, system=system, skip_spamcheck=skip_spamcheck)
                    if result is None:
                        norm_url = citation_obj.url
                    elif result["status"] != CitationUrl.Status.VALID:
                        LOG.warning(f"{citation_obj} status is {citation_obj.status}. Skipping...")
                    else:
                        citation_obj.status = result["status"]
                        citation_obj.last_title = result.get("title")
                        citation_obj.save(update_fields=[
                            "status", "last_title", "last_statuscode",
                            "last_contenttype", "last_contentsize",
                            "last_etag", "last_modified", "last_cachecontrol",
                        ])
                except Exception as e:
                    LOG.warning(f"Failed to fetch citation {norm_url}: {e}")
                    continue

            if citation_obj.status == CitationUrl.Status.VALID:
                valid[norm_url] = (citation_obj, fields)
            else:
                LOG.debug(f"Dropping citation {norm_url}: status={citation_obj.status}")

        return valid

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    # Settings key required for each enricher name (None = no key needed).
    # Keyed by the lowercase class-name stem, e.g. 'claude' for ClaudeEnricher.
    _REQUIRED_SETTING: dict[str, str | None] = {
        'claude':     'ANTHROPIC_API_KEY',
        'chatgpt':    'OPENAI_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY',
        'ollama':     None,
    }

    @classmethod
    def _get_registry(cls) -> dict[str, type["BaseEnricher"]]:
        """Return {name: subclass} by importing every non-base module in this package."""
        import importlib
        import pkgutil
        from pathlib import Path

        pkg_dir = Path(__file__).parent
        for _, mod_name, _ in pkgutil.iter_modules([str(pkg_dir)]):
            if mod_name not in ('base', 'schema'):
                importlib.import_module(f'.{mod_name}', package=__package__)

        return {
            sub.__name__.removesuffix('Enricher').lower(): sub
            for sub in cls.__subclasses__()
        }

    @classmethod
    def create(cls, enricher_type: str, model_override: str | None = None) -> "BaseEnricher":
        """Instantiate the named enricher, raising ValueError if its required settings key is absent."""
        from django.conf import settings

        registry = cls._get_registry()
        if enricher_type not in registry:
            raise ValueError(
                f"Unknown enricher {enricher_type!r}. "
                f"Choose one of: {', '.join(sorted(registry))}"
            )

        required_key = cls._REQUIRED_SETTING.get(enricher_type)
        if required_key and not getattr(settings, required_key, ''):
            raise ValueError(
                f"enricher {enricher_type!r} requires {required_key} to be set in settings"
            )

        return registry[enricher_type]()
