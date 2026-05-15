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
- Voice input and text-to-speech in the student browser UI.
- MathJax rendering for mathematical and chemical notation.
- Prelab quiz generation through `POST /quiz/generate`.
- Draft quiz editing through `PUT /quiz/{quiz_id}`.
- Quiz publishing, single-active-quiz enforcement, and quiz closing.
- Student quiz gate through `GET /quiz/active/{token}` and
  `POST /quiz/{quiz_id}/submit`.
- Retry flow for missed quiz questions in the student UI.
- Anonymous quiz attempt stats through `GET /quiz/{quiz_id}/stats`.

## Current Quality and Process Features

- Markdown specification workflow in `specs/`.
- Current behavior spec for inherited app behavior.
- Reusable spec template for future changes.
- Pytest route-level contract tests.
- Test database isolation through `LAB_TA_DB_PATH`.

## Current Known Constraints

- The app stores API keys locally in SQLite.
- There is no user login or role-based authentication.
- The instructor and student pages are plain HTML/CSS/JavaScript templates.
- Database schema setup is handled with `CREATE TABLE IF NOT EXISTS`; there is
  no migration framework.
- Automated tests cover backend route contracts, not browser UI behavior.
- Live Gemini calls are intentionally excluded from automated tests.

## Future Roadmap

Future work should start as a new or updated spec with explicit acceptance
criteria. The planned feature areas below should be treated as roadmap items,
not current behavior.

### LLM Prompt Externalization

- Move all LLM prompts out of Python source files and into separate Markdown
  files under `/prompts` for better data/code separation.
- Load prompt Markdown files into memory when the application starts, so request
  handlers can reuse validated prompt templates without reading from disk on
  every request.

### LLM Configuration File

- Move LLM configuration, including API key and model name, into a configuration
  file instead of storing or passing those values through lab setup data.

### LiteLLM Provider Support

- Add LiteLLM as the LLM integration layer so the app can switch to other LLM
  services through configuration rather than provider-specific code changes.

### Optional Persistent Chat Logs

- Add an instructor-facing checkbox to enable persistent database storage of
  student chat sessions.
- When enabled, store each chat exchange with the date and time of the student
  question, the question text, and the model response text.
- Store chat records in an ordered form that allows the full sequence of a chat
  session to be extracted as a complete log.
- Keep persistent chat logging disabled unless the instructor explicitly turns
  it on.

### Quiz Completion Feedback

- After a student submits quiz answers, change the student UI background based
  on the result: green when all answers are correct, yellow when exactly one
  answer is incorrect, and red when more than one answer is incorrect.
- Reset the background to the default color whenever the student attempts the
  quiz again.

### Security Audit

- Review the codebase for possible security problems, including API key
  handling, prompt-injection handling, uploaded document processing, database
  access, unauthenticated instructor/student routes, and persisted student data.
- Record any findings as actionable follow-up work with severity, affected
  behavior, and suggested remediation.
