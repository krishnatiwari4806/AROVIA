# Phase 2: Authentication & Profile Management - Research

**Researched:** 2026-08-16  
**Domain:** FastAPI Authentication, Salted Bcrypt Hashing, Dual-Token Architecture, HttpOnly Cookie Rotation, Google OAuth2 ID Token Verification, SlowAPI Rate Limiting, and SQLAlchemy 2.0 User Models  
**Confidence:** HIGH  

---

<user_constraints>
## User Constraints (from CONTEXT.md & Security Guidelines)

### Locked Decisions
- **D-01:** Refresh token cookie is scoped strictly to `Path=/api/v1/auth` with `SameSite=Lax`, `HttpOnly=True`, and `Secure=True` in production (`Secure=False` in development/test over HTTP). Cookie is only transmitted on auth routes (`/refresh`, `/logout`), adhering to least-privilege security. `SameSite=Lax` serves as the primary MVP CSRF defense for cookie-bearing endpoints without requiring extra CSRF framework overhead.
- **D-02:** Single-use refresh token rotation: every `/api/v1/auth/refresh` request revokes the presented refresh token, generates a fresh 32-byte secret, and stores only its SHA-256 hash in `refresh_tokens`. Reuse of an already-revoked token is rejected immediately with HTTP 401.
- **D-03:** Dual-token storage architecture: short-lived (15-min) access tokens live strictly in React memory (`AuthContext`); refresh tokens live in the `HttpOnly` cookie. Zero sensitive tokens in `localStorage`.
- **D-04:** Minimal registration payload: candidates sign up with `full_name`, `email`, and `password` (minimum 12 characters, rejecting common/compromised passwords even if $\ge 12$ chars).
- **D-05:** Career profile configuration: `target_role`, `experience_level` (`junior`, `mid`, `senior`), and `bio` are configured via `PUT /api/v1/auth/me` during onboarding (`/onboarding`) or profile editing (`/profile`).
- **D-06:** Standard console logging in development: when `ENVIRONMENT=development` or `testing`, the backend logs the full clickable reset link (`http://localhost:5173/reset-password?token=<token>`) to `stdout`/application logger. The reset token is never returned in the API response body.
- **D-07:** API responses always return the uniform generic confirmation message (`"If an account with that email exists, password reset instructions have been dispatched"`) for both existing and non-existing emails to prevent email enumeration.
- **D-08:** Reset token management: when issuing a new password reset token, all previous active reset tokens for that candidate are invalidated (`used = True`), ensuring only the newest reset link remains active.
- **D-09:** Google verification fails closed: real application code always calls `google.oauth2.id_token.verify_oauth2_token()` regardless of `ENVIRONMENT`. Production Google authentication fails closed if `GOOGLE_CLIENT_ID` is missing. Tests mock/monkeypatch `verify_oauth2_token` instead of using app-level test bypass flags.
- **D-10:** Google token claim validation: verifies cryptographic signature, audience (`settings.GOOGLE_CLIENT_ID`), issuer (`accounts.google.com` or `https://accounts.google.com`), token expiry, non-empty `sub`, valid `email`, and `email_verified is True`.
- **D-11:** Dedicated `user_oauth_identities` table links Google identities (`provider_user_id` / `sub` claim) to `users.id` with `ON DELETE CASCADE`.
- **D-12:** Anti-silent merge flow: if a Google sign-in matches an existing local password email, the backend rejects silent merging (`ACCOUNT_LINKING_REQUIRED`). Candidate must log in with their password first and explicitly confirm linking.
- **D-13:** Login protection: SlowAPI applies explicit `10/minute` IP rate limiting on `POST /api/v1/auth/login`. Application logic tracks failed attempts per account, adds 2-second sleep delay when `failed_login_attempts >= 3`, and enforces a 15-minute temporary lockout when `failed_login_attempts >= 5`. Accounts are never permanently locked.

### Agent's Discretion
- Pydantic v2 email normalization (`EmailStr.lower()`) and password strength checking against lightweight known-breached list.
- Exact pytest test fixture naming and mock structures in `backend/tests/conftest.py`.

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed strictly within Phase 2 scope.
</user_constraints>

