---
phase: 04
phase_slug: interview-setup-role-configuration
date: 2026-08-18
status: ready
---

# Phase 04: Validation Strategy (Nyquist Verification Matrix)

This document establishes the test harness, automated verification commands, and validation gates for Phase 4 (Interview Setup & Role Configuration).

---

## 1. Test Harness & Environment

- **Framework**: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`
- **Database Fixture**: In-memory SQLite async engine (`sqlite+aiosqlite:///:memory:`)
- **AI Mocking**: Mock `GeminiService.parse_job_description` to test JD structured parsing, transient error retries, and fallback handling without external API costs.

---

## 2. Verification Gates & Requirement Mapping

| Requirement | Test File | Test Method | Description |
|---|---|---|---|
| **CONF-01** | `tests/test_interview_presets.py` | `test_get_presets_catalog` | Validates standard curated role presets, focus skills, seniority tiers, and pacing guidance. |
| **CONF-02** | `tests/test_interview_sessions.py` | `test_session_configuration_validation` | Validates seniority tiers (`junior`, `mid`, `senior`), focus areas (`Technical Core`, `System Design`, `Behavioral`), and practice modes (`full` vs `quick`). |
| **CONF-03** | `tests/test_interview_jd_parser.py` | `test_jd_sanitization_and_gemini_parsing` | Validates 10,000 char length cap, control char sanitization, and structured JD parsing via `google-genai` with fallback resilience. |
| **CONF-04** | `tests/test_interview_sessions.py` | `test_session_lifecycle_and_single_active_policy` | Verifies `POST /sessions` creation, `GET /sessions/active`, `POST /sessions/{id}/abandon`, active session 409 conflict guard, and `resume_id` link with `SET NULL` on delete. |

---

## 3. Automated Verification Commands

```bash
# Run all Phase 4 tests
python -m pytest backend/tests/test_interview_presets.py backend/tests/test_interview_jd_parser.py backend/tests/test_interview_sessions.py -v

# Run full project test suite
python -m pytest backend/tests/ -v
```

---
*Validation strategy locked for Phase 4.*
