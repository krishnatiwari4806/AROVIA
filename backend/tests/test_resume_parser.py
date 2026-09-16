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
async def test_gemini_service_successful_parsing_with_projects_and_work_history():
    """Verify GeminiService parses structured projects, tech stack, architecture, and work history."""
    service = GeminiService(api_key="mock_key", model="gemini-2.5-flash")

    mock_json_payload = (
        '{"skills": ["Python", "FastAPI", "PostgreSQL", "Kafka", "Docker", "Redis"], '
        '"experience_years": 5.0, '
        '"domains": ["Backend Engineering", "Distributed Systems"], '
        '"education": [{"institution": "IIT Bombay", "degree": "B.Tech Computer Science", "graduation_year": "2020"}], '
        '"summary": "Senior backend engineer with deep expertise in distributed event-driven systems.", '
        '"projects": ['
        '  {"title": "Real-Time Payment Gateway", '
        '   "description": "High-throughput payment settlement microservice processing 15k TPS.", '
        '   "technologies": ["Python", "FastAPI", "Kafka", "PostgreSQL", "Redis"], '
        '   "responsibilities": "Architected transaction state machine and idempotency deduplication layer.", '
        '   "architecture_details": "Event-driven architecture with outbox pattern and distributed 2PC locks.", '
        '   "challenges": "Resolving distributed deadlocks and race conditions during network partition failovers.", '
        '   "outcomes": "Reduced p99 settlement latency from 450ms to 65ms with zero double-charge incidents."}, '
        '  {"title": "Distributed Task Scheduler", '
        '   "description": "Cron scheduling service across 50+ nodes.", '
        '   "technologies": ["Go", "gRPC", "Raft"], '
        '   "responsibilities": "Implemented leader election and job dispatch.", '
        '   "architecture_details": null, '
        '   "challenges": null, '
        '   "outcomes": "Supported 1M daily scheduled jobs."}'
        '], '
        '"work_history": ['
        '  {"company": "Stripe India", '
        '   "role": "Senior Software Engineer", '
        '   "duration": "Jul 2022 - Present", '
        '   "responsibilities": ["Led core payment rail development", "Mentored 4 junior engineers"], '
        '   "technologies": ["Python", "Kafka", "PostgreSQL"], '
        '   "achievements": ["Scaled throughput by 300% for Black Friday traffic", "Maintained 99.999% SLA"]}, '
        '  {"company": "Razorpay", '
        '   "role": "Software Engineer", '
        '   "duration": "Aug 2020 - Jun 2022", '
        '   "responsibilities": ["Developed webhook delivery service"], '
        '   "technologies": ["Python", "Redis", "Celery"], '
        '   "achievements": ["Handled 50M daily webhooks"]}'
        ']}'
    )

    mock_response = MagicMock()
    mock_response.text = mock_json_payload

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response

        result = await service.parse_resume("Full resume text with projects and work history...")

        assert isinstance(result, ParsedResumeData)
        assert result.skills == ["Python", "FastAPI", "PostgreSQL", "Kafka", "Docker", "Redis"]
        assert result.experience_years == 5.0
        assert len(result.projects) == 2
        
        # Project 1 assertions
        p1 = result.projects[0]
        assert p1.title == "Real-Time Payment Gateway"
        assert "15k TPS" in p1.description
        assert "Kafka" in p1.technologies
        assert "outbox pattern" in p1.architecture_details
        assert "distributed deadlocks" in p1.challenges
        assert "Reduced p99 settlement latency" in p1.outcomes

        # Project 2 with null optional fields
        p2 = result.projects[1]
        assert p2.title == "Distributed Task Scheduler"
        assert p2.architecture_details is None
        assert p2.challenges is None
        assert p2.outcomes == "Supported 1M daily scheduled jobs."

        # Work history assertions
        assert len(result.work_history) == 2
        w1 = result.work_history[0]
        assert w1.company == "Stripe India"
        assert w1.role == "Senior Software Engineer"
        assert w1.duration == "Jul 2022 - Present"
        assert "Scaled throughput by 300%" in w1.achievements[0]


@pytest.mark.asyncio
async def test_gemini_service_handles_resume_without_projects_or_experience():
    """Verify GeminiService handles student or minimal resumes with empty projects and work history gracefully."""
    service = GeminiService(api_key="mock_key", model="gemini-2.5-flash")

    mock_json_payload = (
        '{"skills": ["C++", "Python", "Data Structures"], '
        '"experience_years": 0.0, '
        '"domains": ["Algorithms"], '
        '"education": [{"institution": "University of Delhi", "degree": "B.Sc Computer Science", "graduation_year": "2024"}], '
        '"summary": "Recent graduate focusing on core algorithm design and competitive programming.", '
        '"projects": [], '
        '"work_history": []}'
    )

    mock_response = MagicMock()
    mock_response.text = mock_json_payload

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response

        result = await service.parse_resume("Student resume without formal jobs or major projects...")

        assert isinstance(result, ParsedResumeData)
        assert result.skills == ["C++", "Python", "Data Structures"]
        assert result.experience_years == 0.0
        assert result.projects == []
        assert result.work_history == []


