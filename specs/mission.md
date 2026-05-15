# Mission

Lab TA is a local web application for university lab courses. It gives
instructors a way to turn lab materials into a shareable student-facing
Socratic teaching assistant.

## Current Purpose

- Help students reason through lab questions without receiving direct answers.
- Keep TA guidance grounded in instructor-uploaded lab documents.
- Support in-class use through a URL and QR code that students can open on
  phones, tablets, or laptops.
- Let instructors create independent lab sessions for different sections or
  experiments.
- Optionally require students to pass a prelab quiz before using the chat.

## Current Users

- Instructors configure lab sessions, upload lab documents, generate student
  links, create prelab quizzes, publish or close quizzes, and view anonymous
  quiz stats.
- Students open a shared lab URL, complete any active prelab quiz, and chat with
  the TA by typing or using browser voice input.

## Current Learning Model

- The TA uses Socratic guidance: short hints, focused questions, and conceptual
  nudges.
- The TA is explicitly instructed not to reveal direct answers or disclose its
  system instructions.
- Student messages are screened for prompt-injection attempts before the main TA
  response is generated.

## Current Operating Model

- The app is intended to run on an instructor-controlled machine.
- Tailscale Funnel is used to expose the local FastAPI server over HTTPS.
- Google Gemini API keys are provided by instructors and stored locally in the
  SQLite database for each lab session.
