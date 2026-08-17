"""Unit tests for GeminiService structured resume parser using google-genai SDK."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import AppError
from app.schemas.resume import ParsedResumeData
from app.services.gemini_service import GeminiService


@pytest.mark.asyncio
async def test_gemini_service_successful_parsing():
    """Verify GeminiService successfully parses structured JSON output into ParsedResumeData."""
    service = GeminiService(api_key="mock_key", model="gemini-2.5-flash")

    mock_json_payload = (
        '{"skills": ["Python", "FastAPI", "PostgreSQL", "Docker"], '
        '"experience_years": 4.5, '
        '"domains": ["Backend Development", "Cloud Systems"], '
        '"education": [{"institution": "MIT", "degree": "B.S. Computer Science", "graduation_year": "2020"}], '
        '"summary": "Experienced backend engineer specializing in distributed async APIs."}'
    )

    mock_response = MagicMock()
    mock_response.text = mock_json_payload

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response

        result = await service.parse_resume("Sample raw resume text with skills and experience...")

        assert isinstance(result, ParsedResumeData)
        assert result.skills == ["Python", "FastAPI", "PostgreSQL", "Docker"]
        assert result.experience_years == 4.5
        assert "Backend Development" in result.domains
        assert len(result.education) == 1
        assert result.education[0].institution == "MIT"
        assert "Experienced backend engineer" in result.summary
        assert mock_gen.call_count == 1


@pytest.mark.asyncio
async def test_gemini_service_retry_on_transient_failure():
    """Verify GeminiService retries once on transient error and succeeds on second attempt."""
    service = GeminiService(api_key="mock_key", model="gemini-2.5-flash")

    mock_json_payload = (
        '{"skills": ["Go", "Kubernetes"], "experience_years": 3.0, "domains": ["Cloud Infrastructure"], '
        '"education": [], "summary": "Cloud engineer."}'
    )
    mock_success_response = MagicMock()
    mock_success_response.text = mock_json_payload

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        # First call fails with transient network error, second succeeds
        mock_gen.side_effect = [
            RuntimeError("Connection timeout"),
            mock_success_response,
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service.parse_resume("Sample resume text...")

            assert result.skills == ["Go", "Kubernetes"]
            assert result.experience_years == 3.0
            assert mock_gen.call_count == 2
            assert mock_sleep.call_count == 1


@pytest.mark.asyncio
async def test_gemini_service_unrecoverable_failure_raises_503():
    """Verify GeminiService raises HTTP 503 AI_SERVICE_UNAVAILABLE on permanent failure."""
    service = GeminiService(api_key="mock_key", model="gemini-2.5-flash")

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("Provider outage")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(AppError) as exc_info:
                await service.parse_resume("Sample resume text...")

            assert exc_info.value.status_code == 503
            assert exc_info.value.error_code == "AI_SERVICE_UNAVAILABLE"
            assert mock_gen.call_count == 2