---

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Password Hashing & JWT Signing | Security Core (`core/security.py`) | Passlib (bcrypt) & PyJWT | Centralized cryptographic functions, constant-time verification |
| IP Rate Limiting | Rate Limit Core (`core/rate_limit.py`) | SlowAPI / FastAPI Middleware | Enforces 10 req/min on `/login` and 3 req/min on `/register` per IP |
| Auth Business Logic & OAuth | Auth Service (`services/auth_service.py`) | Google Auth / DB | Manages registration, credential checks, OAuth verification, token rotation |
| Profile & Session Management | API Router (`api/v1/endpoints/auth.py`) | Security Dependencies | Validates incoming Pydantic DTOs, sets HttpOnly cookies, returns typed responses |
| Identity & Credential Persistence | Database Models (`models/user.py`) | PostgreSQL / SQLAlchemy 2.0 | Persists `User`, `UserOAuthIdentity`, `RefreshToken`, and `PasswordResetToken` |
| Fast Unit/Integration Testing | Test Suite (`tests/test_auth_*.py`) | In-Memory SQLite (`aiosqlite`) | Isolated, fast test runs (< 0.5s) testing all auth flows without network calls |
</architectural_responsibility_map>

---

<research_summary>
## Summary

Phase 2 establishes the end-to-end authentication and candidate identity foundation for AROVIA with defense-in-depth:
1. **Credential Hashing:** Salted `bcrypt` with cost factor 12 via `passlib.context.CryptContext`.
2. **Dual-Token Session Architecture:** Stateless 15-minute access tokens signed with `HS256` (`PyJWT`), paired with 7-day `HttpOnly`, `SameSite=Lax` refresh cookies path-scoped to `/api/v1/auth` (`Secure=True` in production).
3. **Single-Use Token Rotation:** Every refresh invalidates the used refresh token and persists the SHA-256 hash of the replacement token.
4. **Google OAuth Verification (Fail-Closed):** Verified via `google.oauth2.id_token.verify_oauth2_token()` validating Google's public certificates, client ID audience, issuer, expiry, and `email_verified == True`.
5. **Layered Brute-Force & Enumeration Protection:**
   - IP-based rate limiting via SlowAPI (`10/minute` on `/login`).
   - Account/email-based failure tracking (`users.failed_login_attempts`).
   - Progressive 2-second sleep delay when `failed_login_attempts >= 3`.
   - Temporary 15-minute account protection when `failed_login_attempts >= 5`.
   - Uniform generic authentication errors (`"Invalid email or password"`) for both unknown email and bad password.
   - Zero permanent account lockouts.
6. **Password Recovery:** 32-byte cryptographically secure reset tokens (`secrets.token_urlsafe(32)`) hashed with SHA-256, expired after 15 minutes, with invalidation of previous active reset tokens and development console link logging.

---

</research_summary>

<standard_stack>
## Standard Stack

### Core Dependencies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `passlib[bcrypt]` | >=1.7.4 | Password hashing & verification | Secure, battle-tested bcrypt hashing with constant-time verify |
| `bcrypt` | >=4.0.0 | Cryptographic bcrypt backend | C-optimized hashing backend |
| `PyJWT` | >=2.9.0 | JWT generation & decoding | Lightweight, RFC 7519 compliant JSON Web Token library |
| `google-auth` | >=2.30.0 | Google ID Token verification | Official Google library for verifying public JWKS signatures |
| `slowapi` | >=0.1.9 | IP rate limiting | Native FastAPI rate limiting integration based on limits |

### Existing Foundation Dependencies
| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | >=0.115.0 | Web API Framework & Dependency Injection |
| `pydantic` | >=2.9.0 | Schema validation & DTO modeling |
| `sqlalchemy` | >=2.0.30 | Async ORM database operations |
| `asyncpg` | >=0.29.0 | PostgreSQL async driver |
| `aiosqlite` | >=0.20.0 | In-memory SQLite async driver for pytest |
| `httpx` | >=0.28.0 | Async test client with `ASGITransport` |

---

</standard_stack>

<architecture_patterns>
## Architecture & Code Patterns

### 1. Security & Token Utilities (`backend/app/core/security.py`)
```python
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COMMON_PASSWORDS = {
    "password1234", "123456789012", "password123456", "qwertyuiopas",
    "admin12345678", "letmein123456", "welcome123456", "iloveyou123456"
}

def is_common_password(password: str) -> bool:
    return password.lower() in COMMON_PASSWORDS

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: Dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

### 2. Google OAuth Verification Service (`backend/app/services/auth_service.py`)
```python
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import settings
from app.core.exceptions import ValidationError, AppError

