"""
Tool schemas for each enrichable entity type, plus the shared system prompt.
Each schema is passed directly to the LLM backend as the structured output spec.
"""

_SYSTEM_PROMPT_COMMON = (
    "You are an expert database researcher. "
    "Only include information you are confident about. "
    "For every claim, provide a citation URL in the citations list. "
    "Use only neutral, factual language. "
    "Do not include marketing copy, superlatives, or subjective assessments — "
    "for example, do not describe a system as high-performance, industry-leading, "
    "or as handling large volumes of data, and do not describe an organization as "
    "a leading vendor, innovative, or as thriving or struggling."
)

_SYSTEM_PROMPTS: dict[str, str] = {
    "save_enrichment": (
        _SYSTEM_PROMPT_COMMON
        + " Your task is to fill in missing information about {db_desc} "
        "based on the page content provided and your training knowledge. "
        "All feature option slugs and attribute option slugs MUST exactly match the "
        "taxonomy provided - do not invent new slugs."
    ),
    "save_org_enrichment": (
        _SYSTEM_PROMPT_COMMON
        + " Your task is to fill in missing information about an organization / company / person / vendor involved in database development "
        "based on the page content provided and your training knowledge."
    ),
    "save_doc_enrichment": (
        _SYSTEM_PROMPT_COMMON
        + " Your task is to write documentation for a database feature or attribute "
        "based on the page content provided and your training knowledge."
    ),
}


def get_system_prompt(tool_name: str, name: str = '', organization: str = '') -> str:
    template = _SYSTEM_PROMPTS.get(tool_name, _SYSTEM_PROMPTS["save_enrichment"])
    if name:
        db_desc = f"the {name} database management system"
        if organization:
            db_desc += f" from {organization}"
    else:
        db_desc = "a database management system"
    return template.replace('{db_desc}', db_desc)

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
            "wikipedia_url": {
                "type": "string",
                "description": "Wikipedia article URL.",
            },
            "twitter_handle": {
                "type": "string",
                "description": "Twitter/X handle (without @).",
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
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of tag AttributeOption slugs that categorise the system.",
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
# Organization enrichment schema
# ---------------------------------------------------------------------------

# Per-field property definitions for the org enrichment tool.
# build_org_enrichment_tool() selects only the fields that are missing.
_ORG_FIELD_SCHEMAS: dict[str, dict] = {
    "description": {
        "type": "string",
        "description": "One sentence description of the organization. It should be about a company or individual. It should not be about the database system that the company/individual is building. It should only be about the organization.",
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
        "description": "Type of organization. If the organization's name sounds like a person (e.g., it has a first name + last name), then choose 'Individual'.",
    },
    "stock_symbol": {
        "type": "string",
        "description": "Stock ticker symbol (e.g. ORCL, MSFT). Only set if this organization is a company and it is publicly traded.",
    },
    "stock_exchange": {
        "type": "string",
        "description": "Stock exchange where the organization is listed. Only set if publicly traded.",
    },
    "countries": {
        "type": "array",
        "items": {"type": "string"},
        "description": "ISO 3166-1 alpha-2 country codes for countries where this organization originally was started/founded (e.g. [\"US\", \"DE\"]).",
    },
    "former_names": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Previous names this organization was known by.",
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
# Homepage URL extraction schema
# ---------------------------------------------------------------------------

# Per-field LLM property definitions for System homepage URL extraction.
# 'twitter_handle' is exposed as 'twitter_url' so the LLM returns the full URL
# (e.g. https://twitter.com/handle), which we then parse to extract the handle
# reliably via regex rather than trusting the model to strip it cleanly.
_SYSTEM_URL_EXTRACTION_FIELDS: dict[str, dict] = {
    "docs_url": {
        "type": "string",
        "description": "URL of the official documentation site, if linked from this page.",
    },
    "twitter_url": {
        "type": "string",
        "description": (
            "Full Twitter or X.com profile URL found on the page "
            "(e.g. https://twitter.com/handle). Return the full URL, not just the handle."
        ),
    },
}

# Per-field LLM property definitions for Organization homepage URL extraction.
_ORG_URL_EXTRACTION_FIELDS: dict[str, dict] = {
    "linkedin_url": {
        "type": "string",
        "description": (
            "LinkedIn company, school, or personal page URL "
            "(e.g. https://www.linkedin.com/company/handle)."
        ),
    },
}


def build_url_extraction_tool(
    entity: "System | Organization",
    missing_fields: list[str],
) -> dict:
    """
    Build the LLM tool schema for homepage URL extraction.

    Dispatches on the concrete model type so callers pass the entity instance
    directly rather than a magic string, giving Python's type checker something
    to verify.  For Systems, `missing_fields` uses the SystemVersion field names
    ('docs_url', 'twitter_handle'); the schema renames 'twitter_handle' →
    'twitter_url' so the LLM returns a full URL the caller can parse with regex.
    An unsupported type raises TypeError immediately rather than silently
    returning an empty tool.
    """
    from dbdb.core.models import System, Organization
    if isinstance(entity, System):
        # 'twitter_handle' in the SV model → 'twitter_url' in the LLM schema
        field_map = {"docs_url": "docs_url", "twitter_handle": "twitter_url"}
        props = {
            field_map[f]: _SYSTEM_URL_EXTRACTION_FIELDS[field_map[f]]
            for f in missing_fields if f in field_map
        }
    elif isinstance(entity, Organization):
        props = {
            f: _ORG_URL_EXTRACTION_FIELDS[f]
            for f in missing_fields if f in _ORG_URL_EXTRACTION_FIELDS
        }
    else:
        raise TypeError(
            f"build_url_extraction_tool: unsupported entity type {type(entity)!r}"
        )
    return {
        "name": "save_url_extraction",
        "description": "Save URLs found on the entity's homepage.",
        "input_schema": {"type": "object", "properties": props},
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
