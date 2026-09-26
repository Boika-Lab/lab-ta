# Spec: Instructor Lab Index

> Superseded in part by `instructor-access-control.md`: the index API now
> requires the `LAB_TA_ADMIN_PASSPHRASE` passphrase, and dashboard links use
> the instructor token.

## Goal

Let instructors recover previous lab sessions from the local SQLite database
without remembering tokens or manually copying URLs.

## Public Interfaces

- `GET /instructor/labs` serves the saved-labs index page.
- `GET /api/instructor/labs` returns saved labs sorted newest first.
- Each API row includes `token`, `lab_name`, `student_url`, `instructor_url`,
  `chat_logging_enabled`, `created_at`, `quiz_count`, `has_quizzes`,
  `active_quiz_status`, and `chat_log_exchange_count`.
- API rows exclude sensitive fields such as `api_key` and `lab_content`.

## Behavior

- The instructor landing page links to `/instructor/labs`.
- The saved-labs page shows an empty state when no labs exist.
- Each saved-lab row shows lab name, token, created date, chat logging status,
  quiz count/status, and chat exchange count.
- Each row includes a clickable instructor dashboard link to
  `/instructor/{token}`.
- Each row includes a clickable student link to `/lab/{token}`.
- The current unauthenticated token model is unchanged: anyone who can open
  `/instructor/labs` can view local lab metadata and open dashboard or student
  links.

## Non-Goals

- No search, filtering, pagination, deletion, archiving, or editing.
- No authentication or access-control changes.
- No display of API keys or uploaded lab document content.

## Acceptance Criteria

- `GET /instructor/labs` returns saved-labs HTML and is not intercepted by
  `GET /instructor/{token}`.
- `GET /api/instructor/labs` returns an empty list for an empty database.
- Multiple labs are returned newest first.
- API rows include dashboard and student URLs, chat logging status, quiz count,
  active quiz status, and chat log exchange count.
- API rows do not expose `api_key` or `lab_content`.
- Static template tests cover the landing-page link, saved-labs API fetch, and
  clickable dashboard and student links.

## Test Plan

- Run `python -m pytest`.
- Use isolated SQLite databases.
- Verify route contracts through FastAPI test clients and template wiring with
  static tests.
