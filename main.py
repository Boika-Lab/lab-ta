"""Lab TA — FastAPI backend."""

from __future__ import annotations

import logging
import os
import secrets
import sqlite3
import string
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from document_parser import parse_uploaded_file
import llm_config
from llm_client import complete
from prompt_loader import PROMPTS
from quiz_engine import generate_quiz
from ta_engine import build_system_prompt, get_ta_response

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
DB_PATH = Path(os.environ.get("LAB_TA_DB_PATH", BASE_DIR / "lab_ta.db"))
ADMIN_PASSPHRASE_ENV = "LAB_TA_ADMIN_PASSPHRASE"
ADMIN_PASSPHRASE_HEADER = "X-Lab-TA-Passphrase"

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Lab TA")


# ── Database ──────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS labs (
                token      TEXT PRIMARY KEY,
                instructor_token TEXT,
                lab_name   TEXT,
                lab_content TEXT,
                api_key    TEXT,
                model      TEXT,
                screening_model TEXT NOT NULL DEFAULT '{llm_config.SCREENING_MODEL}',
                quiz_model TEXT NOT NULL DEFAULT '{llm_config.QUIZ_MODEL}',
                api_base TEXT NULL,
                created_at TIMESTAMP,
                chat_logging_enabled INTEGER NOT NULL DEFAULT 0,
                quiz_enabled INTEGER NOT NULL DEFAULT 1,
                ta_enabled INTEGER NOT NULL DEFAULT 1,
                ta_language TEXT NOT NULL DEFAULT 'English',
                ta_custom_instructions TEXT NOT NULL DEFAULT ''
            )
        """)
        lab_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(labs)").fetchall()
        }
        if "chat_logging_enabled" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN chat_logging_enabled INTEGER NOT NULL DEFAULT 0"
            )
        if "quiz_enabled" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN quiz_enabled INTEGER NOT NULL DEFAULT 1"
            )
        if "ta_enabled" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN ta_enabled INTEGER NOT NULL DEFAULT 1"
            )
        if "ta_language" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN ta_language TEXT NOT NULL DEFAULT 'English'"
            )
        if "ta_custom_instructions" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN ta_custom_instructions TEXT NOT NULL DEFAULT ''"
            )
        if "screening_model" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN screening_model TEXT NOT NULL "
                f"DEFAULT '{llm_config.SCREENING_MODEL}'"
            )
        if "quiz_model" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN quiz_model TEXT NOT NULL "
                f"DEFAULT '{llm_config.QUIZ_MODEL}'"
            )
        if "api_base" not in lab_columns:
            conn.execute("ALTER TABLE labs ADD COLUMN api_base TEXT NULL")
        if "instructor_token" not in lab_columns:
            conn.execute("ALTER TABLE labs ADD COLUMN instructor_token TEXT")
        missing_instructor_tokens = conn.execute(
            "SELECT token FROM labs "
            "WHERE instructor_token IS NULL OR instructor_token = ''"
        ).fetchall()
        for lab in missing_instructor_tokens:
            conn.execute(
                "UPDATE labs SET instructor_token = ? WHERE token = ?",
                (generate_instructor_token(), lab["token"]),
            )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_labs_instructor_token "
            "ON labs (instructor_token)"
        )
        conn.execute(
            """
            UPDATE labs
            SET model = 'gemini/' || model
            WHERE model LIKE 'gemini-%'
            """
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                token       TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'draft',
                n_questions INTEGER NOT NULL,
                created_at  TIMESTAMP NOT NULL,
                education_level TEXT NULL,
                difficulty TEXT NULL,
                language TEXT NULL,
                custom_instructions TEXT NOT NULL DEFAULT ''
            )
        """)
        quiz_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(quizzes)").fetchall()
        }
        if "education_level" not in quiz_columns:
            conn.execute("ALTER TABLE quizzes ADD COLUMN education_level TEXT NULL")
        if "difficulty" not in quiz_columns:
            conn.execute("ALTER TABLE quizzes ADD COLUMN difficulty TEXT NULL")
        if "language" not in quiz_columns:
            conn.execute("ALTER TABLE quizzes ADD COLUMN language TEXT NULL")
        if "custom_instructions" not in quiz_columns:
            conn.execute(
                "ALTER TABLE quizzes ADD COLUMN custom_instructions TEXT NOT NULL DEFAULT ''"
            )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id       INTEGER NOT NULL,
                question      TEXT NOT NULL,
                choice_a      TEXT NOT NULL,
                choice_b      TEXT NOT NULL,
                choice_c      TEXT NOT NULL,
                choice_d      TEXT NOT NULL,
                correct       TEXT NOT NULL,
                explanation   TEXT NOT NULL,
                display_order INTEGER NOT NULL,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_question_stats (
                question_id      INTEGER PRIMARY KEY,
                total_attempts   INTEGER NOT NULL DEFAULT 0,
                correct_attempts INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                token          TEXT NOT NULL,
                session_id     TEXT NOT NULL,
                exchange_index INTEGER NOT NULL,
                question_at    TIMESTAMP NOT NULL,
                question       TEXT NOT NULL,
                response       TEXT NOT NULL,
                blocked        INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_logs_token_session_exchange
            ON chat_logs (token, session_id, exchange_index)
        """)
        conn.commit()


# ── Token helpers ─────────────────────────────────────────────────────────────
def generate_token() -> str:
    """Eight-character student token from a cryptographically secure source."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def generate_instructor_token() -> str:
    """Private instructor token: 32 URL-safe characters (24 random bytes)."""
    return secrets.token_urlsafe(24)


init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────


def load_html(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def render_instructor_html() -> str:
    html = load_html("instructor.html")
    replacements = {
        "{{CHAT_MODEL}}": llm_config.CHAT_MODEL,
        "{{SCREENING_MODEL}}": llm_config.SCREENING_MODEL,
        "{{QUIZ_MODEL}}": llm_config.QUIZ_MODEL,
    }
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, escape(value))
    return html


def persist_chat_log(
    token: str,
    session_id: Optional[str],
    question: str,
    response: str,
    blocked: bool,
) -> None:
    normalized_session_id = (session_id or "").strip() or "unknown"
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(exchange_index), 0) + 1 AS next_index
            FROM chat_logs
            WHERE token = ? AND session_id = ?
            """,
            (token, normalized_session_id),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO chat_logs
                (token, session_id, exchange_index, question_at, question, response, blocked)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                normalized_session_id,
                row["next_index"],
                datetime.now(UTC).isoformat(),
                question,
                response,
                1 if blocked else 0,
            ),
        )
        conn.commit()


def _disabled_error(feature: str) -> HTTPException:
    return HTTPException(status_code=403, detail=f"{feature} is disabled for this lab")


def require_quiz_enabled_for_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT quiz_enabled FROM labs WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    if not row["quiz_enabled"]:
        raise _disabled_error("Quiz")
    return row


def require_quiz_enabled_for_quiz(conn: sqlite3.Connection, quiz_id: int) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT q.*, l.quiz_enabled
        FROM quizzes q
        JOIN labs l ON l.token = q.token
        WHERE q.id = ?
        """,
        (quiz_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if not row["quiz_enabled"]:
        raise _disabled_error("Quiz")
    return row


def require_instructor_lab(
    conn: sqlite3.Connection, instructor_token: str, columns: str = "token"
) -> sqlite3.Row:
    """Resolve a lab by its private instructor token or raise 404.

    Unknown instructor tokens and student tokens both produce the same 404 so
    the response does not reveal whether a token exists.
    """
    row = conn.execute(
        f"SELECT {columns} FROM labs WHERE instructor_token = ?",
        (instructor_token,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    return row


def require_instructor_quiz(
    conn: sqlite3.Connection, instructor_token: str, quiz_id: int
) -> sqlite3.Row:
    """Resolve a quiz that belongs to the instructor's lab, honoring quiz gating."""
    lab = require_instructor_lab(conn, instructor_token, "token, quiz_enabled")
    if not lab["quiz_enabled"]:
        raise _disabled_error("Quiz")
    row = conn.execute(
        "SELECT * FROM quizzes WHERE id = ? AND token = ?",
        (quiz_id, lab["token"]),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return row


def require_admin_passphrase(provided: Optional[str]) -> None:
    expected = os.environ.get(ADMIN_PASSPHRASE_ENV, "")
    if not expected.strip():
        raise HTTPException(
            status_code=403,
            detail=(
                "The saved-labs index is disabled. Set the "
                f"{ADMIN_PASSPHRASE_ENV} environment variable to enable it."
            ),
        )
    if provided is None or not secrets.compare_digest(
        provided.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Incorrect passphrase")


# ── Request models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list[dict]
    session_id: Optional[str] = None


class GenerateQuizRequest(BaseModel):
    n_questions: int
    education_level: str
    difficulty: str
    language: str
    custom_instructions: str = ""


class FeatureUpdateRequest(BaseModel):
    quiz_enabled: bool
    ta_enabled: bool


class QuestionEdit(BaseModel):
    id: int
    question: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str
    correct: str
    explanation: str


class UpdateQuizRequest(BaseModel):
    questions: list[QuestionEdit]


class SubmitQuizRequest(BaseModel):
    answers: dict[str, str]


def normalize_language(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail=f"{field_name} must not be blank")
    if len(normalized) > 100:
        raise HTTPException(
            status_code=400, detail=f"{field_name} must be at most 100 characters"
        )
    return normalized


def normalize_custom_instructions(value: str, field_name: str) -> str:
    normalized = value.strip()
    if len(normalized) > 4000:
        raise HTTPException(
            status_code=400, detail=f"{field_name} must be at most 4000 characters"
        )
    return normalized


def normalize_model(value: str, field_name: str, default: str) -> str:
    normalized = value.strip() or default
    if len(normalized) > 200:
        raise HTTPException(
            status_code=400, detail=f"{field_name} must be at most 200 characters"
        )
    return normalized


def normalize_api_base(value: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        parsed = urlsplit(normalized)
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="api_base is not a valid URL") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=400, detail="api_base must be an HTTP(S) loopback URL"
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(
            status_code=400,
            detail="api_base must not contain credentials, a query, or a fragment",
        )
    if parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(
            status_code=400,
            detail="api_base must target localhost, 127.0.0.1, or ::1",
        )
    hostname = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    netloc = f"{hostname}:{port}" if port is not None else hostname
    return urlunsplit((parsed.scheme, netloc, parsed.path.rstrip("/"), "", ""))


async def validate_llm_configuration(
    *,
    models: list[str],
    api_key: str | None,
    api_base: str | None,
) -> None:
    for model in dict.fromkeys(models):
        await complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly OK.",
                }
            ],
            api_key=api_key,
            api_base=api_base,
            temperature=0,
        )


def quiz_generation_settings(row: sqlite3.Row) -> dict:
    return {
        "education_level": row["education_level"],
        "difficulty": row["difficulty"],
        "language": row["language"],
        "custom_instructions": row["custom_instructions"],
    }


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def instructor_portal() -> HTMLResponse:
    return HTMLResponse(content=render_instructor_html())


@app.get("/instructor/labs", response_class=HTMLResponse)
async def instructor_labs() -> HTMLResponse:
    return HTMLResponse(content=load_html("instructor_labs.html"))


@app.get("/instructor/{instructor_token}", response_class=HTMLResponse)
async def instructor_dashboard(instructor_token: str) -> HTMLResponse:
    with get_db() as conn:
        require_instructor_lab(conn, instructor_token)
    return HTMLResponse(content=render_instructor_html())


@app.get("/lab/{token}", response_class=HTMLResponse)
async def student_chat(token: str) -> HTMLResponse:
    return HTMLResponse(content=load_html("student.html"))


async def screen_message(
    api_key: str | None,
    api_base: str | None,
    model: str,
    token: str,
    message: str,
) -> bool:
    """Return True if the message should be allowed through, False to block it.

    Calls the configured model to classify the message. Defaults to PASS on any
    error so that a screening failure never breaks the student experience.
    """
    try:
        prompt = PROMPTS["screening"].render(message=message)
        verdict = await complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            api_base=api_base,
            temperature=0,
        )
        verdict = verdict.strip().upper()
        if verdict == "BLOCK":
            logging.warning(
                "Screening blocked message for token=%s: %r", token, message
            )
            return False
    except Exception:
        pass  # Default to PASS so screening errors never break the student
    return True


@app.post("/api/configure")
async def configure(
    api_key: str = Form(""),
    api_base: str = Form(""),
    chat_model: str = Form(llm_config.CHAT_MODEL),
    screening_model: str = Form(llm_config.SCREENING_MODEL),
    quiz_model: str = Form(llm_config.QUIZ_MODEL),
    lab_name: str = Form(...),
    quiz_enabled: bool = Form(True),
    ta_enabled: bool = Form(True),
    ta_language: str = Form("English"),
    ta_custom_instructions: str = Form(""),
    chat_logging_enabled: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
):
    normalized_api_key = api_key.strip() or None
    normalized_api_base = normalize_api_base(api_base)
    chat_model = normalize_model(chat_model, "chat_model", llm_config.CHAT_MODEL)
    screening_model = normalize_model(
        screening_model, "screening_model", llm_config.SCREENING_MODEL
    )
    quiz_model = normalize_model(quiz_model, "quiz_model", llm_config.QUIZ_MODEL)
    ta_language = normalize_language(ta_language, "ta_language")
    ta_custom_instructions = normalize_custom_instructions(
        ta_custom_instructions, "ta_custom_instructions"
    )
    parts: list[str] = []
    for f in files:
        raw = await f.read()
        try:
            text = parse_uploaded_file(f.filename or "", raw)
            parts.append(f"=== {f.filename} ===\n{text}")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    lab_content = "\n\n".join(parts)
    token = generate_token()
    instructor_token = generate_instructor_token()

    try:
        await validate_llm_configuration(
            models=[chat_model, screening_model, quiz_model],
            api_key=normalized_api_key,
            api_base=normalized_api_base,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM configuration validation failed. Check the model names, "
            "credentials, and API base URL.",
        ) from exc

    with get_db() as conn:
        # Ensure uniqueness (astronomically unlikely but correct)
        while conn.execute("SELECT 1 FROM labs WHERE token = ?", (token,)).fetchone():
            token = generate_token()
        while conn.execute(
            "SELECT 1 FROM labs WHERE instructor_token = ?", (instructor_token,)
        ).fetchone():
            instructor_token = generate_instructor_token()
        conn.execute(
            "INSERT INTO labs "
            "(token, instructor_token, lab_name, lab_content, api_key, model, "
            "screening_model, quiz_model, api_base, created_at, "
            "chat_logging_enabled, quiz_enabled, ta_enabled, ta_language, "
            "ta_custom_instructions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                token,
                instructor_token,
                lab_name,
                lab_content,
                normalized_api_key,
                chat_model,
                screening_model,
                quiz_model,
                normalized_api_base,
                datetime.now(UTC).isoformat(),
                1 if chat_logging_enabled else 0,
                1 if quiz_enabled else 0,
                1 if ta_enabled else 0,
                ta_language,
                ta_custom_instructions,
            ),
        )
        conn.commit()

    return {
        "token": token,
        "instructor_token": instructor_token,
        "student_url": f"/lab/{token}",
        "instructor_url": f"/instructor/{instructor_token}",
    }


