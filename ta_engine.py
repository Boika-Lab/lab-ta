"""Gemini-powered Socratic TA engine using the google-genai SDK."""

from __future__ import annotations

from google import genai
from google.genai import types

from prompt_loader import PROMPTS


def build_system_prompt(lab_name: str, lab_content: str) -> str:
    content = lab_content if lab_content.strip() else "(No documents uploaded.)"
    return PROMPTS["ta_system"].render(lab_name=lab_name, lab_content=content)


async def get_ta_response(
    api_key: str,
    model: str,
    system_prompt: str,
    history: list[dict],
) -> str:
    """
    Send the full conversation history to Gemini and return the assistant reply.

    history: list of {"role": "user"|"model", "text": str}
    """
    client = genai.Client(api_key=api_key)

    contents = [
        types.Content(
            role=msg["role"],
            parts=[types.Part.from_text(text=msg["text"])],
        )
        for msg in history
    ]

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.7,
    )

    response = await client.aio.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    return response.text
