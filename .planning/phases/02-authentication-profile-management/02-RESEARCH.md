# Phase 2: Authentication & Profile Management - Research

**Researched:** 2026-08-16  
**Domain:** FastAPI Authentication, Salted Bcrypt Hashing, Dual-Token Architecture, HttpOnly Cookie Rotation, Google OAuth2 ID Token Verification, SlowAPI Rate Limiting, and SQLAlchemy 2.0 User Models  
**Confidence:** HIGH  

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Refresh token cookie is scoped strictly to `Path=/api/v1/auth` with `SameSite=Lax`, `HttpOnly=True`, and `Secure=True` (in production). Cookie is only transmitted on auth routes (`/refresh`, `/logout`), adhering to least-privilege security.
- **D-02:** Single-use refresh token rotation: every `/api/v1/auth/refresh` request revokes the presented refresh token, generates a fresh 32-byte secret, and stores only its SHA-256 hash in `refresh_tokens`. Reuse of a revoked token is rejected immediately with HTTP 401.
- **D-03:** Dual-token storage architecture: short-lived (15-min) access tokens live strictly in React memory (`AuthContext`); refresh tokens live in the `HttpOnly` cookie. Zero sensitive tokens in `localStorage`.
- **D-04:** Minimal registration payload: candidates sign up with `full_name`, `email`, and `password` (minimum 12 characters, rejecting top common passwords).
- **D-05:** Career profile configuration: `target_role`, `experience_level` (`junior`, `mid`, `senior`), and `bio` are configured via `PUT /api/v1/auth/me` during onboarding (`/onboarding`) or profile editing (`/profile`).
- **D-06:** Standard console logging in development: when `ENVIRONMENT=development` or `testing`, the backend logs the full clickable reset link (`http://localhost:5173/reset-password?token=<token>`) to `stdout`/application logger.
- **D-07:** API responses always return the uniform generic confirmation message (`"If an account with that email exists, password reset instructions have been dispatched"`) in both development and production to prevent response divergence or email enumeration.
- **D-08:** Cryptographic verification using official `google-auth` library (`google.oauth2.id_token.verify_oauth2_token`) validating Google public JWKS signatures, `GOOGLE_CLIENT_ID` audience, issuer (`accounts.google.com` or `https://accounts.google.com`), and expiration.
- **D-09:** Dedicated `user_oauth_identities` table links Google identities (`provider_user_id` / `sub` claim) to `users.id` with `ON DELETE CASCADE`.
- **D-10:** Anti-silent merge flow: if a Google sign-in matches an existing local password email, the backend rejects silent merging (`ACCOUNT_LINKING_REQUIRED`). Candidate must log in with their password first and explicitly confirm linking.

### Agent's Discretion
- SlowAPI key generator using client IP (`get_remote_address`).
- Pydantic v2 email normalization (`EmailStr.lower()`) and password validation logic.
- Structure of SQLite in-memory test fixtures and Google ID token mock fixtures in `tests/conftest.py`.

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed strictly within Phase 2 scope.
</user_constraints>

---

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Password Hashing & JWT Signing | Security Core (`core/security.py`) | Passlib (bcrypt) & PyJWT | Centralized cryptographic functions, constant-time verification |
| IP Rate Limiting | Rate Limit Core (`core/rate_limit.py`) | SlowAPI / FastAPI Middleware | Protects login and registration routes from brute-force & credential stuffing |
| Auth Business Logic & OAuth | Auth Service (`services/auth_service.py`) | Google Auth / DB | Manages registration, credential checks, OAuth verification, token rotation |
| Profile & Session Management | API Router (`api/v1/endpoints/auth.py`) | Security Dependencies | Validates incoming Pydantic DTOs, sets HttpOnly cookies, returns typed responses |
| Identity & Credential Persistence | Database Models (`models/user.py`) | PostgreSQL / SQLAlchemy 2.0 | Persists `User`, `UserOAuthIdentity`, `RefreshToken`, and `PasswordResetToken` |
| Fast Unit/Integration Testing | Test Suite (`tests/test_auth.py`) | In-Memory SQLite (`aiosqlite`) | Isolated, fast test runs (< 0.5s) testing all auth flows without network calls |
</architectural_responsibility_map>

---

<research_summary>
## Summary

Phase 2 establishes the end-to-end authentication and candidate identity foundation for AROVIA. The system implements a defense-in-depth security model:
1. **Credential Hashing:** Salted `bcrypt` with cost factor 12 via `passlib.context.CryptContext`.
2. **Dual-Token Session Architecture:** Stateless 15-minute access tokens signed with `HS256` (`PyJWT`), paired with 7-day `HttpOnly`, `Secure`, `SameSite=Lax` refresh cookies path-scoped to `/api/v1/auth`.
3. **Single-Use Token Rotation:** Every refresh invalidates the used refresh token and persists the SHA-256 hash of the replacement token.
4. **Google OAuth Verification:** Verified via `google.oauth2.id_token.verify_oauth2_token()` validating Google's public certificates, client ID audience, and subject claims.
5. **Layered Brute-Force Protection:** SlowAPI IP limits (10 req/min on `/login`), progressive 2-second sleep delay after 3 failures, and 15-minute temporary lockout after 5 consecutive failures without permanently locking accounts.
6. **Password Recovery:** 32-byte cryptographically secure reset tokens (`secrets.token_urlsafe(32)`) hashed with SHA-256, expired after 15 minutes, with development console link logging.

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