@app.get("/api/lab/{token}")
async def get_lab_info(token: str):
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT lab_name, model, quiz_enabled, ta_enabled
            FROM labs
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    return {
        "lab_name": row["lab_name"],
        "model": row["model"],
        "quiz_enabled": bool(row["quiz_enabled"]),
        "ta_enabled": bool(row["ta_enabled"]),
    }


@app.get("/api/instructor/labs")
async def get_instructor_labs(
    passphrase: Optional[str] = Header(default=None, alias=ADMIN_PASSPHRASE_HEADER),
):
    require_admin_passphrase(passphrase)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                l.token,
                l.instructor_token,
                l.lab_name,
                l.created_at,
                l.chat_logging_enabled,
                l.quiz_enabled,
                l.ta_enabled,
                COUNT(DISTINCT q.id) AS quiz_count,
                MAX(CASE WHEN q.status = 'published' THEN q.status ELSE NULL END)
                    AS active_quiz_status,
                COUNT(DISTINCT cl.id) AS chat_log_exchange_count
            FROM labs l
            LEFT JOIN quizzes q ON q.token = l.token
            LEFT JOIN chat_logs cl ON cl.token = l.token
            GROUP BY l.token, l.instructor_token, l.lab_name, l.created_at,
                     l.chat_logging_enabled, l.quiz_enabled, l.ta_enabled
            ORDER BY l.created_at DESC, l.token DESC
            """
        ).fetchall()

    labs = []
    for row in rows:
        quiz_count = row["quiz_count"]
        token = row["token"]
        labs.append(
            {
                "token": token,
                "lab_name": row["lab_name"],
                "student_url": f"/lab/{token}",
                "instructor_url": f"/instructor/{row['instructor_token']}",
                "chat_logging_enabled": bool(row["chat_logging_enabled"]),
                "quiz_enabled": bool(row["quiz_enabled"]),
                "ta_enabled": bool(row["ta_enabled"]),
                "created_at": row["created_at"],
                "quiz_count": quiz_count,
                "has_quizzes": quiz_count > 0,
                "active_quiz_status": row["active_quiz_status"],
                "chat_log_exchange_count": row["chat_log_exchange_count"],
            }
        )
    return labs


@app.get("/api/instructor/lab/{instructor_token}")
async def get_instructor_lab(instructor_token: str):
    with get_db() as conn:
        lab = require_instructor_lab(
            conn,
            instructor_token,
            "token, lab_name, model, screening_model, quiz_model, api_base, "
            "chat_logging_enabled, quiz_enabled, ta_enabled, ta_language, "
            "ta_custom_instructions",
        )
        token = lab["token"]
        quiz = conn.execute(
            """
            SELECT id, status, n_questions, created_at, education_level,
                   difficulty, language, custom_instructions
            FROM quizzes
            WHERE token = ? AND status = 'published'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (token,),
        ).fetchone()

    active_quiz = None
    if quiz:
        active_quiz = {
            "quiz_id": quiz["id"],
            "status": quiz["status"],
            "n_questions": quiz["n_questions"],
            "created_at": quiz["created_at"],
            "generation_settings": quiz_generation_settings(quiz),
        }

    return {
        "token": token,
        "instructor_token": instructor_token,
        "lab_name": lab["lab_name"],
        "model": lab["model"],
        "screening_model": lab["screening_model"],
        "quiz_model": lab["quiz_model"],
        "api_base": lab["api_base"],
        "student_url": f"/lab/{token}",
        "instructor_url": f"/instructor/{instructor_token}",
        "chat_logging_enabled": bool(lab["chat_logging_enabled"]),
        "quiz_enabled": bool(lab["quiz_enabled"]),
        "ta_enabled": bool(lab["ta_enabled"]),
        "ta_language": lab["ta_language"],
        "ta_custom_instructions": lab["ta_custom_instructions"],
        "active_quiz": active_quiz,
    }


