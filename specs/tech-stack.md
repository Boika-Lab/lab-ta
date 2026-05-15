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

- `main.py`: FastAPI app, route handlers, SQLite schema initialization, and quiz
  persistence.
- `ta_engine.py`: Socratic system prompt construction and Gemini chat calls.
- `quiz_engine.py`: Gemini-powered multiple-choice prelab quiz generation.
- `document_parser.py`: Text extraction from uploaded PDF, PPTX, and DOCX files.

## Frontend

- Server-rendered static HTML templates in `templates/`.
- `templates/instructor.html`: instructor setup, file upload, student link, QR
  code, quiz generation, quiz publishing, and stats UI.
- `templates/student.html`: student chat UI, voice input, text-to-speech,
  MathJax rendering, prelab quiz gate, retry flow, and local quiz progress
  storage.
- Browser APIs used by the student UI include Web Speech recognition,
  speech synthesis, `localStorage`, and standard `fetch`.

## External Services

- Google Gemini 2.5 Flash via the `google-genai` SDK for TA responses, message
  screening, and quiz generation.
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
- The current verification command is `python -m pytest`.
