"""Lab TA — FastAPI backend."""

from __future__ import annotations

import logging
import os
import random
import sqlite3
import string
from html import escape
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
from pydantic import BaseModel

from document_parser import parse_uploaded_file
import llm_config
from prompt_loader import PROMPTS
from quiz_engine import generate_quiz
from ta_engine import build_system_prompt, get_ta_response

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
DB_PATH = Path(os.environ.get("LAB_TA_DB_PATH", BASE_DIR / "lab_ta.db"))

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Lab TA")


# ── Database ──────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS labs (
                token      TEXT PRIMARY KEY,
                lab_name   TEXT,
                lab_content TEXT,
                api_key    TEXT,
                model      TEXT,
                created_at TIMESTAMP
            )
        """)
        lab_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(labs)").fetchall()
        }
        if "chat_logging_enabled" not in lab_columns:
            conn.execute(
                "ALTER TABLE labs ADD COLUMN chat_logging_enabled INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                token       TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'draft',
                n_questions INTEGER NOT NULL,
                created_at  TIMESTAMP NOT NULL
            )
        """)
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


init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────
def generate_token() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))


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


# ── Request models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list[dict]
    session_id: Optional[str] = None


class GenerateQuizRequest(BaseModel):
    token: str
    n_questions: int


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


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def instructor_portal() -> HTMLResponse:
    return HTMLResponse(content=render_instructor_html())


@app.get("/instructor/labs", response_class=HTMLResponse)
async def instructor_labs() -> HTMLResponse:
    return HTMLResponse(content=load_html("instructor_labs.html"))


@app.get("/instructor/{token}", response_class=HTMLResponse)
async def instructor_dashboard(token: str) -> HTMLResponse:
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM labs WHERE token = ?", (token,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    return HTMLResponse(content=render_instructor_html())


@app.get("/lab/{token}", response_class=HTMLResponse)
async def student_chat(token: str) -> HTMLResponse:
    return HTMLResponse(content=load_html("student.html"))


async def screen_message(api_key: str, token: str, message: str) -> bool:
    """Return True if the message should be allowed through, False to block it.

    Calls Gemini to classify the message. Defaults to PASS on any error so
    that a screening failure never breaks the student experience.
    """
    try:
        client = genai.Client(api_key=api_key)
        prompt = PROMPTS["screening"].render(message=message)
        response = await client.aio.models.generate_content(
            model=llm_config.SCREENING_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0),
        )
        verdict = response.text.strip().upper()
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
    api_key: str = Form(...),
    lab_name: str = Form(...),
    chat_logging_enabled: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
):
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

    with get_db() as conn:
        # Ensure uniqueness (astronomically unlikely but correct)
        while conn.execute("SELECT 1 FROM labs WHERE token = ?", (token,)).fetchone():
            token = generate_token()
        conn.execute(
            "INSERT INTO labs "
            "(token, lab_name, lab_content, api_key, model, created_at, chat_logging_enabled) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                token,
                lab_name,
                lab_content,
                api_key,
                llm_config.CHAT_MODEL,
                datetime.now(UTC).isoformat(),
                1 if chat_logging_enabled else 0,
            ),
        )
        conn.commit()

    return {
        "token": token,
        "student_url": f"/lab/{token}",
        "instructor_url": f"/instructor/{token}",
    }


@app.get("/api/lab/{token}")
async def get_lab_info(token: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT lab_name, model FROM labs WHERE token = ?", (token,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    return {"lab_name": row["lab_name"], "model": row["model"]}


@app.get("/api/instructor/labs")
async def get_instructor_labs():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                l.token,
                l.lab_name,
                l.created_at,
                l.chat_logging_enabled,
                COUNT(DISTINCT q.id) AS quiz_count,
                MAX(CASE WHEN q.status = 'published' THEN q.status ELSE NULL END)
                    AS active_quiz_status,
                COUNT(DISTINCT cl.id) AS chat_log_exchange_count
            FROM labs l
            LEFT JOIN quizzes q ON q.token = l.token
            LEFT JOIN chat_logs cl ON cl.token = l.token
            GROUP BY l.token, l.lab_name, l.created_at, l.chat_logging_enabled
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
                "instructor_url": f"/instructor/{token}",
                "chat_logging_enabled": bool(row["chat_logging_enabled"]),
                "created_at": row["created_at"],
                "quiz_count": quiz_count,
                "has_quizzes": quiz_count > 0,
                "active_quiz_status": row["active_quiz_status"],
                "chat_log_exchange_count": row["chat_log_exchange_count"],
            }
        )
    return labs


