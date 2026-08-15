---
phase: 02-authentication-profile-management
plan: 02
subsystem: auth
tags: [fastapi, registration, login, refresh-tokens, cookies, brute-force, slowapi]

# Dependency graph
requires:
  - phase: 02-01
    provides: Bcrypt hashing, token utilities, User ORM models, and SlowAPI limiter
provides:
  - Pydantic v2 DTO schemas for candidate registration, login, and token responses
  - AuthService registration, authentication, rotation, and logout business logic
  - POST /api/v1/auth/register endpoint with 12-char passphrase and common-password validation
  - POST /api/v1/auth/login endpoint with 10 req/min rate limit, progressive delay, and 15-min temporary lockout
  - POST /api/v1/auth/refresh with single-use rotation and HttpOnly, SameSite=Lax cookie management
  - POST /api/v1/auth/logout with database token revocation and cookie clearing
  - get_current_user route guard dependency for Bearer access token authorization
affects: [02-03, 03-resume-management, 04-interview-engine]

# Tech tracking
tech-stack:
  added: [email-validator]
  patterns: [HttpOnly SameSite=Lax cookie auth, Single-use refresh token rotation, Layered account lockout & progressive delay, Enumeration-safe generic responses]

key-files:
  created:
    - backend/app/schemas/auth.py
    - backend/app/services/auth_service.py
    - backend/app/api/deps.py
    - backend/app/api/v1/endpoints/auth.py
    - backend/tests/test_auth_register.py
    - backend/tests/test_auth_login.py
    - backend/tests/test_auth_refresh.py
  modified:
    - backend/requirements.txt
    - backend/app/main.py
    - backend/app/api/v1/router.py
    - backend/app/core/exceptions.py
    - backend/app/core/rate_limit.py

key-decisions:
  - "Path-scoped cookie security: Refresh token cookie is strictly scoped to Path=/api/v1/auth with SameSite=Lax as the primary CSRF protection."
  - "Layered brute-force defense: SlowAPI limits login to 10 req/min per IP, accounts experience 2s progressive delay after 3 failed attempts, and 15-min temporary lockout after 5 failed attempts."
  - "Account enumeration defense: Unknown emails and invalid passwords return the exact same HTTP 401 Unauthorized response."

patterns-established:
  - "HttpOnly refresh cookie: set_refresh_cookie() sets 7-day HttpOnly cookie with Path=/api/v1/auth"
  - "Single-use rotation: rotate_refresh_token() revokes presented token, issues new secret, and stores new SHA-256 hash"

requirements-completed:
  - AUTH-01
  - AUTH-02
  - AUTH-03

# Metrics
duration: 12min
completed: 2026-08-16
---

# Phase 02: Plan 02 Summary

**Candidate registration, login with 10 req/min rate limit and 15-min lockout defense, single-use refresh token rotation with HttpOnly SameSite=Lax cookies, and get_current_user route guard.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-16T01:48:00Z
- **Completed:** 2026-08-16T02:00:00Z
- **Tasks:** 3 completed
- **Files modified/created:** 12

## Accomplishments
- Implemented Pydantic v2 DTO schemas (`UserRegisterRequest`, `UserLoginRequest`, `TokenResponse`, `UserResponse`, `MessageResponse`).
- Implemented `AuthService` handling registration with password policy, authentication with progressive delay & 15-min lockout, single-use token rotation, and logout.
- Built `get_current_user` FastAPI dependency for decoding Bearer JWT tokens and loading active users.
- Built REST API endpoints (`/register`, `/login`, `/refresh`, `/logout`) in `backend/app/api/v1/endpoints/auth.py`.
- Enforced account enumeration defense (identical responses for unknown email vs wrong password).
- Verified `HttpOnly`, `Path=/api/v1/auth`, `SameSite=Lax`, and `Max-Age=604800` cookie attributes.
- Wrote integration test suite with 100% pass rate (10/10 tests passing).

## Files Created/Modified
- `backend/app/schemas/auth.py` - Pydantic DTO schemas with validation
- `backend/app/services/auth_service.py` - Core authentication and session business logic
- `backend/app/api/deps.py` - `get_current_user` route guard dependency
- `backend/app/api/v1/endpoints/auth.py` - Register, login, refresh, and logout endpoints
- `backend/app/api/v1/router.py` - Mounted auth router under `/api/v1/auth`
- `backend/app/main.py` - Configured SlowAPI limiter and exception handlers
- `backend/app/core/exceptions.py` - Enhanced exception classes with `message`/`detail` aliases and `ValidationError`
- `backend/app/core/rate_limit.py` - Configured test-aware rate limiter
- `backend/requirements.txt` - Added `email-validator`
- `backend/tests/test_auth_register.py` - Tests for registration, duplicate email, password policy
- `backend/tests/test_auth_login.py` - Tests for login, account lockout, enumeration defense
- `backend/tests/test_auth_refresh.py` - Tests for token rotation, revoked token replay, logout

## Deviations from Plan

### Auto-fixed Issues
**1. [Rule 1 - Bug Fix] Timezone-aware datetime comparison**
- **Found during:** Task 3 execution
- **Issue:** SQLite in-memory engine returned naive datetimes, causing `TypeError` when comparing with timezone-aware UTC timestamps.
- **Fix:** Added `ensure_utc()` helper to ensure all datetime comparisons are timezone-aware.
- **Files modified:** `backend/app/services/auth_service.py`
- **Verification:** All token rotation and lockout tests passed cleanly.

**2. [Rule 3 - Missing Dependency] Added email-validator**
- **Found during:** Task 1 execution
- **Issue:** Pydantic `EmailStr` requires `email-validator`.
- **Fix:** Added `email-validator` to `requirements.txt` and installed it.
- **Files modified:** `backend/requirements.txt`
- **Verification:** Import and tests succeeded.

## Next Plan Readiness
- Plan 02 complete. Ready to proceed with Plan 03: Google OAuth, Profile Management, and Password Reset.

---
*Phase: 02-authentication-profile-management*  
*Completed: 2026-08-16*  
