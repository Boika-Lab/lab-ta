# Feature Roadmap

This roadmap records the current feature surface of the project and planned
future feature areas.

## Current Feature Set

- Instructor portal served at `GET /`.
- Lab session creation through `POST /api/configure`.
- Upload and plain-text extraction for PDF, PPTX, and DOCX lab materials.
- Unique eight-character student tokens and shareable `/lab/{token}` URLs.
- Separate private instructor tokens; durable instructor dashboard URLs at
  `/instructor/{instructor_token}` that students cannot derive from the lab
  link.
- Instructor dashboard hydration through
  `GET /api/instructor/lab/{instructor_token}`.
- Per-lab Quiz Generation and Socratic TA availability controls, editable at
  setup time and later from the instructor dashboard.
- Immutable per-lab Socratic TA language and custom instructions, plus
  immutable per-generation quiz level, difficulty, language, and custom
  instructions.
- Passphrase-protected saved-labs index at `/instructor/labs` with lookup data
  from `GET /api/instructor/labs` (requires `LAB_TA_ADMIN_PASSPHRASE`).
- Server-generated QR code (via `segno`) plus copy/open-link controls for
  student access; the student URL is not sent to any third-party service.
- Student lab page served at `GET /lab/{token}`.
- Lab metadata lookup through `GET /api/lab/{token}`.
- Socratic chat through `POST /api/chat/{token}`.
- Prompt-injection screening before TA response generation.
- Optional Persistent Chat Logs completed: instructors can enable anonymous
  per-lab chat persistence from the setup form, then refresh or download logs
  from the instructor result panel.
- Anonymous chat log export through
  `GET /api/instructor/lab/{instructor_token}/chat-logs` returns sessions
  grouped by browser-local student session ID.
- Voice input and text-to-speech in the student browser UI.
- MathJax rendering for mathematical and chemical notation.
- Prelab quiz generation, draft editing, publishing, single-active-quiz
  enforcement, closing, and stats through instructor-token routes under
  `/api/instructor/lab/{instructor_token}/quiz/...`.
- Instructor quiz export for draft and published quizzes, with copy/pasteable
  student-facing text and answer-key text.
- Student quiz gate through `GET /quiz/active/{token}` and
  `POST /quiz/{quiz_id}/submit`.
- Retry flow for missed quiz questions in the student UI.
- Quiz completion feedback in the student UI: green after a perfect round,
  yellow after one missed question, red after multiple missed questions, and
  reset on retry.
- Anonymous quiz attempt stats through
  `GET /api/instructor/lab/{instructor_token}/quiz/{quiz_id}/stats`.
- LLM Prompt Externalization completed: prompt templates are stored as Markdown
  files under `prompts/` and loaded once at application startup/import.
- Multi-Provider LLM Configuration completed: all LLM calls use LiteLLM, each
  lab stores immutable chat, screening, and quiz model identifiers, and local
  providers can use an optional loopback API base URL.

## Current Quality and Process Features

- Markdown specification workflow in `specs/`.
- Current behavior spec for inherited app behavior.
- Completed LLM Prompt Externalization spec.
- Completed Multi-Provider LLM Configuration spec, including provider-neutral
  dispatch, setup validation, schema upgrades, and loopback endpoint controls.
- Completed Instructor Access Control spec, including separate instructor
  tokens, instructor-only quiz and chat-log routes, secure token generation,
  and the passphrase-protected saved-labs index.
- Completed Local QR Code Generation spec, replacing the third-party QR image
  service with a server-side `segno` route.
- Completed Instructor Token Rotation spec: a dashboard action that replaces
  the instructor token in place and revokes the old instructor URL.
- Completed Quiz Completion Feedback spec.
- Completed Optional Persistent Chat Logs spec, including SQLite upgrade
  behavior, route contracts, and template wiring tests.
- Completed Persistent Instructor Lab Dashboard spec, including durable
  dashboard route contracts and hydration behavior.
- Completed Instructor Lab Index spec, including saved-lab lookup and
  dashboard/student links.
- Completed Lab Feature Availability spec, including grouped Quiz Generation
  and Socratic TA controls.
- Completed Quiz Question Export spec, including read-only student and
  answer-key export text with copy controls.
- Completed Quiz Answer Consistency spec, including prompt instructions that
  ask Gemini to verify correct-answer labels against answer text and
  explanations before returning JSON.
