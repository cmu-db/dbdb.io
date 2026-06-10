"""
Public API for the enrichment package.

Backward-compat module-level functions preserve existing call signatures so
callers don't need to change until they opt into the class-based API.
"""
from .base import BaseEnricher
from .claude import ClaudeEnricher
from .ollama import OllamaEnricher
from .chatgpt import ChatGPTEnricher
from .perplexity import PerplexityEnricher
from .schema import (
    _SYSTEM_PROMPT,
    SYSTEM_ENRICHMENT_TOOL,
    SAVE_ENRICHMENT_TOOL,
    ORG_ENRICHMENT_TOOL,
    DOC_ENRICHMENT_TOOL,
)

__all__ = [
    "BaseEnricher",
    "ClaudeEnricher",
    "OllamaEnricher",
    "ChatGPTEnricher",
    "PerplexityEnricher",
    "_SYSTEM_PROMPT",
    "SYSTEM_ENRICHMENT_TOOL",
    "SAVE_ENRICHMENT_TOOL",
    "ORG_ENRICHMENT_TOOL",
    "DOC_ENRICHMENT_TOOL",
    "call_llm",
    "validate_citations",
    "build_full_prompt",
    "build_feature_prompt",
]


# ---------------------------------------------------------------------------
# Backward-compat module-level wrappers
# ---------------------------------------------------------------------------

def call_llm(user_prompt: str, model_override: str | None = None) -> dict:
    return BaseEnricher.create(model_override).call_llm(
        user_prompt, SYSTEM_ENRICHMENT_TOOL, model_override
    )


def validate_citations(raw_citations: list, system) -> dict:
    return BaseEnricher.create().validate_citations(raw_citations, system)


def build_full_prompt(system, current_version, missing_fields, crawled_pages, features, attributes) -> str:
    return BaseEnricher.create().build_system_prompt(system, current_version, missing_fields, features, attributes,
                                                     crawled_pages)


def build_feature_prompt(system, feature, crawled_pages) -> str:
    return BaseEnricher.create().build_feature_prompt(system, feature, crawled_pages)
