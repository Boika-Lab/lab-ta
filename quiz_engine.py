"""Gemini quiz generation for prelab quizzes."""

from __future__ import annotations

import json

from google import genai
from google.genai import types


_MODEL = "gemini-2.5-flash"

_QUIZ_PROMPT = """\
Generate exactly {n_questions} multiple-choice questions for a university chemistry lab prelab quiz.

Focus on: procedural steps, safety rules, key definitions, and equipment use.
Difficulty: moderate-easy. Not trick questions. Verify the student read the manual.

Lab manual:
{document_text}

Respond with ONLY a JSON array — no markdown fences, no preamble, no extra text:
[
  {{
    "question": "...",
    "choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct": "B",
    "explanation": "Why B is correct — guidance shown to the student on a wrong answer."
  }}
]
"""


async def generate_quiz(api_key: str, document_text: str, n_questions: int) -> list[dict]:
    client = genai.Client(api_key=api_key)
    prompt = _QUIZ_PROMPT.format(n_questions=n_questions, document_text=document_text)

    response = await client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        raw = "\n".join(lines[1:end])

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned malformed JSON: {exc}") from exc

    if not isinstance(questions, list):
        raise ValueError("Gemini response is not a JSON array")

    for i, q in enumerate(questions):
        missing = {"question", "choices", "correct", "explanation"} - set(q)
        if missing:
            raise ValueError(f"Question {i} missing fields: {missing}")
        if not isinstance(q["choices"], dict) or set(q["choices"]) != {"A", "B", "C", "D"}:
            raise ValueError(f"Question {i} has invalid choices structure")
        if q["correct"] not in {"A", "B", "C", "D"}:
            raise ValueError(f"Question {i} invalid correct answer: {q['correct']!r}")

    return questions
