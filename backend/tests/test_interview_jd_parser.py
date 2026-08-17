"""Unit and mock tests for Job Description parsing and sanitization."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.gemini_service import GeminiService, ParsedJobDescription
from app.services.interview_service import sanitize_job_description


def test_sanitize_job_description():
    """Verify that null bytes and non-printable control characters are stripped."""
    assert sanitize_job_description(None) is None
    assert sanitize_job_description("   ") is None

    dirty_text = "Looking for\x00 a Senior\x08 Backend Engineer.\x1f\x7f Must know Python\nand SQL."
    cleaned = sanitize_job_description(dirty_text)
    assert cleaned == "Looking for a Senior Backend Engineer. Must know Python\nand SQL."
    assert "\x00" not in cleaned
    assert "\x08" not in cleaned
    assert "\x1f" not in cleaned
    assert "\x7f" not in cleaned


@pytest.mark.asyncio
async def test_gemini_service_parse_job_description_success():
    """Verify successful structured extraction of Job Description using GeminiService."""
    mock_parsed_json = """{
        "job_title": "Senior Backend Engineer",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "core_responsibilities": ["Design distributed APIs", "Maintain microservices"],
        "key_technologies": ["AWS", "Redis", "Kafka", "Kubernetes"],
        "experience_summary": "5+ years backend systems experience."
    }"""

    mock_response = MagicMock()
    mock_response.text = mock_parsed_json

    service = GeminiService(api_key="fake-test-key", model="gemini-2.5-flash")
    service._client = MagicMock()
    service._client.aio = MagicMock()
    service._client.aio.models = MagicMock()
    service._client.aio.models.generate_content = AsyncMock(
        return_value=mock_response
    )

    result = await service.parse_job_description(
        "Senior Backend Engineer position requiring Python, FastAPI, and AWS."
    )

    assert isinstance(result, ParsedJobDescription)
    assert result.job_title == "Senior Backend Engineer"
    assert "Python" in result.required_skills
    assert "FastAPI" in result.required_skills
    assert "Kafka" in result.key_technologies


@pytest.mark.asyncio
async def test_gemini_service_parse_job_description_fallback_on_failure():
    """Verify graceful fallback return when Gemini API is unreachable during JD extraction."""
    service = GeminiService(api_key="fake-test-key", model="gemini-2.5-flash")
    service._client = MagicMock()
    service._client.aio = MagicMock()
    service._client.aio.models = MagicMock()
    service._client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("AI API connection timed out")
    )

    # Should not raise 503; instead returns fallback ParsedJobDescription
    result = await service.parse_job_description("Raw job description text.")

    assert isinstance(result, ParsedJobDescription)
    assert result.job_title is None
    assert result.required_skills == []
    assert "fallback" in result.experience_summary.lower()
