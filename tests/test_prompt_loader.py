from __future__ import annotations

from pathlib import Path

import pytest

from prompt_loader import (
    PromptTemplateError,
    load_prompt_template,
    load_prompt_templates,
)


def write_prompt(path: Path, name: str, text: str) -> None:
    (path / name).write_text(text, encoding="utf-8")


def test_load_prompt_templates_and_render_without_touching_json_braces(tmp_path):
    write_prompt(tmp_path, "ta_system.md", "TA {{lab_name}}\n{{lab_content}}")
    write_prompt(tmp_path, "screening.md", "Message: {{message}}")
    write_prompt(
        tmp_path,
        "quiz_generation.md",
        'Generate {{n_questions}}\n{{document_text}}\n{"choices": {"A": "x"}}',
    )

    prompts = load_prompt_templates(tmp_path)

    rendered = prompts["quiz_generation"].render(
        n_questions=3,
        document_text="Lab text",
    )
    assert "Generate 3" in rendered
    assert "Lab text" in rendered
    assert '{"choices": {"A": "x"}}' in rendered


def test_missing_prompt_file_raises_clear_error(tmp_path):
    with pytest.raises(PromptTemplateError, match="missing"):
        load_prompt_template("missing", "missing.md", frozenset({"value"}), tmp_path)


def test_empty_prompt_file_raises_clear_error(tmp_path):
    write_prompt(tmp_path, "empty.md", "  \n")

    with pytest.raises(PromptTemplateError, match="empty"):
        load_prompt_template("empty", "empty.md", frozenset({"value"}), tmp_path)


def test_missing_required_placeholder_raises_clear_error(tmp_path):
    write_prompt(tmp_path, "prompt.md", "No placeholder here")

    with pytest.raises(PromptTemplateError, match="missing placeholders"):
        load_prompt_template("prompt", "prompt.md", frozenset({"value"}), tmp_path)


def test_unknown_placeholder_raises_clear_error(tmp_path):
    write_prompt(tmp_path, "prompt.md", "{{value}} {{typo}}")

    with pytest.raises(PromptTemplateError, match="unknown placeholders"):
        load_prompt_template("prompt", "prompt.md", frozenset({"value"}), tmp_path)


def test_render_requires_values_for_all_placeholders(tmp_path):
    write_prompt(tmp_path, "prompt.md", "{{value}}")
    template = load_prompt_template(
        "prompt",
        "prompt.md",
        frozenset({"value"}),
        tmp_path,
    )

    with pytest.raises(PromptTemplateError, match="missing render values"):
        template.render()
