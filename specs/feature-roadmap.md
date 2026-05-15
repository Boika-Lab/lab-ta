# Feature Roadmap

This roadmap records the current feature surface of the project and planned
future feature areas.

## Current Feature Set

- Instructor portal served at `GET /`.
- Lab session creation through `POST /api/configure`.
- Upload and plain-text extraction for PDF, PPTX, and DOCX lab materials.
- Unique eight-character student tokens and shareable `/lab/{token}` URLs.
- QR code display and copy/open-link controls for student access.
- Student lab page served at `GET /lab/{token}`.
- Lab metadata lookup through `GET /api/lab/{token}`.
- Socratic chat through `POST /api/chat/{token}`.
- Prompt-injection screening before TA response generation.
- Optional Persistent Chat Logs completed: instructors can enable anonymous
  per-lab chat persistence from the setup form, then refresh or download logs
  from the instructor result panel.
- Anonymous chat log export through `GET /api/chat-logs/{token}` returns
  sessions grouped by browser-local student session ID.
- Voice input and text-to-speech in the student browser UI.
- MathJax rendering for mathematical and chemical notation.
- Prelab quiz generation through `POST /quiz/generate`.
- Draft quiz editing through `PUT /quiz/{quiz_id}`.
- Quiz publishing, single-active-quiz enforcement, and quiz closing.
- Student quiz gate through `GET /quiz/active/{token}` and
  `POST /quiz/{quiz_id}/submit`.
- Retry flow for missed quiz questions in the student UI.
- Quiz completion feedback in the student UI: green after a perfect round,
  yellow after one missed question, red after multiple missed questions, and
  reset on retry.
- Anonymous quiz attempt stats through `GET /quiz/{quiz_id}/stats`.
- LLM Prompt Externalization completed: prompt templates are stored as Markdown
  files under `prompts/` and loaded once at application startup/import.

## Current Quality and Process Features

- Markdown specification workflow in `specs/`.
- Current behavior spec for inherited app behavior.
- Completed LLM Prompt Externalization spec.
- Completed Quiz Completion Feedback spec.
- Completed Optional Persistent Chat Logs spec, including SQLite upgrade
  behavior, route contracts, and template wiring tests.
- Reusable spec template for future changes.
- Pytest route-level contract tests.
- Test database isolation through `LAB_TA_DB_PATH`.

## Current Known Constraints

- The app stores API keys locally in SQLite.
- There is no user login or role-based authentication.
- The instructor and student pages are plain HTML/CSS/JavaScript templates.
- Database schema setup is handled with `CREATE TABLE IF NOT EXISTS`; there is
  no migration framework.
- Automated tests cover backend route contracts and lightweight static template
  hooks, not full browser UI behavior.
- Live Gemini calls are intentionally excluded from automated tests.

## Future Roadmap

Future work should start as a new or updated spec with explicit acceptance
criteria. The planned feature areas below should be treated as roadmap items,
not current behavior.

### Centralized Gemini Model Configuration

Centralize the currently hardcoded Gemini model names while keeping the app
Gemini-only and preserving the current instructor workflow. This is the
recommended first step before broader provider abstraction.

#### Goal

- Remove duplicated hardcoded model strings from `main.py` and
  `quiz_engine.py`.
- Keep model configuration server-controlled, not instructor-selectable.
- Preserve the existing `POST /api/configure` contract except for storing the
  configured chat model instead of a literal constant.

#### Proposed Behavior

- Add a small configuration module, for example `llm_config.py`, that exposes:
  - `CHAT_MODEL`
  - `SCREENING_MODEL`
  - `QUIZ_MODEL`
- Defaults remain `gemini-2.5-flash` for all three model roles.
- Allow optional environment variable overrides:
  - `LAB_TA_CHAT_MODEL`
  - `LAB_TA_SCREENING_MODEL`
  - `LAB_TA_QUIZ_MODEL`
- `main.py` uses `CHAT_MODEL` when creating new lab rows and `SCREENING_MODEL`
  when screening messages.
- `quiz_engine.py` accepts or imports `QUIZ_MODEL` instead of defining a local
  `_MODEL` constant.
- The instructor UI continues to show the configured chat model as read-only
  text. It should not offer a model dropdown in this step.
- Existing lab rows continue using their stored `model` value for TA chat.
  Only newly configured labs pick up a changed `LAB_TA_CHAT_MODEL`.

#### Acceptance Criteria

- No Gemini model string is duplicated across runtime Python modules.
- Default behavior is unchanged when no environment variables are set.
- Setting `LAB_TA_CHAT_MODEL` changes the model stored for newly created labs.
- Setting `LAB_TA_SCREENING_MODEL` changes the model used by screening.
- Setting `LAB_TA_QUIZ_MODEL` changes the model used by quiz generation.
- Route tests remain deterministic and do not call Gemini.
- README, `specs/current-behavior.md`, and `specs/tech-stack.md` are updated
  when the feature is implemented.

#### Non-Goals

- No provider abstraction.
- No LiteLLM integration.
- No instructor-facing model picker.
- No migration of existing lab rows to a new model.
- No changes to API key storage.

### LiteLLM Provider Support

- Add LiteLLM as the LLM integration layer so the app can switch to other LLM
  services through configuration rather than provider-specific code changes.

### Security Audit

- Review the codebase for possible security problems, including API key
  handling, prompt-injection handling, uploaded document processing, database
  access, unauthenticated instructor/student routes, and persisted student data.
- Record any findings as actionable follow-up work with severity, affected
  behavior, and suggested remediation.
