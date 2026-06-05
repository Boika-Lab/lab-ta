# Spec: Lab Feature Availability

## Goal

Let instructors independently enable or disable prelab quiz functionality and
Socratic TA chat for each lab session while preserving the existing student URL
and instructor dashboard workflow.

## Users

Instructors configure which online activities are available for a lab. Students
use the same lab URL and see only the enabled activities.

## Current Behavior

Every lab has Socratic TA chat enabled. Quiz functionality is always available
to instructors, and students must pass any active published quiz before chatting.

## Proposed Behavior

Each lab stores two feature flags:

- `quiz_enabled`
- `ta_enabled`

Both default to enabled for new and legacy labs. The instructor setup form shows
a visible Lab Features area with separate Quiz Generation and Socratic TA
groups. Each group begins with its checked-by-default enable control. The
Socratic TA group contains the existing anonymous chat log option.

The instructor dashboard shows matching Feature Availability controls so the
instructor can edit both flags later. Disabled quiz data is preserved in SQLite
and becomes available again when quiz generation is re-enabled.

Student behavior:

- Quiz enabled and TA enabled: existing quiz gate, then chat.
- Quiz enabled and TA disabled: quiz-only flow; after completion, no chat is
  shown.
- Quiz disabled and TA enabled: chat is available immediately.
- Quiz disabled and TA disabled: the page shows the lab name and a no-activities
  message.

## API/Data Changes

- `labs` gains `quiz_enabled INTEGER NOT NULL DEFAULT 1`.
- `labs` gains `ta_enabled INTEGER NOT NULL DEFAULT 1`.
- `POST /api/configure` accepts optional `quiz_enabled` and `ta_enabled` form
  fields.
- `GET /api/lab/{token}`, `GET /api/instructor/lab/{token}`, and
  `GET /api/instructor/labs` return both feature flags.
- `PATCH /api/instructor/lab/{token}/features` accepts `quiz_enabled` and
  `ta_enabled`, updates the lab, and returns the updated flags.
- Disabled chat calls return `403` with a Socratic TA disabled message.
- Disabled quiz operations return `403` with a quiz disabled message.

## Acceptance Criteria

- New and legacy labs default to both features enabled.
- Instructors can set both flags during lab creation and edit them later from
  the instructor dashboard.
- Quiz-disabled labs preserve existing quiz rows and stats.
- Disabled feature APIs return `403` and do not call Gemini-facing functions.
- Student UI handles all four feature combinations.
- Documentation describes the grouped controls, default-on behavior, later
  edits, route gating, and student states.

## Test Plan

- Run `python -m pytest`.
- Use isolated SQLite databases.
- Add route tests for migration defaults, creation flags, feature PATCH,
  disabled chat, disabled quiz operations, and preservation after re-enable.
- Add static template tests for grouped instructor controls and student feature
  branching.

## Open Questions

- None.
