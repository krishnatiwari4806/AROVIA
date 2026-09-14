"""Integration and Unit tests for Question Planner, Resume & JD Grounding, Adaptive Probing, and Language (Phase 3)."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.services.candidate_context import build_candidate_context
from app.services.gemini_service import (
    GeminiService,
    get_grounded_fallback_question,
    is_non_answer,
)
from app.services.question_planner import (
    QuestionIntent,
    QuestionPlanner,
    get_question_planner,
)


@pytest.fixture
def sample_candidate_context():
    """Build a rich sample CandidateContext with project, work history, and JD data."""
    resume_data = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Next.js", "Docker"],
        "experience_years": 3.0,
        "domains": ["Backend Systems"],
        "projects": [
            {
                "title": "CryptoTelemetry Engine",
                "description": "High-throughput live orderbook websocket streaming platform.",
                "technologies": ["Python", "FastAPI", "WebSockets", "Redis"],
                "architecture_details": "AsyncIO event loop with Redis pub/sub.",
            }
        ],
        "work_history": [
            {
                "company": "DataTech Solutions",
                "role": "Backend Engineer",
                "duration": "2022 - Present",
                "responsibilities": ["Maintained GraphQL gateway", "Refactored PostgreSQL indexing"],
                "technologies": ["Python", "GraphQL", "PostgreSQL"],
            }
        ],
    }
    parsed_jd = {
        "job_title": "Senior Backend Developer",
        "required_skills": ["Python", "PostgreSQL", "Kafka", "Kubernetes"],
        "core_responsibilities": ["Design distributed event-driven systems"],
    }
    return build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        preferred_language="en",
        resume_data=resume_data,
        parsed_jd_data=parsed_jd,
        introduction_response="Hi! I have worked extensively on websocket data streaming and async Python backend systems.",
    )


def test_question_planner_full_mode_arc(sample_candidate_context):
    """Test QuestionPlanner constructs an adaptive, candidate-grounded arc for 6 core questions."""
    planner = get_question_planner()
    
    # Core Q1 (Index 0): Should prioritize candidate project
    plan_q1 = planner.plan_next_question(
        context=sample_candidate_context,
        planned_core_questions=6,
        current_core_index=0,
    )
    assert plan_q1.intent == QuestionIntent.RESUME_PROJECT
    assert plan_q1.topic == "CryptoTelemetry Engine"
    assert "CryptoTelemetry Engine" in plan_q1.grounding_snippet

    # Core Q2 (Index 1): Should prioritize work history
    plan_q2 = planner.plan_next_question(
        context=sample_candidate_context,
        planned_core_questions=6,
        current_core_index=1,
        covered_topics=["CryptoTelemetry Engine"],
    )
    assert plan_q2.intent == QuestionIntent.WORK_EXPERIENCE
    assert plan_q2.topic == "DataTech Solutions"

    # Core Q4 (Index 3): Should probe missing JD skill (e.g. Kafka or Kubernetes)
    plan_q4 = planner.plan_next_question(
        context=sample_candidate_context,
        planned_core_questions=6,
        current_core_index=3,
        covered_topics=["CryptoTelemetry Engine", "DataTech Solutions"],
    )
    assert plan_q4.intent == QuestionIntent.JD_REQUIREMENT
    assert plan_q4.topic in ["Kafka", "Kubernetes"]


def test_question_planner_quick_mode_arc(sample_candidate_context):
    """Test QuestionPlanner constructs a condensed 3-question arc for Quick mode."""
    planner = get_question_planner()

    plan_q1 = planner.plan_next_question(
        context=sample_candidate_context,
        planned_core_questions=3,
        current_core_index=0,
    )
    assert plan_q1.intent == QuestionIntent.RESUME_PROJECT
    assert plan_q1.topic == "CryptoTelemetry Engine"

    plan_q2 = planner.plan_next_question(
        context=sample_candidate_context,
        planned_core_questions=3,
        current_core_index=1,
        covered_topics=["CryptoTelemetry Engine"],
    )
    assert plan_q2.intent in [QuestionIntent.JD_REQUIREMENT, QuestionIntent.WORK_EXPERIENCE, QuestionIntent.CORE_SKILL]

    plan_q3 = planner.plan_next_question(
        context=sample_candidate_context,
        planned_core_questions=3,
        current_core_index=2,
        covered_topics=["CryptoTelemetry Engine", plan_q2.topic],
    )
    assert plan_q3.intent == QuestionIntent.PRACTICAL_SCENARIO


def test_non_answer_detection():
    """Test detection of 'I don't know', 'pass', 'skip', and Hindi equivalents."""
    assert is_non_answer("I don't know") is True
    assert is_non_answer("i do not know about this") is True
    assert is_non_answer("Pass to the next question please") is True
    assert is_non_answer("Skip this") is True
    assert is_non_answer("No idea, I haven't worked with Kafka") is True
    assert is_non_answer("Mujhe nahi pata") is True
    assert is_non_answer("pata nahi") is True
    assert is_non_answer("") is True
    assert is_non_answer("   ") is True

    # Real answer should NOT be detected as non-answer
    assert is_non_answer(
        "I used Kafka with 3 partitions and a consumer group to process telemetry messages asynchronously."
    ) is False