def verify_google_id_token(token: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise AppError(
            detail="Google Sign-In is not configured on this server.",
            status_code=500,
            error_code="GOOGLE_AUTH_UNCONFIGURED"
        )
    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except Exception as e:
        raise ValidationError(
            detail="Invalid Google ID token signature or expired.",
            error_code="INVALID_GOOGLE_TOKEN"
        )

    # Validate mandatory claims
    issuer = id_info.get("iss")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValidationError(detail="Invalid token issuer", error_code="INVALID_GOOGLE_ISSUER")

    if not id_info.get("sub"):
        raise ValidationError(detail="Invalid subject claim", error_code="INVALID_GOOGLE_SUB")

    if not id_info.get("email"):
        raise ValidationError(detail="Email not provided by Google", error_code="INVALID_GOOGLE_EMAIL")

    if not id_info.get("email_verified", False):
        raise ValidationError(detail="Google email is not verified", error_code="UNVERIFIED_GOOGLE_EMAIL")

    return id_info
```

---

</architecture_patterns>

<validation_architecture>
## Validation Architecture

### Automated Verification Strategy
1. **Security Unit Tests (`tests/test_auth_security.py`):**
   - Bcrypt hashing cost 12 and verification consistency.
   - Rejection of common/compromised passwords $\ge 12$ chars.
   - JWT access token encoding/decoding, expiration checks, and algorithm validation.
   - SHA-256 token hashing consistency.
2. **Registration & Password Policy Tests (`tests/test_auth_register.py`):**
   - Valid registration $\rightarrow$ 201 Created + access token + HttpOnly refresh cookie.
   - Duplicate email $\rightarrow$ 409 Conflict (`EMAIL_ALREADY_EXISTS`).
   - Password $< 12$ characters $\rightarrow$ 422 Unprocessable Entity.
   - Common weak password $\ge 12$ characters $\rightarrow$ 422 Unprocessable Entity.
3. **Login, Rate Limiting & Account Protection Tests (`tests/test_auth_login.py`):**
   - Valid login $\rightarrow$ 200 OK + access token + refresh cookie + failure counter reset.
   - Invalid password $\rightarrow$ 401 Unauthorized (`"Invalid email or password"`).
   - Unknown email $\rightarrow$ 401 Unauthorized (`"Invalid email or password"`). Identical response to prevent enumeration.
   - Progressive delay applied after 3 failed attempts.
   - 15-minute temporary lockout after 5 failed attempts.
   - Rate limit enforcement: 11th request in 1 minute on `/login` returns 429 Too Many Requests.
4. **Token Refresh & Cookie Attribute Tests (`tests/test_auth_refresh.py`):**
   - Valid refresh cookie $\rightarrow$ 200 OK + new access token + new rotated cookie.
   - Replay of revoked refresh token $\rightarrow$ 401 Unauthorized.
   - Cookie attribute assertions: `HttpOnly`, `Path=/api/v1/auth`, `SameSite=Lax`, `Max-Age=604800`, and `Secure` flag matching environment.
   - Logout clears cookie and revokes token in DB.
5. **Google OAuth Verification Tests (`tests/test_auth_google.py`):**
   - Invalid signature $\rightarrow$ 422/400 error.
   - Wrong audience $\rightarrow$ 422/400 error.
   - Wrong issuer $\rightarrow$ 422/400 error.
   - Expired token $\rightarrow$ 422/400 error.
   - Unverified email (`email_verified=False`) $\rightarrow$ 422/400 error.
   - Missing `GOOGLE_CLIENT_ID` in production $\rightarrow$ 500 error.
   - Valid Google ID token $\rightarrow$ 200 OK + candidate registration/login.
   - Existing Google user $\rightarrow$ 200 OK login.
   - Collision with existing local password email $\rightarrow$ 400 (`ACCOUNT_LINKING_REQUIRED`).
   - Explicit linking via `POST /api/v1/auth/google/link` $\rightarrow$ 200 OK.
   - Linking already-linked Google identity to different user $\rightarrow$ 409 Conflict.
6. **Candidate Profile Tests (`tests/test_auth_profile.py`):**
   - `GET /api/v1/auth/me` with Bearer auth $\rightarrow$ 200 OK candidate profile.
   - `PUT /api/v1/auth/me` $\rightarrow$ updates `target_role`, `experience_level`, and `bio`.
7. **Password Reset Tests (`tests/test_auth_reset.py`):**
   - Generic response for existing and non-existing email.
   - Reset URL is logged to stdout logger in development mode.
   - Reset token is NOT returned in API response body.
   - Previous active reset tokens are invalidated when a new reset token is requested.
   - Valid token resets password successfully; old password no longer works.
   - Expired token fails.
   - Used token fails.
   - Password reset revokes all existing refresh tokens for that candidate.
   - Old refresh tokens cannot be reused after password reset.
