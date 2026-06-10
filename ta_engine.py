"""Provider-neutral Socratic TA engine using LiteLLM."""

from __future__ import annotations

from llm_client import complete
from prompt_loader import PROMPTS


def build_system_prompt(
    lab_name: str,
    lab_content: str,
    ta_language: str,
    ta_custom_instructions: str,
) -> str:
    content = lab_content if lab_content.strip() else "(No documents uploaded.)"
    custom_instructions = (
        ta_custom_instructions
        if ta_custom_instructions
        else "(No additional instructor instructions.)"
    )
    return PROMPTS["ta_system"].render(
        lab_name=lab_name,
        lab_content=content,
        ta_language=ta_language,
        ta_custom_instructions=custom_instructions,
    )


async def get_ta_response(
    api_key: str | None,
    api_base: str | None,
    model: str,
    system_prompt: str,
    history: list[dict],
) -> str:
    """
    Send the full conversation history and return the assistant reply.

    history: list of {"role": "user"|"model", "text": str}
    """
    messages = [
        {"role": "system", "content": system_prompt},
        *[
            {
                "role": "assistant" if msg["role"] == "model" else msg["role"],
                "content": msg["text"],
            }
            for msg in history
        ],
    ]
    return await complete(
        model=model,
        messages=messages,
        api_key=api_key,
        api_base=api_base,
        temperature=0.7,
    )
