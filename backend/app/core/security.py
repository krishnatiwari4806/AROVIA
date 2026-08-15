"""Cryptographic security utilities for password hashing, JWTs, and secure tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import settings

COMMON_PASSWORDS = {
    "password1234",
    "123456789012",
    "password123456",
    "qwertyuiopas",
    "admin12345678",
    "letmein123456",
    "welcome123456",
    "iloveyou123456",
    "passphrase1234",
    "testpassword123",
}


def is_common_password(password: str) -> bool:
    """Check if password matches easily guessable/compromised patterns."""
    return password.strip().lower() in COMMON_PASSWORDS


def hash_password(password: str) -> str:
    """Hash a plaintext password with salted bcrypt (cost factor 12)."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash in constant time."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Compute SHA-256 hexadecimal digest for storing refresh and reset tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a high-entropy URL-safe cryptographic token string."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    subject: str, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed JWT access token with 15-minute default expiration."""
    expire_delta = expires_delta or timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token signature, issuer, and expiration."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
