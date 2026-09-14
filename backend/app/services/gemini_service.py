"""Gemini AI Structured Extraction and Evaluation Service using google-genai SDK."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.evaluation import (
    AnswerQualityTier,
    CompletenessLevel,
    ConceptImportance,
    EvidenceCategory,
    ExpectedConcept,
    ImprovementItem,
    QuestionReferencePayload,
    SemanticEvaluationResult,
    SessionEvaluationReport,
    StrengthItem,
    TurnEvaluationItem,
)
from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.schemas.resume import ParsedResumeData
from app.services.answer_classifier import is_non_answer
from app.services.candidate_context import CandidateContext, build_candidate_context
from app.services.conversational_bridge import get_conversational_bridge_engine
from app.services.question_bank import (
    get_competency_stages,
    get_fallback_followup,
    get_fallback_question,
)
from app.services.question_planner import (
    QuestionIntent,
    QuestionPlan,
    QuestionPlanner,
    get_question_planner,
)
from app.services.reference_evaluator import get_reference_evaluator_service
from app.services.score_calibrator import get_score_calibrator
from app.services.semantic_evaluator import get_semantic_evaluator_engine

logger = logging.getLogger(__name__)

RESUME_EXTRACTION_PROMPT_TEMPLATE = """You are an expert technical resume parser for the AROVIA interview evaluation platform.
Extract structured professional career information, engineering projects, and work history from the following candidate resume.

<resume_text>
{raw_text}
</resume_text>

Instructions:
1. Extract all verified technical skills, programming languages, frameworks, databases, and tools into the `skills` list.
2. Estimate total years of professional software engineering experience as a float into `experience_years` (e.g. 4.5). If unknown or student, use 0.0.
3. Identify 1-4 core technical domains into `domains` (e.g. "Backend Systems", "Distributed Systems", "Cloud & DevOps", "Fullstack Development").
4. Extract educational history into `education` items (institution, degree, graduation_year).
5. Write a concise 2-3 sentence executive summary into `summary` describing the candidate's core strengths and technical focus.
6. Extract all candidate engineering projects into `projects`:
   - `title`: Project name or title.
   - `description`: Brief summary of what the project does.
   - `technologies`: Specific languages, frameworks, databases, and tools used in this project.
   - `responsibilities`: Candidate's specific contribution or ownership if stated.
   - `architecture_details`: Architectural patterns, system design, data flows, or implementation details if present in the resume.
   - `challenges`: Key technical challenges or trade-offs mentioned, or null if none specified.
   - `outcomes`: Quantifiable metrics, performance improvements, user scale, or outcomes if stated, or null if none specified.
   - If no distinct projects are mentioned, return an empty list `[]`.
7. Extract professional work history into `work_history`:
   - `company`: Company or organization name.
   - `role`: Job title or role held.
   - `duration`: Date range or duration string (e.g. "Jun 2021 - Aug 2023").
   - `responsibilities`: List of core duties, technical responsibilities, and system ownership.
   - `technologies`: List of tools/technologies used in this role.
   - `achievements`: List of notable quantifiable achievements or feature deliveries.
   - If no formal work experience is listed (e.g. student resume), return an empty list `[]`.
