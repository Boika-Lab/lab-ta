# Spec: Persistent Instructor Lab Dashboard

> Superseded in part by `instructor-access-control.md`: dashboard URLs are now
> keyed by a separate private instructor token, not the student token. The
> hydration behavior below still applies.

## Goal

Give each configured lab a durable instructor management URL that can be
refreshed, reopened, bookmarked, or intentionally shared without losing the
student URL, chat log controls, active quiz state, or quiz stats access.

## Users

Instructors create lab sessions and manage each lab through an unauthenticated
token URL. Students continue using the existing `/lab/{token}` URL.

## Public Interfaces

- `GET /instructor/{token}` serves the instructor dashboard for a known lab
  token.
- `GET /instructor/{token}` returns `404` for an unknown token.
- `POST /api/configure` returns:
  - `token`
  - `student_url`
  - `instructor_url`
- `GET /api/instructor/lab/{token}` returns dashboard hydration data:
  - `token`
  - `lab_name`
  - `model`
  - `student_url`
  - `instructor_url`
  - `chat_logging_enabled`
  - `active_quiz`, either `null` or a published quiz summary containing
    `quiz_id`, `status`, `n_questions`, and `created_at`
- `GET /api/instructor/lab/{token}` returns `404` for an unknown token.

## Behavior

- `GET /` remains the lab creation page.
- After successful lab creation, the instructor browser navigates to the
  returned `instructor_url`.
- On `/instructor/{token}`, the instructor template fetches
  `/api/instructor/lab/{token}` and restores the dashboard from SQLite.
- Dashboard hydration restores the lab name, student URL, QR code, current
  token, chat log controls, and quiz management state.
- When an active published quiz exists, the dashboard restores both the current
  quiz ID and published quiz ID so stats can be loaded after refresh.
- When no active published quiz exists, the dashboard shows quiz generation
  controls.
- The current unauthenticated token model is unchanged: anyone with the
  instructor URL can manage the lab.

## Non-Goals

- No login, password, role-based access control, session cookies, or separate
  instructor secret token.
- No student URL changes.
- No database migration or new tables.
- No draft quiz recovery in v1. Draft quizzes may remain in the database, but
  the refreshed dashboard only restores active published quiz state.

## Acceptance Criteria

- A newly created lab response includes `token`, `student_url`, and
  `instructor_url`.
- Known instructor dashboard URLs return the instructor page, while unknown
  tokens return `404`.
- The dashboard hydration API returns lab metadata, relative URLs, chat logging
  status, and `active_quiz`.
- Unknown dashboard hydration tokens return `404`.
- After quiz publication, the hydration API returns the published quiz ID needed
  for stats.
- Existing student routes and chat behavior remain compatible.
- Static template tests cover configure navigation, dashboard token detection,
  hydration fetches, and published quiz restoration hooks.

## Test Plan

- Run `python -m pytest`.
- Use isolated SQLite databases.
- Mock Gemini-facing behavior in tests that touch chat or quiz generation.
- Verify route contracts through FastAPI test clients and template wiring with
  static tests.