def test_grounded_fallback_generation_multilingual(sample_candidate_context):
    """Test deterministic fallbacks generate candidate-grounded questions in EN, HI, and Hinglish."""
    planner = get_question_planner()
    plan_proj = planner.plan_next_question(
        context=sample_candidate_context,
        planned_core_questions=6,
        current_core_index=0,
    )

    # English
    q_en = get_grounded_fallback_question(
        context=sample_candidate_context, plan=plan_proj, language="en"
    )
    assert "CryptoTelemetry Engine" in q_en.question_text
    assert "architecture" in q_en.question_text.lower()

    # Hindi
    q_hi = get_grounded_fallback_question(
        context=sample_candidate_context, plan=plan_proj, language="hi"
    )
    assert "CryptoTelemetry Engine" in q_hi.question_text
    assert "project" in q_hi.question_text.lower() or "architecture" in q_hi.question_text.lower()

    # Hinglish
    q_hinglish = get_grounded_fallback_question(
        context=sample_candidate_context, plan=plan_proj, language="hinglish"
    )
    assert "CryptoTelemetry Engine" in q_hinglish.question_text
    assert "architecture" in q_hinglish.question_text.lower()


@pytest.mark.asyncio
async def test_adaptive_evaluator_skips_followup_on_dont_know(sample_candidate_context):
    """Test that when a candidate says 'I don't know', the evaluator does NOT generate a follow-up probe."""
    service = GeminiService(api_key="mock-key")

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("Trigger fallback")
    )

    with patch.object(service, "_client", mock_client):
        decision = await service.evaluate_and_generate_next_turn(
            target_role=sample_candidate_context.target_role,
            seniority_level=sample_candidate_context.seniority_level,
            interview_focus=sample_candidate_context.interview_focus,
            focus_skills=sample_candidate_context.skills,
            current_turn_index=1,
            remaining_core_questions=4,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="How do you configure Kafka consumer group partitions?",
            candidate_answer="I don't know, I have never used Kafka.",
            transcript_history=[
                {"turn_index": 0, "question_text": "Intro", "candidate_answer": "Hi", "is_follow_up": False},
                {"turn_index": 1, "question_text": "Kafka?", "candidate_answer": "I don't know", "is_follow_up": False},
            ],
            candidate_context=sample_candidate_context,
        )

        # Must NOT be a follow-up
        assert decision.is_follow_up is False
        assert decision.is_interview_complete is False
        assert decision.question_text is not None


@pytest.mark.asyncio
async def test_live_interview_turn_progression_with_project_grounding(
    client: AsyncClient,
):
    """Integration test: Register -> Create session -> Start Turn 0 -> Submit intro -> Core Q1 is grounded in project."""
    # 1. Register User
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "phase3_grounding@example.com",
            "password": "StrongPassword!123",
            "full_name": "Phase 3 Candidate",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload Resume with a structured project
    from app.schemas.resume import ParsedResumeData, ResumeProjectItem
    from tests.test_resume_upload import create_sample_pdf

    sample_pdf_bytes = create_sample_pdf(
        "John Doe. Experienced Software Engineer with Python, FastAPI, and Next.js. Projects: SkyTrack Flight Radar."
    )
    with patch(
        "app.services.resume_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
        return_value=ParsedResumeData(
            skills=["Python", "FastAPI", "WebSockets", "Redis"],
            experience_years=2.5,
            domains=["Backend"],
            projects=[
                ResumeProjectItem(
                    title="SkyTrack Flight Radar",
                    description="Live flight tracking telemetry engine.",
                    technologies=["Python", "WebSockets", "Redis"],
                )
            ],
            work_history=[],
        ),
    ):
        files = {
            "file": (
                "skytrack_resume.pdf",
                sample_pdf_bytes,
                "application/pdf",
            )
        }
        res_upload = await client.post(
            "/api/v1/resumes/upload", headers=headers, files=files
        )
        assert res_upload.status_code == 201

    # 3. Create Interview Session
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "full",
            "preferred_language": "en",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 4. Start Interview -> Turn 0 Introduction
    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_res.status_code == 200
    turn0 = start_res.json()
    assert turn0["turn_index"] == 0
    assert turn0["question_type"] == "introduction"
    assert turn0["interview_phase"] == "introduction"

    # 5. Submit Turn 0 Answer -> Generates Core Q1 (Grounded in SkyTrack Flight Radar)
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_gen:
        mock_gen.return_value = GeneratedQuestion(
            question_text="I noticed you built 'SkyTrack Flight Radar' using WebSockets and Redis. How did you manage high-frequency telemetry updates?",
            ideal_answer="Explanation of Redis pub/sub, non-blocking asyncio websocket channels, backpressure handling, and packet deduplication.",
            primary_concept="Live Telemetry Architecture",
        )

        submit_t0_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
            json={
                "candidate_answer": "Hi, I am a backend engineer. I recently built a live telemetry system called SkyTrack Flight Radar.",
                "turn_duration_sec": 25,
            },
            headers=headers,
        )
        assert submit_t0_res.status_code == 200
        t0_data = submit_t0_res.json()
        assert t0_data["is_interview_complete"] is False
        assert t0_data["current_core_question_index"] == 0
        assert t0_data["total_core_questions"] == 6
        assert t0_data["interview_phase"] == "core_question"

        turn1 = t0_data["next_turn"]
        assert turn1["turn_index"] == 1
        assert turn1["core_question_number"] == 1
        assert "SkyTrack Flight Radar" in turn1["question_text"]
