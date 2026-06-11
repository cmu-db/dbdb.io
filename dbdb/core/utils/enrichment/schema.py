"""
Tool schemas for each enrichable entity type, plus the shared system prompt.
Each schema is passed directly to the LLM backend as the structured output spec.
"""

_SYSTEM_PROMPT = (
    "You are an expert database researcher. "
    "Your task is to fill in missing information about a database management system "
    "based on the page content provided and your training knowledge. "
    "Only include information you are confident about. "
    "For every claim, provide a citation URL in the citations list. "
    "All feature option slugs and attribute option slugs MUST exactly match the "
    "taxonomy provided — do not invent new slugs. "
    "Use only neutral, factual language. "
    "Do not include marketing copy, superlatives, or subjective assessments — "
    "for example, do not describe a system as high-performance, industry-leading, "
    "or as handling large volumes of data, and do not describe an organization as "
    "a leading vendor, innovative, or as thriving or struggling."
)

# ---------------------------------------------------------------------------
# System enrichment schema
# ---------------------------------------------------------------------------

SYSTEM_ENRICHMENT_TOOL = {
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
            "linkedin_url": {
                "type": "string",
                "description": "Full LinkedIn page URL.",
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

# Backward-compat alias — callers that imported SAVE_ENRICHMENT_TOOL still work.
SAVE_ENRICHMENT_TOOL = SYSTEM_ENRICHMENT_TOOL

# ---------------------------------------------------------------------------
# Organization enrichment schema
# ---------------------------------------------------------------------------

# Per-field property definitions for the org enrichment tool.
# build_org_enrichment_tool() selects only the fields that are missing.
_ORG_FIELD_SCHEMAS: dict[str, dict] = {
    "description": {
        "type": "string",
        "description": "Brief description of the organization and its role in the database ecosystem.",
    },
    "url": {
        "type": "string",
        "description": "Organization's official website URL.",
    },
    "linkedin_url": {
        "type": "string",
        "description": "Organization's LinkedIn page URL.",
    },
    "wikipedia_url": {
        "type": "string",
        "description": "Organization's Wikipedia page URL.",
    },
    "org_type": {
        "type": "string",
        "description": "Type of organization.",
    },
    "stock_symbol": {
        "type": "string",
        "description": "Stock ticker symbol (e.g. ORCL, MSFT). Only set if the organization is publicly traded.",
    },
    "stock_exchange": {
        "type": "string",
        "description": "Stock exchange where the organization is listed. Only set if publicly traded.",
    },
}

_ORG_CITATIONS_SCHEMA = {
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
            },
        },
    },
}


def build_org_enrichment_tool(missing_fields: list[str]) -> dict:
    """Return a save_org_enrichment tool schema limited to *missing_fields*."""
    from dbdb.core.models import OrgType, StockExchange

    _enums = {
        "org_type":      [label for _, label in OrgType.choices],
        "stock_exchange": [label for _, label in StockExchange.choices],
    }

    properties = {}
    for field in missing_fields:
        if field not in _ORG_FIELD_SCHEMAS:
            continue
        schema = dict(_ORG_FIELD_SCHEMAS[field])
        if field in _enums:
            schema["enum"] = _enums[field]
        properties[field] = schema

    properties["citations"] = _ORG_CITATIONS_SCHEMA
    return {
        "name": "save_org_enrichment",
        "description": (
            "Save extracted information about a database organization or vendor. "
            "Only include fields you are confident about."
        ),
        "input_schema": {
            "type": "object",
            "properties": properties,
        },
    }

# ---------------------------------------------------------------------------
# Documentation enrichment schema (Feature / Attribute descriptions)
# ---------------------------------------------------------------------------

DOC_ENRICHMENT_TOOL = {
    "name": "save_doc_enrichment",
    "description": (
        "Save extracted documentation for a database feature or attribute. "
        "Only include information you are confident about."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Clear explanation of the feature or attribute for a technical audience.",
            },
            "examples": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete examples of systems that exhibit this feature/attribute.",
            },
            "citations": {
                "type": "array",
                "description": "URLs that support the description.",
                "items": {
                    "type": "object",
                    "required": ["url", "fields"],
                    "properties": {
                        "url": {"type": "string"},
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}