8. STRICT ACCURACY RULE: ONLY extract information explicitly present in the resume text. Do NOT fabricate, assume, or hallucinate projects, companies, metrics, or technologies that are not stated in the resume. Set missing or unstated optional fields to null or empty lists.
"""

def _get_language_instructions(preferred_language: Optional[str]) -> str:
    """Format prompt guidelines for candidate preferred interview language."""
    lang = (preferred_language or "en").lower().strip()
    if lang == "hi":
        return (
            "Preferred Interview Language: Hindi\n"
            "Language Guidelines:\n"
            "1. Formulate questions in natural, clear, conversational Hindi.\n"
            "2. Standard software engineering terminology (e.g., API, database, latency, microservices, cache, distributed locks, schema) should remain in standard English vocabulary without forced literal translations.\n"
            "3. Candidate is expected to respond in Hindi or mixed Hindi/English. Understand and process Hindi script or transliterated Hindi."
        )
    elif lang == "hinglish":
        return (
            "Preferred Interview Language: Hinglish (Hindi + English Code-Switching)\n"
            "Language Guidelines:\n"
            "1. Communicate naturally in Hinglish using conversational Hindi phrasing integrated with standard English technical terminology.\n"
            "2. Candidate may answer in mixed Hindi and English (e.g., 'Maine Redis use kiya because frequently accessed data ko cache karna tha', 'High traffic ke case mein database bottleneck ho sakta hai').\n"
            "3. Treat code-switching and natural Hindi/English mixing as completely valid technical communication; evaluate technical concepts without penalizing language mixing."
        )
    else:
        return (
            "Preferred Interview Language: English\n"
            "Language Guidelines:\n"
            "1. Formulate questions in clear, professional English.\n"
            "2. Candidate is expected to respond in English."
        )


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

def is_non_answer(answer: Optional[str]) -> bool:
    """Detect if a candidate answer is an explicit admission of not knowing, passing, or skipping."""
    if not answer or not answer.strip():
        return True
    norm = answer.strip().lower()
    non_answer_patterns = [
        "i don't know",
        "i do not know",
        "dont know",
        "dont kow",
        "no idea",
        "not sure",
        "i am not sure",
        "i'm not sure",
        "pass",
        "skip",
        "next question",
        "i haven't worked with",
        "i have not worked with",
        "not familiar",
        "mujhe nahi pata",
        "pata nahi",
        "nahi janta",
        "nhi pta",
        "no clue",
        "i have no experience",
        "no experience with this",
        "cannot answer",
        "can't answer",
    ]
    # Check if string matches or contains any non-answer phrase in short answers (< 15 words)
    words = norm.split()
    if len(words) <= 15:
        for p in non_answer_patterns:
            if p in norm:
                return True
    return False


def get_grounded_fallback_question(
    context: "CandidateContext",
    plan: Optional["QuestionPlan"] = None,
    language: str = "en",
    stage_index: int = 0,
    excluded_question_ids: Optional[Set[str]] = None,
) -> GeneratedQuestion:
    """Construct a high-quality deterministic fallback question strictly grounded in candidate/JD context."""
    from app.services.question_planner import QuestionIntent

    lang = (language or "en").lower().strip()

    if plan:
        intent = plan.intent
        topic = plan.topic

        if intent == QuestionIntent.RESUME_PROJECT:
            if lang == "hi":
                q_text = (
                    f"Maine dekha ki aapne '{topic}' project par kaam kiya hai. "
                    f"Kya aap iska system architecture aur key technical implementation explain kar sakte hain?"
                )
            elif lang == "hinglish":
                q_text = (
                    f"I noticed you built '{topic}'. Can you walk me through the system architecture "
                    f"aur explain karein ki aapne key technical components kaise implement kiye?"
                )
            else:
                q_text = (
                    f"I noticed you built '{topic}'. Could you walk me through the system architecture, "
                    f"core technical decisions, and how you structured the key components?"
                )
            return GeneratedQuestion(
                question_text=q_text,
                ideal_answer=f"Detailed architectural breakdown of {topic}, explaining component boundaries, data flow, error recovery, and tech stack choices.",
                primary_concept=plan.primary_concept or f"Project Architecture: {topic}",
            )

        elif intent == QuestionIntent.WORK_EXPERIENCE:
            if lang == "hi":
                q_text = (
                    f"{topic} mein apne experience ke dauran, aapne systems par kaam kiya. "
                    f"Wahan aapke saamne sabse challenging technical problem kya thi aur aapka solution kya tha?"
                )
            elif lang == "hinglish":
                q_text = (
                    f"During your time at {topic}, what was one of the most challenging technical problems you handled, "
                    f"aur aapne usko kaise resolve kiya?"
                )
            else:
                q_text = (
                    f"During your experience at {topic}, what was one of the most complex technical challenges "
                    f"you encountered in production and how did you resolve it?"
                )
            return GeneratedQuestion(
                question_text=q_text,
                ideal_answer=f"Structured STAR-format explanation of an engineering milestone at {topic}, outlining root-cause analysis, mitigation, and operational metrics.",
                primary_concept=plan.primary_concept or f"Production Engineering at {topic}",
            )

        elif intent == QuestionIntent.JD_REQUIREMENT:
            if lang == "hi":
                q_text = (
                    f"Is role ke liye {topic} ek important technical requirement hai. "
                    f"Production system mein {topic} use karte waqt aapka architecture and reliability approach kya rehta hai?"
                )
            elif lang == "hinglish":
                q_text = (
                    f"This role emphasizes practical experience with {topic}. Production environment mein {topic} "
                    f"ke sath kaam karte waqt aap concurrency and performance optimization ko kaise approach karte hain?"
                )
            else:
                q_text = (
                    f"This {context.target_role} role emphasizes strong practical capability with {topic}. "
                    f"How do you approach designing, optimizing, and debugging systems using {topic} in production?"
                )
            return GeneratedQuestion(
                question_text=q_text,
                ideal_answer=f"Comprehensive explanation of {topic} best practices, concurrency handling, indexing/query patterns, and fault isolation in production systems.",
                primary_concept=plan.primary_concept or f"JD Competency: {topic}",
            )

        elif intent == QuestionIntent.CORE_SKILL and context.has_resume:
            if lang == "hi":
                q_text = (
                    f"{topic} ke saath kaam karte waqt, aap concurrency, error handling aur performance optimization ko kaise manage karte hain?"
                )
            elif lang == "hinglish":
                q_text = (
                    f"Given your background in {topic}, aap concurrency, error handling aur performance optimization ko kaise handle karte hain?"
                )
            else:
                q_text = (
                    f"Given your background with {topic}, how do you approach concurrency, error handling, "
                    f"and performance optimization when designing scalable services?"
                )
            return GeneratedQuestion(
                question_text=q_text,
                ideal_answer=f"In-depth analysis of {topic} internals, async models, memory/CPU efficiency, and resilient error recovery patterns.",
                primary_concept=plan.primary_concept or f"Core Skill: {topic}",
            )

    # Question Bank role-calibrated fallback for standard curriculum or when resume/JD context is absent
    fallback_q = get_fallback_question(
        role=context.target_role,
        seniority=context.seniority_level,
        focus=context.interview_focus,
        stage_index=stage_index,
        excluded_question_ids=excluded_question_ids,
    )
    return GeneratedQuestion(
        question_text=fallback_q.question_text,
        ideal_answer=fallback_q.ideal_answer,
        primary_concept=fallback_q.primary_concept,
    )


def get_semantic_gap_fallback_followup(
    role: str,
    seniority: str = "mid",
    parent_concept: str = "Technical Architecture",
    target_missing_concept: str = "System Trade-offs",
    language: str = "en",
) -> GeneratedQuestion:
    """Generate deterministic, grounded follow-up targeting the specific missing concept in preferred language."""
    lang = (language or "en").lower().strip()
    clean_missing = (target_missing_concept or "underlying trade-offs").strip()

    if lang == "hi":
        q_text = (
            f"Aapne jo explain kiya uske aage, is architecture mein aap '{clean_missing}' ke implementation "
            f"aur trade-offs ko kaise handle karenge?"
        )
    elif lang == "hinglish":
        q_text = (
            f"Building on what you just explained, is architecture mein aap '{clean_missing}' ke implementation "
            f"aur trade-offs ko kaise approach karenge?"
        )
    else:
        q_text = (
            f"Building on what you just shared, could you explain how you would approach '{clean_missing}' "
            f"and its operational trade-offs in that architecture?"
        )

    return GeneratedQuestion(
        question_text=q_text,
        ideal_answer=f"Detailed technical explanation of {clean_missing} principles, implementation mechanics, and operational trade-offs in {role} systems.",
        primary_concept=clean_missing,
    )


INITIAL_QUESTION_PROMPT_TEMPLATE = """You are an expert technical interviewer for the AROVIA mock interview platform.
Generate the first core technical interview question (Core Question 1, following the Turn 0 conversational introduction).

