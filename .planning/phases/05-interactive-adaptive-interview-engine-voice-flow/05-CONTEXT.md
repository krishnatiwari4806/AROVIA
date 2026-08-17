# Phase 05: Interactive Adaptive Interview Engine & Voice Flow - Context

**Gathered:** 2026-08-18  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 5 delivers the live, adaptive mock interview experience. It implements sequential question generation with Google Gemini prompt chaining, dynamic follow-up probing, browser-native Text-to-Speech (TTS) and Speech-to-Text (STT) audio flow, soft turn timers, and the full turn transition lifecycle from the initial question through session completion.

</domain>

<decisions>
## Implementation Decisions

### Adaptive Follow-Up State Machine
- **D-01 (Probing Limits):** Maximum 1 follow-up probe per core question. Session limits: max 3 follow-ups (9 total turns max) in Full mode; max 2 follow-ups (5 total turns max) in Quick mode.
- **D-02 (Trigger Criteria):** When a candidate submits an answer, Gemini analyzes technical depth: if the answer makes unsubstantiated claims, glosses over core mechanics, or warrants architecture drill-down (and follow-up budget remains), the next turn is generated as a follow-up linked to the parent turn (`is_follow_up=True`, `parent_turn_id=parent.id`). Otherwise, advances to the next core question.

### Question Sequencing & Context Progression
- **D-03 (Progressive Difficulty Arc):** Question generation follows a progressive difficulty curve:
  - Turn 1: Warm-up and architectural overview / resume project background.
  - Turns 2-4: Core technical competencies and implementation scenarios aligned with JD requirements.
  - Turns 5-6: Real-world edge cases, scalability trade-offs, failure recovery, or behavioral STAR scenarios.
- **D-04 (Multi-Context Fusion):** The prompt chain fuses: (1) Target Role & Seniority, (2) Interview Focus dimension, (3) Parsed Job Description requirements, (4) Candidate's Parsed Resume background, and (5) Prior turn transcript history (avoiding repetition).

### Speech & Audio Interaction UX (₹0 Zero Cost)
- **D-05 (Browser-Native Web Speech API):** 100% browser-native `window.speechSynthesis` (TTS) and `window.webkitSpeechRecognition` / `SpeechRecognition` (STT). Zero paid speech cloud APIs.
- **D-06 (Voice & Editing Workflow):**
  - Question audio auto-plays on turn load with explicit "Replay Audio" and "Stop Speaking / Mute" controls.
  - Microphone button streams real-time speech dictation into an editable textarea.
  - Candidate can freely edit transcribed text, fix speech errors, or type answers directly.
  - Candidate explicitly clicks "Submit Answer" to confirm submission.

### Turn Timers & Pacing Controls
- **D-07 (Soft Pacing Timer):** Suggested response budget: 120s (`Technical Core` / `Behavioral`), 180s (`System Design`). Visual timer shifts to amber at 30s remaining and red at 0s with a gentle "Wrap up your answer" reminder without forcefully cutting the candidate off.
- **D-08 (Turn Duration Persistence):** Track and store elapsed answer time in `interview_question_turns.turn_duration_sec`.

### the agent's Discretion
- Structured Gemini prompt templates for initial core question generation, dynamic follow-up decision, and ideal answer synthesis.
- Turn transition handlers and endpoint payloads.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Schema & Architecture
- `docs/BACKEND_SCHEMA.md` §2.6 — `interview_sessions` lifecycle state machine.
- `docs/BACKEND_SCHEMA.md` §2.7 — `interview_question_turns` schema (parent turn linking, `turn_index`, `candidate_answer`, `ideal_answer`).
- `.planning/PROJECT.md` — Constraints (§ ₹0 Zero-Cost hard constraint, Web Speech API).

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — Requirements `INTV-01`, `INTV-02`, `INTV-03`, `INTV-04`, `INTV-05`, `INTV-06`.
- `.planning/ROADMAP.md` — Phase 5 scope and success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app.models.interview.InterviewSession` & `InterviewQuestionTurn`: Database models ready with foreign keys and relationships.
- `app.services.gemini_service.GeminiService`: `google-genai` SDK async wrapper with retries and structured schema support.
- `app.api.deps.get_current_user`: Authentication dependency securing turn endpoints.
- `app.core.rate_limit.limiter`: SlowAPI rate limiter for AI generation routes.

### Established Patterns
- SQLAlchemy 2.0 async sessions with declarative ORM models.
- Centralized exception handling (`AppError`, `ValidationError`, `NotFoundError`, `ConflictError`).

### Integration Points
- Mount turn retrieval and answer submission endpoints under `/api/v1/interviews/sessions/{session_id}/turns`.
- Transition session `status` to `'completed'` or `'evaluating'` upon answering the final turn.

</code_context>

<specifics>
## Specific Ideas

- Endpoints to deliver:
  - `POST /api/v1/interviews/sessions/{session_id}/start`: Generate and return turn 0 (first core question).
  - `GET /api/v1/interviews/sessions/{session_id}/current-turn`: Get current pending question turn.
  - `POST /api/v1/interviews/sessions/{session_id}/turns/{turn_id}/answer`: Submit candidate response, trigger adaptive probing evaluation, and generate the next turn (or complete the session).
  - `GET /api/v1/interviews/sessions/{session_id}/turns`: Retrieve full turn transcript history.

</specifics>

<deferred>
## Deferred Ideas

- Post-interview multi-dimensional scoring (0-100 on 5 dimensions) is scheduled for Phase 6.
- Comprehensive visual performance reports and PDF exports are scheduled for Phase 7.

</deferred>

---

*Phase: 05-interactive-adaptive-interview-engine-voice-flow*  
*Context gathered: 2026-08-18*  
