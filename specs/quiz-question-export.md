# Spec: Quiz Question Export

## Goal

Let instructors copy generated prelab quiz questions into another tool or
document without manually selecting fields from the quiz editor.

## Users

Instructors who generate prelab quizzes and need copy/pasteable quiz text for
review, reuse, or record keeping.

## Current Behavior

Generated quiz questions are visible in the instructor draft editor and can be
published for students. The dashboard does not provide a consolidated text
export of the questions or answer key.

## Proposed Behavior

The instructor quiz panel includes an Export Quiz control after a draft quiz is
generated and when a published quiz is restored on the dashboard.

Activating Export Quiz shows a read-only export panel with two text areas:

- Student version: quiz title, numbered questions, and choices A-D.
- Answer key version: quiz title, numbered questions, and the correct answer as
  the answer label plus answer text, such as `B. <choice B>`.

Each version has its own Copy button. Draft exports reflect the current editable
fields in the browser, including instructor edits made before publishing.
Published exports fetch the existing instructor quiz detail route so export
continues to work after refreshing `/instructor/{token}`.

Explanations are not included in either export version.

## API/Data Changes

No database changes are required.

The existing `GET /quiz/{quiz_id}` instructor route continues to provide
published quiz data with answer fields for dashboard export after refresh.

## Acceptance Criteria

- Export Quiz is available after a draft quiz is generated.
- Export Quiz is available for an active published quiz restored on
  `/instructor/{token}`.
- The student export includes choices A-D and does not include correct answers
  or explanations.
- The answer-key export includes only the correct answer label and answer text
  for each question.
- Both export text areas are read-only and have independent Copy buttons.
- Draft export reflects current editor values.

## Test Plan

- Add static template tests for export controls, read-only export text areas,
  copy handlers, draft export collection, answer-key formatting, and published
  quiz fetch behavior.
- Run `python -m pytest`.

## Open Questions

- None.
