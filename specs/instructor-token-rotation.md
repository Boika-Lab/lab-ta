# Spec: Instructor Token Rotation

## Goal

Let an instructor invalidate a leaked or over-shared instructor URL without
recreating the lab, so the student link, published quiz, quiz statistics, and
chat logs are preserved.

## Users

Instructors who suspect their dashboard URL was seen by a student, left in a
shared browser, projected on screen, or pasted into the wrong place.

## Current Behavior

- Each lab has one immutable instructor token, assigned at creation or by
  migration (see `instructor-access-control.md`).
- The only way to revoke an instructor URL is to create a new lab, which
  changes the student link and splits quiz data and chat logs across two labs.
  The old lab stays reachable through the leaked URL.

## Proposed Behavior

- `POST /api/instructor/lab/{instructor_token}/rotate` generates a fresh
  instructor token for the lab, stores it, and returns the student token, the
  new instructor token, and the new relative instructor URL.
- The previous instructor token stops working immediately: every instructor
  route returns `404` for it, exactly as for an unknown token.
- The student token, student URL, lab settings, quizzes, statistics, and chat
  logs are unchanged.
- The new token is generated the same way as at creation (`secrets`,
  at least 32 URL-safe characters) and is unique across labs.
- Unknown or student tokens on the rotate route return `404`.
- The dashboard's Private Instructor Link panel gains a "Rotate Instructor
  Link" button. It asks for confirmation, calls the route, then navigates the
  browser to the new instructor URL so the address bar and any new bookmark
  show the current link.
- The saved-labs index reflects the new instructor URL because it reads the
  stored token on every load.

## API/Data Changes

- New route `POST /api/instructor/lab/{instructor_token}/rotate`. Response:
  `{"token": ..., "instructor_token": ..., "instructor_url": ...}`.
- No schema change; `labs.instructor_token` is updated in place.

## Acceptance Criteria

- Rotation returns a new instructor token that differs from the old one and
  meets the length and alphabet rules.
- After rotation, the old token returns `404` on the dashboard page, hydration,
  chat logs, quiz routes, and the rotate route itself.
- After rotation, the new token works on the same routes and sees the same lab
  data, including a previously published quiz.
- The student token and student routes are unaffected.
- A student token cannot rotate: `404`.
- The dashboard template has the rotate control wired to the route and
  navigates to the returned instructor URL.

## Test Plan

- Run `./venv/bin/python -m pytest`.
- Route tests for the criteria above.
- Static template test for the rotate button, confirmation, fetch, and
  navigation.
- Manual check: rotate from the dashboard and confirm the old URL is `404`.

## Open Questions

- None.
