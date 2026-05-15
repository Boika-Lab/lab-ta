# Spec: Optional Persistent Chat Logs

## Goal

Allow instructors to opt in to persistent, anonymous chat logging for a lab
session. Logging is disabled by default.

## Public Interfaces

- `POST /api/configure` accepts an optional `chat_logging_enabled` form field.
  Missing or unchecked means logging is disabled.
- `POST /api/chat/{token}` accepts an optional `session_id` in the JSON body.
  The student browser generates this identifier and stores it in `localStorage`
  per lab token.
- `GET /api/chat-logs/{token}` returns lab metadata and logged exchanges grouped
  by anonymous browser session.

## Database

- The `labs` table includes `chat_logging_enabled INTEGER NOT NULL DEFAULT 0`.
- Existing SQLite databases are upgraded by `init_db()` when the column is
  missing.
- The `chat_logs` table stores:
  - `id`
  - `token`
  - `session_id`
  - `exchange_index`
  - `question_at`
  - `question`
  - `response`
  - `blocked`
- Exchange order is tracked per `(token, session_id)` by incrementing
  `exchange_index`.

## Behavior

- Normal TA responses are logged only after a complete model response is
  generated.
- Blocked prompt-injection attempts are logged with the neutral refusal response
  and `blocked=true` when logging is enabled.
- Failed TA calls are not logged because no complete response exists.
- When logging is disabled, no rows are written to `chat_logs`.
- Chat log visibility follows the existing unauthenticated instructor model.

## JSON Export

`GET /api/chat-logs/{token}` returns:

```json
{
  "token": "...",
  "lab_name": "...",
  "chat_logging_enabled": true,
  "sessions": [
    {
      "session_id": "...",
      "exchanges": [
        {
          "id": 1,
          "exchange_index": 1,
          "question_at": "ISO-8601 UTC",
          "question": "...",
          "response": "...",
          "blocked": false
        }
      ]
    }
  ]
}
```

Unknown tokens return `404`.

## Acceptance Criteria

- Configure defaults to logging disabled.
- Configure with the checkbox checked stores logging enabled.
- `init_db()` upgrades an existing `labs` table missing the new column.
- Logging disabled produces no `chat_logs` rows.
- Logging enabled stores normal exchanges in order by anonymous session.
- Blocked messages are persisted with `blocked=true` and do not call TA
  generation.
- Failed TA calls are not logged.
- `GET /api/chat-logs/{token}` returns grouped, ordered sessions and `404` for
  unknown tokens.
- The instructor template includes the opt-in checkbox and JSON log controls.
- The student template creates/stores a per-token session ID and includes it in
  chat requests.

## Test Plan

- Run `python -m pytest`.
- Mock Gemini-facing screening and TA generation functions.
- Use isolated SQLite databases for route and schema tests.
