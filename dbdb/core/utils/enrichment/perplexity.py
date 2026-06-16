"""PerplexityEnricher — web-search-backed backend via Perplexity API."""
import json
import logging

from django.conf import settings

from .base import BaseEnricher
from .schema import get_system_prompt

LOG = logging.getLogger(__name__)


class PerplexityEnricher(BaseEnricher):

    def call_llm(
        self,
        user_prompt: str,
        tool_schema: dict,
        model_override: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        import openai

        model = model_override or getattr(settings, "PERPLEXITY_MODEL", "sonar-pro")
        self._last_model = model
        LOG.debug(f"Calling Perplexity model={model}")
        schema_str = json.dumps(tool_schema["input_schema"], indent=2)
        prompt = (
            f"{get_system_prompt(tool_schema['name'], name=self._name, organization=self._organization)}\n\n"
            f"Return ONLY a valid JSON object matching this schema (no prose, no markdown):\n"
            f"{schema_str}\n\n"
            f"{user_prompt}"
        )
        LOG.debug("Prompt:\n%s", prompt)
        if dry_run:
            print(f"=== DRY RUN — Perplexity model={model} ===")
            print(f"[PROMPT]\n{prompt}")
            return {}
        client = openai.OpenAI(
            api_key=settings.PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai",
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = response.choices[0]
        text = choice.message.content.strip()
        LOG.debug("Raw response:\n%s", text)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            result = json.loads(text)
        except json.JSONDecodeError as e:
            LOG.error("JSON parse failed at %s (char %d)", e.msg, e.pos)
            LOG.error("Offending text: %r", text[:500])
            raise

        LOG.debug("Response:\n%s", result)

        # Inject Perplexity's own web-search citations into the result.
        # fields=[] means validate_citations() will verify the URL but won't
        # attach it to any specific field.
        perplexity_citations = getattr(response, "citations", []) or []
        if perplexity_citations:
            LOG.debug("Perplexity provided %d search citations", len(perplexity_citations))
            existing = result.setdefault("citations", [])
            existing_urls = {e.get("url") for e in existing}
            for url in perplexity_citations:
                if url not in existing_urls:
                    existing.append({"url": url, "fields": []})

        return result
