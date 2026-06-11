"""ChatGPTEnricher — OpenAI function-calling backend."""
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
        fn_name = tool_schema["name"]
        LOG.debug(f"Calling OpenAI model={model} function={fn_name}")
        LOG.debug("Prompt:\n%s", user_prompt)
        if dry_run:
            print(f"=== DRY RUN — OpenAI model={model} function={fn_name} ===")
            print(f"[SYSTEM]\n{get_system_prompt(fn_name)}\n")
            print(f"[USER]\n{user_prompt}")
            return {}
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": get_system_prompt(fn_name)},
                {"role": "user", "content": user_prompt},
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": fn_name,
                    "description": tool_schema["description"],
                    "parameters": tool_schema["input_schema"],
                },
            }],
            tool_choice={"type": "function", "function": {"name": fn_name}},
        )
        for choice in response.choices:
            for tc in (choice.message.tool_calls or []):
                if tc.function.name == fn_name:
                    result = json.loads(tc.function.arguments)
                    LOG.debug("Response:\n%s", result)
                    return result
        raise RuntimeError(f"ChatGPT response contained no {fn_name} tool call")
