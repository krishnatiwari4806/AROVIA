"""Interview setup and configuration Pydantic v2 DTO schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SeniorityLevel(str, Enum):
    """Target candidate seniority level tier."""

    junior = "junior"
    mid = "mid"
    senior = "senior"


class InterviewFocus(str, Enum):
    """Interview assessment focus dimension."""

    technical_core = "Technical Core"
    system_design = "System Design"
    behavioral = "Behavioral"


class PracticeMode(str, Enum):
    """Interview length and pacing calibration mode."""

    full = "full"
    quick = "quick"


class SessionStatus(str, Enum):
    """Interview session lifecycle state."""

    in_progress = "in_progress"
    evaluating = "evaluating"
    completed = "completed"
    abandoned = "abandoned"


class RolePresetItem(BaseModel):
    """Curated standard technical role preset item."""

    role_id: str = Field(..., description="Unique role identifier.")
    title: str = Field(..., description="Display title for the role.")
    description: str = Field(..., description="Brief summary of the role scope.")
    default_skills: List[str] = Field(
        default_factory=list, description="Curated baseline technical skills."
    )
    recommended_seniority: List[str] = Field(
        default_factory=list, description="Recommended seniority tiers."
    )


class PresetsCatalogResponse(BaseModel):
    """Complete catalog of role presets, seniority levels, focus areas, and pacing rules."""

    roles: List[RolePresetItem]
    seniority_levels: List[Dict[str, str]]
    focus_areas: List[Dict[str, str]]
    practice_modes: List[Dict[str, Any]]
    pacing_guidelines: Dict[str, int]


class InterviewSessionCreateRequest(BaseModel):
    """Request payload to initialize a mock interview session."""

    target_role: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Target job title (preset or custom).",
    )
    seniority_level: SeniorityLevel = Field(
        ..., description="Candidate target seniority tier."
    )
    interview_focus: InterviewFocus = Field(
        ..., description="Primary interview focus dimension."
    )
    practice_mode: PracticeMode = Field(
        default=PracticeMode.full,
        description="Pacing mode: full (6 core/9 max) or quick (3 core/5 max).",
    )
    custom_job_desc: Optional[str] = Field(
        None,
        max_length=10000,
        description="Optional pasted Job Description text (max 10,000 chars).",
    )
    focus_skills: Optional[List[str]] = Field(
        default_factory=list,
        description="List of specific focus skills or technologies to prioritize.",
    )


class InterviewSessionResponse(BaseModel):
    """Response DTO for an initialized or retrieved interview session."""

    id: str
    user_id: str
    resume_id: Optional[str] = None
    target_role: str
    seniority_level: str
    interview_focus: str
    practice_mode: str
    planned_core_questions: int
    max_total_turns: int
    current_turn_index: int
    status: str
    focus_skills: Optional[List[str]] = None
    custom_job_desc: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