@app.patch("/api/instructor/lab/{instructor_token}/features")
async def update_lab_features(instructor_token: str, req: FeatureUpdateRequest):
    with get_db() as conn:
        token = require_instructor_lab(conn, instructor_token)["token"]
        conn.execute(
            "UPDATE labs SET quiz_enabled = ?, ta_enabled = ? WHERE token = ?",
            (1 if req.quiz_enabled else 0, 1 if req.ta_enabled else 0, token),
        )
        conn.commit()
    return {
        "token": token,
        "quiz_enabled": req.quiz_enabled,
        "ta_enabled": req.ta_enabled,
    }


@app.post("/api/chat/{token}")
async def chat(token: str, req: ChatRequest):
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT lab_name, lab_content, api_key, model, screening_model, api_base,
                   chat_logging_enabled, ta_enabled, ta_language,
                   ta_custom_instructions
            FROM labs
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    if not row["ta_enabled"]:
        raise _disabled_error("Socratic TA")

    system_prompt = build_system_prompt(
        row["lab_name"],
        row["lab_content"],
        row["ta_language"],
        row["ta_custom_instructions"],
    )
    full_history = req.history + [{"role": "user", "text": req.message}]

    passed = await screen_message(
        row["api_key"],
        row["api_base"],
        row["screening_model"],
        token,
        req.message,
    )
    if not passed:
        refusal = "I can only help with questions about this lab activity."
        if row["chat_logging_enabled"]:
            persist_chat_log(token, req.session_id, req.message, refusal, blocked=True)
        return {"response": refusal}

    try:
        ta_response = await get_ta_response(
            api_key=row["api_key"],
            api_base=row["api_base"],
            model=row["model"],
            system_prompt=system_prompt,
            history=full_history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if row["chat_logging_enabled"]:
        persist_chat_log(token, req.session_id, req.message, ta_response, blocked=False)

    return {"response": ta_response}


@app.get("/api/instructor/lab/{instructor_token}/chat-logs")
async def chat_logs(instructor_token: str):
    with get_db() as conn:
        lab = require_instructor_lab(
            conn, instructor_token, "token, lab_name, chat_logging_enabled"
        )
        token = lab["token"]
        rows = conn.execute(
            """
            SELECT id, session_id, exchange_index, question_at, question, response, blocked
            FROM chat_logs
            WHERE token = ?
            ORDER BY session_id, exchange_index
            """,
            (token,),
        ).fetchall()

    sessions_by_id: dict[str, dict] = {}
    for row in rows:
        session = sessions_by_id.setdefault(
            row["session_id"], {"session_id": row["session_id"], "exchanges": []}
        )
        session["exchanges"].append(
            {
                "id": row["id"],
                "exchange_index": row["exchange_index"],
                "question_at": row["question_at"],
                "question": row["question"],
                "response": row["response"],
                "blocked": bool(row["blocked"]),
            }
        )

    return {
        "token": token,
        "lab_name": lab["lab_name"],
        "chat_logging_enabled": bool(lab["chat_logging_enabled"]),
        "sessions": list(sessions_by_id.values()),
    }


# ── Quiz helpers ──────────────────────────────────────────────────────────────
def _get_quiz_questions(conn: sqlite3.Connection, quiz_id: int, include_answer_data: bool = True) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM quiz_questions WHERE quiz_id = ? ORDER BY display_order",
        (quiz_id,),
    ).fetchall()
    result = []
    for row in rows:
        q: dict = {
            "id": row["id"],
            "question": row["question"],
            "choices": {
                "A": row["choice_a"],
                "B": row["choice_b"],
                "C": row["choice_c"],
                "D": row["choice_d"],
            },
            "display_order": row["display_order"],
        }
        if include_answer_data:
            q["correct"] = row["correct"]
            q["explanation"] = row["explanation"]
        result.append(q)
    return result


