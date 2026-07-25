# Spec: Quiz Generation Content Balance

## Goal

Generate prelab quizzes that emphasize broad laboratory understanding instead
of overemphasizing safety questions or distractors distinguished only by small
numerical differences.

## Current Behavior

The quiz-generation prompt requests procedural, safety, definition, and
equipment questions but does not require a category balance or constrain
numerical distractors.

## Proposed Behavior

- Quiz questions belong to one mutually exclusive category: safety, key
  definition, or general procedure.
- A 3–7-question quiz has exactly one safety and one key-definition question.
  An 8–10-question quiz has exactly two of each. All remaining questions cover
  general procedure.
- Safety questions use only handout-stated PPE, hazards, waste, emergency, or
  safety-prohibition content. Key-definition questions use only handout-stated
  concepts and cannot count as safety questions.
- Procedure questions cover workflow, sequence, purpose, equipment use,
  observations, or decision points without redundant variants.
- Choices cannot differ solely by numerical values or small numerical
  variations. A handout-stated number is allowed only when essential to a
  procedure or safety boundary, and alternatives must be conceptually distinct.

## Interfaces and Constraints

This is a prompt-only change to `prompts/quiz_generation.md`. Existing JSON
output, answer-label consistency, language, difficulty, instructor custom
instructions, and document-grounding requirements remain in force. There are
no API, UI, database, code, test, or external-lookup changes.

## Acceptance Criteria

- The prompt states the exact category quotas for each supported question-count
  range and requires category exclusivity.
- The prompt restricts safety content to explicit handout material and requires
  remaining questions to cover general procedure.
- The prompt prohibits numeric-only and near-number distractors while allowing
  essential handout-stated values with conceptually distinct alternatives.
- The final prompt audit retains correct-answer label and explanation checks.

## Test Plan

No automated tests are added or modified for this prompt-and-documentation-only
change. Review the rendered prompt for the required category, distractor, JSON,
and answer-consistency rules.
