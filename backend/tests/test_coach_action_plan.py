"""Comprehensive Tests for Deterministic Coaching Evidence Model, Weakness Resolution Engine, and Action Plan Generation (Step 12.2R Hardening).

Validates:
1. Service-Level Action Plan Generation (generate_actionable_coaching_plan & get_user_coaching_plan).
2. Weakness Resolution Lifecycles:
   - ACTIVE (recurring weakness present without improvement evidence)
   - IMPROVING (frequency decreasing or dimension improving)
   - RESOLVED (weakness absent in subsequent completed sessions)
3. Related Dimension Safety:
   A. Confidently mapped topic via authoritative turn evidence
   B. Unmapped topic -> returns 'unknown'
   C. Ambiguous topic (tied dimension evidence) -> returns 'unknown'
   D. Topic resembling dimension name without authoritative evidence -> returns 'unknown' (no substring guessing)
4. Success Metric Criteria:
   - No arbitrary +5 threshold or magic numbers
5. Multi-User Isolation on Service Layer:
   - Isolated queries per user_id, zero cross-user leakage
6. In-Progress Sessions Ignored:
   - Only completed sessions with overall_score are factored in
7. Deterministic Repeatability & Action Assignment Nature.
8. Endpoint Removal Verification:
   - Confirms /api/v1/coach/action-plan route is removed (returns 404).
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User
from app.schemas.progress import (
    ActionableCoachingPlanDTO,
    CandidateCurrentStateDTO,
    CandidateLongitudinalStateDTO,
    WeaknessResolutionStateDTO,
)
from app.services.progress_service import ProgressIntelligenceService


async def create_user_with_token(
    client: AsyncClient, email: str, full_name: str, password: str = "StrongPassword123!"
) -> tuple[dict[str, str], str]:
    """Helper to register user and return auth headers and user ID."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


# ==============================================================================
# 1. BASELINE & SINGLE SESSION COACHING PLAN
# ==============================================================================

@pytest.mark.asyncio
async def test_single_session_baseline_plan():
    """Requirement: Single completed session produces valid baseline state and coaching plan."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="sess-base-1",
        user_id="user-base",
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        status="completed",
        overall_score=78,
        dimension_scores={"relevance": 82, "correctness": 75, "keywords": 80, "clarity": 85, "confidence": 76},
        evaluation_report={
            "top_improvements": [
                {
                    "title": "State Management",
                    "description": "Evaluate Redux Toolkit selector memoization.",
                    "actionable_recommendation": "Review createSelector mechanics.",
                }
            ],
            "top_strengths": [{"title": "API Design", "description": "RESTful semantics."}],
        },
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )

    # 1. Candidate Current State
    current_state = service.compute_candidate_current_state([s1])
    assert current_state.latest_overall_score == 78
    assert current_state.latest_dimension_scores["correctness"] == 75
    assert current_state.latest_strengths == ["API Design"]
    assert current_state.latest_improvements == ["State Management"]

    # 2. Candidate Longitudinal State
    long_state = service.compute_candidate_longitudinal_state([s1])
    assert long_state.total_completed_interviews == 1
    assert long_state.overall_score_trajectory == [78]
    assert long_state.overall_direction == "Baseline"
    assert len(long_state.recurring_weaknesses) == 0

    # 3. Weakness Resolution State
    res_states = service.compute_weakness_resolution_states([s1])
    assert len(res_states) == 1
    assert res_states[0].display_title == "State Management"
    assert res_states[0].sessions_observed_count == 1
    assert res_states[0].status == "active"
    assert res_states[0].frequency_is_decreasing is False

    # 4. Action Plan Generation
    plan = service.generate_actionable_coaching_plan([s1])
    assert isinstance(plan, ActionableCoachingPlanDTO)
    assert plan.focus_topic == "State Management"
    assert plan.priority_level == "P2 - Recent Gap"
    assert plan.category == "Technical Core"
    assert len(plan.concrete_actions) >= 2
    assert "State Management" in plan.practice_preset["topic"]
    assert plan.practice_preset["focus"] == "Technical Core"
    assert "not flagged as a top improvement" in plan.success_metric


# ==============================================================================
# 2. WEAKNESS LIFECYCLE: ACTIVE, IMPROVING, RESOLVED
# ==============================================================================

@pytest.mark.asyncio
async def test_weakness_lifecycle_improving_via_dimension_score():
    """Requirement: Weakness present in multiple sessions is 'improving' when dimension score increases > 2."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="sess-imp-1",
        user_id="user-imp",
        target_role="Backend Engineer",
        status="completed",
        overall_score=60,
        dimension_scores={"correctness": 50},
        evaluation_report={
            "top_improvements": [
                {"title": "Database Indexing", "related_dimension": "correctness"}
            ]
        },
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="sess-imp-2",
        user_id="user-imp",
        target_role="Backend Engineer",
        status="completed",
        overall_score=72,
        dimension_scores={"correctness": 68},
        evaluation_report={
            "top_improvements": [
                {"title": "Database Indexing Strategies", "related_dimension": "correctness"}
            ]
        },
        started_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    assert len(res_states) == 1
    w = res_states[0]
    assert w.display_title == "Database Indexing"
    assert w.sessions_observed_count == 2
    assert w.first_detected_date == "2026-08-01"
    assert w.latest_detected_date == "2026-08-05"
    assert w.related_dimension == "correctness"
    assert w.related_dimension_score_progression == [50, 68]
    assert w.status == "improving"

    plan = service.generate_actionable_coaching_plan([s1, s2])
    assert plan.priority_level == "P1 - Critical Recurring"
    assert plan.focus_topic == "Database Indexing"
    assert "2 distinct completed" in plan.reason
    assert "50 → 68" in plan.evidence


