"""ClaudeEnricher — Anthropic tool_use backend."""
import logging

import anthropic
from django.conf import settings

from .base import BaseEnricher
from .schema import get_system_prompt

LOG = logging.getLogger(__name__)


class ClaudeEnricher(BaseEnricher):

    def call_llm(
        self,
        user_prompt: str,
        tool_schema: dict,
        model_override: str | None = None,
    ) -> dict:
        model = model_override or settings.ENRICHMENT_LLM_MODEL
        tool_name = tool_schema["name"]
        LOG.debug(f"Calling Anthropic model={model} tool={tool_name}")
        LOG.debug("Prompt:\n%s", user_prompt)
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=get_system_prompt(tool_name),
                tools=[tool_schema],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[{"role": "user", "content": user_prompt}],
            )
            for block in response.content:
                if block.type == "tool_use" and block.name == tool_name:
                    LOG.debug("Response:\n%s", block.input)
                    return block.input
            raise RuntimeError(f"Anthropic response contained no {tool_name} tool call")
        except anthropic.APIError as e:
            LOG.warning(f"Anthropic API error: {e} — falling back to Ollama")
            from .ollama import OllamaEnricher
            return OllamaEnricher().call_llm(user_prompt, tool_schema, model_override)
