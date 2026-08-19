# Phase 05: Interactive Adaptive Interview Engine & Voice Flow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.  
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-18  
**Phase:** 05-interactive-adaptive-interview-engine-voice-flow  
**Areas discussed:** Adaptive Follow-up Trigger Criteria & State Machine, Question Sequencing & Context Progression Strategy, Speech & Audio Interaction UX (Web Speech API), Turn Timers, Answer Timeouts & Submission Controls  

---

## Adaptive Follow-up Trigger Criteria & State Machine

| Option | Description | Selected |
|--------|-------------|----------|
| Balanced Probing (Max 1 follow-up per core question, max 3 per session) | Probe when answer mentions claims/tools without explaining mechanics, trade-offs, or concrete experience; otherwise advance to next core question | ✓ |
| Aggressive Probing | Always generate a follow-up probe for every core question until the hard 9-turn cap is reached | |
| Passive / Candidate-Triggered Probing | Only probe if answer length is under 30 words or candidate explicitly asks for clarification | |

**User's choice:** Balanced Probing (Max 1 follow-up per core question, max 3 per session)  
**Notes:** Prevents infinite follow-up loops while still ensuring genuine technical depth is probed.

---

## Question Sequencing & Context Progression Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Progressive Difficulty Curve (Warmup -> Core Tech -> Edge Cases & Trade-offs) | Start with domain/project context from resume, escalate to deep core skills from JD, and end with complex trade-offs / failure modes | ✓ |
| Uniform Difficulty Distribution | Randomly sample questions equally across all required skills from JD without a structured progressive arc | |
| Strict Scenario-Only Interview | Every question framed as an interactive real-time outage or architecture scenario without general conceptual questions | |

**User's choice:** Progressive Difficulty Curve (Warmup -> Core Tech -> Edge Cases & Trade-offs)  
**Notes:** Reflects realistic top-tier technical interviews by warming up on candidate projects before testing advanced system limits.

---

## Speech & Audio Interaction UX (Web Speech API)

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-Speak with Replay/Mute + Real-time Mic Dictation with Editable Textarea | Question speaks on turn load with replay/mute controls; Mic streams live text into an editable box where candidate can freely edit and explicitly click 'Submit Answer' | ✓ |
| Pure Voice-Driven Flow with Silence Detection | Automatically submit candidate answer after 3 seconds of continuous silence without manual edit step | |
| Text-Only Default with Optional Voice | Voice features off by default, candidate must click to listen or dictate | |

**User's choice:** Auto-Speak with Replay/Mute + Real-time Mic Dictation with Editable Textarea  
**Notes:** 100% browser-native Web Speech API (zero cost). Allows candidate to correct STT errors prior to submission.

---

## Turn Timers, Answer Timeouts & Submission Controls

| Option | Description | Selected |
|--------|-------------|----------|
| Soft Pacing Timer with Visual Warning | Timer turns amber at 30s remaining and red with gentle 'Wrap up your answer' banner at 0s, allowing the candidate to finish their thoughts without forcefully cutting them off | ✓ |
| Hard Auto-Submit at 0s | Automatically submits current answer and locks the input immediately when the timer reaches zero | |
| Grace Period | Soft warning + 60-second overtime buffer before hard locking and submitting | |

**User's choice:** Soft Pacing Timer with Visual Warning  
**Notes:** Reduces candidate anxiety while clearly communicating suggested interview pacing.

---

## the agent's Discretion

- Gemini prompt templates and structured JSON response schemas for dynamic follow-up determination and question formulation.
- REST endpoint URL schemas and DTO models.

---

## Deferred Ideas

- Post-interview evaluation algorithms and 5-dimension report generation are scheduled for Phase 6.
