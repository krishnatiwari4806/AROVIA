"""Comprehensive Unit and Integration Tests for ProgressIntelligenceService and Analytics Engine."""

import math
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewSession
from app.models.user import User
from app.schemas.progress import (
    ActionableNextFocusDTO,
    ConsistencyMetricDTO,
    DashboardProgressResponse,
    DimensionTrendDTO,
    OverallScoreTrendDTO,
    RecurringPatternDTO,
    RolePerformanceDTO,
)
from app.services.progress_service import (
    CANONICAL_TOPIC_ALIASES,
    EVALUATION_DIMENSIONS,
    ProgressIntelligenceService,
    _classify_direction,
    _format_delta,
    get_canonical_topic,
    get_progress_service,
    normalize_title,
)


@pytest.fixture
def progress_service() -> ProgressIntelligenceService:
    """Provide ProgressIntelligenceService instance."""
    return ProgressIntelligenceService()


def create_mock_session(
    session_id: str,
    user_id: str,
    overall_score: int = 80,
    target_role: str = "Backend Engineer",
    seniority: str = "senior",
    status: str = "completed",
    dimension_scores: dict = None,
    evaluation_report: dict = None,
    started_at: datetime = None,
) -> InterviewSession:
    """Helper to instantiate an in-memory InterviewSession model instance."""
    if dimension_scores is None:
        dimension_scores = {
            "relevance": 85,
            "correctness": 80,
            "keywords": 78,
            "clarity": 82,
            "confidence": 80,
        }
    return InterviewSession(
        id=session_id,
        user_id=user_id,
        target_role=target_role,
        seniority_level=seniority,
        interview_focus="Technical Architecture",
        practice_mode="standard",
        status=status,
        overall_score=overall_score,
        dimension_scores=dimension_scores,
        evaluation_report=evaluation_report or {},
        started_at=started_at or datetime.now(timezone.utc),
    )


# ==============================================================================
# 1. HELPER & NORMALIZATION TESTS
# ==============================================================================


def test_normalize_title():
    """Test title cleaning, punctuation removal, and whitespace normalization."""
    assert normalize_title("  Cache_Invalidation-Strategies!  ") == "cache invalidation strategies"
    assert normalize_title("SQL-Query_Optimization") == "sql query optimization"
    assert normalize_title(None) == ""
    assert normalize_title(123) == ""
    assert normalize_title("") == ""


def test_get_canonical_topic_aliases():
    """Test canonical mapping for known topic aliases."""
    key, display = get_canonical_topic("caching expiration policies")
    assert key == "cache invalidation"
    assert display == "Cache Invalidation"

    key, display = get_canonical_topic("db indexing strategies")
    assert key == "database indexing"
    assert display == "Database Indexing"

    key, display = get_canonical_topic("sql query optimization techniques")
    assert key == "sql query optimization"
    assert display == "SQL Query Optimization"

    key, display = get_canonical_topic("api error handling strategies")
    assert key == "api error handling"
    assert display == "API Error Handling"


def test_get_canonical_topic_unseen_and_edge_cases():
    """Test fallback token sorting and empty/invalid values."""
    assert get_canonical_topic(None) is None
    assert get_canonical_topic("") is None
    assert get_canonical_topic("   ") is None

    # Unseen topic with modifiers stripped
    key, display = get_canonical_topic("Kubernetes Pod Eviction Strategies")
    assert "eviction" in key and "kubernetes" in key and "pod" in key
    assert display == "Kubernetes Pod Eviction Strategies"


def test_classify_direction_and_format_delta():
    """Test trend direction thresholds and delta formatting."""
    # STABLE_DELTA_THRESHOLD = 2
    assert _classify_direction(3) == "Improving"
    assert _classify_direction(10) == "Improving"
    assert _classify_direction(-3) == "Declining"
    assert _classify_direction(-15) == "Declining"
    assert _classify_direction(2) == "Stable"
    assert _classify_direction(0) == "Stable"
    assert _classify_direction(-2) == "Stable"

    assert _format_delta(12) == "+12"
    assert _format_delta(0) == "0"
    assert _format_delta(-7) == "-7"


# ==============================================================================
# 2. OVERALL SCORE TREND TESTS (0, 1, 2, Multiple Sessions)
# ==============================================================================


def test_overall_trend_zero_sessions(progress_service: ProgressIntelligenceService):
    """Test trend calculation with zero completed sessions."""
    trend = progress_service.calculate_overall_trend([])
    assert isinstance(trend, OverallScoreTrendDTO)
    assert trend.scores == []
    assert trend.latest_score is None
    assert trend.previous_score is None
    assert trend.net_delta is None
    assert trend.direction == "Insufficient Data"


