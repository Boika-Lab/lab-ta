"""Default LiteLLM model configuration for new labs."""

from __future__ import annotations


CHAT_MODEL = "gemini/gemini-3.5-flash-lite"
SCREENING_MODEL = "gemini/gemini-3.5-flash-lite"
QUIZ_MODEL = "gemini/gemini-3.5-flash-lite"

# Google withdrew the Gemini 2.5 models from new projects in July 2026 and has
# announced retirement dates on Vertex AI. Stored lab identifiers that match a
# key here are rewritten to the value at startup (see init_db in main.py and
# specs/gemini-2-5-retirement.md). Pointing at the constants above keeps the
# migration in step if a default changes again.
RETIRED_MODEL_REPLACEMENTS = {
    "gemini/gemini-2.5-flash": CHAT_MODEL,
    "gemini/gemini-2.5-flash-lite": SCREENING_MODEL,
}