@pytest.mark.asyncio
async def test_gemini_service_retry_on_transient_failure():
    """Verify GeminiService retries once on transient error and succeeds on second attempt."""
    service = GeminiService(api_key="mock_key", model="gemini-2.5-flash")

    mock_json_payload = (
        '{"skills": ["Go", "Kubernetes"], "experience_years": 3.0, "domains": ["Cloud Infrastructure"], '
        '"education": [], "summary": "Cloud engineer.", "projects": [], "work_history": []}'
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
async def test_gemini_service_503_transient_retries_and_succeeds():
    """Verify GeminiService retries on 503 Service Unavailable and returns valid data on retry."""
    service = GeminiService(api_key="mock_key", model="gemini-2.5-flash")

    mock_json_payload = (
        '{"skills": ["Python", "FastAPI"], "experience_years": 4.0, "domains": ["Backend Systems"], '
        '"education": [], "summary": "Python engineer.", "projects": [], "work_history": []}'
    )
    mock_success_response = MagicMock()
    mock_success_response.text = mock_json_payload

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        from google.genai.errors import APIError
        err_503 = APIError(503, {"error": {"code": 503, "message": "This model is currently experiencing high demand.", "status": "UNAVAILABLE"}})
        mock_gen.side_effect = [err_503, mock_success_response]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service.parse_resume("Sample resume text...")

            assert result.skills == ["Python", "FastAPI"]
            assert mock_gen.call_count == 2
            assert mock_sleep.call_count == 1


@pytest.mark.asyncio
async def test_gemini_service_unrecoverable_failure_raises_503():
    """Verify GeminiService raises HTTP 503 AI_SERVICE_UNAVAILABLE with resume analysis terminology."""
    service = GeminiService(api_key="mock_key_secret_12345", model="gemini-2.5-flash")

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("503 Service Unavailable: High Demand")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(AppError) as exc_info:
                await service.parse_resume("Sample resume text...")

            assert exc_info.value.status_code == 503
            assert exc_info.value.error_code == "AI_SERVICE_UNAVAILABLE"
            assert exc_info.value.message == "AI resume analysis service is temporarily unavailable. Please retry shortly."
            assert "evaluation" not in exc_info.value.message.lower()
            assert "mock_key_secret_12345" not in exc_info.value.message
            assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_gemini_service_timeout_retries_and_raises_safe_error():
    """Verify GeminiService retries on TimeoutError and raises sanitized 503 without credential leak."""
    service = GeminiService(api_key="secret_api_key_abcxyz", model="gemini-2.5-flash")

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = TimeoutError("Request timed out after 30000ms")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(AppError) as exc_info:
                await service.parse_resume("Sample resume text...")

            assert exc_info.value.status_code == 503
            assert exc_info.value.error_code == "AI_SERVICE_UNAVAILABLE"
            assert exc_info.value.message == "AI resume analysis service is temporarily unavailable. Please retry shortly."
            assert "secret_api_key_abcxyz" not in exc_info.value.message
            assert "TimeoutError" not in exc_info.value.message
            assert mock_gen.call_count == 2
            assert mock_sleep.call_count == 1


@pytest.mark.asyncio
async def test_gemini_service_429_quota_exhausted_fails_fast_without_retry():
    """Verify 429 RESOURCE_EXHAUSTED fails fast with exactly ONE provider invocation and NO sleep retry."""
    service = GeminiService(api_key="secret_key_987654", model="gemini-3.6-flash")

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        from google.genai.errors import APIError
        quota_err = APIError(
            429,
            {"error": {"code": 429, "message": "RESOURCE_EXHAUSTED: Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests", "status": "RESOURCE_EXHAUSTED"}},
        )
        mock_gen.side_effect = quota_err

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(AppError) as exc_info:
                await service.parse_resume("Sample candidate resume text...")

            assert exc_info.value.status_code == 503
            assert exc_info.value.error_code == "AI_SERVICE_UNAVAILABLE"
            assert exc_info.value.message == "AI resume analysis service is temporarily unavailable. Please retry shortly."
            assert "secret_key_987654" not in exc_info.value.message
            assert "RESOURCE_EXHAUSTED" not in exc_info.value.message
            assert "quota" not in exc_info.value.message.lower()
            # Must make EXACTLY ONE call — no retry on exhausted quota
            assert mock_gen.call_count == 1
            assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_gemini_service_permanent_client_error_does_not_retry():
    """Verify non-transient 400/404 errors do not retry and map cleanly to sanitized AppError."""
    service = GeminiService(api_key="secret_key_111222", model="gemini-invalid")

    with patch.object(service.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        from google.genai.errors import APIError
        err_404 = APIError(404, {"error": {"code": 404, "message": "models/gemini-invalid is not found", "status": "NOT_FOUND"}})
        mock_gen.side_effect = err_404

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(AppError) as exc_info:
                await service.parse_resume("Sample candidate resume text...")

            assert exc_info.value.status_code == 503
            assert exc_info.value.error_code == "AI_SERVICE_UNAVAILABLE"
            assert exc_info.value.message == "AI resume analysis service is temporarily unavailable. Please retry shortly."
            assert "secret_key_111222" not in exc_info.value.message
            assert mock_gen.call_count == 1
            assert mock_sleep.call_count == 0