@pytest.mark.asyncio
async def test_weakness_lifecycle_active_when_stable():
    """Requirement: Weakness present across sessions with no dimension improvement (<= 2 delta) remains 'active'."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="sess-act-1",
        status="completed",
        overall_score=55,
        dimension_scores={"correctness": 50},
        evaluation_report={
            "top_improvements": [
                {"title": "Cache Invalidation", "related_dimension": "correctness"}
            ]
        },
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="sess-act-2",
        status="completed",
        overall_score=56,
        dimension_scores={"correctness": 51},
        evaluation_report={
            "top_improvements": [
                {"title": "Cache Invalidation Strategies", "related_dimension": "correctness"}
            ]
        },
        started_at=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    w = res_states[0]
    assert w.display_title == "Cache Invalidation"
    assert w.sessions_observed_count == 2
    assert w.related_dimension == "correctness"
    assert w.related_dimension_score_progression == [50, 51]
    # Delta +1 <= 2 -> Active (stable, not improving)
    assert w.status == "active"
    assert w.frequency_is_decreasing is False


@pytest.mark.asyncio
async def test_weakness_lifecycle_resolved_when_absent_in_subsequent_session():
    """Requirement: Weakness observed in early sessions but absent in subsequent session is marked RESOLVED."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="sess-res-1",
        status="completed",
        overall_score=55,
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="sess-res-2",
        status="completed",
        overall_score=65,
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    s3 = InterviewSession(
        id="sess-res-3",
        status="completed",
        overall_score=85,
        focus_skills=["Database Indexing"],
        evaluation_report={"top_improvements": [{"title": "API Error Handling"}]},  # Absent & tested in focus_skills!
        started_at=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2, s3])
    db_idx = next(r for r in res_states if r.display_title == "Database Indexing")
    assert db_idx.sessions_observed_count == 2
    assert db_idx.status == "resolved"
    assert db_idx.frequency_is_decreasing is True


# ==============================================================================
# 3. RELATED DIMENSION SAFETY (A, B, C, D)
# ==============================================================================

