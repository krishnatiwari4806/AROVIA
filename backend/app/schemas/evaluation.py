"""Multi-Dimensional Evaluation and Scoring Pydantic v2 DTO schemas."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnswerQualityTier(str, Enum):
    """Authoritative quality tier classification for candidate interview answers."""

    STRONG = "strong"
    PARTIAL = "partial"
    WEAK = "weak"
    INCORRECT = "incorrect"
    IRRELEVANT = "irrelevant"
    NON_ANSWER = "non_answer"
    PASS = "pass"
    EMPTY = "empty"


class AnswerClassificationResult(BaseModel):
    """Structured deterministic or semantic answer classification result."""

    answer_quality_tier: AnswerQualityTier = Field(
        ..., description="Authoritative quality tier assigned to the answer."
    )
    normalized_answer: str = Field(
        ..., description="Normalized answer text (cleaned whitespace, punctuation stripped for comparison)."
    )
    is_non_answer: bool = Field(
        default=False, description="True if answer is an explicit admission of not knowing, passing, or skipping."
    )
    is_empty: bool = Field(
        default=False, description="True if answer is blank, whitespace-only, or missing."
    )
    is_short_but_valid: bool = Field(
        default=False, description="True if answer is concise (e.g. 1-4 words) but contains valid technical content."
    )
    classification_reason: str = Field(
        ..., description="Deterministic or semantic justification for this classification."
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in classification decision (0.0 to 1.0), distinct from candidate speech confidence."
    )
    evidence: List[str] = Field(
        default_factory=list, description="Specific terms, triggers, or concept matches supporting classification."
    )


class ConceptImportance(str, Enum):
    """Importance weighting tier for an evaluated technical or behavioral concept."""

    CORE = "core"
    SUPPORTING = "supporting"


class ExpectedConcept(BaseModel):
    """Structured technical/behavioral concept expected in an ideal response."""

    concept: str = Field(..., description="Short canonical name of the expected concept or pattern.")
    importance: ConceptImportance = Field(
        default=ConceptImportance.CORE,
        description="Importance level: 'core' (essential) or 'supporting' (depth/nuance).",
    )
    description: Optional[str] = Field(
        None, description="Brief explanation of what understanding should be demonstrated."
    )


class EvidenceCategory(str, Enum):
    """Classification of candidate evidence relative to expected concepts and reference knowledge."""

    SUPPORTED = "supported"
    MISSING = "missing"
    CONTRADICTED = "contradicted"
    IRRELEVANT = "irrelevant"
    UNSUPPORTED = "unsupported"


class ConceptEvidence(BaseModel):
    """Evidence mapping candidate response statements to expected concepts."""

    concept: str = Field(..., description="The evaluated concept name.")
    importance: ConceptImportance = Field(
        default=ConceptImportance.CORE, description="Importance level of the concept."
    )
    evidence_status: EvidenceCategory = Field(
        ..., description="Evidence status: supported, missing, contradicted, irrelevant, unsupported."
    )
    candidate_quote: Optional[str] = Field(
        None, description="Verbatim or summarized quote from candidate answer demonstrating the evidence."
    )
    notes: Optional[str] = Field(
        None, description="Evaluator note explaining the evidence classification."
    )


class EvaluationRubric(BaseModel):
    """Structured, explainable evaluation rubric calibrated for a specific question intent."""

    question_intent: str = Field(
        ..., description="Intent classification (e.g. project_deep_dive, core_skill, scenario, behavioral)."
    )
    expected_knowledge: str = Field(
        ..., description="Summary of domain knowledge and mechanics evaluated in this question."
    )
    expected_concepts: List[ExpectedConcept] = Field(
        default_factory=list, description="Structured expected concepts list with core/supporting tiers."
    )
    strong_indicators: List[str] = Field(
        default_factory=list, description="Key characteristics of a STRONG / complete response."
    )
    partial_indicators: List[str] = Field(
        default_factory=list, description="Characteristics of a PARTIAL response with conceptual gaps."
    )
    weak_indicators: List[str] = Field(
        default_factory=list, description="Indicators of a WEAK or shallow response."
    )
    incorrect_indicators: List[str] = Field(
        default_factory=list, description="Specific factual contradictions or anti-patterns."
    )
    irrelevant_indicators: List[str] = Field(
        default_factory=list, description="Signs that the response addresses an unrelated topic."
    )


class ArchitectureNode(BaseModel):
    """Component node in a System Design reference architecture."""

    id: str = Field(..., description="Unique node identifier within the diagram.")
    label: str = Field(..., description="Human-readable title (e.g. 'Redis Sliding Window Cluster').")
    type: str = Field(
        ...,
        description="Component classification: client, gateway, service, cache, database, queue, external.",
    )
    purpose: str = Field(
        ..., description="Architectural responsibility of this component in the system."
    )
    is_core: bool = Field(
        default=True,
        description="True if this is a primary component for the solution; False if secondary/observability.",
    )


class ArchitectureEdge(BaseModel):
    """Directed connection or protocol flow between architecture nodes."""

    source: str = Field(..., description="Source node id.")
    target: str = Field(..., description="Target node id.")
    label: str = Field(..., description="Relationship description (e.g. 'Lookup Token Balance').")
    protocol: Optional[str] = Field(
        None, description="Communication protocol (e.g. https, grpc, sql, redis, kafka, ws)."
    )
    mode: Optional[str] = Field(
        default="sync", description="Interaction mode: 'sync' or 'async'."
    )


class SystemDesignReferenceArchitecture(BaseModel):
    """Deterministic, educational Senior Reference Architecture Blueprint for System Design turns."""

    scenario_id: str = Field(..., description="Canonical scenario identifier.")
    title: str = Field(..., description="Architectural blueprint title.")
    description: str = Field(..., description="Summary of the senior-level reference design.")
    nodes: List[ArchitectureNode] = Field(default_factory=list, description="Topological nodes.")
    edges: List[ArchitectureEdge] = Field(default_factory=list, description="Topological directed edges.")
    key_tradeoffs: List[str] = Field(
        default_factory=list, description="Critical architectural trade-offs to evaluate."
    )
    failure_considerations: List[str] = Field(
        default_factory=list, description="Failure modes, network partitions, and resilience mechanisms."
    )
    scaling_considerations: List[str] = Field(
        default_factory=list, description="Horizontal scaling, partitioning, and bottleneck mitigation."
    )


class QuestionReferencePayload(BaseModel):
    """Complete authoritative reference answer, expected concepts, and rubric container for a question."""

    question_id: Optional[str] = Field(None, description="Canonical Question Bank ID if applicable.")
    question_text: str = Field(..., description="The exact question text asked to the candidate.")
    question_intent: str = Field(
        default="core_skill", description="Strategic question intent (project, core_skill, scenario, behavioral, etc.)."
    )
    reference_answer: str = Field(
        ..., description="Benchmark senior technical or behavioral response for this specific question."
    )
    primary_concept: str = Field(
        ..., description="Primary domain competency or architectural topic evaluated."
    )
    expected_concepts: List[ExpectedConcept] = Field(
        default_factory=list, description="Authoritative list of expected concepts with importance tiers."
    )
    rubric: Optional[EvaluationRubric] = Field(
        None, description="Intent-calibrated evaluation rubric for this question."
    )
    architecture_blueprint: Optional[SystemDesignReferenceArchitecture] = Field(
        None, description="Optional deterministic System Design reference blueprint."
    )
    source: str = Field(
        default="curated_deterministic",
        description="Source of reference payload: 'question_bank', 'curated_deterministic', 'planner_archetype', 'gemini_validated'.",
    )
    is_candidate_specific: bool = Field(
        default=False,
        description="True if question was grounded in candidate resume/JD rather than a static question bank.",
    )


class CompletenessLevel(str, Enum):
    """Assessment of whether an answer sufficiently covers what the question asked."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    NONE = "none"


