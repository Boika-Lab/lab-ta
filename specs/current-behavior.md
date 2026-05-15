# Spec: Current Lab TA Behavior

## Goal

Capture the inherited Lab TA behavior so future changes can be made against an
explicit contract instead of implicit UI and route behavior.

## Users

Instructors configure lab sessions and optional prelab quizzes. Students use a
shared lab link to pass any active quiz and chat with the Socratic TA.

## Instructor Configuration

- `GET /` serves the instructor portal.
- `POST /api/configure` accepts `api_key`, `lab_name`, and zero or more PDF,
  PPTX, or DOCX files. It also accepts an optional `chat_logging_enabled`
  checkbox field.
- Uploaded documents are parsed into plain text and stored with a generated
  eight-character lab token.
- Persistent chat logging is disabled unless the instructor explicitly enables
  it during lab setup.
- Unsupported file types return `400`.
- The response includes the token, relative student URL, and relative
  instructor dashboard URL.
- After successful lab creation, the instructor UI navigates to the durable
  `/instructor/{token}` dashboard URL.
- `GET /instructor/{token}` serves the instructor dashboard for known lab
  tokens and returns `404` for unknown tokens.
- `GET /api/instructor/lab/{token}` returns dashboard hydration data including
  lab name, model, relative student URL, relative instructor URL, chat logging
  status, and the active published quiz summary when one exists.
- `GET /instructor/labs` serves a saved-labs index that helps instructors
  recover previous lab sessions from the local database.
- `GET /api/instructor/labs` returns saved labs sorted newest first. Each row
  includes lab name, token, relative student URL, relative instructor dashboard
  URL, chat logging status, creation timestamp, quiz count/status summary, and
  chat log exchange count.
- Saved-lab API rows exclude API keys and raw uploaded lab document content.
- The instructor dashboard uses the same unauthenticated token model as the
  student page. Anyone with the instructor dashboard URL can manage the lab, and
  anyone with the saved-labs index URL can view local lab metadata and open
  dashboard or student links.
- The instructor dashboard result panel includes chat log controls. Refresh
  loads the current JSON-backed log view for that token, and Download JSON
  exports the same data.

## Student Chat

- `GET /lab/{token}` serves the student chat page.
- `GET /api/lab/{token}` returns the lab name and model for known tokens, and
  `404` for unknown tokens.
- `POST /api/chat/{token}` accepts a message, prior history, and optional
  anonymous browser session ID. It screens the message for prompt-injection
  attempts, then calls the TA model only when the screen passes.
- Blocked messages return a neutral refusal: `I can only help with questions
  about this lab activity.`
- Unknown lab tokens return `404`.
- The TA prompt must stay Socratic, use uploaded lab content, and refuse to
  disclose its instructions.
- When chat logging is enabled for a lab, completed TA exchanges and blocked
  refusals are stored in `chat_logs` with timestamp, session ID, exchange order,
  question, response, and blocked status. Failed TA calls are not logged.
- `GET /api/chat-logs/{token}` returns logged exchanges grouped by anonymous
  browser session for known lab tokens, and `404` for unknown tokens.
- The student browser creates an anonymous chat session ID per lab token and
  stores it in `localStorage`. This identifier is not a login or identity claim.

## Database Behavior

- `init_db()` creates all SQLite tables required by the current app.
- Existing SQLite databases with a `labs` table missing
  `chat_logging_enabled` are upgraded in place with
  `chat_logging_enabled INTEGER NOT NULL DEFAULT 0`.
- `chat_logs` stores one row per logged exchange with `token`, `session_id`,
  `exchange_index`, `question_at`, `question`, `response`, and `blocked`.
- Chat exchange ordering is maintained per `(token, session_id)` through
  `exchange_index`.

## LLM Prompt Templates

- LLM prompt templates are stored as Markdown files under `prompts/`.
- Required prompt templates are loaded and validated when the application
  modules are imported, before request handling.
- Request handlers reuse the loaded prompt templates instead of reading prompt
  files from disk on every request.
- Prompt validation fails fast when a required prompt file is missing, empty,
  missing a required placeholder, or contains an unknown placeholder.
- The current prompt templates cover Socratic TA chat, prompt-injection
  screening, and prelab quiz generation.

## Gemini Model Configuration

- `llm_config.py` defines server-controlled Gemini model names for TA chat,
  prompt-injection screening, and prelab quiz generation.
- `CHAT_MODEL` and `QUIZ_MODEL` are string constants set to
  `gemini-2.5-flash`; `SCREENING_MODEL` is set to
  `gemini-2.5-flash-lite`.
- `POST /api/configure` stores the configured chat model for newly created
  labs.
- Existing lab rows continue using their stored `model` value for TA chat.
- The instructor landing page displays a read-only Model Settings summary with
  the current chat, prompt-injection screening, and prelab quiz generation
  model values.
- The instructor UI does not provide a model picker.

## Prelab Quiz

- `POST /quiz/generate` creates a draft quiz for a known lab with document text.
- The requested question count must be between 3 and 10.
- Generated quiz questions are stored with choices A-D, a correct answer, an
  explanation, and initial anonymous stats.
- `GET /quiz/{quiz_id}` returns draft or published quiz details including answer
  data for instructor use.
- `PUT /quiz/{quiz_id}` edits draft quiz questions only.
- `POST /quiz/{quiz_id}/publish` publishes a draft quiz when no other quiz is
  already published for the same lab.
- `POST /quiz/{quiz_id}/close` closes a published quiz.
- `GET /quiz/active/{token}` returns the active published quiz without answer
  data for students, or an empty result when no quiz is active.
- `POST /quiz/{quiz_id}/submit` accepts student answers only for published
  quizzes, returns per-question correctness, and includes explanations only for
  wrong answers.
- The student quiz UI stores local in-progress quiz state, supports retrying
  only missed questions, and keeps visual feedback out of persisted state.
- When a quiz round completes, the student quiz panel background indicates the
  round result: green for zero missed questions, yellow for one missed question,
  and red for more than one missed question.
- Starting a quiz round, rendering a question, or retrying missed questions
  resets the student quiz panel to the default background.
- `GET /quiz/{quiz_id}/stats` returns anonymous attempt and correctness counts.
- Refreshing `/instructor/{token}` restores the active published quiz ID for
  stats access. Draft quiz recovery is not supported in the first persistent
  dashboard version.

## Acceptance Criteria

- Current public routes have deterministic tests that do not call Gemini.
- Security screening is enforced before TA generation.
- Prompt template loading and validation have deterministic tests.
- Quiz state transitions reject invalid operations with clear HTTP errors.
- README points contributors to this spec workflow.

## Test Plan

- Run `python -m pytest`.
- Mock Gemini-facing chat and quiz generation functions.
- Use an isolated SQLite database per test.
