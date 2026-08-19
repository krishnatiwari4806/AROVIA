"""Unit tests for Gemini Adaptive AI Engine (Phase 5 Plan 01)."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.services.gemini_service import GeminiService


@pytest.mark.asyncio
async def test_gemini_service_generate_initial_question_success():
    """Test generating initial interview question with structured response."""
    service = GeminiService(api_key="mock-key")

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = """{
        "question_text": "Could you walk me through the architecture of a high-throughput microservices system you worked on in Python?",
        "ideal_answer": "Expected explanation of ASGI frameworks, message queues (Kafka/RabbitMQ), caching layers, database indexing, and graceful error recovery.",
        "primary_concept": "Microservices Architecture & Concurrency"
    }"""

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_gemini_response
    )

    with patch.object(service, "_client", mock_client):
        result = await service.generate_initial_question(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="Technical Core",
            focus_skills=["Python", "FastAPI", "PostgreSQL"],
            parsed_jd_data={"required_skills": ["AsyncIO", "PostgreSQL"]},
            resume_data={"skills": ["Python", "Docker"]},
        )

        assert isinstance(result, GeneratedQuestion)
        assert "microservices" in result.question_text.lower()
        assert "Microservices Architecture" in result.primary_concept
        assert len(result.ideal_answer) > 20


@pytest.mark.asyncio
async def test_gemini_service_generate_initial_question_fallback():
    """Test fallback question when AI service generates an error."""
    service = GeminiService(api_key="mock-key")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("API connection timeout")
    )

    with patch.object(service, "_client", mock_client):
        result = await service.generate_initial_question(
            target_role="DevOps Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
        )

        assert isinstance(result, GeneratedQuestion)
        assert "DevOps Engineer" in result.question_text
        assert result.primary_concept == "System Architecture & Project Walkthrough"


@pytest.mark.asyncio
async def test_gemini_service_evaluate_and_generate_next_turn_follow_up():
    """Test adaptive follow-up probing decision when answer lacks depth."""
    service = GeminiService(api_key="mock-key")

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = """{
        "is_follow_up": true,
        "follow_up_reasoning": "Candidate mentioned using Redis for caching but did not explain cache invalidation or stampede mitigation strategies.",
        "question_text": "You mentioned Redis caching; how specifically do you handle cache invalidation and prevent cache stampede under heavy load?",
        "ideal_answer": "Should discuss TTL jitter, mutex/distributed locks, probabilistic early expiration, and cache-aside vs write-through trade-offs.",
        "primary_concept": "Cache Invalidation & High Concurrency",
        "is_interview_complete": false
    }"""

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_gemini_response
    )

    with patch.object(service, "_client", mock_client):
        decision = await service.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="Technical Core",
            focus_skills=["Redis", "PostgreSQL"],
            current_turn_index=0,
            remaining_core_questions=5,
            remaining_followup_budget=3,
            prior_turn_was_followup=False,
            previous_question="How do you architect caching?",
            candidate_answer="We just put Redis in front of the database to make it fast.",
            transcript_history=[],
        )

        assert isinstance(decision, NextTurnDecision)
        assert decision.is_follow_up is True
        assert "Redis" in decision.question_text
        assert "stampede" in decision.follow_up_reasoning.lower()
        assert decision.is_interview_complete is False


@pytest.mark.asyncio
async def test_gemini_service_evaluate_and_generate_next_turn_advance_core():
    """Test advancing to next core question when answer was sufficient or follow-up not warranted."""
    service = GeminiService(api_key="mock-key")

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = """{
        "is_follow_up": false,
        "follow_up_reasoning": "Answer was thorough and covered key distributed locking concepts.",
        "question_text": "Let us discuss data persistence. How do you design database migration strategies with zero downtime for schema modifications?",
        "ideal_answer": "Expand-and-contract pattern, backward-compatible column additions, dual writing, and phased deprecation.",
        "primary_concept": "Zero-Downtime Database Migrations",
        "is_interview_complete": false
    }"""

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_gemini_response
    )

    with patch.object(service, "_client", mock_client):
        decision = await service.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="Technical Core",
            focus_skills=["PostgreSQL"],
            current_turn_index=1,
            remaining_core_questions=4,
            remaining_followup_budget=3,
            prior_turn_was_followup=True,  # Prior was follow-up -> must advance
            previous_question="How do you handle cache invalidation?",
            candidate_answer="We use Redis with distributed locks and TTL jitter to prevent stampedes.",
            transcript_history=[],
        )

        assert isinstance(decision, NextTurnDecision)
        assert decision.is_follow_up is False
        assert "migration" in decision.question_text.lower()
        assert decision.is_interview_complete is False


@pytest.mark.asyncio
async def test_gemini_service_evaluate_and_generate_next_turn_completion():
    """Test session completion decision when core questions are exhausted."""
    service = GeminiService(api_key="mock-key")

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = """{
        "is_follow_up": false,
        "follow_up_reasoning": null,
        "question_text": null,
        "ideal_answer": null,
        "primary_concept": null,
        "is_interview_complete": true
    }"""

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_gemini_response
    )

    with patch.object(service, "_client", mock_client):
        decision = await service.evaluate_and_generate_next_turn(
            target_role="Frontend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["React"],
            current_turn_index=5,
            remaining_core_questions=0,
            remaining_followup_budget=0,
            prior_turn_was_followup=False,
            previous_question="How does React reconcile virtual DOM?",
            candidate_answer="React uses the Fiber architecture with work-in-progress trees and double buffering.",
            transcript_history=[],
        )

        assert isinstance(decision, NextTurnDecision)
        assert decision.is_interview_complete is True
        assert decision.question_text is None