# ── Quiz routes ───────────────────────────────────────────────────────────────
@app.post("/api/instructor/lab/{instructor_token}/quiz/generate")
async def quiz_generate(instructor_token: str, req: GenerateQuizRequest):
    if req.education_level not in {"high_school", "university"}:
        raise HTTPException(
            status_code=400,
            detail="education_level must be high_school or university",
        )
    if req.difficulty not in {"easy", "medium", "hard"}:
        raise HTTPException(
            status_code=400, detail="difficulty must be easy, medium, or hard"
        )
    language = normalize_language(req.language, "language")
    custom_instructions = normalize_custom_instructions(
        req.custom_instructions, "custom_instructions"
    )
    with get_db() as conn:
        row = require_instructor_lab(
            conn,
            instructor_token,
            "token, quiz_enabled, lab_content, api_key, api_base, quiz_model",
        )
        if not row["quiz_enabled"]:
            raise _disabled_error("Quiz")
    token = row["token"]
    if not row["lab_content"] or not row["lab_content"].strip():
        raise HTTPException(status_code=400, detail="No document text available for this lab")
    if not (3 <= req.n_questions <= 10):
        raise HTTPException(status_code=400, detail="n_questions must be between 3 and 10")

    try:
        questions = await generate_quiz(
            row["api_key"],
            row["api_base"],
            row["quiz_model"],
            row["lab_content"],
            req.n_questions,
            req.education_level,
            req.difficulty,
            language,
            custom_instructions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Quiz generation failed — please try again. ({exc})") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Quiz generation failed. Check the saved model configuration "
            "and provider availability.",
        ) from exc

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO quizzes "
            "(token, status, n_questions, created_at, education_level, difficulty, "
            "language, custom_instructions) "
            "VALUES (?, 'draft', ?, ?, ?, ?, ?, ?)",
            (
                token,
                req.n_questions,
                datetime.now(UTC).isoformat(),
                req.education_level,
                req.difficulty,
                language,
                custom_instructions,
            ),
        )
        quiz_id = cur.lastrowid
        for i, q in enumerate(questions):
            qcur = conn.execute(
                "INSERT INTO quiz_questions "
                "(quiz_id, question, choice_a, choice_b, choice_c, choice_d, correct, explanation, display_order) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (quiz_id, q["question"], q["choices"]["A"], q["choices"]["B"],
                 q["choices"]["C"], q["choices"]["D"], q["correct"], q["explanation"], i),
            )
            conn.execute(
                "INSERT INTO quiz_question_stats (question_id, total_attempts, correct_attempts) VALUES (?, 0, 0)",
                (qcur.lastrowid,),
            )
        conn.commit()

    with get_db() as conn:
        quiz_questions = _get_quiz_questions(conn, quiz_id, include_answer_data=True)

    return {
        "quiz_id": quiz_id,
        "status": "draft",
        "generation_settings": {
            "education_level": req.education_level,
            "difficulty": req.difficulty,
            "language": language,
            "custom_instructions": custom_instructions,
        },
        "questions": quiz_questions,
    }


