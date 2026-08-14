---
phase: 1
slug: core-foundation-database-architecture
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `pytest tests/ -k "test_config or test_health" -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~2-3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | SECR-04 | T-01-01 | Settings fail fast if secrets missing; no hardcoded credentials | unit | `pytest tests/test_config.py -v` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | SECR-01 | T-01-02 | Health endpoint validates DB connection and returns typed schema | integration | `pytest tests/test_health.py -k test_health_check -v` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | SECR-01 | T-01-03 | Base ORM models with timestamp mixins and async session lifecycle | unit | `pytest tests/test_models.py -v` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | SECR-05 | T-01-04 | Global exception handler catches 500s and masks internal stack traces | integration | `pytest tests/test_health.py -k test_exception_handler -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/requirements.txt` & `backend/requirements-dev.txt` — dependencies installed
- [ ] `backend/pytest.ini` — async configuration (`asyncio_mode = auto`)
- [ ] `backend/tests/conftest.py` — in-memory SQLite (`aiosqlite`) test fixtures and `httpx.AsyncClient`

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