class SemanticEvaluationResult(BaseModel):
    """Complete semantic evaluation outcome for a single candidate answer against a question reference."""

    is_relevant: bool = Field(..., description="True if answer directly and substantively addresses the question.")
    relevance_reason: str = Field(..., description="Evidence justification for relevance decision.")
    is_correct: bool = Field(..., description="True if technical claims are accurate without material factual contradictions.")
    correctness_reason: str = Field(..., description="Evidence justification for technical correctness.")
    completeness: CompletenessLevel = Field(
        default=CompletenessLevel.PARTIAL,
        description="Degree to which core and supporting concepts are addressed (complete, partial, insufficient, none).",
    )
    completeness_reason: str = Field(..., description="Evidence justification for completeness assessment.")
    concept_evidence: List[ConceptEvidence] = Field(
        default_factory=list, description="Granular evidence mapping per expected concept."
    )
    covered_concepts: List[str] = Field(
        default_factory=list, description="List of expected concept names verified as SUPPORTED."
    )
    missed_concepts: List[str] = Field(
        default_factory=list, description="List of expected concept names categorized as MISSING."
    )
    contradicted_claims: List[str] = Field(
        default_factory=list, description="Specific candidate statements that contradict technical domain facts."
    )
    unsupported_claims: List[str] = Field(
        default_factory=list, description="Claims made by candidate that lack supporting domain evidence."
    )
    assigned_tier: AnswerQualityTier = Field(
        ..., description="Recommended quality tier derived from semantic evidence."
    )
    classification_reason: str = Field(
        ..., description="Comprehensive justification combining relevance, correctness, and completeness."
    )
    reference_answer: Optional[str] = Field(
        default=None, description="Authoritative reference answer used as baseline for evaluation."
    )