### CANDIDATE CONTEXT
{candidate_context}

### JOB DESCRIPTION CONTEXT
{jd_context}

### INTERVIEW STATE & PACING
- Current Turn: Core Question 1 of {total_core_questions}
- Planned Question Intent: {planned_intent}
- Target Topic: {planned_topic}
- Grounding Snippet: {grounding_snippet}

### STRATEGIC GUIDANCE
{planner_guidance}

### LANGUAGE GUIDELINES
{language_instructions}

### QUESTION QUALITY & ANTI-HALLUCINATION RULES
1. STRICT ANTI-HALLUCINATION RULE: ONLY reference projects, companies, technologies, or achievements that are EXPLICITLY listed in the Candidate Context or Job Description above. NEVER fabricate or assume candidate projects, employers, metrics, or technologies.
2. If the planned intent is `resume_project`, formulate a natural, realistic question about that specific project and its technical mechanics.
3. If the candidate has no uploaded resume, ask a solid fundamental question targeting the role ({target_role}) and seniority ({seniority_level}).
4. Formulate ONE clear, conversational interview question in `question_text`.
5. Provide a comprehensive benchmark ideal answer in `ideal_answer` reflecting senior expectations.
6. Specify the evaluated technical concept in `primary_concept`.
"""

ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE = """You are an expert technical interviewer for the AROVIA mock interview platform conducting an adaptive technical interview.
Evaluate the candidate's latest response and determine the next interview turn (either a targeted follow-up probe or the next planned core question).

### CANDIDATE CONTEXT
{candidate_context}

### JOB DESCRIPTION CONTEXT
{jd_context}

### INTERVIEW STATE & PACING
- Core Question Number: {core_question_number} of {total_core_questions}
- Remaining Core Questions Budget: {remaining_core_questions}
- Remaining Follow-up Budget: {remaining_followup_budget}
- Prior Turn Was Follow-up: {prior_turn_was_followup}
- Follow-up Allowed on this Turn: {followup_allowed}
- Planned Next Core Intent: {planned_next_intent}
- Planned Next Core Topic: {planned_next_topic}
- Planned Next Core Grounding: {planned_next_grounding}

### SEMANTIC EVIDENCE OF LATEST ANSWER
- Answer Quality Tier: {evaluated_tier}
- Completeness Level: {evaluated_completeness}
- Covered Concepts: {covered_concepts_str}
- Missing Concepts (Priority): {missing_concepts_str}
- Target Missing Concept: {target_missing_concept}