@app.get("/quiz/active/{token}")
async def quiz_active(token: str):
    with get_db() as conn:
        require_quiz_enabled_for_token(conn, token)
        row = conn.execute(
            "SELECT id FROM quizzes WHERE token = ? AND status = 'published'", (token,)
        ).fetchone()
    if not row:
        return {"quiz_id": None, "questions": []}
    quiz_id = row["id"]
    with get_db() as conn:
        questions = _get_quiz_questions(conn, quiz_id, include_answer_data=False)
    return {"quiz_id": quiz_id, "questions": questions}


@app.get("/api/instructor/lab/{instructor_token}/quiz/{quiz_id}")
async def quiz_get(instructor_token: str, quiz_id: int):
    with get_db() as conn:
        row = require_instructor_quiz(conn, instructor_token, quiz_id)
    with get_db() as conn:
        questions = _get_quiz_questions(conn, quiz_id, include_answer_data=True)
    return {
        "quiz_id": quiz_id,
        "token": row["token"],
        "status": row["status"],
        "generation_settings": quiz_generation_settings(row),
        "questions": questions,
    }


@app.put("/api/instructor/lab/{instructor_token}/quiz/{quiz_id}")
async def quiz_update(instructor_token: str, quiz_id: int, req: UpdateQuizRequest):
    with get_db() as conn:
        row = require_instructor_quiz(conn, instructor_token, quiz_id)
    if row["status"] != "draft":
        raise HTTPException(status_code=400, detail="Only draft quizzes can be edited")

    incoming_ids = {q.id for q in req.questions}
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM quiz_questions WHERE quiz_id = ?", (quiz_id,)
        ).fetchall()
        for r in existing:
            if r["id"] not in incoming_ids:
                conn.execute("DELETE FROM quiz_question_stats WHERE question_id = ?", (r["id"],))
                conn.execute("DELETE FROM quiz_questions WHERE id = ?", (r["id"],))
        for q in req.questions:
            conn.execute(
                "UPDATE quiz_questions SET question=?, choice_a=?, choice_b=?, choice_c=?, "
                "choice_d=?, correct=?, explanation=? WHERE id=? AND quiz_id=?",
                (q.question, q.choice_a, q.choice_b, q.choice_c, q.choice_d,
                 q.correct, q.explanation, q.id, quiz_id),
            )
        conn.commit()
    return {"ok": True}