class TurnEvaluationItem(BaseModel):
    """Granular multi-dimensional evaluation for an individual interview question turn."""

    turn_index: int = Field(..., description="Zero-based index of the evaluated turn.")
    answer_quality_tier: AnswerQualityTier = Field(
        default=AnswerQualityTier.STRONG,
        description="Authoritative quality tier assigned to the candidate's answer.",
    )
    classification_reason: Optional[str] = Field(
        None,
        description="Concise justification for the answer quality tier classification.",
    )
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
    expected_concepts: List[ExpectedConcept] = Field(
        default_factory=list,
        description="Structured list of expected concepts with importance tiers for this turn.",
    )
    concept_evidence: List[ConceptEvidence] = Field(
        default_factory=list,
        description="Evidence classification of candidate answer against expected concepts.",
    )
    completeness: Optional[CompletenessLevel] = Field(
        None, description="Degree of concept completeness achieved for this question."
    )
    contradicted_claims: List[str] = Field(
        default_factory=list, description="Specific erroneous or contradictory claims detected in candidate answer."
    )
    unsupported_claims: List[str] = Field(
        default_factory=list, description="Unverified or unsubstantiated claims outside known project context."
    )
    reference_answer: Optional[str] = Field(
        None,
        description="Authoritative reference benchmark answer for this turn.",
    )
    architecture_blueprint: Optional[SystemDesignReferenceArchitecture] = Field(
        None,
        description="Optional deterministic System Design reference blueprint for this turn.",
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
    question_type: Optional[str] = "technical"
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
    expected_concepts: List[ExpectedConcept] = Field(default_factory=list)
    concept_evidence: List[ConceptEvidence] = Field(default_factory=list)
    completeness: Optional[CompletenessLevel] = None
    contradicted_claims: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    reference_answer: Optional[str] = None
    architecture_blueprint: Optional[SystemDesignReferenceArchitecture] = None
    ideal_answer_comparison: Optional[str] = None
    turn_feedback: Optional[str] = None
    answer_quality_tier: Optional[AnswerQualityTier] = None
    classification_reason: Optional[str] = None
    is_follow_up: Optional[bool] = False
    parent_turn_id: Optional[str] = None
    remediation_note: Optional[str] = None
    remediated_parent_concepts: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SessionEvaluationReportResponse(BaseModel):
    """Complete API response for a finalized mock interview evaluation scorecard."""

    session_id: str
    target_role: str
    seniority_level: str
    interview_focus: str
    preferred_language: str = "en"
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