def test_overall_trend_one_session(progress_service: ProgressIntelligenceService):
    """Test trend calculation with a single completed baseline session."""
    s1 = create_mock_session("s1", "u1", overall_score=82)
    trend = progress_service.calculate_overall_trend([s1])
    assert trend.scores == [82]
    assert trend.latest_score == 82
    assert trend.previous_score is None
    assert trend.net_delta is None
    assert trend.direction == "Baseline"


def test_overall_trend_two_sessions_improving(progress_service: ProgressIntelligenceService):
    """Test trend calculation with 2 sessions demonstrating improvement."""
    s1 = create_mock_session("s1", "u1", overall_score=75)
    s2 = create_mock_session("s2", "u1", overall_score=85)
    trend = progress_service.calculate_overall_trend([s1, s2])
    assert trend.scores == [75, 85]
    assert trend.latest_score == 85
    assert trend.previous_score == 75
    assert trend.net_delta == 10
    assert trend.direction == "Improving"


def test_overall_trend_two_sessions_declining(progress_service: ProgressIntelligenceService):
    """Test trend calculation with 2 sessions demonstrating decline."""
    s1 = create_mock_session("s1", "u1", overall_score=85)
    s2 = create_mock_session("s2", "u1", overall_score=78)
    trend = progress_service.calculate_overall_trend([s1, s2])
    assert trend.scores == [85, 78]
    assert trend.latest_score == 78
    assert trend.previous_score == 85
    assert trend.net_delta == -7
    assert trend.direction == "Declining"


def test_overall_trend_two_sessions_stable(progress_service: ProgressIntelligenceService):
    """Test trend calculation with 2 sessions within stability threshold."""
    s1 = create_mock_session("s1", "u1", overall_score=80)
    s2 = create_mock_session("s2", "u1", overall_score=82)
    trend = progress_service.calculate_overall_trend([s1, s2])
    assert trend.scores == [80, 82]
    assert trend.latest_score == 82
    assert trend.previous_score == 80
    assert trend.net_delta == 2
    assert trend.direction == "Stable"


def test_overall_trend_multiple_sessions(progress_service: ProgressIntelligenceService):
    """Test multi-session trajectory: oldest to newest."""
    sessions = [
        create_mock_session("s1", "u1", overall_score=68),
        create_mock_session("s2", "u1", overall_score=74),
        create_mock_session("s3", "u1", overall_score=79),
        create_mock_session("s4", "u1", overall_score=88),
    ]
    trend = progress_service.calculate_overall_trend(sessions)
    assert trend.scores == [68, 74, 79, 88]
    assert trend.latest_score == 88
    assert trend.previous_score == 79
    assert trend.net_delta == 20  # 88 - 68
    assert trend.direction == "Improving"


def test_overall_trend_ignores_invalid_scores(progress_service: ProgressIntelligenceService):
    """Ensure None and out-of-range scores are filtered without crash."""
    s1 = create_mock_session("s1", "u1", overall_score=70)
    s2 = create_mock_session("s2", "u1", overall_score=None)
    s3 = create_mock_session("s3", "u1", overall_score=150)  # out of 0-100 bound
    s4 = create_mock_session("s4", "u1", overall_score=80)

    trend = progress_service.calculate_overall_trend([s1, s2, s3, s4])
    assert trend.scores == [70, 80]
    assert trend.latest_score == 80
    assert trend.previous_score == 70
    assert trend.net_delta == 10
    assert trend.direction == "Improving"


# ==============================================================================
# 3. FIVE-DIMENSION ANALYTICS TESTS
# ==============================================================================


def test_dimension_trends_structure_and_names(progress_service: ProgressIntelligenceService):
    """Verify all 5 calibrated evaluation dimensions are present and no fabricated dimensions exist."""
    dim_trends = progress_service.calculate_dimension_trends([])
    assert set(dim_trends.keys()) == set(EVALUATION_DIMENSIONS)
    assert set(dim_trends.keys()) == {"relevance", "correctness", "keywords", "clarity", "confidence"}
    assert "logic" not in dim_trends

    for dim, dto in dim_trends.items():
        assert isinstance(dto, DimensionTrendDTO)
        assert dto.dimension == dim
        assert dto.direction == "Insufficient Data"
        assert dto.scores == []


