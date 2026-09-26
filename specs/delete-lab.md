# Spec: Delete Lab

## Goal

Let an instructor permanently remove a lab and everything stored for it, so
old sessions with API keys, uploaded lab text, quizzes, and chat logs do not
accumulate in the database and stay reachable forever.

## Users

Instructors cleaning up after a course, or removing a lab whose links were
shared too widely.

## Current Behavior

- Labs can only be created. Nothing removes a lab, its parsed document text,
  its API key, its quizzes, its quiz statistics, or its chat logs.
- The saved-labs index lists every lab ever created on the server.

## Proposed Behavior

- `DELETE /api/instructor/lab/{instructor_token}` permanently deletes the lab.
  The JSON body must carry `confirm_token` equal to the lab's eight-character
  student token; otherwise the route returns `400` and deletes nothing.
- Deletion removes, in one transaction, the `labs` row, all `chat_logs` rows
  for the token, all `quizzes` rows for the token, their `quiz_questions`,
  and those questions' `quiz_question_stats`.
- After deletion, every instructor and student API route for either token
  returns `404`, and the lab no longer appears in the saved-labs index.
- Unknown or student tokens on the delete route return `404`.
- The dashboard gains a Delete Lab control in a clearly separated danger area.
  It asks the instructor to type the student token, calls the route, and
  navigates to `/` on success.
- The saved-labs index gains a Delete button per row with the same typed-token
  confirmation. On success the row disappears. Index rows now include
  `instructor_token` so the page can address the delete route; the index is
  already passphrase-protected.
- There is no undo, archive, or soft delete.

## API/Data Changes

- New route `DELETE /api/instructor/lab/{instructor_token}` with JSON body
  `{"confirm_token": "<student token>"}`. Response `{"deleted": true,
  "token": "<student token>"}`.
- `GET /api/instructor/labs` rows gain `instructor_token`.
- No schema change.

## Acceptance Criteria

- Deleting with the correct confirmation removes the lab row and every
  dependent row, and returns the deleted student token.
- Deleting with a missing or wrong `confirm_token` returns `400` and leaves all
  rows in place.
- A student token or unknown token returns `404`.
- After deletion, the dashboard page, hydration, chat logs, quiz routes,
  `GET /api/lab/{token}`, `POST /api/chat/{token}`, and
  `GET /quiz/active/{token}` return `404`, and `POST /quiz/{quiz_id}/submit`
  for a deleted quiz returns `404`.
- Deleting one lab leaves other labs' quizzes, stats, and chat logs intact.
- The saved-labs API no longer lists the deleted lab and includes
  `instructor_token` for remaining labs.
- Dashboard and index templates carry the typed-token confirmation and call
  the route.

## Test Plan

- Run `./venv/bin/python -m pytest`.
- Route tests for the criteria above, including the cross-lab isolation case.
- Static template tests for both delete controls.
- Manual check: delete a lab from the index and confirm its student link
  returns a not-found error.

## Open Questions

- None.
