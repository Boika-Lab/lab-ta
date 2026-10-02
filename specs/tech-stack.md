# Tech Stack

This document describes the current implementation stack. It is descriptive,
not a target architecture.

## Runtime

- Python 3.11 or newer. Tested on 3.11, 3.12, and 3.14.
- FastAPI backend served by Uvicorn on port `8000`.
- SQLite database stored as `lab_ta.db` by default.
- Optional `LAB_TA_DB_PATH` environment variable for overriding the database
  path, primarily used by tests.
- Optional `LAB_TA_ADMIN_PASSPHRASE` environment variable that unlocks the
  saved-labs index. When unset, the index API returns `403`.

## Backend Modules

- `main.py`: FastAPI app, route handlers, SQLite schema initialization, chat log
  persistence, and quiz persistence.
- `llm_config.py`: default LiteLLM model role identifiers.
- `llm_client.py`: provider-neutral asynchronous LiteLLM completion adapter.
- `prompt_loader.py`: startup/import-time loading, validation, and rendering of
  Markdown prompt templates from `prompts/`.
- `ta_engine.py`: Socratic prompt rendering and provider-neutral chat calls.
- `quiz_engine.py`: provider-neutral multiple-choice prelab quiz generation.
- `document_parser.py`: Text extraction from uploaded PDF, PPTX, and DOCX files.
- QR codes for student links are rendered server-side as SVG with `segno`
  through `GET /api/instructor/lab/{instructor_token}/qr.svg`.

## Frontend

- Server-rendered static HTML templates in `templates/`.
- `templates/instructor.html`: instructor setup, file upload, optional chat log
  checkbox, durable dashboard hydration for `/instructor/{token}`, student
  link, QR code, chat log export, saved-labs link, grouped feature availability
  controls, quiz generation, quiz publishing, and stats UI.
- The instructor template uses `localStorage` for the last TA language/custom
  instructions and quiz level/difficulty/language/custom instructions.
- `templates/lab_not_found.html`: static, dependency-free page served with
  status `404` for unknown or deleted student and instructor links.
- `templates/instructor_labs.html`: saved-labs index that asks for the admin
  passphrase, keeps it in `sessionStorage`, fetches `/api/instructor/labs` with
  the `X-Lab-TA-Passphrase` header, and links to instructor dashboard and
  student URLs.
- `templates/student.html`: student chat UI, voice input, text-to-speech,
  MathJax rendering, anonymous browser-local chat session ID, prelab quiz gate,
  retry flow, and local quiz progress storage.
- Browser APIs used by the student UI include Web Speech recognition,
  speech synthesis, `crypto.randomUUID`, `localStorage`, and standard `fetch`.

## External Services

- LiteLLM for TA responses, message screening, and quiz generation. Gemini is
  the default provider; loopback services such as Ollama can be selected per
  lab.
- Tailscale Funnel for public HTTPS access to the local server.
- MathJax loaded from a CDN for mathematical and chemical notation rendering.

## Dependencies

- `fastapi`
- `uvicorn[standard]`
- `python-multipart`
- `litellm`
- `pypdf`
- `python-pptx`
- `python-docx`
- `segno` (pure-Python QR code generation)
- `pytest` (tests only)
- `httpx2` (tests only; the FastAPI test client's HTTP backend)

## Testing

- Pytest contract tests live in `tests/`.
- Tests mock LiteLLM-facing functions and use isolated SQLite databases.
- Contract tests cover in-place schema upgrades and immutable generation
  metadata in addition to route and prompt behavior.
- Static template tests verify important UI wiring such as chat logging controls
  instructor dashboard hydration, saved-labs links, feature availability
  controls, and browser-local session IDs.
- The current verification command is `python -m pytest`.

## Access Model

- Student routes are keyed by an eight-character student token.
- Instructor routes are keyed by a separate private instructor token of at
  least 32 URL-safe characters stored in `labs.instructor_token`. Both tokens
  come from the `secrets` module.
- There are no user accounts, sessions, or cookies. Holding an instructor URL
  is what grants management access to that lab. The instructor token can be
  rotated from the dashboard to revoke a leaked URL.

## Environment Variables

- `LAB_TA_DB_PATH`: override the SQLite database path, primarily for tests.
- `LAB_TA_ADMIN_PASSPHRASE`: passphrase required by `GET /api/instructor/labs`.
