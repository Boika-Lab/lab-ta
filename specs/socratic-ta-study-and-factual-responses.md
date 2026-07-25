# Spec: Socratic TA Study and Factual Responses

## Goal

Improve the Socratic TA's usefulness for document-grounded factual questions
and self-directed study without weakening its calculation, safety, lab-content,
or prompt-disclosure protections.

## Current Behavior

The TA receives the complete uploaded lab content and browser-provided chat
history on every request. It has no persistent study-session state, score,
question bank, external lookup service, or retrieval system. Its behavior is
defined by the repository-controlled system prompt.

## Proposed Behavior

- The TA may directly state a fact or numerical datum only when it is explicitly
  present in the uploaded lab content. It identifies a document, section, or
  table only when that source is identifiable in the extracted text.
- When a requested fact is absent, the TA says it could not find it in the
  handout materials and recommends an external database such as ChemSpider or
  WolframAlpha; it does not supply an unsupported answer.
- The TA does not draw, complete, predict, or validate reaction mechanisms. It
  directs students to their manual and instructor, then may discuss only
  handout-supported high-level concepts.
- A literal `\study` starts a fresh, stateless menu of 5–10 handout-grounded
  questions. Students may select a number or provide `number: answer`.
- Study feedback explicitly affirms correct work, scaffolds partial or incorrect
  work without revealing a complete answer, and lets students choose additional
  practice on the same topic or another menu question. `\study off` ends study
  behavior; ordinary questions can interrupt it naturally.
- Study may assess calculation setup but never generates, solves, checks, or
  validates a numerical result. It may repeat values already stated in the
  handout and direct the student to the relevant table or section for
  independent practice.
- Study may test recall of stated procedure and safety requirements, but never
  authorizes, changes, or troubleshoots bench actions.

## Interfaces and Constraints

This is a prompt-only change to `prompts/ta_system.md`. There are no API, UI,
database, code, test, persistent-session, scoring, external-lookup, RAG, or
calculation-backend changes.

## Acceptance Criteria

- The prompt permits only document-grounded factual direct answers and preserves
  the prohibition on calculated results and unsupported information.
- The prompt contains the defined missing-fact, reaction-mechanism, and study
  behavior, while preserving prompt-disclosure, language, safety, and custom
  instruction protections.
- `\study` is explicitly exempted from the general instruction-override rule;
  no other user-requested mode is enabled.
- Documentation accurately describes the prompt-only and stateless limits.

## Test Plan

No automated tests are added or modified for this prompt-and-documentation-only
change. Review the rendered prompt for consistency with this specification and
the protected rules.
