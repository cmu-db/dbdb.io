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
    ) -> dict:
        """Invoke the provider LLM; return the parsed result dict."""

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
            "Provide citations for every claim you make."
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
            "\nUse the save_enrichment tool. Only fill the 'features' key for this feature "
            "and provide citations."
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
            "Provide citations for every claim you make."
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
            "with concrete examples and citations."
        )
        return "".join(parts)

    # ------------------------------------------------------------------
    # Citation validation
    # ------------------------------------------------------------------

    def validate_citations(
        self,
        raw_citations: list[dict],
        system: System,
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
                    citation_obj, result = process_citation_url(citation_obj, system=system)
                    if result is None:
                        norm_url = citation_obj.url
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

    @classmethod
    def create(cls, model_override: str | None = None) -> "BaseEnricher":
        """Return the right enricher based on model name and available API keys."""
        from django.conf import settings
        from .claude import ClaudeEnricher
        from .chatgpt import ChatGPTEnricher
        from .ollama import OllamaEnricher
        from .perplexity import PerplexityEnricher

        model = (model_override or getattr(settings, "ENRICHMENT_LLM_MODEL", "")).lower()

        if model.startswith(("gpt-", "o1", "o3", "o4")):
            return ChatGPTEnricher()
        if model.startswith("sonar") or "perplexity" in model:
            return PerplexityEnricher()
        if getattr(settings, "ANTHROPIC_API_KEY", ""):
            return ClaudeEnricher()
        if getattr(settings, "PERPLEXITY_API_KEY", ""):
            return PerplexityEnricher()
        if getattr(settings, "OPENAI_API_KEY", ""):
            return ChatGPTEnricher()
        return OllamaEnricher()
