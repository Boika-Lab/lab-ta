"""Provider-neutral quiz generation through LiteLLM."""

from __future__ import annotations

import json

from llm_client import complete
from prompt_loader import PROMPTS


async def generate_quiz(
    api_key: str | None,
    api_base: str | None,
    model: str,
    document_text: str,
    n_questions: int,
    education_level: str,
    difficulty: str,
    language: str,
    custom_instructions: str,
) -> list[dict]:
    prompt = PROMPTS["quiz_generation"].render(
        n_questions=n_questions,
        document_text=document_text,
        education_level=education_level,
        difficulty=difficulty,
        quiz_language=language,
        quiz_custom_instructions=(
            custom_instructions
            if custom_instructions
            else "(No additional instructor instructions.)"
        ),
    )

    raw = await complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        api_base=api_base,
        temperature=0.7,
    )
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        raw = "\n".join(lines[1:end])

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM provider returned malformed JSON: {exc}") from exc

    if not isinstance(questions, list):
        raise ValueError("LLM provider response is not a JSON array")

    for i, q in enumerate(questions):
        missing = {"question", "choices", "correct", "explanation"} - set(q)
        if missing:
            raise ValueError(f"Question {i} missing fields: {missing}")
        if not isinstance(q["choices"], dict) or set(q["choices"]) != {"A", "B", "C", "D"}:
            raise ValueError(f"Question {i} has invalid choices structure")
        if q["correct"] not in {"A", "B", "C", "D"}:
            raise ValueError(f"Question {i} invalid correct answer: {q['correct']!r}")

    return questions
