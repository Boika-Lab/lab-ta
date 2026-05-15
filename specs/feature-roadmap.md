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

### Persistent Instructor Lab Dashboard

Add a durable instructor-facing management URL for each lab while preserving the
current unauthenticated no-auth model. The immediate goal is reloadability and
recoverability, not access control.

#### Goal

- Give every configured lab an instructor dashboard URL that can be bookmarked,
  refreshed, reopened, or shared intentionally.
- Let instructors return to chat logs, quiz creation, quiz status, and quiz
  stats for an existing lab without recreating the assignment.
- Reconstruct dashboard state from SQLite instead of relying on in-memory
  browser variables set immediately after `POST /api/configure`.

#### Proposed Behavior

- Add an instructor route such as `GET /instructor/{token}` or
  `GET /manage/{token}` that serves the instructor dashboard for a lab token.
- Extend `POST /api/configure` to return an `instructor_url` alongside the
  existing `token` and `student_url`.
- After successful lab creation, the instructor UI should navigate to or display
  the durable instructor URL.
- Add a lab-level instructor dashboard API, for example
  `GET /api/instructor/lab/{token}`, that returns enough state to rebuild the
  page:
  - lab name
  - model
  - student URL
  - chat logging enabled status
  - active/published quiz summary if one exists
  - draft quiz summaries if draft quiz recovery is supported
  - quiz IDs needed for editing, publishing, closing, and stats
- The instructor dashboard should continue using the existing chat log endpoint
  or equivalent data from the dashboard API.
- Unknown tokens should return `404` from both the page-supporting APIs and any
  new dashboard API.
- Current unauthenticated behavior remains unchanged: anyone with the
  instructor URL can manage that lab.

#### Acceptance Criteria

- Refreshing an instructor dashboard URL restores the lab name, student URL,
  chat log controls, and quiz management state.
- Existing student URLs continue to work unchanged.
- A newly created lab response includes both `student_url` and
  `instructor_url`.
- Instructors can recover the ID of any active/published quiz for the lab after
  refresh and view stats without needing the original browser state.
- If draft quiz recovery is included, instructors can recover and continue
  editing draft quizzes after refresh. If not included, draft recovery is
  explicitly documented as a non-goal for the first version.
- Route/database contract tests cover dashboard restore, unknown-token `404`,
  and reload after quiz publication.
- Static template tests cover URL/token detection and dashboard hydration hooks.
- README, `specs/current-behavior.md`, and `specs/tech-stack.md` are updated
  when implemented.

#### Non-Goals

- No login, password, role-based access control, or session cookies.
- No separate instructor secret token in the first version.
- No changes to the student chat URL contract.
- No migration away from token-based unauthenticated routes.

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