@app.get("/api/instructor/lab/{token}")
async def get_instructor_lab(token: str):
    with get_db() as conn:
        lab = conn.execute(
            """
            SELECT lab_name, model, chat_logging_enabled
            FROM labs
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
        if not lab:
            raise HTTPException(status_code=404, detail="Lab not found")
        quiz = conn.execute(
            """
            SELECT id, status, n_questions, created_at
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
        }

    return {
        "token": token,
        "lab_name": lab["lab_name"],
        "model": lab["model"],
        "student_url": f"/lab/{token}",
        "instructor_url": f"/instructor/{token}",
        "chat_logging_enabled": bool(lab["chat_logging_enabled"]),
        "active_quiz": active_quiz,
    }


@app.post("/api/chat/{token}")
async def chat(token: str, req: ChatRequest):
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT lab_name, lab_content, api_key, model, chat_logging_enabled
            FROM labs
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")

    system_prompt = build_system_prompt(row["lab_name"], row["lab_content"])
    full_history = req.history + [{"role": "user", "text": req.message}]

    passed = await screen_message(row["api_key"], token, req.message)
    if not passed:
        refusal = "I can only help with questions about this lab activity."
        if row["chat_logging_enabled"]:
            persist_chat_log(token, req.session_id, req.message, refusal, blocked=True)
        return {"response": refusal}

    try:
        ta_response = await get_ta_response(
            api_key=row["api_key"],
            model=row["model"],
            system_prompt=system_prompt,
            history=full_history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if row["chat_logging_enabled"]:
        persist_chat_log(token, req.session_id, req.message, ta_response, blocked=False)

    return {"response": ta_response}


@app.get("/api/chat-logs/{token}")
async def chat_logs(token: str):
    with get_db() as conn:
        lab = conn.execute(
            "SELECT lab_name, chat_logging_enabled FROM labs WHERE token = ?", (token,)
        ).fetchone()
        if not lab:
            raise HTTPException(status_code=404, detail="Lab not found")
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
@app.post("/quiz/generate")
async def quiz_generate(req: GenerateQuizRequest):
    with get_db() as conn:
        row = conn.execute(
            "SELECT lab_content, api_key FROM labs WHERE token = ?", (req.token,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    if not row["lab_content"] or not row["lab_content"].strip():
        raise HTTPException(status_code=400, detail="No document text available for this lab")
    if not (3 <= req.n_questions <= 10):
        raise HTTPException(status_code=400, detail="n_questions must be between 3 and 10")

    try:
        questions = await generate_quiz(row["api_key"], row["lab_content"], req.n_questions)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Quiz generation failed — please try again. ({exc})") from exc
    except Exception as exc:
        message = str(exc)
        if "API_KEY_INVALID" in message or "API key not valid" in message:
            detail = (
                "Google API key is invalid or not enabled for Gemini. "
                "Create a new lab session with a valid key."
            )
        else:
            detail = f"Gemini quiz generation failed: {message}"
        raise HTTPException(status_code=502, detail=detail) from exc

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO quizzes (token, status, n_questions, created_at) VALUES (?, 'draft', ?, ?)",
            (req.token, req.n_questions, datetime.now(UTC).isoformat()),
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

    return {"quiz_id": quiz_id, "status": "draft", "questions": quiz_questions}


@app.get("/quiz/active/{token}")
async def quiz_active(token: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM quizzes WHERE token = ? AND status = 'published'", (token,)
        ).fetchone()
    if not row:
        return {"quiz_id": None, "questions": []}
    quiz_id = row["id"]
    with get_db() as conn:
        questions = _get_quiz_questions(conn, quiz_id, include_answer_data=False)
    return {"quiz_id": quiz_id, "questions": questions}


@app.get("/quiz/{quiz_id}")
async def quiz_get(quiz_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    with get_db() as conn:
        questions = _get_quiz_questions(conn, quiz_id, include_answer_data=True)
    return {"quiz_id": quiz_id, "token": row["token"], "status": row["status"], "questions": questions}


@app.put("/quiz/{quiz_id}")
async def quiz_update(quiz_id: int, req: UpdateQuizRequest):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
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


@app.post("/quiz/{quiz_id}/publish")
async def quiz_publish(quiz_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT token, status FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
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


@app.post("/quiz/{quiz_id}/close")
async def quiz_close(quiz_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if row["status"] != "published":
        raise HTTPException(status_code=400, detail="Only published quizzes can be closed")
    with get_db() as conn:
        conn.execute("UPDATE quizzes SET status = 'closed' WHERE id = ?", (quiz_id,))
        conn.commit()
    return {"ok": True}


@app.post("/quiz/{quiz_id}/submit")
async def quiz_submit(quiz_id: int, req: SubmitQuizRequest):
    with get_db() as conn:
        quiz_row = conn.execute(
            "SELECT status FROM quizzes WHERE id = ?", (quiz_id,)
        ).fetchone()
    if not quiz_row:
        raise HTTPException(status_code=404, detail="Quiz not found")
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


@app.get("/quiz/{quiz_id}/stats")
async def quiz_stats(quiz_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz not found")

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
