# Spec: Gemini 3.5 Flash-Lite Defaults

> Superseded by `gemini-2-5-retirement.md` on 2026-10-02: screening now also
> defaults to `gemini/gemini-3.5-flash-lite`, and stored 2.5 identifiers are
> rewritten at startup. The reasoning below is kept for history.

## Goal

Move the default chat and quiz-generation models for new labs from
`gemini/gemini-2.5-flash` to `gemini/gemini-3.5-flash-lite`, and remove the
duplicated model strings that would otherwise leave the change half-applied.

## Current Behavior

`llm_config.py` defines three defaults for new labs: `CHAT_MODEL` and
`QUIZ_MODEL` set to `gemini/gemini-2.5-flash`, and `SCREENING_MODEL` set to
`gemini/gemini-2.5-flash-lite`.

The same two strings are also hardcoded as SQL column defaults in the `labs`
`CREATE TABLE` statement in `main.py`, while the corresponding `ALTER TABLE`
migration path interpolates the `llm_config` values. A change to `llm_config.py`
alone therefore leaves a newly created database defaulting to the old model and
a migrated database defaulting to the new one.

## Proposed Behavior

- `CHAT_MODEL` and `QUIZ_MODEL` are `gemini/gemini-3.5-flash-lite`.
- `SCREENING_MODEL` stays `gemini/gemini-2.5-flash-lite`, which remains the
  cheaper option for that role.
- The `labs` column defaults for `screening_model` and `quiz_model` are
  interpolated from `llm_config`, so the model identifiers exist in exactly one
  place.
- Existing labs are unaffected. Model identifiers are stored per lab and are
  immutable after creation, so this changes only what a newly created lab is
  given.

## Rationale

Google's guidance is that Gemini 3.5 Flash-Lite supersedes 2.5 Flash for this
class of workload, with better quality and higher throughput at the same price.
LiteLLM's model cost map confirms both identifiers carry the same rates:

| Model | Input / M tokens | Output / M tokens |
| --- | --- | --- |
| `gemini/gemini-2.5-flash` | $0.300 | $2.500 |
| `gemini/gemini-3.5-flash-lite` | $0.300 | $2.500 |
| `gemini/gemini-2.5-flash-lite` | $0.100 | $0.400 |

Screening stays on 2.5 Flash-Lite because it is a cheap classification call
where the price difference matters and the quality difference does not.

## Interfaces and Constraints

No API, route, schema, or prompt changes. The `labs` table definition changes
only in the literal default values of two columns, which are a fallback the
application does not rely on — every insert supplies explicit model values.

Model identifiers remain freeform LiteLLM strings, and every distinct model is
still validated before a lab is saved, so an invalid identifier surfaces at lab
creation rather than at first use.

## Acceptance Criteria

- `llm_config.CHAT_MODEL` and `llm_config.QUIZ_MODEL` are
  `gemini/gemini-3.5-flash-lite`; `llm_config.SCREENING_MODEL` is
  `gemini/gemini-2.5-flash-lite`.
- The `labs` table's `screening_model` and `quiz_model` column defaults match
  the corresponding `llm_config` values, with no independently hardcoded copy.
- A newly configured lab that does not specify models is stored with the new
  defaults.
- The legacy prefix migration continues to prepend `gemini/` to an existing
  unprefixed model rather than replacing it with the current default.

## Test Plan

- `test_default_model_identifiers` pins the three literal identifiers, so a typo
  or an unintended edit fails rather than passing silently through the constant.
- `test_labs_table_model_defaults_come_from_llm_config` reads the stored `labs`
  schema and asserts the column defaults match `llm_config`, guarding against
  the duplication returning.
- `test_init_db_upgrades_existing_labs_table_missing_chat_logging_column`
  asserts the migrated legacy model is `gemini/gemini-2.5-flash` — the legacy
  value with the prefix added — rather than comparing against the default, which
  previously matched only by coincidence.
- Existing configure and dashboard tests continue to assert through the
  `llm_config` constants and are unaffected by the values themselves.
