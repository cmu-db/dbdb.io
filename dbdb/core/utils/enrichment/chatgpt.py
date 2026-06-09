"""ChatGPTEnricher — OpenAI function-calling backend."""
import json
import logging

from django.conf import settings

from .base import BaseEnricher
from .schema import _SYSTEM_PROMPT

LOG = logging.getLogger(__name__)


class ChatGPTEnricher(BaseEnricher):

    def call_llm(
        self,
        user_prompt: str,
        tool_schema: dict,
        model_override: str | None = None,
    ) -> dict:
        import openai

        model = model_override or getattr(settings, "OPENAI_MODEL", "gpt-4o")
        fn_name = tool_schema["name"]
        LOG.debug(f"Calling OpenAI model={model} function={fn_name}")
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
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
                    return json.loads(tc.function.arguments)
        raise RuntimeError(f"ChatGPT response contained no {fn_name} tool call")
