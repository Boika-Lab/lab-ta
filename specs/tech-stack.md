# Tech Stack

This document describes the current implementation stack. It is descriptive,
not a target architecture.

## Runtime

- Python 3.9 or newer.
- FastAPI backend served by Uvicorn on port `8000`.
- SQLite database stored as `lab_ta.db` by default.
- Optional `LAB_TA_DB_PATH` environment variable for overriding the database
  path, primarily used by tests.

## Backend Modules

- `main.py`: FastAPI app, route handlers, SQLite schema initialization, chat log
  persistence, and quiz persistence.
- `llm_config.py`: server-controlled Gemini model role constants.
- `prompt_loader.py`: startup/import-time loading, validation, and rendering of
  Markdown prompt templates from `prompts/`.
- `ta_engine.py`: Socratic system prompt rendering and Gemini chat calls.
- `quiz_engine.py`: Gemini-powered multiple-choice prelab quiz generation.
- `document_parser.py`: Text extraction from uploaded PDF, PPTX, and DOCX files.

## Frontend

- Server-rendered static HTML templates in `templates/`.
- `templates/instructor.html`: instructor setup, file upload, optional chat log
  checkbox, student link, QR code, chat log export, quiz generation, quiz
  publishing, and stats UI.
- `templates/student.html`: student chat UI, voice input, text-to-speech,
  MathJax rendering, anonymous browser-local chat session ID, prelab quiz gate,
  retry flow, and local quiz progress storage.
- Browser APIs used by the student UI include Web Speech recognition,
  speech synthesis, `crypto.randomUUID`, `localStorage`, and standard `fetch`.

## External Services

- Google Gemini via the `google-genai` SDK for TA responses, message screening,
  and quiz generation. TA responses and quiz generation currently use
  `gemini-2.5-flash`; message screening uses `gemini-2.5-flash-lite`.
- Tailscale Funnel for public HTTPS access to the local server.
- MathJax loaded from a CDN for mathematical and chemical notation rendering.
- QR code image generation is currently loaded from a third-party QR service in
  the instructor page.

## Dependencies

- `fastapi`
- `uvicorn[standard]`
- `python-multipart`
- `google-genai`
- `pypdf`
- `python-pptx`
- `python-docx`
- `pytest`

## Testing

- Pytest contract tests live in `tests/`.
- Tests mock Gemini-facing functions and use isolated SQLite databases.
- Static template tests verify important UI wiring such as chat logging controls
  and browser-local session IDs.
- The current verification command is `python -m pytest`.

## Environment Variables

- `LAB_TA_DB_PATH`: override the SQLite database path, primarily for tests.
