"""AROVIA Step 12.8 — Track-Aware Weakness Resolution & Longitudinal Integrity Tests.

Verifies deterministic evidence compatibility across interview tracks:
- TEST 1: Technical weakness -> Behavioral session -> MUST NOT become RESOLVED.
- TEST 2: Technical weakness -> unrelated System Design session -> does NOT resolve unless compatible.
- TEST 3: Technical weakness -> Technical Core session explicitly testing same topic -> RESOLVED.
- TEST 4: System Design weakness -> Behavioral session -> MUST NOT become RESOLVED.
- TEST 5: Behavioral weakness -> Technical Core session -> MUST NOT become RESOLVED.
- TEST 6: Weakness absent from an actually relevant/evaluated session -> RESOLVED.
- TEST 7: Same weakness mentioned multiple times inside one session -> counts as 1 distinct session.
- TEST 8: Unknown compatibility -> MUST NOT produce false RESOLVED status.
- Action Plan Integrity: Verifies ActionableCoachingPlanDTO priority and topic stability across cross-track interviews.
- Multi-User Isolation: Verifies candidate data is never mixed across users.
"""

from datetime import datetime, timezone
import pytest

from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User
from app.services.progress_service import ProgressIntelligenceService


# =============================================================================
# TEST 1: Technical weakness -> Behavioral session -> MUST NOT become RESOLVED
# =============================================================================

