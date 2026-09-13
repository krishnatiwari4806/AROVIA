"""Pydantic schemas and Data Transfer Objects for Progress Intelligence & Analytics."""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ScoreProgressionPointDTO(BaseModel):
    """Snapshot of a single completed interview session in the historical timeline."""

    session_id: str
    date: Optional[str] = None
    target_role: str
    seniority_level: Optional[str] = None
    interview_focus: Optional[str] = None
    overall_score: int = Field(ge=0, le=100)
    dimension_scores: Dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DimensionTrendDTO(BaseModel):
    """Historical progression and directional trend for a specific evaluation dimension."""

    dimension: str  # "relevance", "correctness", "keywords", "clarity", "confidence"
    scores: List[int] = Field(default_factory=list)
    latest_score: Optional[int] = None
    previous_score: Optional[int] = None
    net_delta: Optional[int] = None
    direction: str = "Baseline"  # "Improving", "Declining", "Stable", "Baseline", "Insufficient Data"


class OverallScoreTrendDTO(BaseModel):
    """Historical progression and directional trajectory for overall interview scores."""

    scores: List[int] = Field(default_factory=list)
    latest_score: Optional[int] = None
    previous_score: Optional[int] = None
    net_delta: Optional[int] = None
    direction: str = "Baseline"  # "Improving", "Declining", "Stable", "Baseline", "Insufficient Data"


class RecurringPatternDTO(BaseModel):
    """Identified recurring strength or improvement area observed across distinct sessions."""

    canonical_topic: str
    display_title: str
    pattern_type: str  # "weakness" or "strength"
    session_count: int = Field(ge=2)
    sample_descriptions: List[str] = Field(default_factory=list)


class RolePerformanceDTO(BaseModel):
    """Aggregated performance metrics grouped by target role."""

    target_role: str
    seniority_level: Optional[str] = None
    completed_count: int = Field(ge=1)
    average_score: float = Field(ge=0.0, le=100.0)
    best_score: int = Field(ge=0, le=100)
    lowest_score: int = Field(ge=0, le=100)
    latest_score: int = Field(ge=0, le=100)


class ConsistencyMetricDTO(BaseModel):
    """Deterministic score variance and performance stability metric."""

    sample_size: int = Field(ge=0)
    standard_deviation: Optional[float] = None
    score_variance: Optional[float] = None
    consistency_rating: str  # "High Consistency", "Moderate Consistency", "Variable Performance", "Insufficient Data"
    description: str


class ActionableNextFocusDTO(BaseModel):
    """Deterministic recommendation for the candidate's highest-priority next practice focus."""

    focus_topic: str
    reason: str
    source_dimension: Optional[str] = None
    supporting_session_count: int = Field(default=1)
    actionable_recommendation: Optional[str] = None


class DashboardAIInsightDTO(BaseModel):
    """Structured AI insight synthesized over verified candidate progress evidence."""

    headline: str = Field(
        ...,
        description="Crisp, executive 1-sentence headline capturing trajectory or priority focus.",
    )
    summary: str = Field(
        ...,
        description="Concise qualitative synthesis of performance progression.",
    )
    key_observation: str = Field(
        ...,
        description="Primary evidence-based observation from recent sessions or dimension trends.",
    )
    evidence: str = Field(
        ...,
        description="Explicit supporting evidence grounded strictly in completed session scores, trends, or recurring patterns.",
    )
    recommended_action: str = Field(
        ...,
        description="Actionable, high-impact practice recommendation.",
    )
    source_type: str = Field(
        default="ai_grounded",
        description="Source of insight: 'ai_grounded', 'deterministic_fallback', or 'zero_state'.",
    )
    grounding_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence/grounding indicator.",
    )

    model_config = ConfigDict(from_attributes=True)


class DashboardProgressResponse(BaseModel):
    """Complete structured progress intelligence payload for the candidate dashboard."""

    total_completed_interviews: int = Field(ge=0)
    average_overall_score: Optional[float] = None
    best_overall_score: Optional[int] = None
    lowest_overall_score: Optional[int] = None
    latest_overall_score: Optional[int] = None

    overall_trend: OverallScoreTrendDTO
    dimension_trends: Dict[str, DimensionTrendDTO] = Field(default_factory=dict)
    recurring_weaknesses: List[RecurringPatternDTO] = Field(default_factory=list)
    recurring_strengths: List[RecurringPatternDTO] = Field(default_factory=list)
    role_breakdown: List[RolePerformanceDTO] = Field(default_factory=list)
    consistency: ConsistencyMetricDTO
    next_focus: Optional[ActionableNextFocusDTO] = None
    ai_insight: Optional[DashboardAIInsightDTO] = None
    recent_sessions_summary: List[ScoreProgressionPointDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CandidateCurrentStateDTO(BaseModel):
    """Snapshot of the candidate's latest interview performance state."""

    latest_overall_score: Optional[int] = None
    latest_dimension_scores: Dict[str, int] = Field(default_factory=dict)
    latest_strengths: List[str] = Field(default_factory=list)
    latest_improvements: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CandidateLongitudinalStateDTO(BaseModel):
    """Multi-session longitudinal performance trajectory and recurring patterns."""

    total_completed_interviews: int = Field(ge=0)
    overall_score_trajectory: List[int] = Field(default_factory=list)
    overall_direction: str = "Baseline"
    dimension_trajectories: Dict[str, List[int]] = Field(default_factory=dict)
    dimension_directions: Dict[str, str] = Field(default_factory=dict)
    recurring_weaknesses: List[RecurringPatternDTO] = Field(default_factory=list)
    recurring_strengths: List[RecurringPatternDTO] = Field(default_factory=list)
    consistency_rating: str = "Insufficient Data"

    model_config = ConfigDict(from_attributes=True)


class WeaknessResolutionStateDTO(BaseModel):
    """Deterministic tracking of recurring weakness lifecycle and resolution evidence."""

    canonical_topic: str
    display_title: str
    first_detected_date: Optional[str] = None
    latest_detected_date: Optional[str] = None
    sessions_observed_count: int = Field(ge=1)
    related_dimension: Optional[str] = "unknown"
    related_dimension_score_progression: List[int] = Field(default_factory=list)
    frequency_is_decreasing: bool = False
    status: Literal["active", "improving", "resolved"] = "active"

    model_config = ConfigDict(from_attributes=True)


class ActionableCoachingPlanDTO(BaseModel):
    """Deterministic actionable coaching plan with structured assignments and review conditions."""

    focus_topic: str
    category: Literal["Technical Core", "System Design", "Communication", "Role Fundamentals"]
    priority_level: Literal["P1 - Critical Recurring", "P2 - Recent Gap", "P3 - Dimension Calibration"]
    reason: str
    evidence: str
    practice_preset: Dict[str, str] = Field(default_factory=dict)
    concrete_actions: List[str] = Field(default_factory=list)
    success_metric: str
    review_condition: str

    model_config = ConfigDict(from_attributes=True)