@pytest.mark.asyncio
async def test_related_dimension_confidently_mapped_via_turn_evidence():
    """Requirement 3.A: Topic with clear authoritative turn evidence is mapped to the lowest dimension."""
    service = ProgressIntelligenceService()

    turn1 = InterviewQuestionTurn(
        id="t-conf-1",
        session_id="s-conf-1",
        turn_index=1,
        question_text="Explain B-Tree indexing.",
        evaluation_data={"primary_concept": "Database Indexing"},
        relevance_score=85,
        correctness_score=45,  # Lowest dimension
        keywords_score=80,
        clarity_score=75,
        confidence_score=70,
    )
    s1 = InterviewSession(
        id="s-conf-1",
        status="completed",
        overall_score=65,
        dimension_scores={"correctness": 45, "relevance": 85},
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s1.turns = [turn1]

    res_states = service.compute_weakness_resolution_states([s1])
    assert len(res_states) == 1
    assert res_states[0].display_title == "Database Indexing"
    assert res_states[0].related_dimension == "correctness"


@pytest.mark.asyncio
async def test_related_dimension_unmapped_returns_unknown():
    """Requirement 3.B: Topic without turn evidence or explicit dimension metadata safely returns 'unknown'."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s-unmapped-1",
        status="completed",
        overall_score=70,
        evaluation_report={"top_improvements": [{"title": "Proprietary Legacy Scripting Architecture"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1])
    assert len(res_states) == 1
    assert res_states[0].related_dimension == "unknown"
    assert res_states[0].related_dimension_score_progression == []


@pytest.mark.asyncio
async def test_related_dimension_ambiguous_evidence_returns_unknown():
    """Requirement 3.C: Conflicting/tied turn dimension evidence returns 'unknown' without fabricating a choice."""
    service = ProgressIntelligenceService()

    # Turn 1: Lowest is relevance (50)
    turn1 = InterviewQuestionTurn(
        id="t-amb-1",
        session_id="s-amb-1",
        turn_index=1,
        question_text="Explain REST principles.",
        evaluation_data={"primary_concept": "API Design"},
        relevance_score=50,
        correctness_score=80,
        keywords_score=80,
        clarity_score=80,
        confidence_score=80,
    )
    # Turn 2: Lowest is clarity (50) -> Tie between relevance and clarity (1 vote each)
    turn2 = InterviewQuestionTurn(
        id="t-amb-2",
        session_id="s-amb-1",
        turn_index=2,
        question_text="Explain API versioning.",
        evaluation_data={"primary_concept": "API Design"},
        relevance_score=80,
        correctness_score=80,
        keywords_score=80,
        clarity_score=50,
        confidence_score=80,
    )
    s1 = InterviewSession(
        id="s-amb-1",
        status="completed",
        overall_score=68,
        evaluation_report={"top_improvements": [{"title": "API Design"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s1.turns = [turn1, turn2]

    res_states = service.compute_weakness_resolution_states([s1])
    assert len(res_states) == 1
    # Tied evidence (1 relevance vs 1 clarity) -> ambiguous -> returns unknown
    assert res_states[0].related_dimension == "unknown"


@pytest.mark.asyncio
async def test_related_dimension_topic_resembling_dimension_name_without_evidence_returns_unknown():
    """Requirement 3.D: Topic containing dimension words without authoritative turn evidence returns 'unknown'."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s-resemble-1",
        status="completed",
        overall_score=70,
        evaluation_report={
            "top_improvements": [
                {"title": "Confidence in Distributed Systems"},
                {"title": "Relevance of Microservice Boundaries"},
                {"title": "Clarity in System Architecture"},
            ]
        },
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1])
    assert len(res_states) == 3
    for w in res_states:
        # Must not guess 'confidence', 'relevance', or 'clarity' from title alone
        assert w.related_dimension == "unknown"


# ==============================================================================
# 4. SUCCESS METRICS & NO ARBITRARY THRESHOLDS
# ==============================================================================

@pytest.mark.asyncio
async def test_success_metrics_grounded_in_measurable_future_verification():
    """Requirement 4: Success metrics use deterministic AROVIA verification rules without arbitrary +5 thresholds."""
    service = ProgressIntelligenceService()

    # P1 Metric
    m_p1 = service.generate_success_metric(
        focus_topic="Database Indexing", priority_level="P1 - Critical Recurring"
    )
    assert "Zero occurrences of Database Indexing as an evaluated gap" in m_p1
    assert ">= 5" not in m_p1
    assert "+5" not in m_p1

    # P2 Metric
    m_p2 = service.generate_success_metric(
        focus_topic="State Management", priority_level="P2 - Recent Gap"
    )
    assert "State Management is not flagged as a top improvement" in m_p2
    assert ">= 5" not in m_p2
    assert "+5" not in m_p2

    # P3 Metric
    m_p3 = service.generate_success_metric(
        focus_topic="Clarity Calibration", priority_level="P3 - Dimension Calibration", related_dimension="clarity"
    )
    assert "Demonstrate measurable score improvement in Clarity" in m_p3
    assert ">= 5" not in m_p3
    assert "+5" not in m_p3