**Installation Additions (backend/requirements.txt):**
```text
passlib[bcrypt]>=1.7.4
bcrypt>=4.0.0
PyJWT>=2.9.0
google-auth>=2.30.0
slowapi>=0.1.9
```

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

### 2. SQLAlchemy 2.0 User & Auth Models (`backend/app/models/user.py`)
```python
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, CommonModelMixin

class User(CommonModelMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    target_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lockout_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    oauth_identities: Mapped[List["UserOAuthIdentity"]] = relationship(
        "UserOAuthIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )

class UserOAuthIdentity(CommonModelMixin, Base):
    __tablename__ = "user_oauth_identities"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="google")
    provider_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    provider_email: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="oauth_identities")

class RefreshToken(CommonModelMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

class PasswordResetToken(CommonModelMixin, Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="reset_tokens")
```

### 3. FastAPI Dependencies & Route Guards (`backend/app/api/deps.py`)
```python
from typing import Annotated
import jwt
from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import UnauthorizedError, NotFoundError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)

async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[Optional[str], Depends(reusable_oauth2)],
) -> User:
    if not token:
        raise UnauthorizedError(detail="Not authenticated", error_code="NOT_AUTHENTICATED")
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise UnauthorizedError(detail="Invalid token", error_code="INVALID_TOKEN")
    except jwt.PyJWTError:
        raise UnauthorizedError(detail="Token expired or invalid", error_code="INVALID_TOKEN")

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(detail="User not found or inactive", error_code="USER_NOT_FOUND")
    return user
```

---

</architecture_patterns>

<validation_architecture>
## Validation Architecture

### Automated Verification Strategy
1. **Unit Tests (`tests/test_auth_security.py`):**
   - Password hashing, verification, and timing consistency.
   - Access token creation, expiration bounds, and claim validation.
   - High-entropy reset token generation and SHA-256 hash matching.
2. **Endpoint Integration Tests (`tests/test_auth_endpoints.py`):**
   - Registration flow (`POST /api/v1/auth/register`):
     - Valid credentials $\rightarrow$ 201 Created + access token + HttpOnly cookie.
     - Duplicate email $\rightarrow$ 409 Conflict.
     - Password $< 12$ characters $\rightarrow$ 422 Unprocessable Entity.
     - Common weak password $\rightarrow$ 422 Unprocessable Entity.
   - Login flow (`POST /api/v1/auth/login`):
     - Valid credentials $\rightarrow$ 200 OK + access token + HttpOnly cookie + failure counter reset.
     - Invalid password $\rightarrow$ 401 Unauthorized + failure counter increment.
     - 5 consecutive failures $\rightarrow$ 15-minute temporary lockout.
   - Silent refresh flow (`POST /api/v1/auth/refresh`):
     - Valid refresh cookie $\rightarrow$ 200 OK + new access token + rotated refresh cookie.
     - Replaying old revoked refresh token $\rightarrow$ 401 Unauthorized.
   - Google Sign-In (`POST /api/v1/auth/google`):
     - Valid mock Google ID token $\rightarrow$ 200 OK + user account.
     - Collision with existing local account $\rightarrow$ 400 Bad Request (`ACCOUNT_LINKING_REQUIRED`).
   - Profile management (`GET /api/v1/auth/me`, `PUT /api/v1/auth/me`):
     - Authenticated request $\rightarrow$ 200 OK + user profile DTO.
     - Unauthorized request $\rightarrow$ 401 Unauthorized.
   - Password reset flow (`POST /password-reset/request`, `POST /password-reset/confirm`):
     - Request reset $\rightarrow$ 200 OK + console logger URL.
     - Confirm with valid token $\rightarrow$ 200 OK + password updated + token marked used.
     - Confirm with expired/used token $\rightarrow$ 400 Bad Request.

---

</validation_architecture>

## Validation Architecture

Nyquist validation requirements for Phase 02:

| Test Category | Target File | Verification Criteria |
|---|---|---|
| Security Unit Tests | `backend/tests/test_auth_security.py` | Bcrypt hashing cost 12, JWT encode/decode, SHA-256 token hashing |
| Registration Tests | `backend/tests/test_auth_register.py` | 201 on success, 409 duplicate email, 422 weak/short password |
| Login & Rate Limit Tests | `backend/tests/test_auth_login.py` | 200 on success, 401 on bad password, 15-min lockout on 5 failures |
| Token Refresh Rotation Tests | `backend/tests/test_auth_refresh.py` | Cookie extraction, token rotation, rejection of revoked tokens |
| Profile Endpoint Tests | `backend/tests/test_auth_profile.py` | GET/PUT /api/v1/auth/me with Bearer auth, validation of seniority |
| Password Reset Tests | `backend/tests/test_auth_reset.py` | Request reset, console link logging, confirm with SHA-256 token verification |
