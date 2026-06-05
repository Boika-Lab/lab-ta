Generate exactly {{n_questions}} multiple-choice questions for a university chemistry lab prelab quiz.

Focus on: procedural steps, safety rules, key definitions, and equipment use.
Difficulty: moderate-easy. Not trick questions. Verify the student read the manual.

Before returning JSON, verify every question:
- The "correct" value must be the A/B/C/D label for the answer choice that is
  actually correct.
- The explanation must support that same labeled answer choice.
- If the explanation says another choice is correct, fix the "correct" label
  before returning.

Lab manual:
{{document_text}}

Respond with ONLY a JSON array — no markdown fences, no preamble, no extra text:
[
  {
    "question": "...",
    "choices": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct": "B",
    "explanation": "Why B is correct — guidance shown to the student on a wrong answer."
  }
]
