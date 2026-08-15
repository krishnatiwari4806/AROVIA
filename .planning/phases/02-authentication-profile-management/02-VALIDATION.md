---
phase: 2
slug: authentication-profile-management
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-16
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `pytest backend/tests/test_auth_security.py` |
| **Full suite command** | `pytest backend/tests/` |
| **Estimated runtime** | ~0.5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/`
- **After every plan wave:** Run full test suite (`pytest backend/tests/`)
- **Before `/gsd-verify-work`:** Full suite must be 100% green
- **Max feedback latency:** < 1.0 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|:---:|:---:|---|---|---|---|---|:---:|:---:|
| 02-01-01 | 01 | 1 | SECR-02 | T-02-01 | Bcrypt hashing with cost factor 12 | unit | `pytest backend/tests/test_auth_security.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | AUTH-01 | T-02-02 | User models, ORM relationships & Alembic migration | integration | `pytest backend/tests/test_auth_models.py` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | AUTH-01 | T-02-03 | Candidate registration with password policy & token issue | integration | `pytest backend/tests/test_auth_register.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | AUTH-02 | T-02-04 | Candidate login with 5-layer brute-force protection | integration | `pytest backend/tests/test_auth_login.py` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | AUTH-03 | T-02-05 | Silent refresh with single-use token rotation | integration | `pytest backend/tests/test_auth_refresh.py` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | AUTH-04 | T-02-06 | Google OAuth verification & anti-silent account linking | integration | `pytest backend/tests/test_auth_google.py` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | AUTH-05 | T-02-07 | Candidate profile get & update with JWT Bearer auth | integration | `pytest backend/tests/test_auth_profile.py` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 3 | AUTH-02 | T-02-08 | Password reset with 15-min token & console dev delivery | integration | `pytest backend/tests/test_auth_reset.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/requirements.txt` — add `passlib[bcrypt]`, `bcrypt`, `PyJWT`, `google-auth`, `slowapi`
- [ ] `backend/tests/conftest.py` — add user fixtures, auth client helpers, and mock Google ID token fixtures
- [ ] `backend/tests/test_auth_security.py` — unit test suite for cryptographic password hashing and token encoding

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Google Sign-In Browser Popup | AUTH-04 | Requires live browser user interaction with Google Identity Services | Test in browser once frontend connects in later phase |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all dependencies and fixtures
- [x] No watch-mode flags
- [x] Feedback latency < 1.0s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** Approved 2026-08-16
