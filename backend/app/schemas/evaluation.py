"""Multi-Dimensional Evaluation and Scoring Pydantic v2 DTO schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TurnEvaluationItem(BaseModel):
    """Granular multi-dimensional evaluation for an individual interview question turn."""

    turn_index: int = Field(..., description="Zero-based index of the evaluated turn.")
    relevance_score: int = Field(
        ..., ge=0, le=100, description="Relevance and direct prompt alignment score (0-100)."
    )
    correctness_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Technical accuracy, factual correctness, and architectural depth score (0-100).",
    )
    keywords_score: int = Field(
        ..., ge=0, le=100, description="Key concepts and technical keyword coverage score (0-100)."
    )
    clarity_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Logical structure, communication clarity, and articulation score (0-100).",
    )
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence, assertiveness, and speech fluency score (0-100).",
    )
    covered_concepts: List[str] = Field(
        default_factory=list,
        description="List of key technical concepts/patterns successfully addressed.",
    )
    missed_concepts: List[str] = Field(
        default_factory=list,
        description="List of critical concepts or edge-case trade-offs that were omitted.",
    )
    ideal_answer_comparison: str = Field(
        ...,
        description="Concise comparison highlighting the gap against the senior benchmark response.",
    )
    turn_feedback: str = Field(
        ..., description="Specific, constructive feedback takeaway for this turn."
    )


class StrengthItem(BaseModel):
    """Specific technical strength demonstrated by the candidate."""

    title: str = Field(..., description="Short strength title (e.g. 'Strong Concurrency Awareness').")
    description: str = Field(
        ..., description="Evidence-backed description of where and how the strength was shown."
    )
    evidence_turn_index: Optional[int] = Field(
        None, description="Turn index where this strength was demonstrated."
    )


class ImprovementItem(BaseModel):
    """Specific technical improvement area with actionable recommendations."""

    title: str = Field(
        ..., description="Short growth area title (e.g. 'Distributed Transaction Recovery')."
    )
    description: str = Field(
        ..., description="Explanation of what technical gaps were observed."
    )
    actionable_recommendation: str = Field(
        ..., description="Concrete study advice, patterns, or resources to master this area."
    )
    evidence_turn_index: Optional[int] = Field(
        None, description="Turn index where this improvement area was identified."
    )


class SessionEvaluationReport(BaseModel):
    """Structured Gemini LLM response schema for entire interview evaluation."""

    turns_evaluation: List[TurnEvaluationItem] = Field(
        ..., description="List of turn-level evaluations."
    )
    top_strengths: List[StrengthItem] = Field(
        ..., description="Top 3-5 concrete technical strengths."
    )
    top_improvements: List[ImprovementItem] = Field(
        ..., description="Top 3-5 prioritized actionable improvement areas with study advice."
    )
    executive_summary: str = Field(
        ..., description="3-4 sentence comprehensive executive summary of candidate performance."
    )


class TurnEvaluationResponse(BaseModel):
    """API representation of an evaluated turn."""

    id: str
    session_id: str
    turn_index: int
    question_type: str
    question_text: str
    candidate_answer: Optional[str] = None
    ideal_answer: Optional[str] = None
    turn_duration_sec: Optional[int] = None
    relevance_score: Optional[int] = None
    correctness_score: Optional[int] = None
    keywords_score: Optional[int] = None
    clarity_score: Optional[int] = None
    confidence_score: Optional[int] = None
    turn_score: Optional[int] = None
    covered_concepts: List[str] = Field(default_factory=list)
    missed_concepts: List[str] = Field(default_factory=list)
    ideal_answer_comparison: Optional[str] = None
    turn_feedback: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionEvaluationReportResponse(BaseModel):
    """Complete API response for a finalized mock interview evaluation scorecard."""

    session_id: str
    target_role: str
    seniority_level: str
    interview_focus: str
    practice_mode: str
    status: str
    overall_score: int = Field(..., ge=0, le=100, description="Overall composite score (0-100).")
    dimension_scores: Dict[str, int] = Field(
        ..., description="Average scores for each of the 5 evaluation dimensions."
    )
    executive_summary: str
    top_strengths: List[StrengthItem]
    top_improvements: List[ImprovementItem]
    turns_evaluation: List[TurnEvaluationResponse]
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
