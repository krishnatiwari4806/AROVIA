# Phase 2: Authentication & Profile Management - Context

**Gathered:** 2026-08-16  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 2 delivers secure candidate authentication and profile management for AROVIA. This encompasses:
- Candidate registration with salted `bcrypt` password hashing (cost factor 12) and $\ge 12$-character passphrase enforcement.
- Dual-token session management: short-lived (15-min) in-memory access tokens paired with 7-day `HttpOnly`, `Secure`, `SameSite=Lax` refresh cookies.
- Single-use refresh token rotation with immediate invalidation upon reuse.
- Google OAuth ID token verification via `google-auth` (`google.oauth2.id_token.verify_oauth2_token`) and explicit non-silent account linking.
- Candidate profile management (`GET /api/v1/auth/me`, `PUT /api/v1/auth/me`).
- Layered brute-force mitigation: SlowAPI IP rate limiting (10 req/min on login), account-level failure tracking, progressive backoff delay, and 15-minute temporary lockout (never permanent).
- Secure password recovery with 15-minute single-use SHA-256 token hashing and development console URL output.

</domain>

<decisions>
## Implementation Decisions

### Token Cookie Path Scope & Refresh Token Security
- **D-01:** Scoped strictly to `/api/v1/auth` with `SameSite=Lax`, `HttpOnly=True`, and `Secure=True` (in production). Cookie is only transmitted on auth endpoints (`/refresh`, `/logout`), adhering to least-privilege security.
- **D-02:** Single-use refresh token rotation: every `/api/v1/auth/refresh` request revokes the presented refresh token, generates a fresh secret, and stores only its SHA-256 hash in `refresh_tokens`. Reuse of revoked tokens is rejected immediately.
- **D-03:** Dual-token storage architecture: raw access tokens live strictly in React client memory (`AuthContext`); refresh tokens live in the `HttpOnly` cookie. No tokens are written to `localStorage`.

### Registration & Profile Schema
- **D-04:** Minimal registration payload: candidates sign up with `full_name`, `email`, and `password` (minimum 12 characters, rejecting top common passwords).
- **D-05:** Career profile configuration: `target_role`, `experience_level` (`junior`, `mid`, `senior`), and `bio` are configured via `PUT /api/v1/auth/me` during onboarding (`/onboarding`) or profile editing (`/profile`).

### Password Reset Delivery in Local Development
- **D-06:** Standard console logging in development: when `ENVIRONMENT=development` or `testing`, the backend logs the full clickable reset link (`http://localhost:5173/reset-password?token=<token>`) to `stdout`/application logger.
- **D-07:** API responses always return the uniform generic confirmation message (`"If an account with that email exists, password reset instructions have been dispatched"`) in both development and production to prevent response divergence or email enumeration.

### Google OAuth Verification & Identity Linking
- **D-08:** Cryptographic verification using official `google-auth` library (`google.oauth2.id_token.verify_oauth2_token`) validating Google public JWKS signatures, `GOOGLE_CLIENT_ID` audience, issuer (`accounts.google.com`), and expiration.
- **D-09:** Dedicated `user_oauth_identities` table links Google identities (`provider_user_id` / `sub` claim) to `users.id` with `ON DELETE CASCADE`.
- **D-10:** Anti-silent merge flow: if a Google sign-in matches an existing local password email, the backend rejects silent merging (`ACCOUNT_LINKING_REQUIRED`). Candidate must log in with their password first and explicitly confirm linking.

### Agent's Discretion
- Standard SlowAPI key generator using client IP (`get_remote_address`).
- Pydantic v2 validation rules for email normalization (`EmailStr.lower()`) and password strength checking against lightweight known-breached list.
- SQLite in-memory test fixtures with mock Google OAuth verification token mocks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture, Flow & Security Standards
- `docs/TRD.md` §5 — Complete Authentication & Token Architecture (bcrypt, JWT, cookies, Google OAuth, rate limiting, password reset)
- `docs/APP_FLOW.md` §2, §3, §4, §5, §15 — Registration, Login collision UX, Password reset, Onboarding, and Token refresh flows
- `docs/UI_UX_BRIEF.md` §5.2, §5.3, §5.4, §5.5 — Auth and Onboarding UI components, input forms, and error states
- `docs/BACKEND_SCHEMA.md` §2.1, §2.2, §2.3, §2.4, §7 — Schema tables: `users`, `user_oauth_identities`, `refresh_tokens`, `password_reset_tokens`, and layered rate limiting

### Existing Codebase Standards
- `backend/app/core/config.py` — Pydantic Settings (`SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `GOOGLE_CLIENT_ID`)
- `backend/app/core/exceptions.py` — Exception hierarchy (`UnauthorizedError`, `ConflictError`, `ValidationError`, `AppError`)
- `backend/app/db/base.py` — SQLAlchemy 2.0 `Base` class and `CommonModelMixin` (UUIDv4 primary keys, timestamps)
- `backend/app/db/session.py` — Async database engine and `get_db` session dependency

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CommonModelMixin` (`backend/app/db/base.py`): Reusable UUID string primary key (`id`) and UTC timestamps (`created_at`, `updated_at`).
- `Settings` (`backend/app/core/config.py`): Centralized config loading with fail-fast validation for auth secrets and database URLs.
- `global_exception_handler` (`backend/app/core/exceptions.py`): Unified JSON error response envelope masking 500 tracebacks.

### Established Patterns
- SQLAlchemy 2.0 Async declarative models with `Mapped[]` type annotations.
- Pydantic v2 `BaseModel` DTO schemas for request/response validation.
- SQLite in-memory async test harness with `httpx.AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False))`.

### Integration Points
- `backend/app/api/v1/router.py`: Mounting auth endpoints under `/api/v1/auth`.
- `backend/app/core/security.py`: Password hashing helper (`passlib` with bcrypt) and JWT encoding/decoding (`PyJWT`).
- `backend/alembic/versions/`: New versioned migration script adding `users`, `user_oauth_identities`, `refresh_tokens`, and `password_reset_tokens`.

</code_context>

<specifics>
## Specific Ideas

- Fast password hashing and token generation routines with zero external network dependencies in unit tests.
- High-entropy reset tokens generated with `secrets.token_urlsafe(32)` and hashed via SHA-256 before storage.
- Clean separation between OAuth identity records and core user profile fields.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed strictly within Phase 2 scope.

</deferred>

---

*Phase: 02-Authentication & Profile Management*  
*Context gathered: 2026-08-16*  
