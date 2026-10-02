# Spec: Study Question Selection

## Goal

When a student picks a study question by number, the TA must ask that question
and wait for an attempt, not answer it. Study mode exists for retrieval
practice; a question answered on selection teaches nothing.

## Users

Students using `\study` to prepare for quizzes and exams.

## Current Behavior

- Study rule 2 in `prompts/ta_system.md` says: when a student selects a number
  without an answer, ask that selected question.
- Rule 1 and rule 4 tell the TA to answer directly any question whose answer
  is stated outright in the lab content, and study rule 1 requires every menu
  question to be answerable from that content. Nothing says the factual-lookup
  exception stops at a question the TA posed itself.
- Observed during acceptance testing on 2026-09-30 with
  `gemini/gemini-3.5-flash-lite`: after `\study` produced a correct menu, a bare
  number returned the answer at once plus an offer of a similar question, on
  every attempt. The similar question was then asked properly.
- Approved for change by Joshua Schrier on 2026-10-02, since the wording
  narrows an exception inside the protected Socratic rules.

## Proposed Behavior

Prompt-only change to `prompts/ta_system.md`:

- Study rule 2: when the student sends a number alone, the TA repeats that
  question word for word, asks for the student's answer, and stops. It gives no
  answer, explanation, hint, or the fact the question asks for, even when the
  lab content states it outright. The factual-lookup exception in rule 1 does
  not apply to a question the TA posed until the student has attempted it.
  Assessment under study rule 3 begins only after an attempt.
- Rule 1 and rule 4 each gain one sentence saying the factual-lookup exception
  covers facts the student asks for and not a study question the TA posed,
  pointing to study rule 2.
- Everything else is unchanged: `number: answer` replies are assessed at once,
  a wrong attempt or "I don't know" gets a hint under study rule 3, ordinary
  factual questions outside study mode are still answered directly.

## API/Data Changes

None. No placeholders are added or removed, so `PROMPT_DEFINITIONS` is
unchanged.

## Acceptance Criteria

- The prompt imports cleanly through `prompt_loader` with the same
  placeholders.
- Study rule 2 contains the restate-and-wait instruction and the explicit
  statement that the rule 1 exception does not apply until the student has
  attempted the question.
- Rules 1 and 4 each reference study rule 2 for the carve-out.
- Live re-test (manual, cannot run in the automated suite): in a lab with a
  handout that states a fact such as a melting point, send `\study`, then a
  bare number, five times across different menu items. Every reply restates
  the question and asks for an answer with no answer, hint, or explanation.
  Then send `number: answer` twice: the reply assesses the answer. Run on
  `gemini/gemini-3.5-flash-lite`, the model in use.

## Test Plan

- Run `./venv/bin/python -m pytest`.
- Static test asserting the new sentences are present in the prompt file.
- Manual live re-test as above, recorded in the acceptance results.

## Verification

- Live re-test on 2026-10-02 on the summer workstation, `main` at 06f2686,
  model `gemini/gemini-3.5-flash-lite`: after `\study`, selecting a menu
  question about Aliquat 336 (a fact stated in the handout) by bare number
  made the TA restate the question and wait. No answer, hint, or explanation
  was given. Result: pass.

## Open Questions

- None.
