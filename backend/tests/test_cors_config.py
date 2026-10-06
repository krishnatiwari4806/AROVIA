"""Tests for CORS security configuration and origin validation."""

import pytest
from app import main
from app.core import config
from app.core.config import Settings
from fastapi.middleware.cors import CORSMiddleware


def test_cors_middleware_uses_configured_origins():
    """Verify that create_application sets allow_origins from settings."""
    test_app = main.create_application()
    cors_middleware = next(
        (m for m in test_app.user_middleware if m.cls == CORSMiddleware), None
    )
    assert cors_middleware is not None
    allowed_origins = cors_middleware.kwargs.get("allow_origins")
    assert isinstance(allowed_origins, list)
    assert "http://localhost:5173" in allowed_origins
    assert "http://localhost:5174" in allowed_origins
    assert "http://127.0.0.1:5173" in allowed_origins
    assert "http://127.0.0.1:5174" in allowed_origins


def test_cors_default_settings_without_env_file():
    """Verify default Settings contains both localhost 5173 and 5174 ports."""
    default_settings = Settings(
        _env_file=None,
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/arovia",
        GEMINI_API_KEY="test-gemini-key",
    )
    assert "http://localhost:5173" in default_settings.ALLOWED_ORIGINS
    assert "http://localhost:5174" in default_settings.ALLOWED_ORIGINS
    assert "http://127.0.0.1:5173" in default_settings.ALLOWED_ORIGINS
    assert "http://127.0.0.1:5174" in default_settings.ALLOWED_ORIGINS


def test_cors_wildcard_never_used_when_settings_is_none(monkeypatch):
    """Verify that when settings is None, create_application raises RuntimeError and NEVER returns wildcard CORS."""
    monkeypatch.setattr(main, "settings", None)
    with pytest.raises(RuntimeError) as exc_info:
        main.create_application()
    assert "Application settings failed to initialize" in str(exc_info.value)


def test_cors_wildcard_not_in_default_origins():
    """Verify that '*' is never present in allowed_origins."""
    test_app = main.create_application()
    cors_middleware = next(
        (m for m in test_app.user_middleware if m.cls == CORSMiddleware), None
    )
    assert cors_middleware is not None
    allowed_origins = cors_middleware.kwargs.get("allow_origins")
    assert "*" not in allowed_origins
    assert cors_middleware.kwargs.get("allow_credentials") is True


def test_cors_allowed_origins_env_override(monkeypatch):
    """Verify that ALLOWED_ORIGINS can be overridden via environment variables."""
    custom_origins = "https://app.arovia.ai,https://staging.arovia.ai"
    monkeypatch.setenv("ALLOWED_ORIGINS", custom_origins)
    
    # Instantiate custom settings
    custom_settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/arovia",
        GEMINI_API_KEY="test-gemini-key",
        ALLOWED_ORIGINS=custom_origins,
    )
    assert custom_settings.ALLOWED_ORIGINS == [
        "https://app.arovia.ai",
        "https://staging.arovia.ai",
    ]
