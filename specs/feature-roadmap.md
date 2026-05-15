# Feature Roadmap

This roadmap records the current feature surface of the project and planned
future feature areas.

## Current Feature Set

- Instructor portal served at `GET /`.
- Lab session creation through `POST /api/configure`.
- Upload and plain-text extraction for PDF, PPTX, and DOCX lab materials.
- Unique eight-character student tokens and shareable `/lab/{token}` URLs.
- Durable unauthenticated instructor dashboard URLs at `/instructor/{token}`.
- Instructor dashboard hydration through `GET /api/instructor/lab/{token}`.
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
- Centralized Gemini Model Configuration completed: Gemini model names are
  defined in `llm_config.py` as server-controlled constants for chat,
  screening, and quiz generation, and the instructor landing page displays the
  current read-only settings.

## Current Quality and Process Features

- Markdown specification workflow in `specs/`.
- Current behavior spec for inherited app behavior.
- Completed LLM Prompt Externalization spec.
- Completed Centralized Gemini Model Configuration spec, including landing-page
  display of current server-controlled model settings.
- Completed Quiz Completion Feedback spec.
- Completed Optional Persistent Chat Logs spec, including SQLite upgrade
  behavior, route contracts, and template wiring tests.
- Completed Persistent Instructor Lab Dashboard spec, including durable
  dashboard route contracts and hydration behavior.
- Reusable spec template for future changes.
- Pytest route-level contract tests.
- Test database isolation through `LAB_TA_DB_PATH`.

## Current Known Constraints

- The app stores API keys locally in SQLite.
- There is no user login or role-based authentication.
- Anyone with an instructor dashboard URL can manage that lab.
- The instructor and student pages are plain HTML/CSS/JavaScript templates.
- Database schema setup is handled with `CREATE TABLE IF NOT EXISTS`; there is
  no migration framework.
- Automated tests cover backend route contracts and lightweight static template
  hooks, not full browser UI behavior.
- Live Gemini calls are intentionally excluded from automated tests.

## Completed Roadmap Items

### Persistent Instructor Lab Dashboard

Give every configured lab an instructor dashboard URL that can be bookmarked,
refreshed, reopened, or intentionally shared while preserving the current
unauthenticated token model.

#### Implemented Behavior

- `GET /instructor/{token}` serves the instructor dashboard for known lab
  tokens and returns `404` for unknown tokens.
- `POST /api/configure` returns `instructor_url` alongside `token` and
  `student_url`.
- After successful lab creation, the instructor UI navigates to the returned
  dashboard URL.
- `GET /api/instructor/lab/{token}` returns lab metadata, relative student and
  instructor URLs, chat logging status, and the active published quiz summary
  when one exists.
- Refreshing `/instructor/{token}` restores the student URL, QR code, chat log
  controls, current token, published quiz state, and quiz stats access.

#### Non-Goals

- No authentication, login, session cookie, or separate instructor secret token.
- No change to the student URL contract.
- No draft quiz recovery in the first dashboard version.

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
- Values are plain string constants: `gemini-2.5-flash` for chat and quiz
  generation, and `gemini-2.5-flash-lite` for screening.
- `main.py` uses `CHAT_MODEL` when creating new lab rows and `SCREENING_MODEL`
  when screening messages.
- `quiz_engine.py` accepts or imports `QUIZ_MODEL` instead of defining a local
  `_MODEL` constant.
- The instructor landing page shows the configured chat, screening, and quiz
  generation models as read-only text.
- The instructor UI does not offer a model dropdown in this step.
- Existing lab rows continue using their stored `model` value for TA chat.
  Only newly configured labs pick up a changed `CHAT_MODEL`.

#### Acceptance Criteria

- No Gemini model string is duplicated across runtime Python modules.
- Default behavior is unchanged.
- Changing `CHAT_MODEL` changes the model stored for newly created labs.
- Changing `SCREENING_MODEL` changes the model used by screening.
- Changing `QUIZ_MODEL` changes the model used by quiz generation.
- `GET /` renders the current `CHAT_MODEL`, `SCREENING_MODEL`, and
  `QUIZ_MODEL` values on the instructor landing page.