def test_dimension_trends_multi_session(progress_service: ProgressIntelligenceService):
    """Test longitudinal progression across 5 dimensions with mixed trajectories."""
    s1 = create_mock_session(
        "s1",
        "u1",
        dimension_scores={
            "relevance": 70,
            "correctness": 80,
            "keywords": 60,
            "clarity": 85,
            "confidence": 75,
        },
    )
    s2 = create_mock_session(
        "s2",
        "u1",
        dimension_scores={
            "relevance": 85,  # +15 -> Improving
            "correctness": 70,  # -10 -> Declining
            "keywords": 61,  # +1 -> Stable
            "clarity": 85,  # 0 -> Stable
            "confidence": 90,  # +15 -> Improving
        },
    )

    trends = progress_service.calculate_dimension_trends([s1, s2])

    assert trends["relevance"].direction == "Improving"
    assert trends["relevance"].net_delta == 15
    assert trends["relevance"].scores == [70, 85]

    assert trends["correctness"].direction == "Declining"
    assert trends["correctness"].net_delta == -10
    assert trends["correctness"].scores == [80, 70]

    assert trends["keywords"].direction == "Stable"
    assert trends["keywords"].net_delta == 1
    assert trends["keywords"].scores == [60, 61]

    assert trends["clarity"].direction == "Stable"
    assert trends["clarity"].net_delta == 0
    assert trends["clarity"].scores == [85, 85]

    assert trends["confidence"].direction == "Improving"
    assert trends["confidence"].net_delta == 15
    assert trends["confidence"].scores == [75, 90]


def test_dimension_trends_missing_dimensions_handled_safely(progress_service: ProgressIntelligenceService):
    """Ensure sessions with partial/missing dimension dictionaries are handled gracefully."""
    s1 = create_mock_session("s1", "u1", dimension_scores={"relevance": 80})
    s2 = create_mock_session("s2", "u1", dimension_scores={"correctness": 90, "relevance": 85})
    s3 = create_mock_session("s3", "u1", dimension_scores={})

    trends = progress_service.calculate_dimension_trends([s1, s2, s3])

    # Relevance has 2 observations: [80, 85]
    assert trends["relevance"].scores == [80, 85]
    assert trends["relevance"].latest_score == 85
    assert trends["relevance"].previous_score == 80
    assert trends["relevance"].net_delta == 5
    assert trends["relevance"].direction == "Improving"

    # Correctness has 1 observation: [90] -> Baseline
    assert trends["correctness"].scores == [90]
    assert trends["correctness"].latest_score == 90
    assert trends["correctness"].previous_score is None
    assert trends["correctness"].direction == "Baseline"

    # Keywords has 0 observations
    assert trends["keywords"].scores == []
    assert trends["keywords"].direction == "Insufficient Data"


# ==============================================================================
# 4. RECURRING PATTERN AGGREGATION & NORMALIZATION TESTS
# ==============================================================================


def test_recurring_patterns_single_session_duplicate_not_counted_twice(progress_service: ProgressIntelligenceService):
    """Verify that duplicate occurrences within the same session only count as 1 session."""
    report1 = {
        "top_improvements": [
            {"title": "Cache Invalidation", "description": "Missed TTL strategies."},
            {"title": "caching expiration policies", "description": "Duplicate mention in same session."},
        ],
        "top_strengths": [
            {"title": "Communication Clarity", "description": "Very clear speaking style."},
            {"title": "clear communication", "description": "Clear answers throughout."},
        ],
    }

    rec_weak, rec_str = progress_service.aggregate_recurring_patterns([report1])
    assert rec_weak == []  # Not recurring because only in 1 distinct session
    assert rec_str == []

    weak_dtos, str_dtos = progress_service.aggregate_recurring_patterns_structured([report1])
    assert weak_dtos == []
    assert str_dtos == []


