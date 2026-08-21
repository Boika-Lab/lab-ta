# Lab TA Specification Workflow

This project uses a pragmatic specification-driven development workflow.

Specs are the source of truth for meaningful behavior changes. Before changing
application behavior, update or add a spec that describes the goal, public
interfaces, acceptance criteria, and tests that prove the behavior works.

## Workflow

1. Write or update a spec in `specs/`.
2. Capture current behavior before changing brown-field code.
3. Add or update automated tests for the acceptance criteria.
4. Implement the smallest code change that satisfies the spec.
5. Run `python -m pytest` before handing off or merging.

Small typo fixes, comments, and non-behavioral cleanup do not need a dedicated
spec. Any API, database, prompt, workflow, or user-visible behavior change does.

## Current Specs

- `current-behavior.md` documents the inherited app behavior.
- `centralized-gemini-model-configuration.md` documents server-controlled
  Gemini model role configuration from the earlier Gemini-only implementation.
- `gemini-3-5-flash-lite-defaults.md` documents the default chat and quiz model
  identifiers for new labs and where they are defined.
- `instructor-lab-index.md` documents saved-lab lookup and recovery behavior.
- `lab-feature-availability.md` documents per-lab Quiz Generation and Socratic
  TA availability controls.
- `llm-prompt-externalization.md` documents the externalized prompt template
  behavior.
- `multi-provider-llm-configuration.md` documents per-lab LiteLLM models,
  credentials, validation, and local endpoint behavior.
- `persistent-instructor-lab-dashboard.md` documents durable unauthenticated
  instructor dashboard URLs and hydration behavior.
- `persistent-chat-logs.md` documents opt-in anonymous chat log persistence and
  export behavior.
- `per-generation-quiz-and-ta-configuration.md` documents immutable TA
  configuration and per-generation quiz settings.
- `quiz-answer-consistency.md` documents answer-label consistency prompt
  requirements for generated prelab quizzes.
- `quiz-completion-feedback.md` documents the green/yellow/red quiz panel
  background feedback shown at the end of each student quiz round.
- `quiz-generation-content-balance.md` documents prompt-only category balance
  and numerical-distractor requirements for generated prelab quizzes.
- `quiz-question-export.md` documents copy/pasteable instructor export behavior
  for generated prelab quiz questions and answer keys.
- `socratic-ta-study-and-factual-responses.md` documents prompt-only factual
  lookup, reaction-mechanism, and stateless study behavior.
- `template.md` is the starting point for future feature or change specs.

## Test Policy

Automated tests must not call live LLM providers or require a real API key.
Mock LiteLLM-facing functions and verify app behavior through public routes
where possible.
