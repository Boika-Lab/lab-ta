# Spec: Quiz Completion Feedback

## Goal

Give students immediate visual feedback at the end of each quiz round so they
can quickly understand whether they passed, narrowly missed, or need more
review before retrying.

## Users

Students completing a prelab quiz before accessing the Lab TA chat.

## Current Behavior

The student quiz UI reports per-question correctness and shows a round summary
for missed questions. The quiz panel background stays the same for passing and
failing rounds, so there is no round-level visual distinction beyond the text in
the quiz card.

## Proposed Behavior

When a student completes a quiz round, the visible quiz panel background changes
based on the number of missed questions in that round:

- Green when the student misses zero questions.
- Yellow when the student misses exactly one question.
- Red when the student misses more than one question.

The feedback applies only to the quiz panel background. Quiz cards remain white
for readability. The feedback state is derived from the current browser quiz
phase and is not stored in localStorage. Starting or retrying a quiz resets the
panel to the default background before showing the next question.

## API/Data Changes

None.

## Acceptance Criteria

- Completing a round with zero missed questions shows the cleared quiz screen
  on a green quiz panel background.
- Completing a round with exactly one missed question shows the retry summary
  on a yellow quiz panel background.
- Completing a round with two or more missed questions shows the retry summary
  on a red quiz panel background.
- Starting the quiz, rendering active questions, and retrying missed questions
  reset the quiz panel background to the default color.
- Existing quiz route request and response contracts are unchanged.

## Test Plan

- Add a lightweight static contract test for `templates/student.html` verifying
  the feedback classes, helper, reset behavior, retry reset, and
  `failed.length` branching exist.
- Run `venv/bin/python -m pytest`.
- Manual browser checks:
  - Finish a round with all correct answers and verify the cleared screen uses
    a green quiz panel background.
  - Finish a round with exactly one wrong answer and verify the retry summary
    uses a yellow quiz panel background.
  - Finish a round with two or more wrong answers and verify the retry summary
    uses a red quiz panel background.
  - Click retry and verify the quiz panel returns to the default background
    before the next question.

## Open Questions

- None.