def test_recurring_patterns_two_sessions(progress_service: ProgressIntelligenceService):
    """Verify recurrence when pattern appears across 2 distinct completed sessions."""
    report1 = {
        "top_improvements": [
            {"title": "cache invalidation strategies", "description": "Failed to explain write-through TTL."}
        ],
        "top_strengths": [
            {"title": "SQL Query Optimization", "description": "Effective use of covering indexes."}
        ],
    }
    report2 = {
        "top_improvements": [
            {"title": "caching expiration policies", "description": "No cache stampede mitigation mentioned."}
        ],
        "top_strengths": [
            {"title": "database query optimization", "description": "Mastered EXPLAIN ANALYZE interpretation."}
        ],
    }

    rec_weak, rec_str = progress_service.aggregate_recurring_patterns([report1, report2])
    assert rec_weak == ["Cache Invalidation (2 sessions)"]
    assert rec_str == ["SQL Query Optimization (2 sessions)"]

    weak_dtos, str_dtos = progress_service.aggregate_recurring_patterns_structured([report1, report2])
    assert len(weak_dtos) == 1
    assert weak_dtos[0].display_title == "Cache Invalidation"
    assert weak_dtos[0].session_count == 2
    assert weak_dtos[0].pattern_type == "weakness"
    assert len(weak_dtos[0].sample_descriptions) == 2

    assert len(str_dtos) == 1
    assert str_dtos[0].display_title == "SQL Query Optimization"
    assert str_dtos[0].session_count == 2
    assert str_dtos[0].pattern_type == "strength"


def test_recurring_patterns_three_sessions_multiple_topics(progress_service: ProgressIntelligenceService):
    """Test 3-session recurrence with multiple topics and frequency ranking."""
    report1 = {
        "top_improvements": [
            {"title": "API Error Handling", "description": "Missed 429 Retry-After header."},
            {"title": "Database Indexing", "description": "Missing compound index explanation."},
        ]
    }
    report2 = {
        "top_improvements": [
            {"title": "api error handling strategies", "description": "No idempotency key on retry."},
            {"title": "Database Indexing", "description": "B-tree vs Hash index confusion."},
        ]
    }
    report3 = {
        "top_improvements": [
            {"title": "error handling in apis", "description": "Unhandled circuit breaker exceptions."},
        ]
    }

    weak_dtos, _ = progress_service.aggregate_recurring_patterns_structured([report1, report2, report3])
    assert len(weak_dtos) == 2
    # API Error Handling appeared in 3 sessions -> ranked first
    assert weak_dtos[0].display_title == "API Error Handling"
    assert weak_dtos[0].session_count == 3
    # Database Indexing appeared in 2 sessions -> ranked second
    assert weak_dtos[1].display_title == "Database Indexing"
    assert weak_dtos[1].session_count == 2


# ==============================================================================
# 5. ROLE & SENIORITY ANALYTICS TESTS
# ==============================================================================


def test_role_analytics_aggregation(progress_service: ProgressIntelligenceService):
    """Test aggregation of completed sessions by target role."""
    sessions = [
        create_mock_session("s1", "u1", overall_score=75, target_role="Backend Engineer", seniority="senior"),
        create_mock_session("s2", "u1", overall_score=85, target_role="Backend Engineer", seniority="senior"),
        create_mock_session("s3", "u1", overall_score=90, target_role="Backend Engineer", seniority="senior"),
        create_mock_session("s4", "u1", overall_score=82, target_role="Full Stack Engineer", seniority="mid"),
    ]

    breakdown = progress_service.calculate_role_analytics(sessions)
    assert len(breakdown) == 2

    # Backend Engineer is first (3 sessions)
    be = breakdown[0]
    assert be.target_role == "Backend Engineer"
    assert be.seniority_level == "senior"
    assert be.completed_count == 3
    assert be.average_score == 83.3  # (75+85+90)/3 = 83.333... -> 83.3
    assert be.best_score == 90
    assert be.lowest_score == 75
    assert be.latest_score == 90

    # Full Stack Engineer is second (1 session)
    fs = breakdown[1]
    assert fs.target_role == "Full Stack Engineer"
    assert fs.completed_count == 1
    assert fs.average_score == 82.0
    assert fs.best_score == 82
    assert fs.lowest_score == 82
    assert fs.latest_score == 82


def test_role_analytics_missing_or_blank_role(progress_service: ProgressIntelligenceService):
    """Test fallback when target_role is missing or None."""
    s1 = create_mock_session("s1", "u1", overall_score=80, target_role=None)
    s2 = create_mock_session("s2", "u1", overall_score=88, target_role="   ")

    breakdown = progress_service.calculate_role_analytics([s1, s2])
    assert len(breakdown) == 1
    assert breakdown[0].target_role == "General Software Engineer"
    assert breakdown[0].completed_count == 2
    assert breakdown[0].average_score == 84.0


# ==============================================================================
# 6. CONSISTENCY & VARIANCE ANALYTICS TESTS
# ==============================================================================


def test_consistency_insufficient_data(progress_service: ProgressIntelligenceService):
    """Test consistency metric with 0 and 1 scores."""
    c0 = progress_service.calculate_consistency([])
    assert c0.consistency_rating == "Insufficient Data"
    assert c0.sample_size == 0
    assert c0.standard_deviation is None

    c1 = progress_service.calculate_consistency([85])
    assert c1.consistency_rating == "Insufficient Data"
    assert c1.sample_size == 1
    assert c1.standard_deviation is None


