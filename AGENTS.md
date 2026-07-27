# AGENTS.md

Conventions for any AI coding agent working in this repository. Read this before
making changes. It records the things that are easy to get wrong here, not the
things you can read off the codebase.

## Specs come first

This project uses spec-driven development. `specs/README.md` defines the
workflow; follow it rather than reinventing one.

The project constitution is `specs/mission.md`, `specs/tech-stack.md`, and
`specs/feature-roadmap.md`. Read the mission before proposing scope changes.

A change to any prompt, API, database schema, workflow, or user-visible behavior
requires a spec. Typo fixes, comments, and non-behavioral cleanup do not.

When you add or change behavior:

1. Add or update the spec in `specs/`.
2. Update `specs/current-behavior.md` — this is the single description of how
   the app actually behaves, and it goes stale fastest.
3. Add the new spec to the `## Current Specs` list in `specs/README.md`.
4. Update or add tests for the acceptance criteria.
5. Run the tests (see below) before opening a PR.

Steps 2 and 3 are the ones agents skip. A spec that exists but is unlisted and
unreflected in `current-behavior.md` is drift, not documentation.

## Prompts

Prompt templates live in `prompts/` and are the product. Changing one is a
behavior change and needs a spec.

**`prompt_loader.py` validates prompts strictly at import time.** Placeholders in
each `.md` file must match `PROMPT_DEFINITIONS` exactly — a missing placeholder
*or an unknown one* raises `PromptTemplateError` when the module is imported,
which breaks app startup and every test. If you add a `{{placeholder}}` to a
prompt, add it to `PROMPT_DEFINITIONS` in the same commit, and vice versa.

Verify a prompt edit by importing the loader, not by eyeballing the Markdown:

```bash
./venv/bin/python -c "import prompt_loader; print(sorted(prompt_loader.PROMPTS))"
```

### Editing prompt files

- **One sentence per line.** Prompt files are not hard-wrapped to a column
  limit. Start each sentence on its own line and let the editor soft-wrap it.
  Git diffs line by line, so this keeps an edit to one sentence from touching
  its neighbours, and keeps the changed line short enough to read in a diff.
- **Do not reflow lines you are not changing.** Rewrapping a whole file turns a
  three-line semantic change into an unreviewable diff.
- Keep one numbered rule per list item, and keep the numbering contiguous.
- When you renumber rules, check for cross-references — several rules refer to
  each other by number ("the sequence in rule 4", "permitted by rule 1"), and
  those break silently.
- After any edit, re-read the neighbouring rules for contradictions. Rules that
  say "never" often need amending when a new exception is introduced elsewhere.

### Protected TA rules

`prompts/ta_system.md` contains protected rule categories: Socratic method,
safety and bench-action deferral, the never-calculate constraint, lab-content
grounding, and prompt-disclosure resistance. Instructor custom instructions are
explicitly subordinate to them.

Do not weaken, narrow, or add exceptions to these categories on your own
initiative, even when it would make the TA more helpful. Propose the change in
the PR description and let a human decide. Pedagogical intent here is a teaching
decision, not an implementation detail.

## Tests

```bash
./venv/bin/python -m pytest
```

Use the project venv. System Python does not have the dependencies installed and
will fail at collection with import errors that look like broken code.

Tests must never call live LLM providers or require a real API key. Mock the
LiteLLM-facing functions and assert app behavior through public routes.

## Git and PRs

- Branch for every change; never commit directly to `main`.
- Keep diffs small enough to review in one sitting. Prefer several focused PRs
  over one large one.
- Reference the issue in the PR body with `Closes #N` so it closes on merge.
- Merge commits, not squash — this repo's history uses them. Delete the branch
  after merging.
- Say so explicitly in the PR description when a prompt was substantially
  written or rewritten by an AI agent, so reviewers know to read it closely
  rather than skim the diff.

## Do not commit

`lab_ta.db` and its sidecars, `venv/`, `__pycache__/`, `.idea/`. These are
already in `.gitignore`; do not add generated databases or environment
directories back.
