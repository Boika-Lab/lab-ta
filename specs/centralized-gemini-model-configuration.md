# Spec: Centralized Gemini Model Configuration

> Superseded by `multi-provider-llm-configuration.md`. This file records the
> earlier Gemini-only design.

## Goal

Centralize Gemini model names so runtime Python modules do not duplicate
hardcoded model strings, while keeping Lab TA Gemini-only and preserving the
current instructor workflow.

## Users

Instructors continue configuring lab sessions with a Google Gemini API key, lab
name, optional chat logging, and uploaded lab documents. Model selection remains
server-controlled and is not exposed as an instructor-facing picker.

## Behavior

- `llm_config.py` exposes three model-role constants:
  - `CHAT_MODEL`
  - `SCREENING_MODEL`
  - `QUIZ_MODEL`
- All three are plain string constants. `CHAT_MODEL` and `QUIZ_MODEL` are
  currently set to `gemini-2.5-flash`; `SCREENING_MODEL` is currently set to
  `gemini-2.5-flash-lite`.
- `POST /api/configure` stores the configured chat model for newly created labs.
- Existing lab rows continue using their stored `model` value for TA chat.
- Prompt-injection screening uses the configured screening model.
- Prelab quiz generation uses the configured quiz model.
- The instructor UI continues to display the configured chat model as
  read-only text through existing lab metadata. It does not offer a model
  dropdown.
- The instructor landing page displays a read-only model settings summary
  before lab creation, sourced from `llm_config.py`, with one visible entry for
  each model role:
  - TA chat model: `CHAT_MODEL`
  - Prompt-injection screening model: `SCREENING_MODEL`
  - Prelab quiz generation model: `QUIZ_MODEL`
- The landing page model settings summary must update when the constants in
  `llm_config.py` change. It must not duplicate model string literals in the
  HTML template.

## Non-Goals

- No provider abstraction.
- No LiteLLM integration.
- No instructor-facing model picker.
- No environment-variable model overrides.
- No migration of existing lab rows to a new model.
- No changes to Google API key storage.

## Acceptance Criteria

- No Gemini model string is duplicated across runtime Python modules.
- Default behavior is unchanged.
- Changing `CHAT_MODEL` changes the model stored for newly created labs.
- Changing `SCREENING_MODEL` changes the model used by screening.
- Changing `QUIZ_MODEL` changes the model used by quiz generation.
- `GET /` renders the instructor landing page with the current `CHAT_MODEL`,
  `SCREENING_MODEL`, and `QUIZ_MODEL` values visible as read-only settings.
- Route tests remain deterministic and do not call Gemini.

## Test Plan

- Run `python -m pytest`.
- Add deterministic tests for configured model values.
- Add route or template tests proving the instructor landing page displays the
  current model role settings.
- Mock Gemini-facing client calls when verifying screening and quiz generation
  model selection.