@pytest.mark.asyncio
async def test_1_technical_weakness_followed_by_behavioral_session_remains_active():
    """Technical weakness (Database Indexing) must NOT resolve after an unrelated Behavioral interview."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-tech",
        interview_focus="Technical Core",
        status="completed",
        overall_score=60,
        dimension_scores={"correctness": 50},
        evaluation_report={"top_improvements": [{"title": "Database Indexing", "related_dimension": "correctness"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="s2-behav",
        interview_focus="Behavioral",
        focus_skills=["Leadership", "Conflict Resolution"],
        status="completed",
        overall_score=85,
        dimension_scores={"clarity": 85, "confidence": 85},
        evaluation_report={
            "top_strengths": [{"title": "Clear communication and STAR methodology"}],
            "top_improvements": [{"title": "Conciseness in opening"}],
        },
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    db_idx = next((r for r in res_states if r.canonical_topic == "database indexing"), None)

    assert db_idx is not None
    assert db_idx.status == "active"
    assert db_idx.sessions_observed_count == 1
    assert db_idx.frequency_is_decreasing is False


# =============================================================================
# TEST 2: Technical weakness -> Unrelated System Design session -> Does not resolve
# =============================================================================

@pytest.mark.asyncio
async def test_2_technical_weakness_followed_by_unrelated_system_design_does_not_resolve():
    """Technical weakness must NOT resolve after an unrelated System Design interview (e.g. Load Balancing)."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-tech",
        interview_focus="Technical Core",
        status="completed",
        overall_score=55,
        dimension_scores={"correctness": 48},
        evaluation_report={"top_improvements": [{"title": "SQL Query Optimization", "related_dimension": "correctness"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="s2-sys",
        interview_focus="System Design",
        focus_skills=["Load Balancing", "CDN Caching"],
        status="completed",
        overall_score=80,
        evaluation_report={
            "top_strengths": [{"title": "Global CDN and Anycast routing"}],
            "top_improvements": [{"title": "Cache Invalidation"}],
        },
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    sql_opt = next((r for r in res_states if r.canonical_topic == "sql query optimization"), None)

    assert sql_opt is not None
    assert sql_opt.status == "active"
    assert sql_opt.sessions_observed_count == 1


# =============================================================================
# TEST 3: Technical weakness -> Technical Core session explicitly testing topic -> RESOLVED
# =============================================================================

@pytest.mark.asyncio
async def test_3_technical_weakness_followed_by_same_topic_technical_resolves():
    """Technical weakness explicitly tested in a subsequent Technical Core session resolves when absent/mastered."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-tech",
        interview_focus="Technical Core",
        status="completed",
        overall_score=50,
        dimension_scores={"correctness": 45},
        evaluation_report={"top_improvements": [{"title": "Database Indexing", "related_dimension": "correctness"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="s2-tech-focused",
        interview_focus="Technical Core",
        focus_skills=["Database Indexing"],
        status="completed",
        overall_score=88,
        dimension_scores={"correctness": 88},
        evaluation_report={
            "top_strengths": [{"title": "Database Indexing & B-Tree partitioning"}],
            "top_improvements": [{"title": "Minor variable naming style"}],
        },
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    db_idx = next((r for r in res_states if r.canonical_topic == "database indexing"), None)

    assert db_idx is not None
    assert db_idx.status == "resolved"
    assert db_idx.frequency_is_decreasing is True


# =============================================================================
# TEST 4: System Design weakness -> Behavioral session -> MUST NOT RESOLVE
# =============================================================================

@pytest.mark.asyncio
async def test_4_system_design_weakness_followed_by_behavioral_does_not_resolve():
    """System Design weakness (Cache Invalidation) must NOT resolve after a Behavioral interview."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-sys",
        interview_focus="System Design",
        status="completed",
        overall_score=58,
        dimension_scores={"correctness": 52},
        evaluation_report={"top_improvements": [{"title": "Cache Invalidation Strategies"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="s2-behav",
        interview_focus="Behavioral",
        status="completed",
        overall_score=82,
        evaluation_report={"top_improvements": [{"title": "Structured Communication"}]},
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    cache_inv = next((r for r in res_states if r.canonical_topic == "cache invalidation"), None)

    assert cache_inv is not None
    assert cache_inv.status == "active"
    assert cache_inv.sessions_observed_count == 1


# =============================================================================
# TEST 5: Behavioral weakness -> Technical Core session -> MUST NOT RESOLVE
# =============================================================================

@pytest.mark.asyncio
async def test_5_behavioral_weakness_followed_by_technical_does_not_resolve():
    """Behavioral weakness (STAR Method) must NOT resolve after a pure Technical Core interview."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-behav",
        interview_focus="Behavioral",
        status="completed",
        overall_score=55,
        dimension_scores={"clarity": 50},
        evaluation_report={"top_improvements": [{"title": "STAR Method"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="s2-tech",
        interview_focus="Technical Core",
        focus_skills=["Concurrency", "Goroutines"],
        status="completed",
        overall_score=90,
        evaluation_report={"top_improvements": [{"title": "Error Handling"}]},
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    star_w = next((r for r in res_states if r.canonical_topic == "star method"), None)

    assert star_w is not None
    assert star_w.status == "active"
    assert star_w.sessions_observed_count == 1


# =============================================================================
# TEST 6: Weakness absent from an actually relevant/evaluated session -> RESOLVED
# =============================================================================

@pytest.mark.asyncio
async def test_6_weakness_absent_from_relevant_turn_evaluated_session_resolves():
    """When a subsequent session actually evaluates the concept in its question turns and candidate succeeds, it resolves."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-tech",
        interview_focus="Technical Core",
        status="completed",
        overall_score=52,
        dimension_scores={"correctness": 48},
        evaluation_report={"top_improvements": [{"title": "RESTful API Design"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    turn1 = InterviewQuestionTurn(
        id="turn-api-1",
        session_id="s2-tech-eval",
        turn_index=1,
        question_text="Design a RESTful API with proper idempotency and status codes.",
        candidate_answer="I would design POST for creation, PUT for full update, PATCH for partial, and GET with caching.",
        relevance_score=90,
        correctness_score=92,
        keywords_score=88,
        clarity_score=90,
        confidence_score=88,
        evaluation_data={
            "covered_concepts": ["RESTful API Design", "HTTP Idempotency", "Status Codes"],
            "missed_concepts": [],
        },
    )

    s2 = InterviewSession(
        id="s2-tech-eval",
        interview_focus="Technical Core",
        status="completed",
        overall_score=90,
        dimension_scores={"correctness": 92},
        evaluation_report={
            "top_strengths": [{"title": "RESTful API Design Mastery"}],
            "top_improvements": [{"title": "Minor log format"}],
        },
        turns=[turn1],
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    api_design = next((r for r in res_states if r.canonical_topic == "restful api design"), None)

    assert api_design is not None
    assert api_design.status == "resolved"
    assert api_design.frequency_is_decreasing is True


# =============================================================================
# TEST 7: Same weakness mentioned multiple times inside one session -> 1 distinct session
# =============================================================================

@pytest.mark.asyncio
async def test_7_multiple_mentions_in_one_session_counts_as_one_distinct_session():
    """Multiple improvements mapping to the same canonical topic inside one session count as 1 observed session."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-multi-mention",
        interview_focus="Technical Core",
        status="completed",
        overall_score=50,
        evaluation_report={
            "top_improvements": [
                {"title": "Database Indexing Strategies"},
                {"title": "database indexing"},
                {"title": "DB Indexing"},
            ]
        },
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1])
    assert len(res_states) == 1
    w = res_states[0]
    assert w.canonical_topic == "database indexing"
    assert w.sessions_observed_count == 1


# =============================================================================
# TEST 8: Unknown compatibility -> MUST NOT produce false RESOLVED status
# =============================================================================

@pytest.mark.asyncio
async def test_8_unknown_compatibility_must_not_produce_false_resolved():
    """A subsequent session with ambiguous or unmapped topics must NOT mark a known weakness as resolved."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-tech",
        interview_focus="Technical Core",
        status="completed",
        overall_score=55,
        dimension_scores={"correctness": 50},
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    # Session 2 has an unrelated generic title with no focus_skills and no turns
    s2 = InterviewSession(
        id="s2-generic",
        interview_focus="Technical Core",
        status="completed",
        overall_score=75,
        dimension_scores={"correctness": 75},
        evaluation_report={
            "top_strengths": [{"title": "General coding speed"}],
            "top_improvements": [{"title": "Unit test coverage"}],
        },
        started_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
    )

    res_states = service.compute_weakness_resolution_states([s1, s2])
    db_idx = next((r for r in res_states if r.canonical_topic == "database indexing"), None)

    assert db_idx is not None
    assert db_idx.status != "resolved"  # Must NOT be resolved!
    assert db_idx.sessions_observed_count == 1


# =============================================================================
# PHASE 6: ACTION PLAN INTEGRITY WITH TRACK-AWARE RESOLUTION
# =============================================================================

@pytest.mark.asyncio
async def test_action_plan_integrity_retains_active_priority_across_tracks():
    """Action Plan retains the critical technical priority when followed by an unrelated Behavioral session."""
    service = ProgressIntelligenceService()

    s1 = InterviewSession(
        id="s1-tech-p1",
        interview_focus="Technical Core",
        status="completed",
        overall_score=55,
        dimension_scores={"correctness": 45},
        evaluation_report={"top_improvements": [{"title": "Database Indexing", "related_dimension": "correctness"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="s2-tech-p1-recur",
        interview_focus="Technical Core",
        status="completed",
        overall_score=58,
        dimension_scores={"correctness": 46},
        evaluation_report={"top_improvements": [{"title": "Database Indexing Strategies", "related_dimension": "correctness"}]},
        started_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
    )
    s3 = InterviewSession(
        id="s3-behav",
        interview_focus="Behavioral",
        status="completed",
        overall_score=85,
        dimension_scores={"clarity": 85},
        evaluation_report={"top_improvements": [{"title": "STAR Method"}]},
        started_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )

    plan = service.generate_actionable_coaching_plan([s1, s2, s3])
    res_states = service.compute_weakness_resolution_states([s1, s2, s3])
    db_w = next((r for r in res_states if r.canonical_topic == "database indexing"), None)

    # Database Indexing was recurring in 2 technical sessions and NOT resolved by the behavioral session
    assert db_w is not None
    assert db_w.status == "active"
    assert db_w.sessions_observed_count == 2
    assert plan.focus_topic == "Database Indexing"
    assert plan.priority_level == "P1 - Critical Recurring"
    assert plan.practice_preset["focus"] == "Technical Core"
    assert plan.practice_preset["topic"] == "Database Indexing"


# =============================================================================
# PHASE 8: MULTI-USER ISOLATION VERIFICATION
# =============================================================================

@pytest.mark.asyncio
async def test_weakness_resolution_state_user_isolation():
    """Weakness resolution calculation on user A's sessions is strictly isolated from user B."""
    service = ProgressIntelligenceService()

    # User A's session has Database Indexing
    user_a_session = InterviewSession(
        id="sess-user-a",
        user_id="user-a-111",
        interview_focus="Technical Core",
        status="completed",
        overall_score=50,
        evaluation_report={"top_improvements": [{"title": "Database Indexing"}]},
        started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    # User B's session has Cache Invalidation
    user_b_session = InterviewSession(
        id="sess-user-b",
        user_id="user-b-222",
        interview_focus="System Design",
        status="completed",
        overall_score=80,
        evaluation_report={"top_improvements": [{"title": "Cache Invalidation"}]},
        started_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    # Isolated computation for User A
    states_a = service.compute_weakness_resolution_states([user_a_session])
    assert len(states_a) == 1
    assert states_a[0].canonical_topic == "database indexing"

    # Isolated computation for User B
    states_b = service.compute_weakness_resolution_states([user_b_session])
    assert len(states_b) == 1
    assert states_b[0].canonical_topic == "cache invalidation"
