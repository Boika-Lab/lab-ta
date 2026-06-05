# Spec: Quiz Answer Consistency

## Goal

Reduce generated prelab quizzes where the stored correct-answer label disagrees
with the choice text or explanation shown to instructors and students.

## Users

Instructors reviewing generated quizzes and students answering published prelab
quizzes.

## Current Behavior

Quiz generation validates that Gemini returns JSON with choices A-D, a correct
label, and an explanation. It does not prevent structurally valid responses
where the correct label is inconsistent with the answer described by the
explanation.

## Proposed Behavior

Quiz generation uses an explicit prompt instruction requiring the model to
verify that each `correct` label points to the answer choice supported by the
explanation.

## API/Data Changes

None.

## Acceptance Criteria

- The quiz generation prompt tells Gemini to verify every correct-answer label
  against the corresponding answer text and explanation before returning JSON.
- Existing quiz generation model settings are unchanged.
- Existing route and database contracts are unchanged.

## Test Plan

- Add automated tests for the existing quiz generation temperature and the
  answer-label consistency instruction in the externalized prompt.
- Run `python -m pytest`.

## Open Questions

- None.
