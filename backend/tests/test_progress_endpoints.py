"""Comprehensive REST API Integration and Contract Tests for Progress Intelligence Endpoints."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewSession
from app.models.user import User


async def create_authenticated_user(
    client: AsyncClient, email: str, full_name: str, password: str = "SecurePassword123!"
) -> tuple[dict[str, str], str]:
    """Helper to register a user, retrieve JWT access token, and return auth headers and user id."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    token = user_data["access_token"]
    user_id = user_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id


# ==============================================================================
# 1. AUTHENTICATION & SECURITY (ANTI-IDOR) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_unauthenticated_rejected(client: AsyncClient):
    """GET /api/v1/progress without token must return 401 Unauthorized."""
    res = await client.get("/api/v1/progress")
    assert res.status_code == 401
    assert "detail" in res.json()


@pytest.mark.asyncio
async def test_progress_endpoint_cross_user_isolation_anti_idor(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify strict user isolation (Anti-IDOR): User A and User B only receive their own data."""
    headers_a, user_a_id = await create_authenticated_user(
        client, "user_alpha_progress@example.com", "User Alpha"
    )
    headers_b, user_b_id = await create_authenticated_user(
        client, "user_beta_progress@example.com", "User Beta"
    )

    # 1. Insert completed sessions for User A
    sess_a = InterviewSession(
        id="sess-api-a-1",
        user_id=user_a_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Architecture",
        status="completed",
        overall_score=75,
        dimension_scores={"relevance": 80, "correctness": 70, "keywords": 75, "clarity": 75, "confidence": 75},
        evaluation_report={
            "top_improvements": [{"title": "Cache Invalidation", "description": "TTL omission."}]
        },
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    # 2. Insert completed sessions for User B
    sess_b = InterviewSession(
        id="sess-api-b-1",
        user_id=user_b_id,
        target_role="Data Scientist",
        seniority_level="lead",
        interview_focus="Machine Learning Systems",
        status="completed",
        overall_score=95,
        dimension_scores={"relevance": 95, "correctness": 95, "keywords": 95, "clarity": 95, "confidence": 95},
        evaluation_report={
            "top_improvements": [{"title": "Feature Drift Detection", "description": "KS-test analysis."}]
        },
        started_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([sess_a, sess_b])
    await db_session.commit()

    # 3. Query as User A
    res_a = await client.get("/api/v1/progress", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()

    assert data_a["total_completed_interviews"] == 1
    assert data_a["latest_overall_score"] == 75
    assert data_a["role_breakdown"][0]["target_role"] == "Backend Engineer"
    assert len(data_a["recent_sessions_summary"]) == 1
    assert data_a["recent_sessions_summary"][0]["session_id"] == "sess-api-a-1"

    # 4. Query as User B
    res_b = await client.get("/api/v1/progress", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()

    assert data_b["total_completed_interviews"] == 1
    assert data_b["latest_overall_score"] == 95
    assert data_b["role_breakdown"][0]["target_role"] == "Data Scientist"
    assert len(data_b["recent_sessions_summary"]) == 1
    assert data_b["recent_sessions_summary"][0]["session_id"] == "sess-api-b-1"


# ==============================================================================
# 2. EMPTY & BASELINE STATES
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_zero_completed_sessions(client: AsyncClient):
    """Verify clean response when an authenticated user has zero completed sessions."""
    headers, _ = await create_authenticated_user(
        client, "user_zero_sessions@example.com", "Zero Candidate"
    )

    res = await client.get("/api/v1/progress", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_completed_interviews"] == 0
    assert data["average_overall_score"] is None
    assert data["best_overall_score"] is None
    assert data["lowest_overall_score"] is None
    assert data["latest_overall_score"] is None

    assert data["overall_trend"]["scores"] == []
    assert data["overall_trend"]["direction"] == "Insufficient Data"
    assert data["overall_trend"]["latest_score"] is None
    assert data["overall_trend"]["previous_score"] is None
    assert data["overall_trend"]["net_delta"] is None

    assert data["recurring_weaknesses"] == []
    assert data["recurring_strengths"] == []
    assert data["role_breakdown"] == []
    assert data["consistency"]["consistency_rating"] == "Insufficient Data"
    assert data["next_focus"] is None
    assert data["recent_sessions_summary"] == []


@pytest.mark.asyncio
async def test_progress_endpoint_one_completed_session_baseline(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify single-session baseline state."""
    headers, user_id = await create_authenticated_user(
        client, "user_one_session@example.com", "Baseline Candidate"
    )

    sess = InterviewSession(
        id="sess-api-single-1",
        user_id=user_id,
        target_role="Frontend Engineer",
        seniority_level="mid",
        interview_focus="React Performance",
        status="completed",
        overall_score=82,
        dimension_scores={"relevance": 85, "correctness": 80, "keywords": 80, "clarity": 85, "confidence": 80},
        evaluation_report={
            "top_improvements": [
                {
                    "title": "Virtual DOM Reconciliation",
                    "description": "Explain fiber tree reconciliation heuristics.",
                    "actionable_recommendation": "Review React Fiber diffing algorithms.",
                }
            ]
        },
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(sess)
    await db_session.commit()

    res = await client.get("/api/v1/progress", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_completed_interviews"] == 1
    assert data["average_overall_score"] == 82.0
    assert data["latest_overall_score"] == 82

    assert data["overall_trend"]["scores"] == [82]
    assert data["overall_trend"]["direction"] == "Baseline"
    assert data["overall_trend"]["latest_score"] == 82
    assert data["overall_trend"]["previous_score"] is None
    assert data["overall_trend"]["net_delta"] is None

    # Next focus should target latest session's top improvement
    assert data["next_focus"] is not None
    assert data["next_focus"]["focus_topic"] == "Virtual DOM Reconciliation"
    assert data["next_focus"]["source_dimension"] == "Latest Session Evaluation"


# ==============================================================================
# 3. MULTI-SESSION PROGRESSION, DETERMINISM, & DIMENSIONS
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_multi_session_progression_and_dimensions(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify exact progression values [55, 68, 76] -> net_delta=+21 (oldest to newest), latest=76, previous=68."""
    headers, user_id = await create_authenticated_user(
        client, "user_multi_progression@example.com", "Multi Candidate"
    )

    s1 = InterviewSession(
        id="sess-api-multi-1",
        user_id=user_id,
        target_role="Full Stack Engineer",
        seniority_level="senior",
        interview_focus="Web Architecture",
        status="completed",
        overall_score=55,
        dimension_scores={"relevance": 60, "correctness": 50, "keywords": 55, "clarity": 60, "confidence": 50},
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="sess-api-multi-2",
        user_id=user_id,
        target_role="Full Stack Engineer",
        seniority_level="senior",
        interview_focus="Web Architecture",
        status="completed",
        overall_score=68,
        dimension_scores={"relevance": 70, "correctness": 65, "keywords": 65, "clarity": 70, "confidence": 70},
        started_at=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
    )
    s3 = InterviewSession(
        id="sess-api-multi-3",
        user_id=user_id,
        target_role="Full Stack Engineer",
        seniority_level="senior",
        interview_focus="Web Architecture",
        status="completed",
        overall_score=76,
        dimension_scores={"relevance": 80, "correctness": 75, "keywords": 72, "clarity": 78, "confidence": 75},
        started_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([s1, s2, s3])
    await db_session.commit()

    res = await client.get("/api/v1/progress", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_completed_interviews"] == 3
    assert data["average_overall_score"] == round((55 + 68 + 76) / 3, 1)  # 66.3
    assert data["best_overall_score"] == 76
    assert data["lowest_overall_score"] == 55
    assert data["latest_overall_score"] == 76

    # Overall trend
    trend = data["overall_trend"]
    assert trend["scores"] == [55, 68, 76]
    assert trend["latest_score"] == 76
    assert trend["previous_score"] == 68
    assert trend["net_delta"] == 21  # 76 - 55
    assert trend["direction"] == "Improving"

    # Five dimensions
    dims = data["dimension_trends"]
    assert set(dims.keys()) == {"relevance", "correctness", "keywords", "clarity", "confidence"}
    assert dims["relevance"]["scores"] == [60, 70, 80]
    assert dims["relevance"]["latest_score"] == 80
    assert dims["relevance"]["previous_score"] == 70
    assert dims["relevance"]["net_delta"] == 20
    assert dims["relevance"]["direction"] == "Improving"

    assert dims["correctness"]["scores"] == [50, 65, 75]
    assert dims["correctness"]["net_delta"] == 25
    assert dims["correctness"]["direction"] == "Improving"


# ==============================================================================
# 4. RECURRING PATTERNS CANONICAL AGGREGATION CONTRACT
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_recurring_patterns_canonical_normalization(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify recurrence across 3 sessions: Database Indexing, Database Indexing Strategies, db indexing."""
    headers, user_id = await create_authenticated_user(
        client, "user_recurring_canonical@example.com", "Canonical Candidate"
    )

    s1 = InterviewSession(
        id="sess-api-rec-1",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Databases",
        status="completed",
        overall_score=70,
        evaluation_report={
            "top_improvements": [{"title": "Database Indexing", "description": "B-tree internals."}],
            "top_strengths": [{"title": "Clear Communication", "description": "Structured answers."}],
        },
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="sess-api-rec-2",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Databases",
        status="completed",
        overall_score=75,
        evaluation_report={
            "top_improvements": [{"title": "Database Indexing Strategies", "description": "Covering index trade-offs."}],
            "top_strengths": [{"title": "Communication Clarity", "description": "Punchy articulation."}],
        },
        started_at=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
    )
    s3 = InterviewSession(
        id="sess-api-rec-3",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Databases",
        status="completed",
        overall_score=80,
        evaluation_report={
            "top_improvements": [{"title": "db indexing", "description": "Partial index query planning."}],
        },
        started_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([s1, s2, s3])
    await db_session.commit()

    res = await client.get("/api/v1/progress", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Recurring Weaknesses
    weaknesses = data["recurring_weaknesses"]
    assert len(weaknesses) == 1
    assert weaknesses[0]["canonical_topic"] == "database indexing"
    assert weaknesses[0]["display_title"] == "Database Indexing"
    assert weaknesses[0]["session_count"] == 3
    assert len(weaknesses[0]["sample_descriptions"]) == 2

    # Recurring Strengths
    strengths = data["recurring_strengths"]
    assert len(strengths) == 1
    assert strengths[0]["display_title"] == "Communication Clarity"
    assert strengths[0]["session_count"] == 2

    # Next focus must automatically prioritize the top recurring weakness (Database Indexing, 3 sessions)
    assert data["next_focus"] is not None
    assert data["next_focus"]["focus_topic"] == "Database Indexing"
    assert data["next_focus"]["supporting_session_count"] == 3
    assert data["next_focus"]["source_dimension"] == "Cross-Session Recurrence"


# ==============================================================================
# 5. ROLE ANALYTICS CONTRACT & ORDERING
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_role_analytics(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify deterministic role breakdown for multiple roles: Backend Engineer [55, 65], Data Scientist [72, 80]."""
    headers, user_id = await create_authenticated_user(
        client, "user_roles_test@example.com", "Role Candidate"
    )

    s1 = InterviewSession(
        id="sess-api-role-1",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Backend API",
        status="completed",
        overall_score=55,
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="sess-api-role-2",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Backend API",
        status="completed",
        overall_score=65,
        started_at=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
    )
    s3 = InterviewSession(
        id="sess-api-role-3",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Backend API",
        status="completed",
        overall_score=75,
        started_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
    )
    s4 = InterviewSession(
        id="sess-api-role-4",
        user_id=user_id,
        target_role="Data Scientist",
        seniority_level="mid",
        interview_focus="Machine Learning",
        status="completed",
        overall_score=72,
        started_at=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
    )
    s5 = InterviewSession(
        id="sess-api-role-5",
        user_id=user_id,
        target_role="Data Scientist",
        seniority_level="mid",
        interview_focus="Machine Learning",
        status="completed",
        overall_score=80,
        started_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([s1, s2, s3, s4, s5])
    await db_session.commit()

    res = await client.get("/api/v1/progress", headers=headers)
    assert res.status_code == 200
    data = res.json()

    roles = data["role_breakdown"]
    assert len(roles) == 2

    # Backend Engineer ranked first (3 completed sessions)
    assert roles[0]["target_role"] == "Backend Engineer"
    assert roles[0]["completed_count"] == 3
    assert roles[0]["average_score"] == 65.0  # (55 + 65 + 75) / 3
    assert roles[0]["best_score"] == 75
    assert roles[0]["lowest_score"] == 55
    assert roles[0]["latest_score"] == 75

    # Data Scientist ranked second (2 completed sessions)
    assert roles[1]["target_role"] == "Data Scientist"
    assert roles[1]["completed_count"] == 2
    assert roles[1]["average_score"] == 76.0  # (72 + 80) / 2
    assert roles[1]["best_score"] == 80
    assert roles[1]["lowest_score"] == 72
    assert roles[1]["latest_score"] == 80


# ==============================================================================
# 6. CONSISTENCY METRIC FORMULA VERIFICATION
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_consistency_formula(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify consistency calculation on exact scores [60, 70, 80].

    mean = 70.0
    variance = ((60-70)^2 + (70-70)^2 + (80-70)^2) / 3 = 200 / 3 = 66.666... -> 66.7
    std_dev = sqrt(66.666...) = 8.1649... -> 8.2
    rating = Moderate Consistency (4.0 < std_dev <= 10.0)
    """
    headers, user_id = await create_authenticated_user(
        client, "user_consistency_test@example.com", "Consistency Candidate"
    )

    s1 = InterviewSession(
        id="sess-api-cons-1",
        user_id=user_id,
        target_role="Software Engineer",
        seniority_level="senior",
        interview_focus="Core",
        status="completed",
        overall_score=60,
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = InterviewSession(
        id="sess-api-cons-2",
        user_id=user_id,
        target_role="Software Engineer",
        seniority_level="senior",
        interview_focus="Core",
        status="completed",
        overall_score=70,
        started_at=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
    )
    s3 = InterviewSession(
        id="sess-api-cons-3",
        user_id=user_id,
        target_role="Software Engineer",
        seniority_level="senior",
        interview_focus="Core",
        status="completed",
        overall_score=80,
        started_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([s1, s2, s3])
    await db_session.commit()

    res = await client.get("/api/v1/progress", headers=headers)
    assert res.status_code == 200
    data = res.json()

    cons = data["consistency"]
    assert cons["sample_size"] == 3
    assert cons["standard_deviation"] == 8.2
    assert cons["score_variance"] == 66.7
    assert cons["consistency_rating"] == "Moderate Consistency"


# ==============================================================================
# 7. DATA FILTERING: EXCLUSION OF INCOMPLETE SESSIONS
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_filters_incomplete_and_null_scores(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that in_progress, evaluating, abandoned sessions, and sessions without overall_score are excluded."""
    headers, user_id = await create_authenticated_user(
        client, "user_filter_test@example.com", "Filter Candidate"
    )

    # 1 Valid Completed Session
    s_comp = InterviewSession(
        id="sess-api-f-comp",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="APIs",
        status="completed",
        overall_score=88,
        started_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )
    # Excluded: in_progress
    s_in_prog = InterviewSession(
        id="sess-api-f-prog",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="APIs",
        status="in_progress",
        overall_score=None,
        started_at=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
    )
    # Excluded: evaluating
    s_eval = InterviewSession(
        id="sess-api-f-eval",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="APIs",
        status="evaluating",
        overall_score=None,
        started_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
    )
    # Excluded: abandoned
    s_aban = InterviewSession(
        id="sess-api-f-aban",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="APIs",
        status="abandoned",
        overall_score=40,
        started_at=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
    )
    # Excluded: completed but overall_score is None
    s_null_score = InterviewSession(
        id="sess-api-f-null",
        user_id=user_id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="APIs",
        status="completed",
        overall_score=None,
        started_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([s_comp, s_in_prog, s_eval, s_aban, s_null_score])
    await db_session.commit()

    res = await client.get("/api/v1/progress", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Total completed must be strictly 1
    assert data["total_completed_interviews"] == 1
    assert data["latest_overall_score"] == 88
    assert len(data["recent_sessions_summary"]) == 1
    assert data["recent_sessions_summary"][0]["session_id"] == "sess-api-f-comp"


# ==============================================================================
# 8. QUERY PARAMETER LIMIT BEHAVIOR
# ==============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_limit_parameter(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify ?limit=2 restricts evaluated trajectory to the latest 2 completed sessions."""
    headers, user_id = await create_authenticated_user(
        client, "user_limit_test@example.com", "Limit Candidate"
    )

    for i, score in enumerate([60, 70, 80, 90], start=1):
        s = InterviewSession(
            id=f"sess-api-lim-{i}",
            user_id=user_id,
            target_role="DevOps Engineer",
            seniority_level="senior",
            interview_focus="Kubernetes",
            status="completed",
            overall_score=score,
            started_at=datetime(2026, 8, i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(s)
    await db_session.commit()

    # Query with limit=2
    res = await client.get("/api/v1/progress?limit=2", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Total completed in database is still 4
    assert data["total_completed_interviews"] == 4
    # Evaluated scores limited to the last 2: [80, 90]
    assert data["overall_trend"]["scores"] == [80, 90]
    assert data["overall_trend"]["latest_score"] == 90
    assert data["overall_trend"]["previous_score"] == 80
    assert data["overall_trend"]["net_delta"] == 10
    assert len(data["recent_sessions_summary"]) == 2
