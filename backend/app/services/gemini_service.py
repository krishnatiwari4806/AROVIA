"""Gemini AI Structured Extraction Service using google-genai SDK."""

import asyncio
import json
import logging
from typing import List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.resume import ParsedResumeData

logger = logging.getLogger(__name__)

RESUME_EXTRACTION_PROMPT_TEMPLATE = """You are an expert technical resume parser for the AROVIA interview evaluation platform.
Extract structured professional career information from the following candidate resume.

<resume_text>
{raw_text}
</resume_text>

Instructions:
1. Extract all verified technical skills, programming languages, frameworks, databases, and tools into the `skills` list.
2. Estimate total years of professional software engineering experience as a float into `experience_years` (e.g. 4.5). If unknown or student, use 0.0.
3. Identify 1-4 core technical domains into `domains` (e.g. "Backend Systems", "Distributed Systems", "Cloud & DevOps", "Fullstack Development").
4. Extract educational history into `education` items (institution, degree, graduation_year).
5. Write a concise 2-3 sentence executive summary into `summary` describing the candidate's core strengths and technical focus.
"""

JD_EXTRACTION_PROMPT_TEMPLATE = """You are an expert technical interviewer and job requirements analyzer for the AROVIA interview evaluation platform.
Extract structured target requirements, core responsibilities, and key technologies from the following Job Description (JD).

<job_description>
{raw_text}
</job_description>

Instructions:
1. Extract the target job title into `job_title` if specified, or null.
2. Extract all mandatory technical skills into `required_skills`.
3. Extract core job responsibilities into `core_responsibilities`.
4. Extract specific frameworks, languages, databases, cloud tools, or methodologies into `key_technologies`.
5. Provide a 1-2 sentence qualification summary into `experience_summary`.
"""


class ParsedJobDescription(BaseModel):
    """Structured extraction from a target Job Description."""

    job_title: Optional[str] = Field(
        None, description="Extracted or inferred target job title."
    )
    required_skills: List[str] = Field(
        default_factory=list, description="Mandatory technical and engineering skills."
    )
    core_responsibilities: List[str] = Field(
        default_factory=list, description="Primary duties and responsibilities."
    )
    key_technologies: List[str] = Field(
        default_factory=list,
        description="Specific frameworks, languages, databases, or cloud tools.",
    )
    experience_summary: str = Field(
        "", description="Summary of expected experience and qualification level."
    )


class GeminiService:
    """Service for interacting with Google Gemini models using the google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or (settings.GEMINI_API_KEY if settings else "")
        self.model = model or (
            settings.GEMINI_MODEL if settings else "gemini-2.5-flash"
        )
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        """Lazy client initialization."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def parse_resume(self, raw_text: str) -> ParsedResumeData:
        """Parse raw resume text into structured Pydantic schema using Gemini with 1 retry.

        Args:
            raw_text: Sanitized candidate resume text.

        Returns:
            ParsedResumeData: Structured extracted career profile.

        Raises:
            AppError (503): When AI service is unavailable or unrecoverable error occurs.
        """
        prompt = RESUME_EXTRACTION_PROMPT_TEMPLATE.format(raw_text=raw_text)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedResumeData,
            temperature=0.1,
        )

        last_exception: Optional[Exception] = None
        max_attempts = 2  # 1 initial try + 1 retry

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                if not response.text:
                    raise ValueError("Gemini returned empty response text.")

                # Validate and parse response JSON into Pydantic model
                parsed = ParsedResumeData.model_validate_json(response.text)
                return parsed

            except (PydanticValidationError, json.JSONDecodeError) as parse_err:
                logger.warning(
                    f"Gemini structured response schema parsing error on attempt {attempt}: {parse_err}"
                )
                last_exception = parse_err
            except Exception as exc:
                logger.warning(
                    f"Gemini API request failed on attempt {attempt}/{max_attempts}: {exc}"
                )
                last_exception = exc

            if attempt < max_attempts:
                # 1s exponential backoff before retry
                await asyncio.sleep(1.0)

        logger.error(
            f"Gemini structured resume extraction failed after {max_attempts} attempts: {last_exception}"
        )
        raise AppError(
            message="AI evaluation service is temporarily unavailable. Please retry shortly.",
            status_code=503,
            error_code="AI_SERVICE_UNAVAILABLE",
        )

    async def parse_job_description(self, raw_text: str) -> ParsedJobDescription:
        """Parse raw Job Description text into structured requirements.

        Falls back gracefully if AI service is temporarily unreachable to ensure
        session initialization is not blocked.

        Args:
            raw_text: Sanitized Job Description text.

        Returns:
            ParsedJobDescription: Structured requirements and technologies.
        """
        prompt = JD_EXTRACTION_PROMPT_TEMPLATE.format(raw_text=raw_text)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedJobDescription,
            temperature=0.1,
        )

        last_exception: Optional[Exception] = None
        max_attempts = 2

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                if not response.text:
                    raise ValueError("Gemini returned empty response text.")

                parsed = ParsedJobDescription.model_validate_json(response.text)
                return parsed

            except (PydanticValidationError, json.JSONDecodeError) as parse_err:
                logger.warning(
                    f"Gemini JD response schema parsing error on attempt {attempt}: {parse_err}"
                )
                last_exception = parse_err
            except Exception as exc:
                logger.warning(
                    f"Gemini JD request failed on attempt {attempt}/{max_attempts}: {exc}"
                )
                last_exception = exc

            if attempt < max_attempts:
                await asyncio.sleep(1.0)

        logger.warning(
            f"Gemini JD extraction failed after {max_attempts} attempts: {last_exception}. Falling back to default empty extraction."
        )
        return ParsedJobDescription(
            job_title=None,
            required_skills=[],
            core_responsibilities=[],
            key_technologies=[],
            experience_summary="Job description captured (fallback parsing mode).",
        )


def get_gemini_service() -> GeminiService:
    """Dependency provider for GeminiService."""
    return GeminiService()
