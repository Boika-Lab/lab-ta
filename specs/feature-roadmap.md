# Feature Roadmap

This roadmap records the current feature surface of the project. It does not
define future priorities yet.

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

No future roadmap has been defined yet. Future work should start as a new or
updated spec with explicit acceptance criteria.