@app.post("/api/instructor/lab/{instructor_token}/quiz/{quiz_id}/publish")
async def quiz_publish(instructor_token: str, quiz_id: int):
    with get_db() as conn:
        row = require_instructor_quiz(conn, instructor_token, quiz_id)
    if row["status"] == "published":
        raise HTTPException(status_code=400, detail="Quiz is already published")

    token = row["token"]
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM quizzes WHERE token = ? AND status = 'published'", (token,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"A published quiz already exists for this lab (quiz #{existing['id']}). "
                       "Close it before publishing a new one.",
            )
        conn.execute("UPDATE quizzes SET status = 'published' WHERE id = ?", (quiz_id,))
        conn.commit()
    return {"ok": True, "quiz_id": quiz_id}


@app.post("/api/instructor/lab/{instructor_token}/quiz/{quiz_id}/close")
async def quiz_close(instructor_token: str, quiz_id: int):
    with get_db() as conn:
        row = require_instructor_quiz(conn, instructor_token, quiz_id)
    if row["status"] != "published":
        raise HTTPException(status_code=400, detail="Only published quizzes can be closed")
    with get_db() as conn:
        conn.execute("UPDATE quizzes SET status = 'closed' WHERE id = ?", (quiz_id,))
        conn.commit()
    return {"ok": True}