### PREVIOUS CONVERSATION
Recent Turns Transcript:
{transcript_history}

Latest Question Asked:
{previous_question}

Candidate Latest Answer:
"{candidate_answer}"

### STRATEGIC GUIDANCE FOR NEXT QUESTION
{planner_guidance}

### LANGUAGE GUIDELINES
{language_instructions}

### ADAPTIVE DECISION & ANTI-HALLUCINATION RULES
1. NON-ANSWER / PASS / IRRELEVANT RULE: If candidate said "I don't know", "no idea", "pass", "skip", or gave an off-topic/empty answer (tier: {evaluated_tier}), DO NOT generate a follow-up probe. Set `is_follow_up=False` and advance to the next planned core question!
2. COMPLETE / STRONG ANSWER RULE: If candidate covered all core concepts thoroughly ({evaluated_completeness} / {evaluated_tier}), DO NOT ask redundant follow-up probes. Set `is_follow_up=False` and advance to the next planned core question ({planned_next_topic}).
3. SEMANTIC-GAP PROBE RULE: If `followup_allowed` is True and the candidate gave a partial/incomplete answer missing key concepts:
   - Set `is_follow_up=True`.
   - Provide `follow_up_reasoning` explaining that '{target_missing_concept}' was omitted.
   - Formulate a targeted, conversational follow-up in `question_text` specifically probing '{target_missing_concept}'. Do NOT ask about concepts already covered ({covered_concepts_str}).
4. ADVANCING TO NEXT CORE QUESTION: If `is_follow_up=False` and `remaining_core_questions` > 0:
   - Generate the next core question based on the Planned Next Core Intent ({planned_next_intent}) and Topic ({planned_next_topic}).
   - Ground the question strictly in the provided Candidate Context or Job Description without hallucinating facts.
5. CONVERSATIONAL TRANSITION: Include a brief, natural conversational transition phrase connecting the previous discussion to the next inquiry without repeating candidate words word-for-word.
6. INTERVIEW COMPLETION: If `remaining_core_questions` <= 0 and no follow-up is warranted:
   - Set `is_interview_complete=True`, `is_follow_up=False`, and leave question_text null.
7. AVOID DUPLICATION: Never repeat questions or topics already discussed in previous turns.
"""

SESSION_EVALUATION_PROMPT_TEMPLATE = """You are the Chief Technical Interview Evaluator for the AROVIA platform.
Perform a rigorous, evidence-based multi-dimensional assessment of the candidate's complete interview session.

Candidate Target Profile:
- Target Role: {target_role}
- Seniority Level: {seniority_level}
- Interview Focus: {interview_focus}
- Focus Skills: {focus_skills}

{language_instructions}

Job Description Context:
{jd_context}

Candidate Resume Background:
{resume_context}

Complete Interview Transcript (Questions, Candidate Answers, Benchmark Ideal Answers):
{transcript_data}

Evaluation Instructions:
1. For EACH turn in the transcript, classify and evaluate:
   - `answer_quality_tier`: Categorize the candidate's answer into exactly one of these 8 tiers:
     * "strong": Relevant, technically accurate, covers core expected concepts, directly answers the specific question with expected depth.
     * "partial": Relevant and correct knowledge but lacks completeness or leaves out critical concepts/trade-offs.
     * "weak": Relevant attempt but shallow, vague, or lacking mechanical detail.
     * "incorrect": Factually or technically erroneous claim or contradiction made in the attempt.
     * "irrelevant": Answers an off-topic subject completely different from what was asked.
     * "non_answer": Candidate explicitly stated they do not know, gave up, or cannot answer (e.g. "I don't know", "no idea").
     * "pass": Candidate explicitly requested to pass or skip.
     * "empty": Empty, blank, or unusable response.
   - `classification_reason`: 1-2 sentence justification for the chosen answer quality tier.
   - `relevance_score`: How directly and thoroughly the answer addressed the specific question asked (0-100).
   - `correctness_score`: Technical accuracy, architectural depth, correctness of data structures, algorithms, protocols, or design patterns (0-100).
   - `keywords_score`: Coverage of core domain terminology, frameworks, and engineering concepts (0-100).
   - `clarity_score`: Communication structure, logical flow, articulation, and concise phrasing (0-100).
   - `confidence_score`: Assertiveness, technical conviction, and decisive engineering authority (0-100).
   - `covered_concepts`: List of technical concepts, patterns, or tools successfully demonstrated by candidate.
   - `missed_concepts`: List of critical technical considerations, failure edge cases, or trade-offs omitted.
   - `completeness`: Degree of concept completeness ("complete", "partial", "insufficient", "none").
   - `contradicted_claims`: Specific candidate statements that contradict technical domain facts.
   - `unsupported_claims`: Claims made by candidate that lack supporting domain evidence.
   - `ideal_answer_comparison`: 2-3 sentence diff comparing candidate response against the benchmark ideal answer.
   - `turn_feedback`: 1-2 sentence constructive takeaway for this question.

