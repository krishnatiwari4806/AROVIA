"""Backend integration and fidelity tests for Step 12.5: Coach Action Plan UI & Safe Practice Launch."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User
from app.services.coach_service import CoachService
from app.services.progress_service import ProgressIntelligenceService


@pytest.fixture
def mock_coach_ai():
    """Mock CoachAIService methods at the service boundary."""
    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        new_callable=AsyncMock,
    ) as mock_debrief, patch(
        "app.services.coach_ai_service.CoachAIService.generate_chat_reply",
        new_callable=AsyncMock,
    ) as mock_chat:
        mock_debrief.return_value = (
            "### AI Coach Debrief\n\nGreat systems analysis on database optimization!"
        )
        mock_chat.return_value = {
            "coach_response": "To improve your answer, discuss B-Tree indexing and query execution plans.",
            "suggested_followups": [
                "How do composite indexes work?",
                "Give me a model answer for Turn 1.",
            ],
        }
        yield {"debrief": mock_debrief, "chat": mock_chat}


import uuid

@pytest.fixture
async def sample_user_and_session(db_session: AsyncSession):
    """Create a sample user and interview session in test DB."""
    uid = f"user-{uuid.uuid4()}"
    user = User(
        id=uid,
        email=f"user_{uuid.uuid4()}@example.com",
        full_name="Alex ActionPlan",
        hashed_password="hashed_pw_test",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    session = InterviewSession(
        id=f"sess-{uuid.uuid4()}",
        user_id=user.id,
        target_role="Backend Systems Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="in_progress",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return user, session


@pytest.mark.asyncio
async def test_coach_conversation_response_carries_actionable_plan_and_resolutions(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_coach_ai,
):
    """Verify POST /api/v1/coach/conversation contains deterministic actionable_plan and weakness_resolutions."""
    from tests.test_coach_endpoints import create_user_and_session

    headers, session_id = await create_user_and_session(
        client, "action_plan_user_1@example.com", "Action Plan Candidate 1"
    )

    # 1. First session completed with lower correctness in database indexing
    res = await db_session.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    sess = res.scalar_one()
    sess.status = "completed"
    sess.overall_score = 72
    sess.dimension_scores = {
        "relevance": 75,
        "correctness": 65,
        "keywords": 70,
        "clarity": 80,
        "confidence": 70,
    }
    sess.evaluation_report = {
        "overall_score": 72,
        "strengths": ["Good communication structure"],
        "improvements": ["Database Indexing & Query Optimization"],
    }
    await db_session.commit()

    # Call /api/v1/coach/conversation
    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    assert conv_res.status_code == 200
    data = conv_res.json()

    # Verify structured action plan fields are present
    assert "actionable_plan" in data
    assert data["actionable_plan"] is not None
    plan = data["actionable_plan"]

    assert "focus_topic" in plan
    assert "category" in plan
    assert "priority_level" in plan
    assert "reason" in plan
    assert "evidence" in plan
    assert "practice_preset" in plan
    assert "concrete_actions" in plan
    assert isinstance(plan["concrete_actions"], list)
    assert len(plan["concrete_actions"]) >= 2
    assert "success_metric" in plan
    assert "review_condition" in plan

    # Verify weakness resolutions list is present
    assert "weakness_resolutions" in data
    assert isinstance(data["weakness_resolutions"], list)


@pytest.mark.asyncio
async def test_coach_history_response_carries_actionable_plan_and_resolutions(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_coach_ai,
):
    """Verify GET /api/v1/coach/history/{session_id} carries actionable_plan and weakness_resolutions."""
    from tests.test_coach_endpoints import create_user_and_session

    headers, session_id = await create_user_and_session(
        client, "action_plan_hist_user@example.com", "Action Plan Hist Candidate"
    )

    res = await db_session.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    sess = res.scalar_one()
    sess.status = "completed"
    sess.overall_score = 75
    sess.dimension_scores = {
        "relevance": 80,
        "correctness": 70,
        "keywords": 75,
        "clarity": 80,
        "confidence": 75,
    }
    sess.evaluation_report = {
        "overall_score": 75,
        "strengths": ["REST Design"],
        "improvements": ["Caching Mechanisms"],
    }
    await db_session.commit()

    # Initialize conversation first
    await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": False},
        headers=headers,
    )

    # Fetch history
    hist_res = await client.get(
        f"/api/v1/coach/history/{session_id}",
        headers=headers,
    )
    assert hist_res.status_code == 200
    hist_data = hist_res.json()

    assert "actionable_plan" in hist_data
    assert hist_data["actionable_plan"] is not None
    assert "weakness_resolutions" in hist_data
    assert isinstance(hist_data["weakness_resolutions"], list)


@pytest.mark.asyncio
async def test_zero_completed_sessions_returns_baseline_plan(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_coach_ai,
):
    """Verify candidate with 0 completed sessions receives baseline ActionableCoachingPlanDTO and weakness_resolutions=[]."""
    from tests.test_coach_endpoints import create_user_and_session

    headers, session_id = await create_user_and_session(
        client, "zero_sess_user@example.com", "Zero Sess Candidate"
    )

    # Note: Session is in_progress / not completed
    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": False},
        headers=headers,
    )
    assert conv_res.status_code == 200
    data = conv_res.json()

    assert data["actionable_plan"] is not None
    assert data["actionable_plan"]["focus_topic"] == "Core Technical Fundamentals"
    assert data["actionable_plan"]["evidence"] == "0 completed sessions in AROVIA database."
    assert data["weakness_resolutions"] == []


@pytest.mark.asyncio
async def test_action_plan_user_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_coach_ai,
):
    """Verify User B cannot view User A's action plan or weakness resolutions."""
    from tests.test_coach_endpoints import create_user_and_session

    headers_a, session_id_a = await create_user_and_session(
        client, "isolated_user_a@example.com", "User A"
    )
    headers_b, session_id_b = await create_user_and_session(
        client, "isolated_user_b@example.com", "User B"
    )

    # Set up session A with specific improvement
    res_a = await db_session.execute(
        select(InterviewSession).where(InterviewSession.id == session_id_a)
    )
    sess_a = res_a.scalar_one()
    sess_a.status = "completed"
    sess_a.overall_score = 65
    sess_a.dimension_scores = {
        "relevance": 70,
        "correctness": 60,
        "keywords": 65,
        "clarity": 70,
        "confidence": 60,
    }
    sess_a.evaluation_report = {
        "overall_score": 65,
        "strengths": ["Communication"],
        "improvements": ["Exclusive Secret Weakness of User A"],
    }
    await db_session.commit()

    # User A calls their coach conversation
    conv_res_a = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id_a, "auto_debrief": False},
        headers=headers_a,
    )
    assert conv_res_a.status_code == 200
    data_a = conv_res_a.json()
    assert data_a["actionable_plan"] is not None
    # User A has 1 completed session with scores, so their evidence is grounded in real evaluation data
    assert "0 completed sessions" not in data_a["actionable_plan"]["evidence"]

    # User B calls their own coach conversation
    conv_res_b = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id_b, "auto_debrief": False},
        headers=headers_b,
    )
    assert conv_res_b.status_code == 200
    data_b = conv_res_b.json()

    # User B has no completed sessions, must receive baseline plan
    assert data_b["actionable_plan"]["focus_topic"] == "Core Technical Fundamentals"
    assert data_b["actionable_plan"]["evidence"] == "0 completed sessions in AROVIA database."
    assert data_b["weakness_resolutions"] == []

    # User B attempting to access User A's session history gets 404
    hist_res = await client.get(
        f"/api/v1/coach/history/{session_id_a}",
        headers=headers_b,
    )
    assert hist_res.status_code == 404