# ==============================================================================
# 5. MULTI-USER ISOLATION ON SERVICE LAYER & IN-PROGRESS SESSIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_service_level_multi_user_isolation(db_session: AsyncSession):
    """Requirement 5: progress_service.get_user_coaching_plan isolates candidate data strictly by user_id."""
    service = ProgressIntelligenceService()

    user_a = User(id="usr-iso-a", email="user_a@test.com", hashed_password="pw", full_name="User A")
    user_b = User(id="usr-iso-b", email="user_b@test.com", hashed_password="pw", full_name="User B")
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # User A has 2 sessions with Database Indexing
    s_a1 = InterviewSession(
        id="s-iso-a1", user_id="usr-iso-a", target_role="Backend Engineer", seniority_level="senior",
        interview_focus="Technical Core", status="completed", overall_score=60,
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s_a2 = InterviewSession(
        id="s-iso-a2", user_id="usr-iso-a", target_role="Backend Engineer", seniority_level="senior",
        interview_focus="Technical Core", status="completed", overall_score=75,
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    # User B has 1 session with Cache Invalidation
    s_b1 = InterviewSession(
        id="s-iso-b1", user_id="usr-iso-b", target_role="Backend Engineer", seniority_level="senior",
        interview_focus="Technical Core", status="completed", overall_score=88,
        evaluation_report={"top_improvements": [{"title": "Cache Invalidation"}]},
        started_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    db_session.add_all([s_a1, s_a2, s_b1])
    await db_session.commit()

    # Query User A plan
    plan_a = await service.get_user_coaching_plan(db=db_session, current_user=user_a)
    assert plan_a.focus_topic == "Database Indexing"
    assert plan_a.priority_level == "P1 - Critical Recurring"
    assert "Cache Invalidation" not in plan_a.focus_topic

    # Query User B plan (Strictly isolated)
    plan_b = await service.get_user_coaching_plan(db=db_session, current_user=user_b)
    assert plan_b.focus_topic == "Cache Invalidation"
    assert plan_b.priority_level == "P2 - Recent Gap"
    assert "Database Indexing" not in plan_b.focus_topic


@pytest.mark.asyncio
async def test_in_progress_sessions_ignored_by_service():
    """Requirement: In-progress sessions are strictly ignored during state and plan calculations."""
    service = ProgressIntelligenceService()

    s_done = InterviewSession(
        id="s-done-1", status="completed", overall_score=80,
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s_inprog = InterviewSession(
        id="s-inprog-1", status="in_progress", overall_score=None,
        evaluation_report=None,
        started_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    current_state = service.compute_candidate_current_state([s_done, s_inprog])
    assert current_state.latest_overall_score == 80

    long_state = service.compute_candidate_longitudinal_state([s_done, s_inprog])
    assert long_state.total_completed_interviews == 1

    plan = service.generate_actionable_coaching_plan([s_done, s_inprog])
    assert plan.focus_topic == "Database Indexing"


# ==============================================================================
# 6. DETERMINISTIC REPEATABILITY & ACTION ASSIGNMENTS
# ==============================================================================

@pytest.mark.asyncio
async def test_deterministic_repeatability():
    """Requirement: Identical session inputs produce 100% byte-for-byte identical DTO outputs."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s-rep-1", status="completed", overall_score=75,
        evaluation_report={"top_improvements": [{"title": "Cache Invalidation"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="s-rep-2", status="completed", overall_score=80,
        evaluation_report={"top_improvements": [{"title": "Cache Invalidation"}]},
        started_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    plan1 = service.generate_actionable_coaching_plan([s1, s2])
    plan2 = service.generate_actionable_coaching_plan([s1, s2])

    assert plan1.model_dump() == plan2.model_dump()


@pytest.mark.asyncio
async def test_concrete_actions_are_assignments_never_marked_completed():
    """Requirement: Concrete actions are actionable instructions, never claiming prior completion."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s-act-assign", status="completed", overall_score=80,
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    plan = service.generate_actionable_coaching_plan([s1])
    for action in plan.concrete_actions:
        assert not action.startswith("Completed")
        assert not action.startswith("Finished")
        assert not action.startswith("Done")


# ==============================================================================
# 7. ROUTE REMOVAL VERIFICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_action_plan_rest_endpoint_is_removed(client: AsyncClient):
    """Requirement: Verifies GET /api/v1/coach/action-plan is removed and returns 404/405."""
    headers, _ = await create_user_with_token(client, "alice_route@example.com", "Alice Route")
    res = await client.get("/api/v1/coach/action-plan", headers=headers)
    assert res.status_code in (404, 405)
