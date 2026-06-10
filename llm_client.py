"""Provider-neutral LLM calls through the LiteLLM Python SDK."""

from __future__ import annotations

from typing import Any

from litellm import acompletion


def _response_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise ValueError("LLM provider returned an invalid response") from exc
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM provider returned an empty response")
    return content


async def complete(
    *,
    model: str,
    messages: list[dict[str, str]],
    api_key: str | None = None,
    api_base: str | None = None,
    temperature: float | None = None,
) -> str:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "drop_params": True,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = await acompletion(**kwargs)
    return _response_text(response)
