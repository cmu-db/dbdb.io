"""
LLM-based enrichment for SystemVersion records.

Builds prompts from existing system data and crawled page content, invokes an
LLM (Anthropic Claude primary, Ollama fallback), parses the structured response,
and validates the suggested citations.
"""
import json
import logging

import anthropic
import ollama
from django.conf import settings

from dbdb.core.models import (
    Attribute, AttributeOption,
    CitationUrl,
    Feature, FeatureOption,
    System, SystemVersion,
)
from dbdb.core.utils.citations import normalize_url, process_citation_url

LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schema — used for Anthropic tool_use; also documents expected JSON
# structure for Ollama fallback.
# ---------------------------------------------------------------------------

SAVE_ENRICHMENT_TOOL = {
    "name": "save_enrichment",
    "description": (
        "Save extracted information about a database system. "
        "Only include fields you are confident about. "
        "All option slugs must match exactly the provided taxonomy."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Prose summary of what the system is and the workloads it targets.",
            },
            "history": {
                "type": "string",
                "description": "Narrative of the system's origins, milestones, and lineage.",
            },
            "start_year": {
                "type": "integer",
                "description": "Year the project was first released or publicly announced.",
            },
            "end_year": {
                "type": ["integer", "null"],
                "description": "Year active development ceased, or null if still active.",
            },
            "system_url": {
                "type": "string",
                "description": "Official homepage URL.",
            },
            "docs_url": {
                "type": "string",
                "description": "Official technical documentation URL.",
            },
            "sourcerepo_url": {
                "type": "string",
                "description": "Public source-code repository URL.",
            },
            "wikipedia_url": {
                "type": "string",
                "description": "Wikipedia article URL.",
            },
            "twitter_handle": {
                "type": "string",
                "description": "Twitter/X handle (without @).",
            },
            "linkedin_handle": {
                "type": "string",
                "description": "LinkedIn page handle or URL.",
            },
            "project_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of project-type AttributeOption slugs.",
            },
            "licenses": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of license AttributeOption slugs.",
            },
            "oses": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of OS AttributeOption slugs.",
            },
            "written_in": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of programming-language AttributeOption slugs.",
            },
            "features": {
                "type": "object",
                "description": "Map of feature_slug → [option_slug, …]. Only include features you are confident about.",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "citations": {
                "type": "array",
                "description": "URLs that support the provided information.",
                "items": {
                    "type": "object",
                    "required": ["url", "fields"],
                    "properties": {
                        "url": {"type": "string"},
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Field names this URL supports (e.g. ['description', 'start_year']).",
                        },
                    },
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an expert database researcher. "
    "Your task is to fill in missing information about a database management system "
    "based on the page content provided and your training knowledge. "
    "Only include information you are confident about. "
    "For every claim, provide a citation URL in the citations list. "
    "All feature option slugs and attribute option slugs MUST exactly match the "
    "taxonomy provided — do not invent new slugs."
)


def build_full_prompt(
    system: System,
    current_version: SystemVersion,
    missing_fields: list[str],
    crawled_pages: dict[str, str],
    features: list,
    attributes: list,
) -> str:
    """Build the user-turn prompt for a single comprehensive LLM call."""
    parts = [f"# System: {system.name}\n"]

    # Existing non-empty context
    if current_version.description:
        parts.append(f"## Existing Description\n{current_version.description[:500]}\n")
    if current_version.start_year:
        parts.append(f"Existing Start Year: {current_version.start_year}\n")

    # Crawled page excerpts
    if crawled_pages:
        parts.append("## Crawled Pages\n")
        for url, text in crawled_pages.items():
            parts.append(f"### {url}\n{text[:3000]}\n")

    # Missing fields to fill
    parts.append(f"## Missing Fields to Fill\n{', '.join(missing_fields)}\n")

    # Feature taxonomy
    parts.append("## Feature Taxonomy (slug → label → options)\n")
    for feature in features:
        opts = [f"{o.slug}={o.value!r}" for o in feature.options.all()]
        parts.append(f"- {feature.slug} ({feature.label}): {', '.join(opts)}\n")

    # Attribute taxonomy
    parts.append("## Attribute Taxonomy (slug → name → options)\n")
    for attr in attributes:
        opts = [f"{o.slug}={o.name!r}" for o in attr.options.all()]
        sv_field = attr.sv_field
        parts.append(f"- {sv_field} ({attr.name}): {', '.join(opts)}\n")

    parts.append(
        "\nUse the save_enrichment tool to return your answer. "
        "Only fill the missing fields listed above. "
        "Provide citations for every claim you make."
    )
    return "".join(parts)


def build_feature_prompt(
    system: System,
    feature: Feature,
    crawled_pages: dict[str, str],
) -> str:
    """Build a focused prompt for a single feature (used in --per-feature mode)."""
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


# ---------------------------------------------------------------------------
# LLM invocation
# ---------------------------------------------------------------------------

def call_llm(user_prompt: str, model_override: str | None = None) -> dict:
    """
    Call Anthropic Claude (primary) or Ollama (fallback).
    Returns parsed enrichment dict from the save_enrichment tool.
    Raises RuntimeError if neither backend succeeds.
    """
    model = model_override or settings.ENRICHMENT_LLM_MODEL

    if settings.ANTHROPIC_API_KEY:
        LOG.debug(f"Calling Anthropic model={model}")
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                tools=[SAVE_ENRICHMENT_TOOL],
                tool_choice={"type": "tool", "name": "save_enrichment"},
                messages=[{"role": "user", "content": user_prompt}],
            )
            for block in response.content:
                if block.type == "tool_use" and block.name == "save_enrichment":
                    return block.input
            raise RuntimeError("Anthropic response contained no save_enrichment tool call")
        except anthropic.APIError as e:
            LOG.warning(f"Anthropic API error: {e} — falling back to Ollama")

    # Ollama fallback
    fallback_model = model_override or settings.ENRICHMENT_LLM_FALLBACK_MODEL
    LOG.debug(f"Calling Ollama model={fallback_model}")
    schema_str = json.dumps(SAVE_ENRICHMENT_TOOL["input_schema"], indent=2)
    ollama_prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Return ONLY a valid JSON object matching this schema (no prose, no markdown):\n"
        f"{schema_str}\n\n"
        f"{user_prompt}"
    )
    LOG.debug("Ollama prompt:\n%s", ollama_prompt)
    resp = ollama.chat(
        model=fallback_model,
        messages=[{"role": "user", "content": ollama_prompt}],
        options={"temperature": 0.2},
    )
    text = resp["message"]["content"].strip()
    LOG.debug("Ollama raw response:\n%s", text)
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    LOG.debug("Ollama text after fence strip:\n%s", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        LOG.error("JSON parse failed at %s (char %d)", e.msg, e.pos)
        LOG.error("Offending text: %r", text[:500])
        raise


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------

def validate_citations(
    raw_citations: list[dict],
    system: System,
) -> dict[str, tuple[CitationUrl, list[str]]]:
    """
    Validate each suggested citation URL.

    Returns a dict mapping normalized_url → (CitationUrl, field_list) for
    citations whose status is VALID.  DEAD/SPAM/IGNORE citations are logged
    and dropped.
    """
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

        # Only re-fetch if we haven't validated recently
        if citation_obj.status == CitationUrl.Status.UNKNOWN or citation_obj.last_checked is None:
            try:
                citation_obj, result = process_citation_url(citation_obj, system=system)
                if result is None:
                    # was merged; surviving citation already has its status set
                    norm_url = citation_obj.url
                else:
                    citation_obj.status = result["status"]
                    citation_obj.last_title = result.get("title")
                    citation_obj.save(update_fields=["status", "last_title", "last_statuscode",
                                                     "last_contenttype", "last_contentsize",
                                                     "last_etag", "last_modified", "last_cachecontrol"])
            except Exception as e:
                LOG.warning(f"Failed to fetch citation {norm_url}: {e}")
                continue

        if citation_obj.status == CitationUrl.Status.VALID:
            valid[norm_url] = (citation_obj, fields)
        else:
            LOG.debug(f"Dropping citation {norm_url}: status={citation_obj.status}")

    return valid