- Completed Per-Generation Quiz and TA Configuration spec, including schema
  upgrades, protected prompt interpolation, dashboard display, validation, and
  browser preference restoration.
- Reusable spec template for future changes.
- Pytest route-level contract tests.
- Test database isolation through `LAB_TA_DB_PATH`.

## Current Known Constraints

- The app stores API keys locally in SQLite in plaintext.
- There is no user login or role-based authentication. Access is link-based:
  the student link and a separate private instructor link per lab.
- Anyone with an instructor dashboard URL can manage that lab. A leaked URL
  is revoked by rotating the instructor token from the dashboard.
- The saved-labs index requires the `LAB_TA_ADMIN_PASSPHRASE` passphrase; when
  it is unset the index is disabled.
- The instructor and student pages are plain HTML/CSS/JavaScript templates.
- Database schema setup is handled with `CREATE TABLE IF NOT EXISTS`; there is
  no migration framework.
- Automated tests cover backend route contracts and lightweight static template
  hooks, not full browser UI behavior.
- Live provider calls are intentionally excluded from automated tests.

## Completed Roadmap Items

### Instructor Access Control

Separate instructor access from student access so a student holding the lab
link cannot reach the dashboard, answer key, chat logs, or quiz controls.

#### Implemented Behavior

- Each lab has a private `instructor_token` (32+ URL-safe characters from
  `secrets.token_urlsafe`) in addition to the eight-character student token,
  which now also comes from the `secrets` module.
- All instructor routes are keyed by the instructor token and return `404`
  for unknown tokens, including student tokens.
- Quiz management and chat-log routes moved under
  `/api/instructor/lab/{instructor_token}`; the old unauthenticated routes
  were removed.
- The saved-labs index requires the `LAB_TA_ADMIN_PASSPHRASE` passphrase via
  the `X-Lab-TA-Passphrase` header.
- Existing databases are upgraded in place with backfilled instructor tokens.

#### Non-Goals

- No user accounts, sessions, or cookies.
- Rotation was added later by the Instructor Token Rotation spec.

### Multi-Provider LLM Configuration

Implement GitHub issue #11 by replacing direct Gemini SDK calls with LiteLLM
and allowing instructors to select the model used for each LLM role.

#### Implemented Behavior

- Lab setup accepts freeform LiteLLM model identifiers for TA chat,
  prompt-injection screening, and quiz generation.
- The roles share an optional API key and optional loopback-only API base URL.
- Every distinct model is validated with a minimal live call before the lab is
  stored.
- Model settings are immutable and visible read-only on the instructor
  dashboard.
- Existing Gemini model values are upgraded to LiteLLM provider-prefixed
  identifiers.

#### Non-Goals

- No post-creation model editing.
- No arbitrary remote custom API base URLs.
- No separate credential or endpoint per role.

### Instructor Lab Index

Add an instructor-facing index of saved lab assignments in the local database.
The index builds on the persistent dashboard feature by linking each lab row to
its dashboard and student URL.

#### Implemented Behavior

- `GET /instructor/labs` serves the saved-labs index page.
- `GET /api/instructor/labs` returns saved labs sorted newest first.
- Each row shows lab name, token, created date, chat logging status, quiz
  count/status, and chat log exchange count.
- Each row includes clickable links to `/instructor/{token}` and `/lab/{token}`.
- Empty databases show an empty state.
- API responses exclude API keys and raw uploaded lab content.

#### Non-Goals

- No search, filtering, pagination, archiving, deletion, or editing.
- No authentication or access-control change.

### Lab Feature Availability

Let instructors independently enable or disable Quiz Generation and Socratic TA
for each lab.

#### Implemented Behavior

- New and legacy labs default to both features enabled.
- The setup form shows a Lab Features area with separate Quiz Generation and
  Socratic TA groups.
- The instructor dashboard shows matching Feature Availability controls for
  later edits.
- Disabled feature APIs return `403`.
- Quiz-disabled labs preserve existing quiz data and stats.
- Student pages handle both enabled, quiz-only, TA-only, and both-disabled
  states.

#### Non-Goals

- No authentication or access-control change.
- No destructive deletion or auto-closing of disabled quiz data.

### Quiz Question Export

Add an instructor-facing export control for generated prelab quiz questions so
instructors can copy quiz text without manually selecting fields from the draft
editor.

#### Implemented Behavior

- Draft quizzes expose an Export Quiz button after generation.
- Published quizzes expose Export Quiz after dashboard refresh by using the
  existing instructor quiz detail route.
