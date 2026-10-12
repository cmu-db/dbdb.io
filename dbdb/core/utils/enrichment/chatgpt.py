"""ChatGPTEnricher — OpenAI function-calling backend (Responses API)."""
import json
import logging

from django.conf import settings

from .base import BaseEnricher
from .schema import get_system_prompt

LOG = logging.getLogger(__name__)


class ChatGPTEnricher(BaseEnricher):

    def call_llm(
        self,
        user_prompt: str,
        tool_schema: dict,
        model_override: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        import openai

        model = model_override or getattr(settings, "OPENAI_MODEL", "gpt-4o")
        self._last_model = model
        fn_name = tool_schema["name"]
        LOG.debug(f"Calling OpenAI model={model} function={fn_name}")
        LOG.debug("Prompt:\n%s", user_prompt)
        if dry_run:
            print(f"=== DRY RUN — OpenAI model={model} function={fn_name} ===")
            print(f"[SYSTEM]\n{get_system_prompt(fn_name, name=self._name, organization=self._organization)}\n")
            print(f"[USER]\n{user_prompt}")
            return {}
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        # Use the Responses API: reasoning models (gpt-5+, o-series) do not allow
        # function tools on /v1/chat/completions unless reasoning_effort is 'none',
        # and some newer models do not support 'none' at all.
        response = client.responses.create(
            model=model,
            instructions=get_system_prompt(fn_name, name=self._name, organization=self._organization),
            input=user_prompt,
            tools=[{
                "type": "function",
                "name": fn_name,
                "description": tool_schema["description"],
                "parameters": tool_schema["input_schema"],
                # Strict mode is the default here; our schemas have optional fields
                "strict": False,
            }],
            tool_choice={"type": "function", "name": fn_name},
        )
        for item in response.output:
            if item.type == "function_call" and item.name == fn_name:
                result = json.loads(item.arguments)
                LOG.debug("Response:\n%s", result)
                return result
        raise RuntimeError(f"ChatGPT response contained no {fn_name} tool call")
