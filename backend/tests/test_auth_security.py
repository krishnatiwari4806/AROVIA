"""Unit tests for cryptographic security utilities."""

from datetime import timedelta
import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    hash_token,
    generate_secure_token,
    create_access_token,
    decode_access_token,
    is_common_password,
)


def test_password_hashing_and_verification():
    raw = "super-secret-passphrase-1234"
    hashed = hash_password(raw)

    assert hashed != raw
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong-password-here", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw, "") is False


def test_is_common_password():
    assert is_common_password("password123456") is True
    assert is_common_password("123456789012") is True
    assert is_common_password("PASSWORD123456") is True
    assert is_common_password("unique-safe-passphrase-for-interview") is False


def test_token_hashing_and_generation():
    token1 = generate_secure_token(32)
    assert len(token1) >= 40
    hashed1 = hash_token(token1)
    assert len(hashed1) == 64
    assert hashed1 == hash_token(token1)

    token2 = generate_secure_token(32)
    assert hash_token(token1) != hash_token(token2)


def test_create_and_decode_access_token():
    user_id = "test-user-uuid-123"
    token = create_access_token(subject=user_id)
    payload = decode_access_token(token)

    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert "exp" in payload


def test_expired_access_token_raises_error():
    user_id = "test-user-uuid-123"
    expired_token = create_access_token(
        subject=user_id, expires_delta=timedelta(seconds=-10)
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)
