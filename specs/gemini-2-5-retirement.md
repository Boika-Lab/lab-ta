# Spec: Gemini 2.5 Retirement

## Goal

Stop depending on the Gemini 2.5 models, which Google has withdrawn from new
projects, so that a fresh installation can create a lab with the default
settings and so that existing labs do not lose their screening layer silently
when the models are shut down.

## Users

New instructors installing LabTA with a new Google project. Existing
instructors whose labs store a 2.5 identifier. Students, indirectly, because
screening protects the Socratic rules.

## Current Behavior

- `SCREENING_MODEL` defaults to `gemini/gemini-2.5-flash-lite`. Lab creation
  validates every configured model with a live call, so a project that cannot
  use 2.5 fails with "LLM configuration validation failed" on the defaults.
- Labs created before 2026-08-21 store `gemini/gemini-2.5-flash` for chat and
  quiz; all labs created before this change store `gemini/gemini-2.5-flash-lite`
  for screening. Stored identifiers are immutable.
- `screen_message` swallows every provider error and lets the message through
  without logging. A retired screening model would therefore disable
  prompt-injection screening with no visible sign.
- Google's position as of 2026-10-02: the Gemini API deprecations page lists
  `gemini-2.5-flash` and `gemini-2.5-flash-lite` as "not deprecated" with "no
  shutdown date announced", but access is "limited to users who have actively
  used them in the past"; new projects are told to use 3.5 Flash-Lite or 3.8
  Flash. Developers reported "no longer available" errors for both models on
  new projects from 2026-07-09. Vertex AI lists 2026-10-20 as the retirement
  date for 2.5 Flash-Lite.

## Proposed Behavior

- All three defaults for new labs are `gemini/gemini-3.5-flash-lite`:
  `CHAT_MODEL`, `QUIZ_MODEL`, and `SCREENING_MODEL`.
- `llm_config.RETIRED_MODEL_REPLACEMENTS` maps each retired identifier to its
  replacement: `gemini/gemini-2.5-flash` to `CHAT_MODEL` and
  `gemini/gemini-2.5-flash-lite` to `SCREENING_MODEL`. Because the map points
  at the constants, changing a default later also changes where retired rows
  are sent.
- `init_db()` rewrites those identifiers in the `model`, `screening_model`,
  and `quiz_model` columns of every existing lab after the existing
  `gemini/` prefix migration, and logs how many rows changed. This is a
  deliberate, narrow exception to the rule that stored models are immutable:
  it applies only to identifiers Google has withdrawn, and other identifiers
  (other Gemini versions, Ollama, any custom model) are untouched.
- `screen_message` logs a warning naming the lab token, the model, and the
  error whenever the screening call fails, and still lets the message through
  so a provider outage does not interrupt students.

## Decision Record

`gemini/gemini-3.5-flash` was considered for chat and quiz generation. It is
stable with no shutdown date, but Google's models page now calls it "our
legacy Flash model", the deprecations page names `gemini-3.5-flash-lite` as
its recommended replacement, and it costs $1.50 in / $9.00 out per million
tokens against $0.30 / $2.50 for Flash-Lite. Every TA turn resends the full
handout, so that is roughly five times the chat cost for a model Google is
steering away from. Flash-Lite is also the model the study-mode fix was
re-tested on. The choice is one constant; flipping `CHAT_MODEL` and
`QUIZ_MODEL` to `gemini/gemini-3.5-flash` would carry the migration with it.

| Model | Input / M tokens | Output / M tokens | Google status (2026-10-02) |
| --- | --- | --- | --- |
| `gemini/gemini-3.5-flash-lite` | $0.30 | $2.50 | Stable, recommended |
| `gemini/gemini-3.5-flash` | $1.50 | $9.00 | Stable, "legacy", replacement 3.5 Flash-Lite |
| `gemini/gemini-3.1-flash-lite` | $0.25 | $1.50 | Shutdown 2027-05-07 |
| `gemini/gemini-2.5-flash-lite` | $0.10 | $0.40 | New projects refused |

## API/Data Changes

- `llm_config.py`: `SCREENING_MODEL` changes; new `RETIRED_MODEL_REPLACEMENTS`.
- `init_db()`: new in-place update of three `labs` columns.
- `screen_message`: failure path logs a warning. No route or schema changes.

## Acceptance Criteria

- The three defaults are `gemini/gemini-3.5-flash-lite`, and the `labs` column
  defaults still come from `llm_config`.
- A legacy database row with bare `gemini-2.5-flash` ends up as
  `gemini/gemini-3.5-flash-lite` after one startup.
- Rows with `gemini/gemini-2.5-flash` or `gemini/gemini-2.5-flash-lite` in any
  of the three columns are rewritten to the replacements; rows with any other
  identifier are unchanged; a second startup changes nothing.
- A screening call that raises logs a warning containing the token and model
  and returns PASS.
- README, `specs/current-behavior.md`, and `specs/multi-provider-llm-configuration.md`
  state the new defaults, the migration, and the warning; the earlier defaults
  spec carries a supersession note.

## Test Plan

- Run `./venv/bin/python -m pytest`.
- Update the defaults test and the legacy migration test; add a migration test
  covering all three columns, untouched identifiers, and idempotence; add a
  screening-failure logging test using `caplog`.
- Manual: on the summer workstation after `git pull` and a service restart,
  confirm the log reports the number of rows migrated, open a summer lab's
  dashboard and confirm Feature Availability shows 3.5 Flash-Lite for all three
  roles, then rerun acceptance plan Parts 4 and 6 against a newly created lab.

## Sources

- [Gemini API deprecations](https://ai.google.dev/gemini-api/docs/deprecations)
- [Gemini API models](https://ai.google.dev/gemini-api/docs/models)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Developer forum: 2.5 Flash and Flash-Lite returning 404 since July 9](https://discuss.ai.google.dev/t/gemini-2-5-flash-and-gemini-2-5-flash-lite-returning-404-no-longer-available-today-july-9-contradicts-oct-16-2026-shutdown-date/174267)
- [Developer forum: 2.5 Flash-Lite retirement date differs between APIs](https://discuss.google.dev/t/gemini-2-5-flash-lite-retirement-date-different-for-gemini-api-vs-vertex-ai/389197)

## Open Questions

- None.
