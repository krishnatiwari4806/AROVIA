# Phase 05: Interactive Adaptive Interview Engine & Voice Flow - Technical Research

**Phase:** 05-interactive-adaptive-interview-engine-voice-flow  
**Status:** Complete  
**Date:** 2026-08-18  

---

## 1. Domain & Technical Objectives

Phase 5 implements the live adaptive mock interview loop. Candidates receive conversational questions sequentially, hear them via browser-native Text-to-Speech (TTS), dictate answers via Speech-to-Text (STT) or type them manually, receive dynamic follow-up probes when answers warrant depth, and advance through the session until completion.

### Key Requirements (MUST Address)
- **INTV-01:** Sequential turn progression, presenting one question prompt at a time with active turn indicators and response timer.
- **INTV-02:** Verbal question reading via browser-native Text-to-Speech (`window.speechSynthesis`).
- **INTV-03:** Candidate verbal dictation via Speech-to-Text (`window.webkitSpeechRecognition` / `SpeechRecognition`), with editable textarea and manual typing fallback.
- **INTV-04:** Dynamic adaptive follow-up probing: Gemini evaluates whether an answer leaves core mechanics unexplained or makes unbacked claims, generating a targeted follow-up probe before moving to the next core question.
- **INTV-05:** Pacing limits: Hard turn cap (max 9 turns for full, max 5 for quick), max 1 follow-up per core question, and max 3 follow-ups total.
- **INTV-06:** Session completion transition: Once final turn is answered, session status transitions to `'evaluating'` / `'completed'` and the interview room displays completion status.

### Zero-Cost Hard Constraint (₹0)
- **Audio Flow**: 100% Browser-Native Web Speech API. Zero external speech APIs (ElevenLabs, Deepgram, Whisper Cloud).
- **AI Engine**: Google Gemini API free-tier (`gemini-2.5-flash` via `google-genai` SDK with strict JSON schema enforcement).

---

## 2. Technical Architecture & State Machine

```
[Session Created (in_progress)]
           │
           ▼
[POST /sessions/{id}/start]
           │
           ├─► Gemini generates Turn 0 (First Core Question + Ideal Answer)
           └─► Returns Turn 0 to Candidate
                    │
                    ▼
          [Candidate Answers Turn]
           (TTS auto-play + STT dictation / Manual typing + Soft Timer)
                    │
                    ▼
[POST /sessions/{id}/turns/{turn_id}/answer]
                    │
                    ▼
     [Evaluate Answer & Pacing]
                    │
    ┌───────────────┴────────────────┐
    ▼                                ▼
[Follow-up Warranted &        [No Follow-up or
 Budget Remaining?]           Budget Exhausted]
    │                                │
    ├─► YES: Generate Follow-up      ├─► Has More Core Questions?
    │   (is_follow_up=True,          │    ├─► YES: Generate Next Core Turn
    │    parent_turn_id=turn.id)     │    └─► NO: Mark session 'evaluating'
    │                                │        (is_interview_complete=True)
    └─► Advance Turn Index           └─► Advance Turn Index
```

### 2.1 Pacing & Turn Limit Formulas
- **Full Mode**:
  - `planned_core_questions`: 6
  - `max_total_turns`: 9
  - `max_follow_ups`: 3
- **Quick Mode**:
  - `planned_core_questions`: 3
  - `max_total_turns`: 5
  - `max_follow_ups`: 2
- **Invariant**: A core question can have at most ONE direct follow-up probe. If turn $K$ is already a follow-up, turn $K+1$ MUST either be the next core question or session completion.

### 2.2 Gemini Structured Schemas (`google-genai`)
```python
class GeneratedQuestion(BaseModel):
    question_text: str = Field(..., description="Conversational interview question prompt.")
    ideal_answer: str = Field(..., description="Comprehensive senior benchmark answer covering key technical concepts.")
    primary_concept: str = Field(..., description="The main technical topic being assessed.")

class NextTurnDecision(BaseModel):
    is_follow_up: bool = Field(..., description="Whether to probe deeper on current topic.")
    follow_up_reasoning: Optional[str] = Field(None, description="Why follow-up is warranted.")
    question_text: Optional[str] = Field(None, description="The follow-up probe or next core question text.")
    ideal_answer: Optional[str] = Field(None, description="Benchmark model answer.")
    primary_concept: Optional[str] = Field(None, description="Key concept assessed.")
    is_interview_complete: bool = Field(False, description="True if all planned questions are exhausted.")
```

---

## 3. REST API Contract

- `POST /api/v1/interviews/sessions/{session_id}/start`
  - Initializes the interview run by generating turn index 0.
  - Returns `InterviewQuestionTurnResponse`.
- `GET /api/v1/interviews/sessions/{session_id}/current-turn`
  - Retrieves the latest pending turn for the active session.
  - Returns `InterviewQuestionTurnResponse`.
- `POST /api/v1/interviews/sessions/{session_id}/turns/{turn_id}/answer`
  - Submits candidate's answer and duration.
  - Returns `TurnAnswerSubmissionResponse` with `next_turn: Optional[InterviewQuestionTurnResponse]` and `is_interview_complete: bool`.
- `GET /api/v1/interviews/sessions/{session_id}/turns`
  - Retrieves full chronologically ordered turn transcript history.
  - Returns `List[InterviewQuestionTurnResponse]`.

---

## 4. Frontend Voice Interview Room (Web Speech API)

- **`useSpeechSynthesis`**:
  - Manages `window.speechSynthesis.speak(utterance)`.
  - Exposes `speak(text)`, `cancel()`, `isSpeaking`.
  - Auto-reads new question text when turn changes.
- **`useSpeechRecognition`**:
  - Manages `window.webkitSpeechRecognition` or `window.SpeechRecognition`.
  - Exposes `startListening()`, `stopListening()`, `isListening`, `transcript`, `error`.
  - Real-time continuous transcription streamed into parent answer state.
- **Timer & Controls**:
  - Soft countdown timer with color shift (Green $\rightarrow$ Amber at 30s $\rightarrow$ Red at 0s with reminder badge).
  - Explicit "Submit Answer" button with confirmation.
- **Completion View**:
  - Displays session summary banner once `is_interview_complete` is true, indicating evaluation in progress.

---
*Research completed for Phase 5 planning.*
