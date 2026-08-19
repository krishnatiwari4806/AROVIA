"""Gemini AI Structured Extraction and Evaluation Service using google-genai SDK."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.evaluation import (
    ImprovementItem,
    SessionEvaluationReport,
    StrengthItem,
    TurnEvaluationItem,
)
from app.schemas.interview import GeneratedQuestion, NextTurnDecision
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

INITIAL_QUESTION_PROMPT_TEMPLATE = """You are an expert technical interviewer conducting an adaptive mock interview for the AROVIA platform.
Generate the very first question (Turn 0) for this candidate.

Candidate Target Profile:
- Target Role: {target_role}
- Seniority Level: {seniority_level}
- Interview Focus: {interview_focus}
- Focus Skills: {focus_skills}

Job Description Context:
{jd_context}

Candidate Resume Background:
{resume_context}

Instructions:
1. Turn 0 is a warm-up question establishing baseline engineering context, domain background, or a key project mentioned on their resume that relates to the target role.
2. Formulate a realistic, clear, and conversational interview question in `question_text`.
3. Provide a comprehensive senior-level benchmark answer in `ideal_answer` covering expected technical depths, concepts, and best practices.
4. Specify the primary concept being evaluated in `primary_concept`.
"""

ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE = """You are the AI technical interviewer for the AROVIA platform conducting an adaptive mock interview.
Evaluate the candidate's latest response and determine the next interview step.

Candidate Target Profile:
- Target Role: {target_role}
- Seniority Level: {seniority_level}
- Interview Focus: {interview_focus}
- Focus Skills: {focus_skills}

Interview State & Pacing:
- Current Turn Index: {current_turn_index}
- Remaining Core Questions: {remaining_core_questions}
- Remaining Follow-up Budget: {remaining_followup_budget}
- Prior Turn Was Follow-up: {prior_turn_was_followup}

Previous Turn Q&A:
- Question Prompt: {previous_question}
- Candidate Answer: {candidate_answer}

Full Transcript History (Prior Turns):
{transcript_history}

Adaptive Logic & Rules:
1. If `prior_turn_was_followup` is True, you CANNOT generate another follow-up. You MUST advance to the next core topic (or conclude if all core questions are done).
2. If `remaining_followup_budget` <= 0, you CANNOT generate a follow-up. You MUST advance to the next core topic (or conclude if all core questions are done).
3. If `remaining_core_questions` <= 0 and no follow-up is warranted (or budget exhausted), set `is_interview_complete=True`, `is_follow_up=False`, and leave question_text null.
4. If follow-up IS allowed (`prior_turn_was_followup` is False and `remaining_followup_budget` > 0):
   - Evaluate candidate answer: Did the candidate make bold claims without explaining mechanics? Was the answer shallow, vague, or missing critical trade-offs?
   - If YES: set `is_follow_up=True`, explain why in `follow_up_reasoning`, formulate a targeted probing question in `question_text`, provide `ideal_answer`, and `primary_concept`.
   - If NO (answer was thorough/complete) OR candidate answered well: set `is_follow_up=False`, formulate the next core question according to the progressive difficulty arc (Core Concepts -> Edge Cases & System Trade-offs), provide `ideal_answer`, and `primary_concept`.
5. Ensure the next question does not duplicate topics already thoroughly covered in prior turns.
"""

SESSION_EVALUATION_PROMPT_TEMPLATE = """You are the Chief Technical Interview Evaluator for the AROVIA platform.
Perform a rigorous, multi-dimensional assessment of the candidate's complete interview session.

Candidate Target Profile:
- Target Role: {target_role}
- Seniority Level: {seniority_level}
- Interview Focus: {interview_focus}
- Focus Skills: {focus_skills}

Job Description Context:
{jd_context}

Candidate Resume Background:
{resume_context}

Complete Interview Transcript (Questions, Candidate Answers, Benchmark Ideal Answers):
{transcript_data}

Evaluation Instructions:
1. For EACH turn in the transcript, evaluate and score (0-100 integers):
   - `relevance_score`: How directly and thoroughly the answer addressed the specific question asked.
   - `correctness_score`: Technical accuracy, architectural depth, correctness of data structures, algorithms, protocols, or design patterns.
   - `keywords_score`: Coverage of core domain terminology, frameworks, and engineering concepts.
   - `clarity_score`: Communication structure, logical flow, articulation, and concise phrasing.
   - `confidence_score`: Assertiveness, technical conviction, and decisive engineering authority.
   - `covered_concepts`: List of technical concepts, patterns, or tools successfully explained.
   - `missed_concepts`: List of critical technical considerations, failure edge cases, or trade-offs omitted.
   - `ideal_answer_comparison`: 2-3 sentence diff comparing candidate response against the benchmark ideal answer.
   - `turn_feedback`: 1-2 sentence constructive takeaway for this question.

