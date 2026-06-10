from __future__ import annotations

import asyncio

import pytest

import llm_client
import ta_engine


def test_complete_passes_optional_provider_settings_and_extracts_text(monkeypatch):
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        message = type("Message", (), {"content": " provider response "})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()

    monkeypatch.setattr(llm_client, "acompletion", fake_acompletion)
    result = asyncio.run(
        llm_client.complete(
            model="ollama/llama3.1",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="key",
            api_base="http://localhost:11434",
            temperature=0.7,
        )
    )

    assert result == " provider response "
    assert captured["drop_params"] is True
    assert captured["api_key"] == "key"
    assert captured["api_base"] == "http://localhost:11434"


def test_complete_rejects_empty_provider_response(monkeypatch):
    async def fake_acompletion(**kwargs):
        message = type("Message", (), {"content": "   "})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()

    monkeypatch.setattr(llm_client, "acompletion", fake_acompletion)
    with pytest.raises(ValueError, match="empty response"):
        asyncio.run(
            llm_client.complete(
                model="test/model",
                messages=[{"role": "user", "content": "Hello"}],
            )
        )


def test_ta_engine_converts_browser_model_role_to_assistant(monkeypatch):
    captured = {}

    async def fake_complete(**kwargs):
        captured.update(kwargs)
        return "Question?"

    monkeypatch.setattr(ta_engine, "complete", fake_complete)
    result = asyncio.run(
        ta_engine.get_ta_response(
            api_key=None,
            api_base="http://localhost:11434",
            model="ollama/llama3.1",
            system_prompt="System",
            history=[
                {"role": "model", "text": "Earlier response"},
                {"role": "user", "text": "New question"},
            ],
        )
    )

    assert result == "Question?"
    assert captured["messages"] == [
        {"role": "system", "content": "System"},
        {"role": "assistant", "content": "Earlier response"},
        {"role": "user", "content": "New question"},
    ]
