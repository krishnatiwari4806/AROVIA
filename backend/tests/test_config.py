"""Tests for Pydantic Settings and configuration validation."""

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_valid_settings_creation():
    """Test that valid configuration passes validation without errors."""
    valid_data = {
        "SECRET_KEY": "a" * 32,
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/arovia",
        "GEMINI_API_KEY": "test-gemini-key-12345",
        "ALLOWED_ORIGINS": ["http://localhost:3000", "http://localhost:5173"],
    }
    app_settings = Settings(**valid_data)
    assert app_settings.SECRET_KEY == "a" * 32
    assert app_settings.API_V1_PREFIX == "/api/v1"
    assert app_settings.ENVIRONMENT in ["development", "testing"]
    assert "http://localhost:3000" in app_settings.ALLOWED_ORIGINS


def test_settings_missing_secret_key_raises_error(monkeypatch):
    """Test that omitting SECRET_KEY raises ValidationError."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/arovia",
            GEMINI_API_KEY="test-gemini-key",
            # SECRET_KEY omitted
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("SECRET_KEY",) for err in errors)


def test_settings_short_secret_key_raises_error(monkeypatch):
    """Test that SECRET_KEY with fewer than 32 characters raises ValidationError."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            SECRET_KEY="too-short",
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/arovia",
            GEMINI_API_KEY="test-gemini-key",
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("SECRET_KEY",) for err in errors)


def test_settings_missing_database_url_raises_error(monkeypatch):
    """Test that omitting DATABASE_URL raises ValidationError."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            SECRET_KEY="b" * 32,
            GEMINI_API_KEY="test-gemini-key",
            # DATABASE_URL omitted
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("DATABASE_URL",) for err in errors)


def test_settings_missing_gemini_api_key_raises_error(monkeypatch):
    """Test that omitting GEMINI_API_KEY raises ValidationError."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            SECRET_KEY="c" * 32,
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/arovia",
            # GEMINI_API_KEY omitted
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("GEMINI_API_KEY",) for err in errors)


def test_cors_origins_string_parsing():
    """Test parsing stringified CORS origins into list of strings."""
    app_settings = Settings(
        SECRET_KEY="d" * 32,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/arovia",
        GEMINI_API_KEY="test-gemini-key",
        ALLOWED_ORIGINS='["http://localhost:5173", "http://127.0.0.1:5173"]',
    )
    assert len(app_settings.ALLOWED_ORIGINS) == 2
    assert "http://localhost:5173" in app_settings.ALLOWED_ORIGINS