@pytest.mark.asyncio
async def test_fidelity_values_match_progress_intelligence_service(
    db_session: AsyncSession,
    sample_user_and_session,
    mock_coach_ai,
):
    """Verify CoachService action plan values exactly match ProgressIntelligenceService deterministic calculations."""
    user, session = sample_user_and_session

    # Complete the session
    session.status = "completed"
    session.overall_score = 70
    session.dimension_scores = {
        "relevance": 72,
        "correctness": 60,
        "keywords": 68,
        "clarity": 75,
        "confidence": 65,
    }
    session.evaluation_report = {
        "overall_score": 70,
        "strengths": ["Clear code structure"],
        "improvements": ["Database Indexing & Query Optimization"],
    }
    await db_session.commit()

    coach_service = CoachService()
    progress_service = ProgressIntelligenceService()

    # Call CoachService
    conv, followups, plan_from_coach, resolutions_from_coach = (
        await coach_service.get_or_create_conversation(
            db=db_session,
            current_user=user,
            session_id=session.id,
            auto_debrief=False,
        )
    )

    # Call ProgressIntelligenceService directly
    plan_direct = progress_service.generate_actionable_coaching_plan([session])
    resolutions_direct = progress_service.compute_weakness_resolution_states([session])

    assert plan_from_coach is not None
    assert plan_direct is not None
    assert plan_from_coach.focus_topic == plan_direct.focus_topic
    assert plan_from_coach.category == plan_direct.category
    assert plan_from_coach.priority_level == plan_direct.priority_level
    assert plan_from_coach.reason == plan_direct.reason
    assert plan_from_coach.evidence == plan_direct.evidence
    assert plan_from_coach.practice_preset == plan_direct.practice_preset
    assert plan_from_coach.concrete_actions == plan_direct.concrete_actions
    assert plan_from_coach.success_metric == plan_direct.success_metric
    assert plan_from_coach.review_condition == plan_direct.review_condition

    assert len(resolutions_from_coach) == len(resolutions_direct)
    if resolutions_from_coach and resolutions_direct:
        assert resolutions_from_coach[0].status == resolutions_direct[0].status
        assert (
            resolutions_from_coach[0].canonical_topic
            == resolutions_direct[0].canonical_topic
        )
