"""Unit tests for Gemini Adaptive AI Engine, Question Bank Integration, and Hardening (Step 5C)."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.services.gemini_service import GeminiService
from app.services.question_bank import (
    BACKEND_BANK,
    FRONTEND_BANK,
    get_competency_stages,
    get_fallback_question,
)


@pytest.mark.asyncio
async def test_gemini_service_generate_initial_question_success():
    """Test A / Test 6: Gemini success path returns a generated question."""
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
    """Test B: Gemini failure on Turn 0 triggers Question Bank fallback with role-specific Stage 0 question."""
    service = GeminiService(api_key="mock-key")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("API connection timeout")
    )

    with patch.object(service, "_client", mock_client):
        result = await service.generate_initial_question(
            target_role="DevOps / Cloud Engineer",
            seniority_level="junior",
            interview_focus="Technical Core",
        )

        assert isinstance(result, GeneratedQuestion)
        assert "Docker" in result.question_text or "container" in result.question_text.lower()
        assert "Container" in result.primary_concept or "Docker" in result.primary_concept


@pytest.mark.asyncio
async def test_gemini_fallback_no_static_caching_question():
    """Test C: Static repeated caching question is eliminated; role-calibrated questions are returned."""
    service = GeminiService(api_key="mock-key")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("Gemini quota exceeded")
    )

    with patch.object(service, "_client", mock_client):
        decision_fe = await service.evaluate_and_generate_next_turn(
            target_role="Frontend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["React"],
            current_turn_index=0,
            remaining_core_questions=3,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="Tell me about DOM events",
            candidate_answer="A detailed 50-word answer describing event delegation, bubbling, and stopPropagation mechanics across DOM trees.",
            transcript_history=[
                {"turn_index": 0, "question_text": "DOM", "candidate_answer": "ans", "is_follow_up": False}
            ],
        )

        assert isinstance(decision_fe, NextTurnDecision)
        assert decision_fe.is_follow_up is False
        assert "caching, database indexing" not in decision_fe.question_text.lower()
        assert (
            "Optimization" in decision_fe.primary_concept
            or "Web Vitals" in decision_fe.primary_concept
            or "Component" in decision_fe.primary_concept
        )


@pytest.mark.asyncio
async def test_gemini_fallback_advances_competency_stages():
    """Test D: Fallback questions advance through valid competency stages across turns."""
    service = GeminiService(api_key="mock-key")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("Service unavailable")
    )

    with patch.object(service, "_client", mock_client):
        # Turn 1 (1 completed core turn -> targets Stage 1)
        history_turn1 = [
            {"turn_index": 0, "question_text": "Q0", "candidate_answer": "A0", "is_follow_up": False}
        ]
        decision_stage1 = await service.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["Python"],
            current_turn_index=1,
            remaining_core_questions=3,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="Previous question",
            candidate_answer="Thorough technical explanation of layered architecture and separation of concerns across service layers.",
            transcript_history=history_turn1,
        )

        # Turn 2 (2 completed core turns -> targets Stage 2)
        history_turn2 = [
            {"turn_index": 0, "question_text": "Q0", "candidate_answer": "A0", "is_follow_up": False},
            {"turn_index": 1, "question_text": "Q1", "candidate_answer": "A1", "is_follow_up": False},
        ]
        decision_stage2 = await service.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["Python"],
            current_turn_index=2,
            remaining_core_questions=2,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="Previous question",
            candidate_answer="Thorough technical explanation of asynchronous event loops and non-blocking I/O.",
            transcript_history=history_turn2,
        )

        assert decision_stage1.question_text != decision_stage2.question_text
        assert decision_stage1.primary_concept != decision_stage2.primary_concept


@pytest.mark.asyncio
async def test_gemini_fallback_excludes_previously_used_question_ids():
    """Test E / Test 3: Excluded question IDs are not repeated during fallback."""
    service = GeminiService(api_key="mock-key")

    stages = get_competency_stages(role="backend-engineer", seniority="junior")
    first_q_id = stages[0].core_questions[0].id

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("LLM down")
    )

    with patch.object(service, "_client", mock_client):
        result = await service.generate_initial_question(
            target_role="Backend Engineer",
            seniority_level="junior",
            interview_focus="Technical Core",
            excluded_question_ids={first_q_id},
        )

        assert result.question_text != stages[0].core_questions[0].question_text


@pytest.mark.asyncio
async def test_gemini_fallback_followup_is_concept_specific():
    """Test F: Follow-up fallback on shallow answer is concept-specific to parent question."""
    service = GeminiService(api_key="mock-key")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("Rate limited")
    )

    with patch.object(service, "_client", mock_client):
        decision = await service.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="Technical Core",
            focus_skills=["Kafka"],
            current_turn_index=0,
            remaining_core_questions=4,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="How does Transactional Outbox work?",
            candidate_answer="We write to a table.",  # Very brief (5 words < 10)
            transcript_history=[
                {"turn_index": 0, "question_text": "How does Transactional Outbox work?", "candidate_answer": "We write to a table."}
            ],
        )

        assert decision.is_follow_up is True
        assert len(decision.question_text) > 10
        assert "underlying mechanics" in decision.follow_up_reasoning.lower() or "concise" in decision.follow_up_reasoning.lower() or "omitted" in decision.follow_up_reasoning.lower()


@pytest.mark.asyncio
async def test_gemini_empty_or_malformed_response_triggers_question_bank_fallback():
    """Test G: Empty or malformed LLM response triggers Question Bank fallback gracefully."""
    service = GeminiService(api_key="mock-key")

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "{ malformed json: true "

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=mock_gemini_response
    )

    with patch.object(service, "_client", mock_client):
        decision = await service.evaluate_and_generate_next_turn(
            target_role="Fullstack Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["React", "FastAPI"],
            current_turn_index=0,
            remaining_core_questions=3,
            remaining_followup_budget=1,
            prior_turn_was_followup=False,
            previous_question="Tell me about type safety",
            candidate_answer="We use TypeScript and Pydantic with generated OpenAPI client code.",
            transcript_history=[],
        )

        assert isinstance(decision, NextTurnDecision)
        assert decision.question_text is not None
        assert len(decision.question_text) > 10


@pytest.mark.asyncio
async def test_premature_completion_override_in_gemini_service():
    """Test 1: If Gemini attempts premature completion while remaining_core > 0, override with Question Bank fallback."""
    service = GeminiService(api_key="mock-key")

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = """{
        "is_follow_up": false,
        "follow_up_reasoning": "Completed early.",
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
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["Python"],
            current_turn_index=0,
            remaining_core_questions=3,  # 3 core questions remain!
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="Tell me about REST APIs",
            candidate_answer="REST uses HTTP verbs like GET, POST, PUT, DELETE for idempotent resource manipulation.",
            transcript_history=[
                {"turn_index": 0, "question_text": "REST", "candidate_answer": "ans", "is_follow_up": False}
            ],
        )

        # Must NOT complete prematurely! Must produce a valid next core question from Question Bank
        assert decision.is_interview_complete is False
        assert decision.question_text is not None
        assert len(decision.question_text) > 10
        assert decision.is_follow_up is False


@pytest.mark.asyncio
async def test_legitimate_completion_when_core_zero():
    """Test 4: When core questions are exhausted (remaining_core=0), completion is accepted."""
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
            remaining_core_questions=0,  # Zero core remaining
            remaining_followup_budget=0,
            prior_turn_was_followup=False,
            previous_question="How does React reconcile virtual DOM?",
            candidate_answer="React uses Fiber architecture with work-in-progress trees.",
            transcript_history=[],
        )

        assert isinstance(decision, NextTurnDecision)
        assert decision.is_interview_complete is True
        assert decision.question_text is None
