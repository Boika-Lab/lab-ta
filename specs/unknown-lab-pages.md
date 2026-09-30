# Spec: Unknown Lab Pages

## Goal

Make a dead link fail clearly. A student or instructor who opens a link for a
lab that was deleted, never existed, or whose token was mistyped should see a
plain "this link is not available" page, not a working-looking chat screen
that errors on the first message.

## Users

Students following an old bookmark or a QR code from a deleted lab.
Instructors opening a stale dashboard bookmark after rotation or deletion.

## Current Behavior

- `GET /lab/{token}` returns the student chat page with `200` without checking
  whether the lab exists.
- The page then calls `GET /api/lab/{token}`, which correctly returns `404`.
  The page swallows that error, falls back to the title "Lab TA", enables
  chat by default, and shows the welcome message and input box.
- The first question fails with the toast "Error: Lab not found". Quiz,
  chat, and lab-info APIs are already `404`, so no data is exposed, but the
  page is misleading.
- `GET /instructor/{instructor_token}` for an unknown token returns a bare
  JSON `404` body, which is unfriendly for someone following a bookmark.
- Found in review by Joshua Schrier on 2026-09-30.

## Proposed Behavior

- `GET /lab/{token}` checks that the lab exists. If it does not, the server
  returns a small static HTML page, `templates/lab_not_found.html`, with HTTP
  status `404`. The page says the link is not available, that the lab may
  have been removed or the link copied incorrectly, and that students should
  ask their instructor for the current link. It loads no external resources.
- `GET /instructor/{instructor_token}` for an unknown token returns the same
  page with status `404`. The page adds one line for instructors: current
  links can be recovered from the saved-labs index.
- The student page treats a `404` from `GET /api/lab/{token}` as "lab not
  available": it shows the unavailable message in place of the chat, hides
  the input bar and quiz panel, and does not initialize the quiz. This covers
  a lab deleted while a student already had the page open in a tab and then
  reloaded it.
- If a chat request or the active-quiz request returns `404` during a session
  (lab deleted while the page is open), the page switches to the same
  unavailable state instead of showing a toast and leaving the input active.
- All API routes keep their existing `404` JSON responses.

## API/Data Changes

- `GET /lab/{token}`: `404` with HTML for unknown tokens (was `200`).
- `GET /instructor/{instructor_token}`: `404` body is now HTML (was JSON).
- New template `templates/lab_not_found.html`. No database changes.

## Acceptance Criteria

- Unknown student token: `GET /lab/{token}` returns `404`, an HTML body
  containing the not-available message, and no chat input markup.
- Known student token: `GET /lab/{token}` still returns the chat page with
  `200`.
- Unknown instructor token: `GET /instructor/{instructor_token}` returns
  `404` with the same HTML page.
- After deleting a lab, both `GET /lab/{token}` and
  `GET /instructor/{instructor_token}` return `404`.
- The student template handles `404` from the lab-info, chat, and active-quiz
  requests by showing the unavailable state.
- `specs/current-behavior.md`, `specs/tech-stack.md`, and the README template
  listing mention the new page.

## Test Plan

- Run `./venv/bin/python -m pytest`.
- Route tests for the criteria above; extend the deletion test with both HTML
  routes.
- Static template test for the student page's `404` handling.
- Manual check: open a random `/lab/xxxxxxxx` link and a deleted lab's link in
  a browser.

## Open Questions

- None.
