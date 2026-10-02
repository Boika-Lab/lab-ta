# Spec: Multi-Provider LLM Configuration

## Goal

Allow instructors to use hosted or local LiteLLM-supported models instead of
requiring Google Gemini for every LLM operation.

## Users

Instructors choose the models and shared provider connection used by each lab.
Students continue using the same quiz and Socratic TA interfaces.

## Proposed Behavior

- Each lab stores immutable model identifiers for TA chat, screening, and quiz
  generation.
- The three roles share one optional API key and one optional API base URL.
- New labs default to `gemini/gemini-3.5-flash-lite` for chat, quiz generation,
  and screening. See `gemini-2-5-retirement.md` for the current values, the
  rationale, and the one-time rewrite of retired identifiers.
- Model identifiers are freeform LiteLLM model strings.
- Custom API base URLs are limited to HTTP(S) loopback addresses:
  `localhost`, `127.0.0.1`, and `::1`.
- Lab setup validates every distinct configured model with a minimal live
  completion before saving. A validation failure creates no lab.
- Model settings are displayed read-only on the instructor dashboard and cannot
  be changed after creation.
- Screening remains fail-open if its runtime call fails.

## API/Data Changes

- `POST /api/configure` accepts optional `api_key` and `api_base` fields plus
  `chat_model`, `screening_model`, and `quiz_model`.
- `labs.model` remains the chat model. `labs.screening_model`,
  `labs.quiz_model`, and `labs.api_base` are added.
- Legacy Gemini model names beginning with `gemini-` are upgraded to the
  LiteLLM `gemini/` provider format.
- `GET /api/instructor/lab/{token}` returns the three model identifiers and
  optional API base, but never returns the API key.

## Acceptance Criteria

- All runtime LLM calls use LiteLLM rather than a provider SDK.
- Hosted Gemini remains the default configuration.
- Local LiteLLM-compatible services can be configured through a loopback URL
  without an API key.
- Unsafe or malformed custom API base URLs return `400`.
- Invalid model or credential configurations return `502` before persistence.
- Existing labs continue to work after in-place schema initialization.
- Provider failures do not expose stored credentials in API errors.

## Test Plan

- Mock LiteLLM calls; automated tests must not contact live providers.
- Cover schema upgrades, configuration persistence, loopback URL validation,
  validation deduplication, and rollback on validation failure.
- Verify role-specific dispatch, provider-neutral errors, and credential
  exclusion.
- Run `python -m pytest`.

## Non-Goals

- Editing model settings after lab creation.
- Arbitrary remote custom API base URLs.
- Separate credentials or endpoints for each model role.
- Running a LiteLLM proxy as part of this application.