def test_consistency_high_moderate_and_variable_tiers(progress_service: ProgressIntelligenceService):
    """Test consistency ratings based on exact population standard deviation formulas."""
    # High Consistency: std_dev <= 4.0 (e.g., [84, 85, 86, 85] -> mean=85, std_dev=0.7)
    high_res = progress_service.calculate_consistency([84, 85, 86, 85])
    assert high_res.sample_size == 4
    assert high_res.standard_deviation is not None and high_res.standard_deviation <= 4.0
    assert high_res.consistency_rating == "High Consistency"

    # Moderate Consistency: 4.0 < std_dev <= 10.0 (e.g., [70, 80, 85, 90] -> mean=81.25, std_dev=7.39)
    mod_res = progress_service.calculate_consistency([70, 80, 85, 90])
    assert mod_res.consistency_rating == "Moderate Consistency"
    assert 4.0 < mod_res.standard_deviation <= 10.0

    # Variable Performance: std_dev > 10.0 (e.g., [50, 95, 60, 90] -> mean=73.75, std_dev=19.16)
    var_res = progress_service.calculate_consistency([50, 95, 60, 90])
    assert var_res.consistency_rating == "Variable Performance"
    assert var_res.standard_deviation > 10.0


# ==============================================================================
# 7. DETERMINISTIC NEXT FOCUS SELECTION TESTS
# ==============================================================================


def test_next_focus_priority_1_recurring_weakness(progress_service: ProgressIntelligenceService):
    """Priority 1: Select top recurring weakness when present."""
    s1 = create_mock_session("s1", "u1", overall_score=80)
    recurring_weakness = [
        RecurringPatternDTO(
            canonical_topic="cache invalidation",
            display_title="Cache Invalidation",
            pattern_type="weakness",
            session_count=3,
            sample_descriptions=["Missed TTL strategies.", "No cache stampede handling."],
        )
    ]

    focus = progress_service.determine_next_focus([s1], recurring_weakness)
    assert isinstance(focus, ActionableNextFocusDTO)
    assert focus.focus_topic == "Cache Invalidation"
    assert focus.supporting_session_count == 3
    assert focus.source_dimension == "Cross-Session Recurrence"
    assert "Missed TTL strategies" in focus.actionable_recommendation


def test_next_focus_priority_2_latest_session_evaluation_improvement(progress_service: ProgressIntelligenceService):
    """Priority 2: When no recurring weaknesses exist, select latest session top improvement."""
    s1 = create_mock_session(
        "s1",
        "u1",
        overall_score=82,
        evaluation_report={
            "top_improvements": [
                {
                    "title": "Distributed Locking",
                    "description": "Redlock algorithm trade-offs were omitted.",
                    "actionable_recommendation": "Review fencing tokens and lease timeouts.",
                }
            ]
        },
    )

    focus = progress_service.determine_next_focus([s1], [])
    assert isinstance(focus, ActionableNextFocusDTO)
    assert focus.focus_topic == "Distributed Locking"
    assert focus.supporting_session_count == 1
    assert focus.source_dimension == "Latest Session Evaluation"
    assert focus.actionable_recommendation == "Review fencing tokens and lease timeouts."


def test_next_focus_priority_3_lowest_dimension_calibration(progress_service: ProgressIntelligenceService):
    """Priority 3: When no report improvements exist, calibrate lowest scoring dimension."""
    s1 = create_mock_session(
        "s1",
        "u1",
        overall_score=80,
        dimension_scores={
            "relevance": 90,
            "correctness": 88,
            "keywords": 65,  # Lowest
            "clarity": 85,
            "confidence": 80,
        },
        evaluation_report={},
    )

    focus = progress_service.determine_next_focus([s1], [])
    assert isinstance(focus, ActionableNextFocusDTO)
    assert focus.focus_topic == "Keywords Calibration"
    assert "Keywords was the lowest scoring dimension (65/100)" in focus.reason
    assert focus.source_dimension == "Keywords"


def test_next_focus_empty_sessions(progress_service: ProgressIntelligenceService):
    """Test next focus returns None when no sessions exist."""
    assert progress_service.determine_next_focus([], []) is None


