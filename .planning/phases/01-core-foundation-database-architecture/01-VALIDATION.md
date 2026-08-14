---
phase: 1
slug: core-foundation-database-architecture
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.4+ |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `python -m pytest backend/tests/ -k "test_config or test_health" -v` |
| **Full suite command** | `python -m pytest backend/tests/ -v` |
| **Estimated runtime** | ~0.15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/ -v`
- **After every plan wave:** Run `python -m pytest backend/tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | SECR-04 | T-01-01 | Settings fail fast if secrets missing; no hardcoded credentials | unit | `python -m pytest backend/tests/test_config.py -v` | ✅ | ✅ green |
| 01-01-02 | 01 | 1 | SECR-01 | T-01-02 | Health endpoint validates DB connection and returns typed schema | integration | `python -m pytest backend/tests/test_health.py -k test_health_check -v` | ✅ | ✅ green |
| 01-02-01 | 02 | 2 | SECR-01 | T-01-03 | Base ORM models with timestamp mixins and async session lifecycle | unit | `python -m pytest backend/tests/test_models.py -v` | ✅ | ✅ green |
| 01-02-02 | 02 | 2 | SECR-05 | T-01-04 | Global exception handler catches 500s and masks internal stack traces | integration | `python -m pytest backend/tests/test_health.py -k test_global_exception_handler -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/requirements.txt` & `backend/requirements-dev.txt` — dependencies installed
- [x] `backend/pytest.ini` — async configuration (`asyncio_mode = auto`)
- [x] `backend/tests/conftest.py` — in-memory SQLite (`aiosqlite`) test fixtures and `httpx.AsyncClient`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| *None* | — | — | All Phase 1 behaviors have automated pytest verification |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** Approved 2026-08-15
