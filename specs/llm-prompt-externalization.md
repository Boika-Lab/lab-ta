# Spec: LLM Prompt Externalization

## Goal

Move LLM prompt text out of Python source files and into Markdown files so
prompt content can be reviewed and edited separately from application logic.

## Users

Maintainers who review prompt behavior and developers who modify Gemini-backed
chat, screening, or quiz generation behavior.

## Current Behavior

The TA system prompt, prompt-injection screening prompt, and quiz generation
prompt are embedded as Python string literals in `ta_engine.py`, `main.py`, and
`quiz_engine.py`.

## Proposed Behavior

- Store all Gemini prompt templates as Markdown files under `prompts/`.
- Load and validate required prompt templates once when the application modules
  are imported.
- Reuse loaded templates in request-time code instead of reading prompt files
  from disk per request.
- Fail fast when a required prompt file is missing, empty, missing a required
  placeholder, or contains an unknown placeholder.
- Preserve the existing prompt wording and public behavior.

## API/Data Changes

- No public route, request, response, database, or UI changes.
- Prompt Markdown files become a repository-level data interface:
  - `prompts/ta_system.md`
  - `prompts/screening.md`
  - `prompts/quiz_generation.md`

## Acceptance Criteria

- Python source files no longer contain the full LLM prompt bodies.
- Prompt templates are loaded into memory at startup/import time.
- Prompt rendering replaces required placeholders for lab name, lab content,
  student message, question count, and document text.
- Invalid prompt templates raise clear configuration errors before request
  handling.
- Existing chat, screening, and quiz route contracts remain unchanged.

## Test Plan

- Add unit tests for prompt loading, validation, and rendering.
- Keep route contract tests mocked so automated tests never call Gemini.
- Run `python -m pytest`.

## Open Questions

- None.
