# Spec: Local QR Code Generation

## Goal

Generate the student-link QR code on the Lab TA server instead of fetching it
from a third-party web service, so the student URL is never sent to an outside
party and the dashboard works without internet access to that service.

## Users

Instructors see the QR code on the dashboard after creating a lab and after
reopening the dashboard. Students scan it; nothing changes for them.

## Current Behavior

- The instructor template sets the QR image source to
  `https://api.qrserver.com/v1/create-qr-code/?data=<student URL>&size=200x200`.
- The full student URL, including the Tailscale hostname and the student
  token, is therefore sent to that service every time the dashboard renders.
- The QR code fails to load when the service or the instructor's connection to
  it is unavailable.

## Proposed Behavior

- The server renders the QR code as SVG with the pure-Python `segno` library.
- `GET /api/instructor/lab/{instructor_token}/qr.svg?student_url=<absolute URL>`
  returns `image/svg+xml`. The browser supplies the absolute student URL it
  displays, so the QR code always encodes exactly the link shown next to it,
  including the public Tailscale origin the server cannot reliably know.
- The route requires the instructor token and returns `404` for unknown or
  student tokens, like every other instructor route.
- The route validates `student_url`: it must be an `http` or `https` URL with
  no query or fragment whose path is exactly this lab's `/lab/{token}`.
  Anything else returns `400`. The server is therefore not a general-purpose
  QR generator for arbitrary content.
- The instructor template sets the QR image source to that route and no longer
  references any third-party service.
- QR parameters: error correction level M, two-module quiet zone, black on
  white, rendered at a size that fills the existing 200 pixel image box.

## API/Data Changes

- New route `GET /api/instructor/lab/{instructor_token}/qr.svg` with a
  required `student_url` query parameter.
- New runtime dependency `segno`.
- No database changes.

## Acceptance Criteria

- The route returns an SVG document with `image/svg+xml` content type for the
  lab's own student URL under any host.
- The route returns `404` for a student token or unknown instructor token.
- The route returns `400` when `student_url` is missing, uses another scheme,
  has a different path, has a query or fragment, or names another lab's token.
- The instructor template requests the QR image from the new route and
  contains no reference to `api.qrserver.com`.
- README, `specs/current-behavior.md`, `specs/tech-stack.md`, and
  `specs/feature-roadmap.md` no longer describe a third-party QR service.

## Test Plan

- Run `./venv/bin/python -m pytest`.
- Route tests for the success case and each rejection case above.
- Static template test for the new image source and the absence of the old
  service URL.
- Manual check: open a dashboard and scan the QR code with a phone.

## Open Questions

- None.
