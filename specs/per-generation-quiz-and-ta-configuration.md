# Spec: Per-Generation Quiz and TA Configuration

## Goal

Let instructors configure language and custom instructions independently for
the Socratic TA and each generated quiz while preserving repository-controlled
prompt, safety, output, and Socratic rules.

## Behavior

- Lab creation accepts an immutable TA language and optional custom
  instructions. Language defaults to `English`.
- Each quiz generation requires an education level, difficulty, and nonblank
  language, and accepts optional custom instructions.
- Quiz settings are stored on the generated quiz and remain immutable while
  questions and answers remain editable through the draft editor.
- The dashboard displays TA settings read-only and displays quiz generation
  settings above draft and published quiz states.
- Legacy quizzes expose null generation metadata, rendered as
  `Unavailable for legacy quiz`.
- Browser `localStorage` remembers the last TA and quiz settings. Languages
  default to `English` on first use; education level and difficulty have no
  first-use default.

## Validation

- Education level is `high_school` or `university`.
- Difficulty is `easy`, `medium`, or `hard`.
- Languages are trimmed, nonblank, and at most 100 characters.
- Custom instructions are trimmed and at most 4,000 characters.

## Prompt Protection

- Quiz and TA prompts receive only their respective language and custom
  instruction values.
- Blank custom instructions mean no additional instructions.
- Protected prompts explicitly require the selected language.
- Custom instructions cannot override quiz JSON and answer-consistency rules,
  Socratic behavior, safety rules, lab-content boundaries, or prompt-disclosure
  protections.
- Rendered prompts are not persisted or returned by APIs.

## Database and API

- `labs` stores `ta_language` and `ta_custom_instructions`.
- `quizzes` stores `education_level`, `difficulty`, `language`, and
  `custom_instructions`.
- Existing databases are upgraded in place.
- `POST /api/configure`, `POST /quiz/generate`,
  `GET /api/instructor/lab/{token}`, and `GET /quiz/{quiz_id}` expose the
  corresponding configuration contracts.
- No settings-update route is provided.

## Test Plan

- Test in-place legacy schema upgrades and defaults.
- Test validation, trimming, persistence, immutable quiz snapshots, and
  replacement quizzes with different settings.
- Test independent TA and quiz prompt rendering with protected rules present.
- Test dashboard, draft, published, legacy-display, and `localStorage` hooks.
- Mock Gemini-facing calls and run `python -m pytest`.