2. Deterministic Non-Answer Safety Rule:
   - If the candidate stated "I don't know", "no idea", "mujhe nahi pata", "pass", or gave an empty answer, set `answer_quality_tier` to "non_answer", "pass", or "empty".
   - Set `covered_concepts` to [] (do NOT hallucinate covered concepts for non-answers).

3. Short-Answer Rule:
   - Concise answers (e.g. "PostgreSQL.", "GET.", "Pandas.", "O(1)") that are factually correct must NOT be marked "empty", "non_answer", or "weak" merely because of brevity. If accurate and direct, classify as "strong" or "partial" and mark completeness as "complete".

4. Language & Code-Switching Rule:
   - Evaluate technical accuracy, depth, and conceptual clarity regardless of whether the candidate answered in English, Hindi, or mixed Hinglish. Do NOT penalize natural code-switching or conversational Hindi/English syntax as long as technical engineering concepts are sound.

5. Synthesize Session-Level Insights:
   - `top_strengths`: 3-5 concrete, evidence-backed engineering strengths demonstrated by the candidate (include title, detailed description, and evidence_turn_index).
   - `top_improvements`: 3-5 prioritized technical growth areas (include title, description of gap, concrete actionable study recommendation/resources, and evidence_turn_index).
   - `executive_summary`: 3-4 sentence comprehensive executive summary of overall candidate performance against the target seniority standard.