# ==============================================================================
# 8. ASYNC DB INTEGRATION & USER ISOLATION (ANTI-IDOR) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_get_user_progress_anti_idor_and_status_filtering(
    db_session: AsyncSession, progress_service: ProgressIntelligenceService
):
    """Verify strict user isolation (Anti-IDOR) and exclusion of incomplete/in-progress sessions."""
    # 1. Create two separate users
    user_a = User(
        id="user-a-progress-1",
        email="user_a@example.com",
        full_name="User Alpha",
        hashed_password="pw_hash_test",
    )
    user_b = User(
        id="user-b-progress-2",
        email="user_b@example.com",
        full_name="User Beta",
        hashed_password="pw_hash_test",
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # 2. Add sessions for User A: 2 completed, 1 in_progress, 1 abandoned
    sess_a_1 = InterviewSession(
        id="sess-a-comp-1",
        user_id=user_a.id,
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
    sess_a_2 = InterviewSession(
        id="sess-a-comp-2",
        user_id=user_a.id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Architecture",
        status="completed",
        overall_score=85,
        dimension_scores={"relevance": 90, "correctness": 80, "keywords": 85, "clarity": 85, "confidence": 85},
        evaluation_report={
            "top_improvements": [{"title": "caching strategies", "description": "Write-behind buffer."}]
        },
        started_at=datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc),
    )
    sess_a_in_progress = InterviewSession(
        id="sess-a-active",
        user_id=user_a.id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Architecture",
        status="in_progress",
        overall_score=None,
        started_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
    )
    sess_a_abandoned = InterviewSession(
        id="sess-a-abandoned",
        user_id=user_a.id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Architecture",
        status="abandoned",
        overall_score=40,
        started_at=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
    )

    # 3. Add sessions for User B: 1 completed with score 99
    sess_b_1 = InterviewSession(
        id="sess-b-comp-1",
        user_id=user_b.id,
        target_role="Staff Architect",
        seniority_level="staff",
        interview_focus="System Design",
        status="completed",
        overall_score=99,
        dimension_scores={"relevance": 99, "correctness": 99, "keywords": 99, "clarity": 99, "confidence": 99},
        started_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([sess_a_1, sess_a_2, sess_a_in_progress, sess_a_abandoned, sess_b_1])
    await db_session.commit()

    # 4. Fetch progress for User A
    progress_a = await progress_service.get_user_progress(db_session, user_a)

    assert isinstance(progress_a, DashboardProgressResponse)
    # Total completed should be strictly 2 (excluding in_progress, abandoned, and User B's session)
    assert progress_a.total_completed_interviews == 2
    assert progress_a.average_overall_score == 80.0  # (75 + 85) / 2
    assert progress_a.best_overall_score == 85
    assert progress_a.lowest_overall_score == 75
    assert progress_a.latest_overall_score == 85

    # Check overall trend
    assert progress_a.overall_trend.scores == [75, 85]
    assert progress_a.overall_trend.net_delta == 10
    assert progress_a.overall_trend.direction == "Improving"

    # Check User B's score 99 NEVER leaked to User A
    for pt in progress_a.recent_sessions_summary:
        assert pt.overall_score != 99
        assert pt.session_id in ("sess-a-comp-1", "sess-a-comp-2")

    # 5. Fetch progress for User B
    progress_b = await progress_service.get_user_progress(db_session, user_b)
    assert progress_b.total_completed_interviews == 1
    assert progress_b.average_overall_score == 99.0
    assert progress_b.overall_trend.scores == [99]
    assert progress_b.overall_trend.direction == "Baseline"


@pytest.mark.asyncio
async def test_get_user_progress_zero_sessions_in_db(
    db_session: AsyncSession, progress_service: ProgressIntelligenceService
):
    """Verify DB query for new user with zero sessions produces valid empty response."""
    user = User(
        id="user-new-progress-0",
        email="new_progress_user@example.com",
        full_name="New Candidate",
        hashed_password="pw_hash_test",
    )
    db_session.add(user)
    await db_session.commit()

    res = await progress_service.get_user_progress(db_session, user)
    assert isinstance(res, DashboardProgressResponse)
    assert res.total_completed_interviews == 0
    assert res.average_overall_score is None
    assert res.latest_overall_score is None
    assert res.overall_trend.direction == "Insufficient Data"
    assert res.consistency.consistency_rating == "Insufficient Data"
    assert res.next_focus is None
    assert res.recent_sessions_summary == []


def test_dependency_provider():
    """Verify get_progress_service provider returns instance."""
    svc = get_progress_service()
    assert isinstance(svc, ProgressIntelligenceService)
