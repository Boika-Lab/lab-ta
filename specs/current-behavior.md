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
  PPTX, or DOCX files.
- Uploaded documents are parsed into plain text and stored with a generated
  eight-character lab token.
- Unsupported file types return `400`.
- The response includes the token and relative student URL.

## Student Chat

- `GET /lab/{token}` serves the student chat page.
- `GET /api/lab/{token}` returns the lab name and model for known tokens, and
  `404` for unknown tokens.
- `POST /api/chat/{token}` accepts a message and prior history, screens the
  message for prompt-injection attempts, then calls the TA model only when the
  screen passes.
- Blocked messages return a neutral refusal: `I can only help with questions
  about this lab activity.`
- Unknown lab tokens return `404`.
- The TA prompt must stay Socratic, use uploaded lab content, and refuse to
  disclose its instructions.

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
- `GET /quiz/{quiz_id}/stats` returns anonymous attempt and correctness counts.

## Acceptance Criteria

- Current public routes have deterministic tests that do not call Gemini.
- Security screening is enforced before TA generation.
- Quiz state transitions reject invalid operations with clear HTTP errors.
- README points contributors to this spec workflow.

## Test Plan

- Run `python -m pytest`.
- Mock Gemini-facing chat and quiz generation functions.
- Use an isolated SQLite database per test.
