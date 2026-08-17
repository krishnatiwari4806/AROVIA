"""Pydantic schemas for Resume ingestion, structured extraction, and CRUD operations."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EducationItem(BaseModel):
    """Educational qualification entry."""

    institution: str = Field(..., description="Name of the school, university, or college.")
    degree: Optional[str] = Field(None, description="Degree or program title (e.g. B.Tech Computer Science).")
    graduation_year: Optional[str] = Field(None, description="Year or date range of graduation.")


class ParsedResumeData(BaseModel):
    """Standardized AI-extracted resume profile data."""

    skills: List[str] = Field(
        default_factory=list,
        description="Extracted technical skills, programming languages, frameworks, and tools.",
    )
    experience_years: float = Field(
        default=0.0,
        ge=0.0,
        description="Total estimated years of professional software engineering experience.",
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Core technical domain specializations (e.g. Backend, Cloud, ML/AI, Fullstack).",
    )
    education: List[EducationItem] = Field(
        default_factory=list,
        description="List of educational qualifications and degrees.",
    )
    summary: str = Field(
        default="",
        description="2-3 sentence executive career summary highlighting candidate focus and strengths.",
    )


class ResumeParsedDataUpdateRequest(BaseModel):
    """Candidate manual override/edit schema for parsed resume data."""

    skills: Optional[List[str]] = Field(None, description="Updated list of technical skills.")
    experience_years: Optional[float] = Field(None, ge=0.0, description="Updated experience in years.")
    domains: Optional[List[str]] = Field(None, description="Updated technical domains.")
    education: Optional[List[EducationItem]] = Field(None, description="Updated education history.")
    summary: Optional[str] = Field(None, description="Updated executive summary.")


class ResumeResponse(BaseModel):
    """Public candidate resume response schema."""

    id: str
    user_id: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    parsed_data: ParsedResumeData
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeUploadResponse(BaseModel):
    """Response returned upon successful resume upload and parsing."""

    message: str = "Resume successfully uploaded and parsed."
    resume: ResumeResponse
