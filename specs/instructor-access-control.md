# Spec: Instructor Access Control

## Goal

Separate instructor access from student access so that a student who holds the
shared lab link cannot open the instructor dashboard, read the quiz answer key,
read chat logs, publish or close quizzes, or change feature availability. Also
protect the saved-labs index, which links to every lab's dashboard, behind a
server-side passphrase.

## Users

Instructors manage labs through a private, unguessable instructor URL that is
distinct from the student link. Students keep the existing `/lab/{token}` URL
and the student-facing routes. Whoever operates the server chooses the
passphrase for the saved-labs index.

## Current Behavior

- The instructor dashboard reuses the eight-character student token:
  `/lab/{token}` for students and `/instructor/{token}` for the dashboard.
  Editing the path is enough to reach the dashboard.
- `GET /quiz/{quiz_id}` returns every question with its correct answer and
  explanation and requires no token at all. The student quiz page fetches
  `/quiz/active/{token}`, whose response includes the numeric quiz ID, so the
  answer key is one request away. Quiz IDs are sequential, so other labs'
  answer keys can be enumerated.
- `PUT /quiz/{quiz_id}`, `POST /quiz/{quiz_id}/publish`,
  `POST /quiz/{quiz_id}/close`, and `GET /quiz/{quiz_id}/stats` require no
  token.
- `GET /api/chat-logs/{token}` and `PATCH /api/instructor/lab/{token}/features`
  use the student token.
- `GET /instructor/labs` and `GET /api/instructor/labs` are served at fixed
  paths with no protection and link to every dashboard.
- Tokens are generated with `random.choices`, which is not a cryptographically
  secure source.

## Proposed Behavior

### Tokens

- Each lab keeps its eight-character student `token`, now generated with the
  `secrets` module.
- Each lab gains an `instructor_token`: a URL-safe random string of at least 32
  characters generated with `secrets.token_urlsafe`. It is unique per lab,
  immutable, and never returned by any student-facing route.
- Existing databases are upgraded in place: the column is added and every
  existing lab receives a fresh instructor token. Instructors recover the new
  instructor URLs from the passphrase-protected saved-labs index.

### Instructor routes

Every instructor route is keyed by the instructor token. An unknown instructor
token returns `404`, the same status as a missing lab, so the response does not
reveal whether a token exists. A student token used on an instructor route is
simply an unknown instructor token and returns `404`.

- `GET /instructor/{instructor_token}` serves the dashboard page.
- `GET /api/instructor/lab/{instructor_token}` returns dashboard hydration
  data. The response includes both `token` (student) and `instructor_token`,
  plus `student_url` and `instructor_url`.
- `PATCH /api/instructor/lab/{instructor_token}/features` updates feature
  flags.
- `GET /api/instructor/lab/{instructor_token}/chat-logs` returns chat logs.
- `POST /api/instructor/lab/{instructor_token}/quiz/generate` creates a draft
  quiz. The request body no longer carries a lab token.
- `GET /api/instructor/lab/{instructor_token}/quiz/{quiz_id}` returns quiz
  details including answer data.
- `PUT /api/instructor/lab/{instructor_token}/quiz/{quiz_id}` edits a draft.
- `POST /api/instructor/lab/{instructor_token}/quiz/{quiz_id}/publish` and
  `.../close` change quiz status.
- `GET /api/instructor/lab/{instructor_token}/quiz/{quiz_id}/stats` returns
  anonymous stats.
- A quiz route whose `quiz_id` belongs to a different lab returns `404`.
- Feature gating is unchanged: quiz routes return `403` when quiz generation is
  disabled for the lab.

The following unauthenticated routes are removed: `POST /quiz/generate`,
`GET /quiz/{quiz_id}`, `PUT /quiz/{quiz_id}`, `POST /quiz/{quiz_id}/publish`,
`POST /quiz/{quiz_id}/close`, `GET /quiz/{quiz_id}/stats`, and
`GET /api/chat-logs/{token}`.

### Student routes

Unchanged: `GET /lab/{token}`, `GET /api/lab/{token}`,
`POST /api/chat/{token}`, `GET /quiz/active/{token}`, and
`POST /quiz/{quiz_id}/submit`. None of them returns answer data, the instructor
token, or the instructor URL.

### Lab creation

`POST /api/configure` returns `token`, `instructor_token`, `student_url`, and
`instructor_url`. The instructor browser navigates to `instructor_url` as
before. The dashboard shows the instructor URL with a notice that it is a
private management link that must not be shared with students.

### Saved-labs index

- The server operator sets the `LAB_TA_ADMIN_PASSPHRASE` environment variable.
- `GET /instructor/labs` always serves the page. The page asks for the
  passphrase, keeps it in `sessionStorage` for the browser session, and sends
  it in the `X-Lab-TA-Passphrase` header.
- `GET /api/instructor/labs` returns `403` when the environment variable is
  unset or blank, `401` when the header is missing or does not match, and the
  lab rows otherwise. Comparison uses `secrets.compare_digest`.
- Rows include `instructor_url` built from the instructor token. They still
  exclude API keys and lab content.

## API/Data Changes

- `labs` gains `instructor_token TEXT` with a unique index. `init_db()` adds
  the column to existing tables and backfills blank values.
- `POST /api/configure` response gains `instructor_token`.
- `GET /api/instructor/lab/{instructor_token}` response gains
  `instructor_token`.
- Route changes as listed above. `GenerateQuizRequest` drops `token`.
- New environment variable `LAB_TA_ADMIN_PASSPHRASE`.
- New request header `X-Lab-TA-Passphrase` on `GET /api/instructor/labs`.

## Acceptance Criteria

- Lab creation returns an instructor token of at least 32 characters that
  differs from the student token, and `instructor_url` uses it.
- The student token returns `404` on the dashboard page, hydration, chat-log,
  feature, and every quiz management route.
- The removed routes no longer exist, and no route reachable with only a
  student token or a quiz ID returns `correct` or `explanation` fields except
  the explanation for a wrong answer in the submit response.
- Quiz management with the wrong lab's instructor token returns `404`.
- Existing quiz lifecycle behavior (draft edit, single published quiz, close,
  stats, feature gating) works unchanged through the instructor-token routes.
- `init_db()` upgrades a legacy `labs` table by adding `instructor_token` and
  assigning a distinct token to every existing row.
- `GET /api/instructor/labs` returns `403` without the environment variable,
  `401` with a wrong or missing header, and rows with instructor URLs with the
  right header.
- Student routes and templates are unchanged apart from tests.
- Instructor and saved-labs templates call the new routes and send the
  passphrase header.
- README, `specs/current-behavior.md`, `specs/tech-stack.md`, and
  `specs/feature-roadmap.md` describe the new model.

## Test Plan

- Run `./venv/bin/python -m pytest`.
- Update the contract tests to drive instructor routes with the instructor
  token, and add the negative cases above.
- Add a migration test for the backfilled instructor tokens.
- Add passphrase tests using `monkeypatch.setenv` and `monkeypatch.delenv`.
- Add static template tests for the dashboard's instructor-token API calls,
  the private-link notice, and the saved-labs passphrase form and header.
- Manual check: create a lab, confirm the dashboard opens from the returned
  URL, confirm `/instructor/{student_token}` is `404`, and confirm the index
  prompts for the passphrase.

## Open Questions

- None. The design matches the manuscript's Limitations section: a separate,
  unguessable per-lab instructor URL and a passphrase-protected saved-labs
  index. Revoking a leaked instructor URL still requires recreating the lab.
