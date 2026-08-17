---
phase: 05
phase_slug: interactive-adaptive-interview-engine-voice-flow
date: 2026-08-18
status: ready
---

# Phase 05: Validation Strategy (Nyquist Verification Matrix)

This document establishes the test harness, automated verification commands, and validation gates for Phase 5 (Interactive Adaptive Interview Engine & Voice Flow).

---

## 1. Test Harness & Environment

- **Backend**: `pytest` + `pytest-asyncio` + `httpx.AsyncClient` + in-memory SQLite async engine.
- **Frontend**: Component and hook unit tests + live browser interaction validation.
- **AI Mocking**: Mock Gemini API responses for initial question generation, dynamic probing evaluation, and fallback error handling to guarantee deterministic, fast test runs without external API quotas.

---

## 2. Verification Gates & Requirement Mapping

| Requirement | Test File | Test Method | Description |
|---|---|---|---|
| **INTV-01** | `backend/tests/test_interview_turns.py` | `test_turn_progression_and_turn_indicators` | Verifies sequential turn progression (one question per turn) with correct turn indexing and limits. |
| **INTV-02** | `frontend/src/hooks/__tests__/useSpeechSynthesis.test.ts` (or integration) | `test_speech_synthesis_flow` | Verifies browser-native Text-to-Speech playback, replay, and cancel triggers. |
| **INTV-03** | `frontend/src/hooks/__tests__/useSpeechRecognition.test.ts` | `test_speech_recognition_and_manual_edit` | Verifies live microphone transcription into editable state and manual text edit fallback. |
| **INTV-04** | `backend/tests/test_interview_adaptive_engine.py` | `test_adaptive_follow_up_generation_and_linking` | Verifies dynamic follow-up generation when answers warrant depth, correctly setting `is_follow_up=True` and `parent_turn_id`. |
| **INTV-05** | `backend/tests/test_interview_turns.py` | `test_pacing_and_turn_cap_enforcement` | Verifies turn cap limits (max 9 turns for full, max 5 for quick, max 1 follow-up per core question). |
| **INTV-06** | `backend/tests/test_interview_turns.py` | `test_session_completion_transition` | Verifies status transition to `'evaluating'` / `'completed'` once final turn is answered. |

---

## 3. Automated Verification Commands

```bash
# Run Phase 5 backend tests
python -m pytest backend/tests/test_interview_adaptive_engine.py backend/tests/test_interview_turns.py -v

# Run full project test suite
python -m pytest backend/tests/ -v
```

---
*Validation strategy locked for Phase 5.*
