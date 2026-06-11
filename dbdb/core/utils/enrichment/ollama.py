"""OllamaEnricher — local Ollama JSON-in-prompt backend."""
import json
import logging

import ollama
from django.conf import settings

from .base import BaseEnricher
from .schema import get_system_prompt

LOG = logging.getLogger(__name__)


class OllamaEnricher(BaseEnricher):

    def call_llm(
        self,
        user_prompt: str,
        tool_schema: dict,
        model_override: str | None = None,
    ) -> dict:
        model = model_override or settings.ENRICHMENT_LLM_FALLBACK_MODEL
        LOG.debug(f"Calling Ollama model={model}")
        schema_str = json.dumps(tool_schema["input_schema"], indent=2)
        prompt = (
            f"{get_system_prompt(tool_schema['name'])}\n\n"
            f"Return ONLY a valid JSON object matching this schema (no prose, no markdown):\n"
            f"{schema_str}\n\n"
            f"{user_prompt}"
        )
        LOG.debug("Ollama prompt:\n%s", prompt)
        resp = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )
        text = resp["message"]["content"].strip()
        LOG.debug("Ollama raw response:\n%s", text)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        LOG.debug("Ollama text after fence strip:\n%s", text)
        try:
            result = json.loads(text)
            LOG.debug("Response:\n%s", result)
            return result
        except json.JSONDecodeError as e:
            LOG.error("JSON parse failed at %s (char %d)", e.msg, e.pos)
            LOG.error("Offending text: %r", text[:500])
            raise
