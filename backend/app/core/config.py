"""Application Configuration Module."""

import json
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings managed by Pydantic v2."""

    PROJECT_NAME: str = "AROVIA API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret key for cryptographic operations and JWT signing (min 32 characters).",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_CLIENT_ID: Optional[str] = None

    DATABASE_URL: str = Field(
        ...,
        description="Async database connection URL (e.g., postgresql+asyncpg://...)",
    )
    GEMINI_API_KEY: str = Field(
        ..., description="Google Gemini API key for LLM structured operations."
    )
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: list[str] | str) -> list[str]:
        """Parse ALLOWED_ORIGINS whether passed as a JSON list, comma-separated string, or Python list."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return [
                        item.strip().strip("'\"")
                        for item in value.strip("[]").split(",")
                        if item.strip()
                    ]
            return [item.strip() for item in value.split(",") if item.strip()]
        elif isinstance(value, (list, tuple, set)):
            return list(value)
        raise ValueError(f"Invalid CORS origins format: {value}")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


def get_settings() -> Settings:
    """Instantiate and return Settings singleton."""
    return Settings()


# Default singleton instance (loads from .env if present or raises if required fields are missing)
try:
    settings = get_settings()
except Exception:  # noqa: BLE001
    # Allow lazy instantiation in test environments with dependency overrides
    settings = None  # type: ignore[assignment]