@app.post("/quiz/{quiz_id}/submit")
async def quiz_submit(quiz_id: int, req: SubmitQuizRequest):
    with get_db() as conn:
        quiz_row = require_quiz_enabled_for_quiz(conn, quiz_id)
    if quiz_row["status"] != "published":
        raise HTTPException(status_code=400, detail="Quiz is not published")

    question_ids = [int(k) for k in req.answers.keys()]
    if not question_ids:
        raise HTTPException(status_code=400, detail="No answers submitted")

    placeholders = ",".join("?" * len(question_ids))
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT id, correct, explanation FROM quiz_questions "
            f"WHERE id IN ({placeholders}) AND quiz_id = ?",
            (*question_ids, quiz_id),
        ).fetchall()

    if len(rows) != len(question_ids):
        raise HTTPException(status_code=400, detail="One or more question IDs are invalid for this quiz")

    results: dict = {}
    all_correct = True
    for row in rows:
        qid = row["id"]
        chosen = req.answers[str(qid)].upper()
        is_correct = chosen == row["correct"]
        results[qid] = {
            "correct": is_correct,
            "explanation": None if is_correct else row["explanation"],
        }
        if not is_correct:
            all_correct = False

    with get_db() as conn:
        for row in rows:
            qid = row["id"]
            conn.execute(
                "UPDATE quiz_question_stats "
                "SET total_attempts = total_attempts + 1, "
                "correct_attempts = correct_attempts + ? "
                "WHERE question_id = ?",
                (1 if results[qid]["correct"] else 0, qid),
            )
        conn.commit()

    response: dict = {"passed": all_correct, "results": results}
    if all_correct:
        response["message"] = "All correct! You're cleared to begin the lab."
    return response


@app.get("/api/instructor/lab/{instructor_token}/quiz/{quiz_id}/stats")
async def quiz_stats(instructor_token: str, quiz_id: int):
    with get_db() as conn:
        row = require_instructor_quiz(conn, instructor_token, quiz_id)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT qq.id, qq.question, qq.display_order,
                   COALESCE(s.total_attempts, 0)   AS total_attempts,
                   COALESCE(s.correct_attempts, 0) AS correct_attempts
            FROM quiz_questions qq
            LEFT JOIN quiz_question_stats s ON s.question_id = qq.id
            WHERE qq.quiz_id = ?
            ORDER BY qq.display_order
            """,
            (quiz_id,),
        ).fetchall()

    stats = []
    for r in rows:
        total = r["total_attempts"]
        correct = r["correct_attempts"]
        stats.append({
            "question_id": r["id"],
            "question": r["question"],
            "total_attempts": total,
            "correct_attempts": correct,
            "pct_correct": round(correct / total * 100, 1) if total > 0 else None,
        })
    return {"quiz_id": quiz_id, "status": row["status"], "stats": stats}
