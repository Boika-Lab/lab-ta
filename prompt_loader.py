"""Load and render LLM prompt templates from Markdown files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"

PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


class PromptTemplateError(RuntimeError):
    """Raised when a prompt template is missing or malformed."""


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    text: str
    required_placeholders: frozenset[str]

    def render(self, **values: object) -> str:
        missing = self.required_placeholders - set(values)
        if missing:
            raise PromptTemplateError(
                f"Prompt {self.name!r} missing render values: {sorted(missing)}"
            )

        def replace(match: re.Match[str]) -> str:
            placeholder = match.group(1)
            return str(values[placeholder])

        return PLACEHOLDER_RE.sub(replace, self.text)


PROMPT_DEFINITIONS: dict[str, tuple[str, frozenset[str]]] = {
    "ta_system": ("ta_system.md", frozenset({"lab_name", "lab_content"})),
    "screening": ("screening.md", frozenset({"message"})),
    "quiz_generation": (
        "quiz_generation.md",
        frozenset({"n_questions", "document_text"}),
    ),
}


def load_prompt_template(
    name: str,
    filename: str,
    required_placeholders: frozenset[str],
    prompts_dir: Path = PROMPTS_DIR,
) -> PromptTemplate:
    path = prompts_dir / filename
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptTemplateError(f"Required prompt file is missing: {path}") from exc

    if not text.strip():
        raise PromptTemplateError(f"Required prompt file is empty: {path}")

    found_placeholders = frozenset(PLACEHOLDER_RE.findall(text))
    missing = required_placeholders - found_placeholders
    if missing:
        raise PromptTemplateError(
            f"Prompt {name!r} is missing placeholders: {sorted(missing)}"
        )

    unknown = found_placeholders - required_placeholders
    if unknown:
        raise PromptTemplateError(
            f"Prompt {name!r} has unknown placeholders: {sorted(unknown)}"
        )

    return PromptTemplate(
        name=name,
        text=text,
        required_placeholders=required_placeholders,
    )


def load_prompt_templates(
    prompts_dir: Path = PROMPTS_DIR,
) -> dict[str, PromptTemplate]:
    return {
        name: load_prompt_template(name, filename, placeholders, prompts_dir)
        for name, (filename, placeholders) in PROMPT_DEFINITIONS.items()
    }


PROMPTS = load_prompt_templates()