- Route tests remain deterministic and do not call Gemini.
- README, `specs/current-behavior.md`, and `specs/tech-stack.md` are updated
  when the feature is implemented.

#### Non-Goals

- No provider abstraction.
- No LiteLLM integration.
- No instructor-facing model picker.
- No migration of existing lab rows to a new model.
- No changes to API key storage.

## Future Roadmap

Future work should start as a new or updated spec with explicit acceptance
criteria. The planned feature areas below should be treated as roadmap items,
not current behavior.

### Instructor Lab Index

Add an instructor-facing index of saved lab assignments in the local database.
This should build on the Persistent Instructor Lab Dashboard feature, because
each row should link directly to the durable instructor dashboard for that lab.
The feature follows the current unauthenticated no-auth model unless and until a
future authentication design changes that.

#### Goal

- Let instructors recover existing lab assignments without remembering or
  manually copying tokens.
- Make the local database contents visible in a compact operational view.
- Provide a fast path from a saved lab row to its instructor dashboard.

#### Proposed Behavior

- Add an instructor lab list route, for example `GET /instructor/labs` or
  `GET /manage`, that serves a saved-labs index page.
- Add a supporting API, for example `GET /api/instructor/labs`, that returns one
  row per lab in the database.
- Each row should include:
  - lab name
  - lab token / identifier
  - student URL
  - instructor dashboard URL
  - chat logging enabled status
  - created timestamp
  - quiz count
  - whether any quiz exists
  - published/active quiz count or active quiz status
  - chat log exchange count if chat logging is enabled
- The UI should display a scan-friendly table or list with columns for lab name,
  identifier, quiz status/count, chat logging status, and creation date.
- Clicking a row, or a clear action within the row, should open the instructor
  dashboard for that lab.
- The list should sort by newest lab first by default.
- Unknown or empty databases should show an empty state rather than an error.

#### Acceptance Criteria

- Instructors can open the lab index and see all lab tokens currently stored in
  SQLite.
- Each listed lab shows lab name, identifier, chat logging status, and whether
  quizzes exist with a quiz count.
- Each listed lab links to the persistent instructor dashboard URL from the
  previous roadmap feature.
- The API returns deterministic aggregate counts for quizzes and chat logs.
- The list excludes sensitive fields such as API keys and raw lab document
  content.
- Route/database contract tests cover empty database, multiple labs, quiz
  counts, chat log counts, and newest-first ordering.
- Static template tests cover the presence of the saved-labs index and dashboard
  links.
- README, `specs/current-behavior.md`, and `specs/tech-stack.md` are updated
  when implemented.

#### Non-Goals

- No search, filtering, pagination, archiving, or deletion in the first version.
- No authentication or access-control change.
- No display of API keys or uploaded lab content.
- No editing lab metadata from the index.

### Instructor Authentication and Access Control

Evaluate whether Lab TA should move beyond unauthenticated instructor URLs. This
is a separate design effort from the persistent dashboard because it affects
sharing, classroom setup, operational complexity, and privacy expectations.

#### Questions to Resolve

- Should instructor access use a separate unguessable instructor token, a shared
  passphrase, local-only admin access, OAuth, or full user accounts?
- Should the student token and instructor token be different identifiers?
- Should chat logs and quiz stats require stronger protection than student chat
  access?
- How should existing lab sessions be migrated if an access-control model is
  added later?
- What is acceptable friction for an instructor running a temporary local lab
  server in a classroom?

#### Candidate Acceptance Criteria

- The chosen model is documented before implementation.
- The threat model covers student access, instructor access, API key storage,
  chat logs, quiz data, and public Tailscale Funnel exposure.
- Any implementation preserves a low-friction classroom workflow.
- Automated tests cover authorized access, unauthorized access, and backwards
  compatibility or migration behavior.

### LiteLLM Provider Support

- Add LiteLLM as the LLM integration layer so the app can switch to other LLM
  services through configuration rather than provider-specific code changes.

### Security Audit

- Review the codebase for possible security problems, including API key
  handling, prompt-injection handling, uploaded document processing, database
  access, unauthenticated instructor/student routes, and persisted student data.
- Record any findings as actionable follow-up work with severity, affected
  behavior, and suggested remediation.