"""


def _build_fallback_evaluation_report(
    transcript_turns: List[Dict[str, Any]], target_role: str, seniority_level: str
) -> SessionEvaluationReport:
    """Construct a high-quality deterministic semantic fallback evaluation report without arbitrary word-count formulas."""
    from app.schemas.evaluation import AnswerQualityTier
    from app.services.reference_evaluator import get_reference_evaluator_service
    from app.services.score_calibrator import get_score_calibrator
    from app.services.semantic_evaluator import get_semantic_evaluator_engine

    ref_service = get_reference_evaluator_service()
    semantic_engine = get_semantic_evaluator_engine()
    score_calibrator = get_score_calibrator()
    turn_evals: List[TurnEvaluationItem] = []

    for t in transcript_turns:
        t_idx = t.get("turn_index", 0)
        ans = t.get("candidate_answer") or ""
        q_text = t.get("question_text", "Interview Question")
        ideal_ans = t.get("ideal_answer", "Senior engineering benchmark response.")
        prim_concept = t.get("primary_concept")

        ref_payload = ref_service.resolve_reference_for_turn(
            question_text=q_text,
            ideal_answer=ideal_ans,
            primary_concept=prim_concept,
            target_role=target_role,
            seniority_level=seniority_level,
            is_follow_up=t.get("is_follow_up", False),
        )

        sem_result = semantic_engine.evaluate_turn_semantics(
            candidate_answer=ans,
            reference_payload=ref_payload,
            question_text=q_text,
        )

        calibrated = score_calibrator.calibrate_turn(
            sem_result=sem_result,
            speech_confidence_score=50,
            is_candidate_specific=ref_payload.is_candidate_specific,
        )

        tier = calibrated.assigned_tier
        rel_score = calibrated.relevance_score
        corr_score = calibrated.correctness_score
        kw_score = calibrated.keywords_score
        cla_score = calibrated.clarity_score
        conf_score = calibrated.confidence_score

        comparison = (
            f"The candidate gave a non-answer for '{q_text}'. Benchmark expectation: {ideal_ans}"
            if tier in (AnswerQualityTier.NON_ANSWER, AnswerQualityTier.EMPTY, AnswerQualityTier.PASS)
            else f"Candidate response evaluated against benchmark for '{q_text}': {sem_result.correctness_reason}"
        )

        feedback = (
            f"Review the core domain concepts for {prim_concept or q_text} to articulate structured responses."
            if tier in (AnswerQualityTier.NON_ANSWER, AnswerQualityTier.EMPTY, AnswerQualityTier.PASS, AnswerQualityTier.IRRELEVANT)
            else f"{sem_result.classification_reason} Deepen explanations of underlying trade-offs and edge-case mechanics."
        )

        turn_evals.append(
            TurnEvaluationItem(
                turn_index=t_idx,
                answer_quality_tier=tier,
                classification_reason=sem_result.classification_reason,
                expected_concepts=ref_payload.expected_concepts,
                concept_evidence=sem_result.concept_evidence,
                completeness=sem_result.completeness,
                contradicted_claims=sem_result.contradicted_claims,
                unsupported_claims=sem_result.unsupported_claims,
                reference_answer=ref_payload.reference_answer,
                relevance_score=rel_score,
                correctness_score=corr_score,
                keywords_score=kw_score,
                clarity_score=cla_score,
                confidence_score=conf_score,
                covered_concepts=sem_result.covered_concepts,
                missed_concepts=sem_result.missed_concepts,
                ideal_answer_comparison=comparison,
                turn_feedback=feedback,
            )
        )

    all_non_answers = all(
        te.answer_quality_tier in (AnswerQualityTier.NON_ANSWER, AnswerQualityTier.EMPTY, AnswerQualityTier.PASS, AnswerQualityTier.IRRELEVANT)
        for te in turn_evals
    )

    if all_non_answers:
        top_strengths = []
        top_improvements = [
            ImprovementItem(
                title="Demonstrate Technical Domain Knowledge",
                description=f"Candidate did not demonstrate technical understanding of the questions evaluated during this {target_role} session.",
                actionable_recommendation=f"Study core domain principles, data structures, and architectural trade-offs relevant to {target_role}.",
                evidence_turn_index=0,
            )
        ]
        exec_summary = (
            f"Candidate did not demonstrate technical knowledge for the questions asked during this {target_role} mock interview. "
            "Scores are calibrated to 0 based on non-answers / lack of concept demonstration."
        )
    else:
        top_strengths = [
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
        ]
        top_improvements = [
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
        ]
        exec_summary = (
            f"The candidate completed the mock interview for {target_role} ({seniority_level}) demonstrating solid domain fundamentals and structured thinking. Enhancing technical depth in edge cases, distributed failure recovery, and architectural trade-offs will elevate readiness for senior-level evaluations."
        )

    return SessionEvaluationReport(
        turns_evaluation=turn_evals,
        top_strengths=top_strengths,
        top_improvements=top_improvements,
        executive_summary=exec_summary,
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
        excluded_question_ids: Optional[Set[str]] = None,
        preferred_language: Optional[str] = "en",
        candidate_context: Optional[CandidateContext] = None,
        question_plan: Optional[QuestionPlan] = None,
    ) -> GeneratedQuestion:
        """Generate the first initial core interview question (Core Q1) grounded in candidate evidence and planner."""
        # 1. Build context if not provided
        if candidate_context is None:
            candidate_context = build_candidate_context(
                target_role=target_role,
                seniority_level=seniority_level,
                interview_focus=interview_focus,
                preferred_language=preferred_language or "en",
                resume_data=resume_data,
                parsed_jd_data=parsed_jd_data,
                focus_skills=focus_skills,
            )

        # 2. Formulate plan if not provided
        if question_plan is None:
            planner = get_question_planner()
            question_plan = planner.plan_next_question(
                context=candidate_context,
                planned_core_questions=6,
                current_core_index=0,
            )

        cand_summary = candidate_context.format_candidate_summary()
        jd_summary = candidate_context.format_jd_summary()

        prompt = INITIAL_QUESTION_PROMPT_TEMPLATE.format(
            candidate_context=cand_summary,
            jd_context=jd_summary,
            total_core_questions=6,
            planned_intent=question_plan.intent.value,
            planned_topic=question_plan.topic,
            grounding_snippet=question_plan.grounding_snippet,
            planner_guidance=question_plan.guidance,
            language_instructions=_get_language_instructions(preferred_language),
            target_role=target_role,
            seniority_level=seniority_level,
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedQuestion,
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
                    parsed = GeneratedQuestion.model_validate_json(response.text)
                    if parsed.question_text and parsed.question_text.strip():
                        return parsed
            except Exception as exc:
                logger.warning(
                    f"Gemini initial question generation attempt {attempt}/{max_attempts} failed: {exc}"
                )
                last_exception = exc

            if attempt < max_attempts:
                await asyncio.sleep(1.0)

        logger.warning(
            f"Initial question generation failed: {last_exception}. Using grounded fallback."
        )
        return get_grounded_fallback_question(
            context=candidate_context,
            plan=question_plan,
            language=preferred_language or "en",
            stage_index=0,
            excluded_question_ids=excluded_question_ids,
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
        excluded_question_ids: Optional[Set[str]] = None,
        preferred_language: Optional[str] = "en",
        parsed_jd_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
        candidate_context: Optional[CandidateContext] = None,
        question_plan: Optional[QuestionPlan] = None,
        semantic_result: Optional[SemanticEvaluationResult] = None,
        reference_payload: Optional[QuestionReferencePayload] = None,
    ) -> NextTurnDecision:
        """Evaluate candidate answer and decide whether to probe deeper or advance using Semantic Evidence, Context, and Planner."""
        # 1. Build context if not provided
        if candidate_context is None:
            intro_ans = None
            for t in transcript_history:
                if t.get("turn_index") == 0:
                    intro_ans = t.get("candidate_answer")
                    break
            candidate_context = build_candidate_context(
                target_role=target_role,
                seniority_level=seniority_level,
                interview_focus=interview_focus,
                preferred_language=preferred_language or "en",
                resume_data=resume_data,
                parsed_jd_data=parsed_jd_data,
                focus_skills=focus_skills,
                introduction_response=intro_ans,
            )

        # Count completed core turns in transcript
        completed_core_turns = sum(
            1 for t in transcript_history if not t.get("is_follow_up", False) and t.get("turn_index", 0) > 0
        )
        # Total core target
        total_core_target = completed_core_turns + remaining_core_questions
        current_core_number = max(1, completed_core_turns)

        # 2. Formulate next core plan if not provided
        if question_plan is None and remaining_core_questions > 0:
            covered_topics = [
                t.get("question_text", "") for t in transcript_history if t.get("question_text")
            ]
            planner = get_question_planner()
            question_plan = planner.plan_next_question(
                context=candidate_context,
                planned_core_questions=total_core_target,
                current_core_index=completed_core_turns,
                covered_topics=covered_topics,
                previous_turns=transcript_history,
            )

        # 3. Resolve reference payload and evaluate turn semantics if not supplied
        if reference_payload is None:
            ref_service = get_reference_evaluator_service()
            # Construct a lightweight mock turn to resolve reference payload
            from app.models.interview import InterviewQuestionTurn
            mock_turn = InterviewQuestionTurn(
                turn_index=current_turn_index,
                question_text=previous_question,
                candidate_answer=candidate_answer,
                question_type="core",
                is_follow_up=prior_turn_was_followup,
            )
            reference_payload = ref_service.resolve_reference_for_turn(
                turn=mock_turn,
                parsed_jd_data=parsed_jd_data,
                resume_data=resume_data,
                focus_skills=focus_skills,
                target_role=target_role,
                seniority_level=seniority_level,
            )

        if semantic_result is None:
            sem_engine = get_semantic_evaluator_engine()
            semantic_result = sem_engine.evaluate_turn_semantics(
                candidate_answer=candidate_answer,
                reference_payload=reference_payload,
                question_text=previous_question,
                interview_focus=interview_focus,
            )

        # 4. Extract Semantic Evidence
        evaluated_tier = (
            semantic_result.assigned_tier.value
            if hasattr(semantic_result.assigned_tier, "value")
            else str(semantic_result.assigned_tier)
        )
        evaluated_completeness = (
            semantic_result.completeness.value
            if hasattr(semantic_result.completeness, "value")
            else str(semantic_result.completeness)
        )
        covered_concepts_str = (
            ", ".join(semantic_result.covered_concepts)
            if semantic_result.covered_concepts
            else "None"
        )
        missing_concepts_str = (
            ", ".join(semantic_result.missed_concepts)
            if semantic_result.missed_concepts
            else "None"
        )

        # Prioritize CORE missing concepts over SUPPORTING missing concepts
        target_missing_concept = "None (All key concepts demonstrated)"
        if semantic_result.missed_concepts:
            # Check if any missing concept has CORE importance
            core_missing = []
            for missed in semantic_result.missed_concepts:
                missed_norm = missed.lower().strip()
                for exp in reference_payload.expected_concepts:
                    exp_name = getattr(exp, "concept", getattr(exp, "concept_name", ""))
                    if exp.importance == ConceptImportance.CORE:
                        if exp_name.lower().strip() in missed_norm or missed_norm in exp_name.lower().strip():
                            core_missing.append(exp_name)
                            break
            if core_missing:
                target_missing_concept = core_missing[0]
            else:
                target_missing_concept = semantic_result.missed_concepts[0]

        # 5. Semantic Follow-up Rules
        # Non-answers (I don't know, pass, skip, empty, irrelevant) MUST NOT receive follow-up probes
        candidate_said_dont_know = (
            semantic_result.assigned_tier in (
                AnswerQualityTier.NON_ANSWER,
                AnswerQualityTier.EMPTY,
                AnswerQualityTier.PASS,
                AnswerQualityTier.IRRELEVANT,
            )
            or is_non_answer(candidate_answer)
        )

        followup_allowed = (
            not prior_turn_was_followup
            and remaining_followup_budget > 0
            and not candidate_said_dont_know
        )

        # Semantic gap follow-up is warranted if partial/insufficient and key concepts were missed
        followup_warranted = (
            followup_allowed
            and semantic_result.completeness in (
                CompletenessLevel.PARTIAL,
                CompletenessLevel.INSUFFICIENT,
            )
            and bool(semantic_result.missed_concepts)
            and target_missing_concept != "None (All key concepts demonstrated)"
        )

        # If all core questions are completed and no follow-up is allowed, complete session
        if not followup_allowed and remaining_core_questions <= 0:
            return NextTurnDecision(
                is_follow_up=False,
                is_interview_complete=True,
                follow_up_reasoning="All planned core questions completed.",
            )

        cand_summary = candidate_context.format_candidate_summary()
        jd_summary = candidate_context.format_jd_summary()

        history_str = "\n".join(
            [
                f"Turn {t.get('turn_index')}: [Q: {t.get('question_text')}] -> [A: {t.get('candidate_answer')}]"
                for t in transcript_history[-4:]
            ]
        ) or "None (Turn 0 completed)"

        planned_intent_str = question_plan.intent.value if question_plan else "core_progression"
        planned_topic_str = question_plan.topic if question_plan else "Core Engineering Competency"
        planned_grounding_str = question_plan.grounding_snippet if question_plan else "Role Technical Fundamentals"
        planner_guidance_str = question_plan.guidance if question_plan else "Formulate the next progressive core question."

        prompt = ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE.format(
            candidate_context=cand_summary,
            jd_context=jd_summary,
            core_question_number=current_core_number,
            total_core_questions=total_core_target,
            remaining_core_questions=remaining_core_questions,
            remaining_followup_budget=remaining_followup_budget,
            prior_turn_was_followup=prior_turn_was_followup,
            followup_allowed=followup_allowed,
            planned_next_intent=planned_intent_str,
            planned_next_topic=planned_topic_str,
            planned_next_grounding=planned_grounding_str,
            evaluated_tier=evaluated_tier,
            evaluated_completeness=evaluated_completeness,
            covered_concepts_str=covered_concepts_str,
            missing_concepts_str=missing_concepts_str,
            target_missing_concept=target_missing_concept,
            transcript_history=history_str,
            previous_question=previous_question,
            candidate_answer=candidate_answer,
            planner_guidance=planner_guidance_str,
            language_instructions=_get_language_instructions(preferred_language),
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
                    parsed = NextTurnDecision.model_validate_json(response.text)
                    # Enforce strict non-answer & budget guardrails on LLM output
                    if candidate_said_dont_know and parsed.is_follow_up:
                        logger.info("Candidate gave a non-answer; overriding LLM follow-up decision to advance.")
                        parsed.is_follow_up = False

                    if not followup_allowed and parsed.is_follow_up:
                        logger.info("Follow-up not allowed by budget/prior turn; overriding LLM follow-up decision.")
                        parsed.is_follow_up = False

                    if parsed.is_follow_up and semantic_result.completeness == CompletenessLevel.COMPLETE:
                        logger.info("Candidate answer is complete; overriding LLM follow-up decision to advance.")
                        parsed.is_follow_up = False

                    if parsed.is_interview_complete:
                        if remaining_core_questions > 0:
                            logger.warning(
                                f"Gemini returned premature completion with {remaining_core_questions} core questions remaining. Overriding with grounded fallback."
                            )
                            break
                        return parsed
                    elif parsed.question_text and parsed.question_text.strip():
                        return parsed
            except Exception as exc:
                logger.warning(
                    f"Gemini next turn generation attempt {attempt}/{max_attempts} failed: {exc}"
                )
                last_exception = exc

            if attempt < max_attempts:
                await asyncio.sleep(1.0)

        logger.warning(
            f"Adaptive next turn generation failed: {last_exception}. Using grounded fallback decision."
        )

        # 1. If all core questions are completed and no follow-up is warranted, end session cleanly
        if remaining_core_questions <= 0 and not (followup_allowed and followup_warranted):
            return NextTurnDecision(
                is_follow_up=False,
                is_interview_complete=True,
                follow_up_reasoning="All core questions completed.",
            )

        # 2. If follow-up is warranted based on semantic gap (NOT word count!)
        if (
            followup_allowed
            and followup_warranted
            and target_missing_concept != "None (All key concepts demonstrated)"
        ):
            followup_probe = get_semantic_gap_fallback_followup(
                role=target_role,
                seniority=seniority_level,
                parent_concept=previous_question,
                target_missing_concept=target_missing_concept,
                language=preferred_language or "en",
            )
            return NextTurnDecision(
                is_follow_up=True,
                is_interview_complete=False,
                follow_up_reasoning=f"Candidate omitted '{target_missing_concept}'; probing missing domain concept directly.",
                question_text=followup_probe.question_text,
                ideal_answer=followup_probe.ideal_answer,
                primary_concept=followup_probe.primary_concept,
            )

        # 3. Otherwise, advance to the next progressive grounded core question
        fallback_core = get_grounded_fallback_question(
            context=candidate_context,
            plan=question_plan,
            language=preferred_language or "en",
            stage_index=completed_core_turns,
            excluded_question_ids=excluded_question_ids,
        )
        return NextTurnDecision(
            is_follow_up=False,
            is_interview_complete=False,
            question_text=fallback_core.question_text,
            ideal_answer=fallback_core.ideal_answer,
            primary_concept=fallback_core.primary_concept,
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
        preferred_language: Optional[str] = "en",
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
            language_instructions=_get_language_instructions(preferred_language),
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