- The export panel shows two read-only text areas: a student version with
  numbered questions and choices A-D, and an answer-key version with numbered
  questions and the correct answer label plus answer text.
- The answer-key format preserves answer text, for example `B. <choice B>`.
- Each export version has an independent Copy button.
- Draft exports use current editor values. Explanations are excluded from both
  export versions.

#### Non-Goals

- No new database tables or migrations.
- No new export API route.
- No automatic correction of already-generated quiz records.

### Quiz Answer Consistency

Add a prompt-level guard for a generation error observed during testing, where
an existing generated quiz had correct-answer labels that disagreed with the
explanations and answer text.

#### Implemented Behavior

- The quiz generation prompt asks Gemini to verify every question before
  returning JSON.
- The prompt requires the `correct` label to identify the answer choice that is
  actually correct.
- The prompt requires the explanation to support the same labeled answer
  choice, and instructs Gemini to fix the label before returning if the
  explanation points to another choice.
- The existing quiz generation temperature remains `0.7`.

#### Non-Goals

- No post-generation semantic answer validator.
- No retroactive repair of existing quiz data.

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

Historical item superseded by Multi-Provider LLM Configuration.

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

### Delete Saved Labs

Add a destructive cleanup flow for saved labs and all data associated with a lab
token. This builds on the saved-labs index, which currently allows lookup and
navigation but has no way to remove obsolete or sensitive sessions.

#### Goal

- Let instructors permanently remove old lab sessions from the local SQLite
  database.
- Delete sensitive stored data for a lab, including the Google API key, uploaded
  lab document text, anonymous chat logs, quizzes, quiz questions, and quiz
  stats.
- Keep the deletion control discoverable from the saved-labs index while making
  accidental deletion unlikely.

#### Proposed Behavior

- Add a delete action to each row on `/instructor/labs`.
- Require typed-token confirmation before deletion. The instructor must type the
  exact lab token before the destructive action is enabled or submitted.
- Add a supporting API, for example `DELETE /api/instructor/lab/{token}`, that
  permanently deletes:
  - the `labs` row for the token
  - all `chat_logs` rows for the token
  - all `quizzes` rows for the token
  - all `quiz_questions` rows belonging to those quizzes
  - all `quiz_question_stats` rows belonging to those quiz questions
- After deletion, remove the lab row from the saved-labs UI and show a concise
  success message.
- Deleted lab student URLs and instructor dashboard URLs should return `404`.
- Unknown tokens should return `404` from the deletion API.
- Deletion is initiated from the passphrase-protected saved-labs index and
  should require the passphrase on the deletion API as well.

#### Acceptance Criteria

- Instructors can delete a saved lab from `/instructor/labs` only after typing
  the matching token.
- Deleting a lab removes the lab row, uploaded lab content, stored API key,
  chat logs, quizzes, quiz questions, and quiz stats associated with that token.
- After deletion, the lab no longer appears in `GET /api/instructor/labs`.
- After deletion, `GET /instructor/{token}`, `GET /api/instructor/lab/{token}`,
  `GET /api/lab/{token}`, and student chat/quiz routes for that token no longer
  expose the deleted lab.
- Route/database contract tests cover full cascade deletion, unknown-token
  `404`, saved-labs list refresh behavior, and deleted-route `404` behavior.
- Static template tests cover the delete control, typed-token confirmation, and
  deletion API call.
- README, `specs/current-behavior.md`, and `specs/tech-stack.md` are updated
  when implemented.

#### Non-Goals

- No archive, undo, soft-delete, recycle bin, or recovery flow in the first
  version.
- No bulk deletion.
- No deletion from the per-lab dashboard in the first version.
- No authentication or access-control change.

### Stronger Instructor Authentication

The Instructor Access Control and Instructor Token Rotation items settled on
separate, rotatable per-lab instructor tokens plus a passphrase for the
saved-labs index. The remaining question for a later spec is whether a
login-based model (a shared passphrase for all dashboards, OAuth, or user
accounts) is worth the added classroom friction.

### LiteLLM Provider Support

- Add LiteLLM as the LLM integration layer so the app can switch to other LLM
  services through configuration rather than provider-specific code changes.

### Security Audit

- Review the codebase for possible security problems, including API key
  handling, prompt-injection handling, uploaded document processing, database
  access, unauthenticated instructor/student routes, and persisted student data.
- Record any findings as actionable follow-up work with severity, affected
  behavior, and suggested remediation.