2. Synthesize Session-Level Insights:
   - `top_strengths`: 3-5 concrete, evidence-backed engineering strengths demonstrated by the candidate (include title, detailed description, and evidence_turn_index).
   - `top_improvements`: 3-5 prioritized technical growth areas (include title, description of gap, concrete actionable study recommendation/resources, and evidence_turn_index).
   - `executive_summary`: 3-4 sentence comprehensive executive summary of overall candidate performance against the target seniority standard.
"""


def _build_fallback_evaluation_report(
    transcript_turns: List[Dict[str, Any]], target_role: str, seniority_level: str
) -> SessionEvaluationReport:
    """Construct a high-quality fallback evaluation report if the AI service experiences a transient outage."""
    turn_evals: List[TurnEvaluationItem] = []
    for t in transcript_turns:
        t_idx = t.get("turn_index", 0)
        ans = t.get("candidate_answer") or ""
        word_count = len(ans.split())
        base = min(85, max(40, 50 + int(word_count * 0.3)))
        turn_evals.append(
            TurnEvaluationItem(
                turn_index=t_idx,
                relevance_score=base,
                correctness_score=base,
                keywords_score=max(40, base - 5),
                clarity_score=min(90, base + 5),
                confidence_score=base,
                covered_concepts=["Core Problem Solving", "Domain Fundamentals"],
                missed_concepts=["Edge Case Handling", "High Scale Stress Scenarios"],
                ideal_answer_comparison=f"The candidate outlined fundamental concepts for {target_role}. A senior-level benchmark would incorporate deeper architectural trade-offs and failure mitigation strategies.",
                turn_feedback=f"Clear high-level overview. Deepen explanations of underlying mechanics and performance trade-offs for {seniority_level} roles.",
            )
        )

    return SessionEvaluationReport(
        turns_evaluation=turn_evals,
        top_strengths=[
            StrengthItem(
                title="Structured Communication",
                description=f"Demonstrated clear communication and logical problem breakdown appropriate for a {seniority_level} {target_role}.",
                evidence_turn_index=0,
            ),
            StrengthItem(
                title="Foundational Knowledge",
                description="Showed solid familiarity with core engineering patterns and technology fundamentals.",
                evidence_turn_index=0,
            ),
        ],
        top_improvements=[
            ImprovementItem(
                title="Deep Architectural Trade-offs",
                description="Answers focused on standard happy paths without analyzing system failure modes or high concurrency bottlenecks.",
                actionable_recommendation=f"Review distributed systems patterns, database indexing internals, and cache invalidation strategies relevant to {target_role}.",
                evidence_turn_index=0,
            ),
            ImprovementItem(
                title="Concrete Metric & Impact Evidence",
                description="Technical explanations could benefit from referencing concrete operational metrics (latencies, QPS, error budgets).",
                actionable_recommendation="Practice framing technical decisions using measurable benchmarks and operational trade-offs.",
                evidence_turn_index=0,
            ),
        ],
        executive_summary=f"The candidate completed the mock interview for {target_role} ({seniority_level}) demonstrating solid domain fundamentals and structured thinking. Enhancing technical depth in edge cases, distributed failure recovery, and architectural trade-offs will elevate readiness for senior-level evaluations.",
    )


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
        """Parse raw resume text into structured Pydantic schema using Gemini with 1 retry."""
        prompt = RESUME_EXTRACTION_PROMPT_TEMPLATE.format(raw_text=raw_text)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedResumeData,
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
        """Parse raw Job Description text into structured requirements."""
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

    async def generate_initial_question(
        self,
        target_role: str,
        seniority_level: str,
        interview_focus: str,
        focus_skills: Optional[List[str]] = None,
        parsed_jd_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
    ) -> GeneratedQuestion:
        """Generate the first initial core interview question (Turn 0)."""
        jd_ctx = (
            json.dumps(parsed_jd_data, indent=2)
            if parsed_jd_data
            else "No custom job description provided."
        )
        resume_ctx = (
            json.dumps(resume_data, indent=2)
            if resume_data
            else "No candidate resume provided."
        )
        skills_str = ", ".join(focus_skills) if focus_skills else "General technical core"

        prompt = INITIAL_QUESTION_PROMPT_TEMPLATE.format(
            target_role=target_role,
            seniority_level=seniority_level,
            interview_focus=interview_focus,
            focus_skills=skills_str,
            jd_context=jd_ctx,
            resume_context=resume_ctx,
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedQuestion,
            temperature=0.4,
        )

        max_attempts = 2
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                if response.text:
                    return GeneratedQuestion.model_validate_json(response.text)
            except Exception as exc:
                logger.warning(
                    f"Gemini initial question generation attempt {attempt}/{max_attempts} failed: {exc}"
                )
                last_exception = exc

            if attempt < max_attempts:
                await asyncio.sleep(1.0)

        logger.warning(
            f"Initial question generation failed: {last_exception}. Using fallback template question."
        )
        return GeneratedQuestion(
            question_text=f"To start our interview for the {target_role} position, could you walk me through a technically complex project you built recently and the key architectural decisions you made?",
            ideal_answer="A structured walkthrough of an end-to-end system including requirements, architectural choices, database design, trade-offs, and scalability bottlenecks.",
            primary_concept="System Architecture & Project Walkthrough",
        )

    async def evaluate_and_generate_next_turn(
        self,
        target_role: str,
        seniority_level: str,
        interview_focus: str,
        focus_skills: Optional[List[str]],
        current_turn_index: int,
        remaining_core_questions: int,
        remaining_followup_budget: int,
        prior_turn_was_followup: bool,
        previous_question: str,
        candidate_answer: str,
        transcript_history: List[Dict[str, Any]],
    ) -> NextTurnDecision:
        """Evaluate candidate answer and decide whether to probe deeper or advance."""
        history_str = "\n".join(
            [
                f"Turn {t.get('turn_index')}: [Q: {t.get('question_text')}] -> [A: {t.get('candidate_answer')}]"
                for t in transcript_history
            ]
        ) or "None (Turn 0 completed)"

        skills_str = ", ".join(focus_skills) if focus_skills else "General technical skills"

        prompt = ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE.format(
            target_role=target_role,
            seniority_level=seniority_level,
            interview_focus=interview_focus,
            focus_skills=skills_str,
            current_turn_index=current_turn_index,
            remaining_core_questions=remaining_core_questions,
            remaining_followup_budget=remaining_followup_budget,
            prior_turn_was_followup=prior_turn_was_followup,
            previous_question=previous_question,
            candidate_answer=candidate_answer,
            transcript_history=history_str,
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=NextTurnDecision,
            temperature=0.3,
        )

        max_attempts = 2
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                if response.text:
                    return NextTurnDecision.model_validate_json(response.text)
            except Exception as exc:
                logger.warning(
                    f"Gemini next turn generation attempt {attempt}/{max_attempts} failed: {exc}"
                )
                last_exception = exc

            if attempt < max_attempts:
                await asyncio.sleep(1.0)

        logger.warning(
            f"Adaptive next turn generation failed: {last_exception}. Using fallback turn decision."
        )
        if remaining_core_questions <= 0:
            return NextTurnDecision(
                is_follow_up=False,
                is_interview_complete=True,
                follow_up_reasoning="All core questions completed.",
            )

        return NextTurnDecision(
            is_follow_up=False,
            is_interview_complete=False,
            question_text=f"Moving on to our next topic for {target_role}: How do you approach caching, database indexing, and query optimization when scaling read-heavy services?",
            ideal_answer="A comprehensive discussion covering Redis/Memcached cache-aside patterns, TTLs, invalidation strategies, B-tree indexes, execution plans, and connection pooling.",
            primary_concept="Performance Optimization & Caching",
        )

    async def evaluate_interview_session(
        self,
        target_role: str,
        seniority_level: str,
        interview_focus: str,
        focus_skills: Optional[List[str]],
        transcript_turns: List[Dict[str, Any]],
        parsed_jd_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
    ) -> SessionEvaluationReport:
        """Perform comprehensive multi-dimensional assessment of a completed interview session."""
        jd_ctx = (
            json.dumps(parsed_jd_data, indent=2)
            if parsed_jd_data
            else "No custom job description provided."
        )
        resume_ctx = (
            json.dumps(resume_data, indent=2)
            if resume_data
            else "No candidate resume provided."
        )
        skills_str = ", ".join(focus_skills) if focus_skills else "General technical skills"

        transcript_data = "\n\n".join(
            [
                f"Turn {t.get('turn_index')}:\n"
                f"- Question: {t.get('question_text')}\n"
                f"- Candidate Answer: {t.get('candidate_answer')}\n"
                f"- Ideal Answer Benchmark: {t.get('ideal_answer')}"
                for t in transcript_turns
            ]
        )

        prompt = SESSION_EVALUATION_PROMPT_TEMPLATE.format(
            target_role=target_role,
            seniority_level=seniority_level,
            interview_focus=interview_focus,
            focus_skills=skills_str,
            jd_context=jd_ctx,
            resume_context=resume_ctx,
            transcript_data=transcript_data,
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SessionEvaluationReport,
            temperature=0.2,
        )

        max_attempts = 2
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                if response.text:
                    return SessionEvaluationReport.model_validate_json(response.text)
            except Exception as exc:
                logger.warning(
                    f"Gemini session evaluation attempt {attempt}/{max_attempts} failed: {exc}"
                )
                last_exception = exc

            if attempt < max_attempts:
                await asyncio.sleep(1.0)

        logger.warning(
            f"Session evaluation generation failed: {last_exception}. Using fallback evaluation report."
        )
        return _build_fallback_evaluation_report(
            transcript_turns=transcript_turns,
            target_role=target_role,
            seniority_level=seniority_level,
        )


def get_gemini_service() -> GeminiService:
    """Dependency provider for GeminiService."""
    return GeminiService()
