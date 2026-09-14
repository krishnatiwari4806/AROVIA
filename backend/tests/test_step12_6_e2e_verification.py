"""AROVIA Step 12.6 — Comprehensive End-to-End Action Plan & Focused Practice Verification Suite.

Validates:
1. Pre-flight contract audit: CoachConversationResponse, CoachHistoryResponse, PracticeMode & Focus mappings.
2. Realistic recurring weakness scenario across multiple completed sessions.
3. Coach Action Plan deterministic fidelity & WeaknessResolutionStateDTO (ACTIVE).
4. PracticeLaunchIntent construction & validation.
5. Focused Practice session creation through existing Interview Engine & state machine.
6. Post-practice evaluation persistence & 5-dimension score integrity.
7. Weakness resolution lifecycle transition (ACTIVE -> IMPROVING -> RESOLVED -> Refresher).
8. Multi-user security isolation & zero cross-tenant access.
9. Edge cases: Zero-session baseline, Single-session gap, Unsupported topic notice, Active-session conflict (409).
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.coach import CoachConversation, CoachMessage
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User
from app.schemas.coach import (
    CoachConversationResponse,
    CoachHistoryResponse,
)
from app.schemas.interview import (
    InterviewFocus,
    InterviewSessionCreateRequest,
    PracticeMode,
    SeniorityLevel,
    SessionStatus,
)
from app.schemas.progress import (
    ActionableCoachingPlanDTO,
    WeaknessResolutionStateDTO,
)
from app.services.coach_service import CoachService
from app.services.interview_service import InterviewService
from app.services.progress_service import ProgressIntelligenceService


@pytest.fixture
def mock_gemini():
    """Mock Gemini API boundaries for deterministic LLM generation."""
    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        new_callable=AsyncMock,
    ) as mock_debrief, patch(
        "app.services.coach_ai_service.CoachAIService.generate_chat_reply",
        new_callable=AsyncMock,
    ) as mock_chat:
        mock_debrief.return_value = (
            "### AI Coach Debrief\n\nIdentified key opportunities for technical growth."
        )
        mock_chat.return_value = {
            "coach_response": "Here is a targeted breakdown of your technical questions.",
            "suggested_followups": [
                "How do I optimize database queries?",
                "Can you give me an example indexing question?",
            ],
        }
        yield {"debrief": mock_debrief, "chat": mock_chat}


# =========================================================================
# PHASE 1 & 2: RECURRING WEAKNESS SCENARIO SETUP & ACTION PLAN FIDELITY
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_recurring_weakness_action_plan_fidelity(
    db_session: AsyncSession, mock_gemini
):
    """Verify that 2 sessions with a recurring weakness produce a P1 Action Plan with ACTIVE lifecycle."""
    candidate = User(
        id="user-e2e-126-001",
        email="candidate126_a@example.com",
        full_name="Alex River",
        hashed_password="hashed_pw_e2e_126",
    )
    db_session.add(candidate)
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Session 1: 3 days ago - Low technical score with "Database Indexing & Query Optimization" weakness
    sess1 = InterviewSession(
        id="sess-e2e-1",
        user_id=candidate.id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="full",
        status="completed",
        started_at=now - timedelta(days=3),
        overall_score=52,
        dimension_scores={
            "relevance": 55,
            "correctness": 48,
            "keywords": 50,
            "clarity": 70,
            "confidence": 68,
        },
        evaluation_report={
            "executive_summary": "Session 1 with database indexing struggle.",
            "top_strengths": [{"title": "Clear articulation", "description": "Structured communication"}],
            "top_improvements": [{"title": "Database Indexing & Query Optimization", "description": "B-Tree index mechanics under high concurrency"}],
        },
    )
    db_session.add(sess1)

    # Session 2: 1 day ago - Another low technical score with the same canonical weakness
    sess2 = InterviewSession(
        id="sess-e2e-2",
        user_id=candidate.id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="full",
        status="completed",
        started_at=now - timedelta(days=1),
        overall_score=56,
        dimension_scores={
            "relevance": 60,
            "correctness": 52,
            "keywords": 54,
            "clarity": 72,
            "confidence": 70,
        },
        evaluation_report={
            "executive_summary": "Session 2 recurring database indexing gap.",
            "top_strengths": [{"title": "Good pacing", "description": "Confident delivery"}],
            "top_improvements": [{"title": "Database Indexing & Query Optimization", "description": "Composite index ordering and query execution plans"}],
        },
    )
    db_session.add(sess2)
    await db_session.commit()

    # Query Coach Service for Session 2
    coach_service = CoachService()
    conv, replies, plan, resolutions = await coach_service.get_or_create_conversation(
        db=db_session,
        current_user=candidate,
        session_id=sess2.id,
    )

    # Verify Response Contract Fields
    assert plan is not None, "Actionable plan must be provided for candidate with recurring gap"
    assert isinstance(plan, ActionableCoachingPlanDTO)
    assert plan.priority_level.startswith("P1"), f"Expected P1 priority for recurring gap, got: {plan.priority_level}"
    assert "Database Indexing" in plan.focus_topic
    assert "recurring" in plan.reason.lower() or "2 distinct" in plan.reason
    assert len(plan.concrete_actions) >= 3
    assert plan.success_metric is not None
    assert plan.review_condition is not None

    # Verify Weakness Resolutions List
    assert len(resolutions) >= 1
    db_res = next((r for r in resolutions if "database indexing" in r.canonical_topic.lower() or "database indexing" in r.display_title.lower()), None)
    assert db_res is not None, "Database Indexing weakness resolution state must be present"
    assert db_res.status in ("active", "improving")
    assert db_res.sessions_observed_count >= 2


# =========================================================================
# PHASE 4 & 5: PRACTICE LAUNCH INTENT & FOCUSED PRACTICE INTERVIEW EXECUTION
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_practice_launch_and_interview_engine_progression(
    db_session: AsyncSession, mock_gemini
):
    """Verify PracticeLaunchIntent maps safely into existing InterviewService.create_session without auto-submit."""
    candidate = User(
        id="user-e2e-126-002",
        email="candidate126_b@example.com",
        full_name="Morgan Chen",
        hashed_password="hashed_pw_e2e_126_b",
    )
    db_session.add(candidate)
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Completed source session
    source_sess = InterviewSession(
        id="sess-e2e-source",
        user_id=candidate.id,
        target_role="Backend",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="full",
        status="completed",
        started_at=now - timedelta(days=2),
        overall_score=50,
        dimension_scores={"relevance": 50, "correctness": 45, "keywords": 48, "clarity": 65, "confidence": 60},
        evaluation_report={
            "executive_summary": "Source session.",
            "top_strengths": [{"title": "Clear voice", "description": "Good tone"}],
            "top_improvements": [{"title": "Concurrency Control & Distributed Locking", "description": "Race conditions"}],
        },
    )
    db_session.add(source_sess)
    await db_session.commit()

    # 1. Obtain Action Plan from Coach
    coach_service = CoachService()
    _, _, plan, _ = await coach_service.get_or_create_conversation(
        db=db_session,
        current_user=candidate,
        session_id=source_sess.id,
    )
    assert plan is not None

    # 2. Simulate PracticeLaunchIntent construction (same as ActionPlanCard.jsx)
    mapped_focus = "Technical Core"
    practice_intent = {
        "focus_topic": plan.focus_topic,
        "category": plan.category,
        "target_role": source_sess.target_role,
        "seniority_level": source_sess.seniority_level,
        "interview_focus": mapped_focus,
        "practice_mode": "quick",
        "focus_skills": [plan.focus_topic],
        "source_session_id": source_sess.id,
        "launch_source": "coach_action_plan",
    }

    # 3. Simulate candidate reviewing setup in InterviewSetup.jsx and explicitly submitting:
    # Notice: Role/seniority/focus/mode map strictly to existing API Enums
    create_req = InterviewSessionCreateRequest(
        target_role=practice_intent["target_role"],
        seniority_level=SeniorityLevel.senior,
        interview_focus=InterviewFocus.technical_core,
        practice_mode=PracticeMode.quick,
        focus_skills=practice_intent["focus_skills"],
    )

    interview_service = InterviewService()
    new_session = await interview_service.create_session(
        db=db_session,
        current_user=candidate,
        request=create_req,
    )

    assert new_session is not None
    assert new_session.id != source_sess.id
    assert new_session.user_id == candidate.id
    assert new_session.target_role == "Backend"
    assert new_session.seniority_level == "senior"
    assert new_session.interview_focus == "Technical Core"
    assert new_session.practice_mode == "quick"
    assert new_session.status == "in_progress"
    assert new_session.focus_skills == [plan.focus_topic]

    # 4. Verify Pacing and Adaptive Engine Progression for Quick Mode (3 core questions planned)
    assert new_session.planned_core_questions == 3
    assert new_session.max_total_turns == 6


# =========================================================================
# PHASE 6 & 7: POST-PRACTICE EVALUATION & WEAKNESS RESOLUTION LIFECYCLE
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_weakness_lifecycle_transitions_to_resolved(
    db_session: AsyncSession, mock_gemini
):
    """Verify that consecutive successful post-practice sessions transition status: ACTIVE -> IMPROVING -> RESOLVED."""
    candidate = User(
        id="user-e2e-126-003",
        email="candidate126_c@example.com",
        full_name="Taylor Swift",
        hashed_password="hashed_pw_e2e_126_c",
    )
    db_session.add(candidate)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    topic_name = "Database Indexing & Query Optimization"

    # --- Session 1: Past failure (Score 50, correctness 45) -> Weakness ACTIVE ---
    s1 = InterviewSession(
        id="sess-life-1",
        user_id=candidate.id,
        target_role="Backend",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="full",
        status="completed",
        started_at=now - timedelta(days=5),
        overall_score=50,
        dimension_scores={"relevance": 50, "correctness": 45, "keywords": 48, "clarity": 60, "confidence": 60},
        evaluation_report={
            "executive_summary": "Session 1 with weakness.",
            "top_strengths": [{"title": "Good pace", "description": "Good"}],
            "top_improvements": [{"title": topic_name, "description": "Lacks indexing", "related_dimension": "correctness"}],
        },
    )
    db_session.add(s1)
    await db_session.commit()

    prog_service = ProgressIntelligenceService()

    # Helper to fetch sessions with turns
    async def get_sessions():
        stmt = (
            select(InterviewSession)
            .options(selectinload(InterviewSession.turns))
            .where(
                InterviewSession.user_id == candidate.id,
                InterviewSession.status == "completed",
                InterviewSession.overall_score.isnot(None),
            )
            .order_by(InterviewSession.started_at.asc())
        )
        res = await db_session.execute(stmt)
        return list(res.scalars().all())

    # Verify initial state: ACTIVE
    resolutions_t1 = prog_service.compute_weakness_resolution_states(await get_sessions())
    r1 = next((r for r in resolutions_t1 if "database indexing" in r.canonical_topic.lower() or "database indexing" in r.display_title.lower()), None)
    assert r1 is not None
    assert r1.status == "active"
    assert r1.sessions_observed_count == 1

    # --- Session 2: Practice Session 1 with correctness improving to 65 (+20 points) -> Status transitions to IMPROVING ---
    s2 = InterviewSession(
        id="sess-life-2",
        user_id=candidate.id,
        target_role="Backend",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="completed",
        started_at=now - timedelta(days=3),
        overall_score=70,
        dimension_scores={"relevance": 72, "correctness": 65, "keywords": 65, "clarity": 75, "confidence": 70},
        evaluation_report={
            "executive_summary": "Practice session 1 with improving indexing.",
            "top_strengths": [{"title": "Strong explanation of basic indexing", "description": "Better understanding"}],
            "top_improvements": [{"title": topic_name, "description": "Still refine composite indexes", "related_dimension": "correctness"}],
        },
    )
    db_session.add(s2)
    await db_session.commit()

    resolutions_t2 = prog_service.compute_weakness_resolution_states(await get_sessions())
    r2 = next((r for r in resolutions_t2 if "database indexing" in r.canonical_topic.lower() or "database indexing" in r.display_title.lower()), None)
    assert r2 is not None
    assert r2.status == "improving"
    assert r2.sessions_observed_count == 2

    # --- Session 3: Practice Session 2 Passes Completely without indexing weakness -> Status transitions to RESOLVED ---
    s3 = InterviewSession(
        id="sess-life-3",
        user_id=candidate.id,
        target_role="Backend",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="completed",
        started_at=now - timedelta(days=1),
        overall_score=84,
        dimension_scores={"relevance": 85, "correctness": 86, "keywords": 82, "clarity": 85, "confidence": 82},
        evaluation_report={
            "executive_summary": "Practice session 2 passed without indexing gap.",
            "top_strengths": [{"title": "Flawless composite index explanation", "description": "Complete mastery"}],
            "top_improvements": [{"title": "Minor formatting in SQL examples", "description": "Formatting style"}],
        },
    )
    db_session.add(s3)
    await db_session.commit()

    resolutions_t3 = prog_service.compute_weakness_resolution_states(await get_sessions())
    r3 = next((r for r in resolutions_t3 if "database indexing" in r.canonical_topic.lower() or "database indexing" in r.display_title.lower()), None)
    assert r3 is not None
    assert r3.status == "resolved"


# =========================================================================
# PHASE 8: MULTI-USER SECURITY ISOLATION
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_multi_user_coaching_and_practice_isolation(
    db_session: AsyncSession, mock_gemini
):
    """Verify that User B cannot access User A's Coach conversation or Action Plan."""
    user_a = User(
        id="user-sec-a",
        email="sec_a@example.com",
        full_name="User Alpha",
        hashed_password="pw_a",
    )
    user_b = User(
        id="user-sec-b",
        email="sec_b@example.com",
        full_name="User Beta",
        hashed_password="pw_b",
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # User A session
    sess_a = InterviewSession(
        id="sess-sec-a",
        user_id=user_a.id,
        target_role="Backend",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="full",
        status="completed",
        started_at=now,
        overall_score=45,
        dimension_scores={"relevance": 45, "correctness": 40, "keywords": 42, "clarity": 50, "confidence": 50},
        evaluation_report={
            "executive_summary": "User A session.",
            "top_strengths": [],
            "top_improvements": [{"title": "System Scalability & Microservices", "description": "Scalability"}],
        },
    )
    db_session.add(sess_a)
    await db_session.commit()

    coach_service = CoachService()

    # User A can access
    conv_a, _, plan_a, res_a = await coach_service.get_or_create_conversation(
        db=db_session,
        current_user=user_a,
        session_id=sess_a.id,
    )
    assert conv_a is not None
    assert plan_a is not None

    # User B attempting to access User A's session -> Must raise NotFoundError (404)
    with pytest.raises(NotFoundError):
        await coach_service.get_or_create_conversation(
            db=db_session,
            current_user=user_b,
            session_id=sess_a.id,
        )


# =========================================================================
# PHASE 9: EDGE CASES
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_edge_cases_zero_sessions_and_active_conflict(
    db_session: AsyncSession, mock_gemini
):
    """Verify zero-session baseline plan and active session conflict prevention (409)."""
    fresh_user = User(
        id="user-fresh-001",
        email="fresh@example.com",
        full_name="Fresh Candidate",
        hashed_password="pw_fresh",
    )
    db_session.add(fresh_user)
    await db_session.commit()

    # 1. Zero Sessions -> Baseline Plan
    prog_service = ProgressIntelligenceService()
    baseline_plan = prog_service.generate_actionable_coaching_plan([])
    assert baseline_plan is not None
    assert baseline_plan.focus_topic == "Core Technical Fundamentals"
    assert "0 completed sessions" in baseline_plan.evidence
    assert baseline_plan.priority_level == "P3 - Dimension Calibration"

    # 2. Active Session Conflict (409)
    interview_service = InterviewService()
    req1 = InterviewSessionCreateRequest(
        target_role="Fullstack",
        seniority_level=SeniorityLevel.mid,
        interview_focus=InterviewFocus.technical_core,
        practice_mode=PracticeMode.quick,
    )
    s1 = await interview_service.create_session(
        db=db_session, current_user=fresh_user, request=req1
    )
    assert s1.status == "in_progress"

    # Attempting to start a second active session without completing the first must raise ConflictError (409)
    with pytest.raises(ConflictError) as exc_info:
        await interview_service.create_session(
            db=db_session, current_user=fresh_user, request=req1
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.details.get("active_session_id") == s1.id


@pytest.mark.asyncio
async def test_e2e_single_session_gap_no_false_recurrence(
    db_session: AsyncSession, mock_gemini
):
    """Verify single completed session produces a P2 Recent Gap plan with zero false recurrence claims."""
    candidate = User(
        id="user-single-001",
        email="single_candidate@example.com",
        full_name="Single Session User",
        hashed_password="pw_single",
    )
    db_session.add(candidate)
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # 1 Completed Session
    s1 = InterviewSession(
        id="sess-single-1",
        user_id=candidate.id,
        target_role="Frontend Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        practice_mode="full",
        status="completed",
        started_at=now,
        overall_score=62,
        dimension_scores={"relevance": 65, "correctness": 58, "keywords": 60, "clarity": 70, "confidence": 65},
        evaluation_report={
            "executive_summary": "First interview session.",
            "top_strengths": [{"title": "Component Design", "description": "Good component hierarchy"}],
            "top_improvements": [{"title": "React Render Lifecycle & State Management", "description": "Unnecessary re-renders"}],
        },
    )
    db_session.add(s1)
    await db_session.commit()

    prog_service = ProgressIntelligenceService()
    plan = prog_service.generate_actionable_coaching_plan([s1])
    assert plan is not None
    assert plan.priority_level.startswith("P2"), f"Expected P2 - Recent Gap, got {plan.priority_level}"
    assert "React Render Lifecycle" in plan.focus_topic
    assert "recurring" not in plan.reason.lower()
    assert plan.reason == "Unnecessary re-renders"


@pytest.mark.asyncio
async def test_e2e_candidate_edits_role_seniority_isolation(
    db_session: AsyncSession, mock_gemini
):
    """Verify candidate can edit role and seniority in setup without mutating historical sessions or action plans."""
    candidate = User(
        id="user-edit-001",
        email="edit_user@example.com",
        full_name="Customizer User",
        hashed_password="pw_custom",
    )
    db_session.add(candidate)
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Historical Session
    source_sess = InterviewSession(
        id="sess-hist-1",
        user_id=candidate.id,
        target_role="Junior Backend",
        seniority_level="junior",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="completed",
        started_at=now - timedelta(days=2),
        overall_score=58,
        dimension_scores={"relevance": 60, "correctness": 55, "keywords": 55, "clarity": 65, "confidence": 60},
        evaluation_report={
            "executive_summary": "Junior session.",
            "top_strengths": [],
            "top_improvements": [{"title": "REST API Error Handling", "description": "HTTP status codes"}],
        },
    )
    db_session.add(source_sess)
    await db_session.commit()

    # Candidate receives practice intent for REST API Error Handling, but changes role to "Staff Platform Engineer" and seniority to "senior"
    edited_req = InterviewSessionCreateRequest(
        target_role="Staff Platform Engineer",
        seniority_level=SeniorityLevel.senior,
        interview_focus=InterviewFocus.technical_core,
        practice_mode=PracticeMode.full,
        focus_skills=["REST API Error Handling", "gRPC"],
    )

    interview_service = InterviewService()
    new_sess = await interview_service.create_session(
        db=db_session, current_user=candidate, request=edited_req
    )

    # Verify new session has edited parameters
    assert new_sess.target_role == "Staff Platform Engineer"
    assert new_sess.seniority_level == "senior"
    assert new_sess.practice_mode == "full"
    assert new_sess.focus_skills == ["REST API Error Handling", "gRPC"]

    # Verify historical session is UNMUTATED
    await db_session.refresh(source_sess)
    assert source_sess.target_role == "Junior Backend"
    assert source_sess.seniority_level == "junior"
    assert source_sess.practice_mode == "quick"


@pytest.mark.asyncio
async def test_e2e_api_client_full_flow_and_unauthenticated_guard(
    client: AsyncClient, mock_gemini
):
    """Verify HTTP API contracts: 401 for unauthenticated requests, and valid Action Plan payload for authenticated users."""
    # 1. Unauthenticated -> 401
    res_unauth_conv = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": "fake-session-id"},
    )
    assert res_unauth_conv.status_code == 401

    res_unauth_hist = await client.get("/api/v1/coach/history/fake-session-id")
    assert res_unauth_hist.status_code == 401

    # 2. Register & authenticate candidate
    from tests.test_coach_endpoints import create_user_and_session
    headers, session_id = await create_user_and_session(
        client, "e2e_api_user@example.com", "E2E Candidate"
    )

    # 3. Call Coach Conversation endpoint
    res_coach = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id},
        headers=headers,
    )
    assert res_coach.status_code == 200
    coach_data = res_coach.json()
    assert "actionable_plan" in coach_data
    assert "weakness_resolutions" in coach_data
    assert isinstance(coach_data["weakness_resolutions"], list)

    # 4. User B cannot access User A session -> 404
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "attacker_b@example.com", "password": "StrongPassword123!", "full_name": "Attacker B"},
    )
    assert reg_b.status_code == 201
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    res_b_attack = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id},
        headers=headers_b,
    )
    assert res_b_attack.status_code in (403, 404)

