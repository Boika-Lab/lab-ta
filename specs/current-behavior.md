# Spec: Current Lab TA Behavior

## Goal

Capture the inherited Lab TA behavior so future changes can be made against an
explicit contract instead of implicit UI and route behavior.

## Users

Instructors configure lab sessions and optional prelab quizzes. Students use a
shared lab link to pass any active quiz and chat with the Socratic TA.

## Instructor Configuration

- `GET /` serves the instructor portal.
- `POST /api/configure` accepts `lab_name`, optional shared `api_key` and
  loopback `api_base`, three LiteLLM model identifiers, and zero or more PDF,
  PPTX, or DOCX files. It also accepts optional `quiz_enabled`, `ta_enabled`,
  and `chat_logging_enabled` checkbox fields.
- Setup validates every distinct configured model before saving the lab.
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
- The instructor setup form and dashboard show separate Quiz Generation and
  Socratic TA feature groups. Both features default to enabled, and instructors
  can edit both flags later from the dashboard.
- Lab setup also captures immutable Socratic TA language and optional custom
  instructions. The dashboard returns and displays these settings read-only.
- The browser remembers the last TA and quiz configuration in `localStorage`.
  Language defaults to `English` on first use; quiz level and difficulty do not
  have defaults.

## Student Chat

- `GET /lab/{token}` serves the student chat page.
- `GET /api/lab/{token}` returns the lab name and model for known tokens, and
  `404` for unknown tokens. It also returns whether quiz and Socratic TA
  features are enabled.
- `POST /api/chat/{token}` accepts a message, prior history, and optional
  anonymous browser session ID. It screens the message for prompt-injection
  attempts, then calls the TA model only when the screen passes.
- When Socratic TA is disabled, chat requests return `403` and do not call
  screening or TA generation.
- Blocked messages return a neutral refusal: `I can only help with questions
  about this lab activity.`
- Unknown lab tokens return `404`.
- The TA prompt stays Socratic, uses uploaded lab content, and refuses to
  disclose its instructions. It may directly repeat a factual statement or
  numerical datum only when that information is explicitly present in the
  uploaded content, with an identifiable document, section, or table reference
  when available. It does not calculate or verify a numerical result. If a
  requested fact is absent from the uploaded material, it says so and suggests
  consulting an external database such as ChemSpider or WolframAlpha.
- A literal `\study` message begins a fresh, stateless, document-grounded study
  interaction. The TA presents 5–10 potential questions, accepts either a
  number or `number: answer`, and gives concise, scaffolded feedback. It does
  not claim persistent progress or scoring. `\study off` explicitly ends study
  behavior, while ordinary lab questions may be handled normally at any point.
- The TA does not draw, complete, predict, or validate reaction mechanisms. It
  directs students to the manual and instructor, but may discuss high-level,
  document-grounded conceptual principles.
- The configured `ta_language` is the TA's default response language. If a
  student writes in another language, the TA may respond in that language. The
  stored lab setting is unchanged and remains read-only, and switching language
  does not relax any other prompt rule.
- Uploaded lab documents are parsed into plain text and stored as a single
  `labs.lab_content` text value. The app does not store original document
  binaries, chunk document text, create embeddings, or perform retrieval
  augmented generation (RAG). On every TA chat request, the server reloads the
  full stored `lab_content`, renders it into the configured model's system
  instruction, and sends that system instruction with the current message and
  browser-provided chat history. The lab content is not only injected at the
  beginning of a browser chat session.
- Provider-side prompt caching may reduce repeated-context cost when supported,
  but the app does not configure explicit cached content.
- Excessively long uploaded documents may eventually hit context-length or cost
  limits because the full parsed text is sent as context for each TA turn. This
  is not expected to be a typical issue for the lab handouts and articles the
  app currently targets.
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
- Existing SQLite databases with a `labs` table missing `quiz_enabled` or
  `ta_enabled` are upgraded in place with both feature flags enabled.
- Existing labs are upgraded with `ta_language='English'` and empty TA custom
  instructions. Existing quizzes are upgraded with nullable education level,
  difficulty, and language plus empty custom instructions.
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

## LLM Model Configuration

- LiteLLM dispatches TA chat, screening, and quiz generation across supported
  hosted and local providers.
- `llm_config.py` defines Gemini defaults using LiteLLM provider-prefixed model
  identifiers: `gemini/gemini-3.5-flash-lite` for chat and quiz generation, and
  `gemini/gemini-2.5-flash-lite` for screening. The `labs` table's model column
  defaults are interpolated from these values rather than hardcoded separately.
- Each lab stores immutable chat, screening, and quiz model identifiers with a
  shared optional API key and optional loopback API base URL.
- The instructor setup form exposes freeform model fields. The dashboard shows
  saved values read-only and never returns the API key.
- Existing unprefixed Gemini model values are upgraded in place.

## Prelab Quiz

- `POST /quiz/generate` creates a draft quiz for a known lab with document text.
- Every generation requires `high_school` or `university`, `easy`, `medium`, or
  `hard`, and a nonblank language. Optional custom instructions are stored with
  that quiz generation.
- Quiz generation settings are immutable snapshots returned with generated and
  instructor-detail responses. Legacy quiz metadata remains null.
- Quiz operations return `403` when quiz generation is disabled for the owning
  lab. Existing quiz data is preserved while disabled.
- The requested question count must be between 3 and 10.
- Quiz-generation prompt categories are mutually exclusive. Quizzes with 3–7
  questions contain one handout-supported safety question and one
  key-definition question; quizzes with 8–10 contain two of each; the remaining
  questions cover general procedure. Answer choices do not differ solely by
  numerical values or small numerical variations.
- Generated quiz questions are stored with choices A-D, a correct answer, an
  explanation, and initial anonymous stats.
- Quiz and TA prompts independently receive their selected languages and custom
  instructions. Protected prompt rules explicitly prevent custom instructions
  from overriding output, consistency, Socratic, safety, or disclosure rules.
- Quiz generation asks the configured model to verify each correct-answer label
  against its answer text and explanation before returning JSON.
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
- The instructor quiz panel can export generated questions as read-only,
  copy/pasteable text. The student-facing export includes numbered questions
  and choices A-D. The answer-key export includes numbered questions and only
  the correct answer label plus answer text, such as `B. <choice B>`.
  Explanations are not included in either export. Draft exports use the current
  editor values, and published quiz exports remain available after refreshing
  `/instructor/{token}`.

## Acceptance Criteria

- Current public routes have deterministic tests that do not call live providers.
- Security screening is enforced before TA generation.
- Prompt template loading and validation have deterministic tests.
- Quiz state transitions reject invalid operations with clear HTTP errors.
- README points contributors to this spec workflow.

## Test Plan

- Run `python -m pytest`.
- Mock LiteLLM-facing chat and quiz generation functions.
- Use an isolated SQLite database per test.
