"""Question Planner Layer.

Determines the strategic intent, topic focus, and factual grounding for each core question
in the interview session, ensuring questions are deeply candidate-specific, grounded in real evidence,
and free of hallucinations.
"""

from enum import Enum
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.candidate_context import CandidateContext, normalize_skill

logger = logging.getLogger(__name__)


class QuestionIntent(str, Enum):
    """Strategic intent category for a planned core interview question."""

    RESUME_PROJECT = "resume_project"
    WORK_EXPERIENCE = "work_experience"
    CORE_SKILL = "core_skill"
    JD_REQUIREMENT = "jd_requirement"
    PRACTICAL_SCENARIO = "practical_scenario"
    INTRODUCTION_CONTINUITY = "introduction_continuity"


class QuestionPlan(BaseModel):
    """Strategic plan specifying the intent, topic, factual context, and generator guidance."""

    intent: QuestionIntent
    topic: str = Field(..., description="Target project, skill, company, or architectural topic.")
    grounding_snippet: str = Field(
        ..., description="Exact facts from candidate context to anchor the question on."
    )
    guidance: str = Field(
        ..., description="Specific instructions to the question generator on what to ask."
    )
    primary_concept: str = Field(
        ..., description="Benchmark evaluated technical concept."
    )
    stage_index: int = Field(0, description="0-indexed core question sequence number.")
    stage_key: Optional[str] = Field(None, description="Stage key identifier for staged interviews.")
    is_escalated: bool = Field(False, description="True if question difficulty was escalated for high performer.")


class QuestionPlanner:
    """Intelligent planner deciding the sequence of interview areas based on available evidence."""

    def plan_next_question(
        self,
        context: CandidateContext,
        planned_core_questions: int,
        current_core_index: int,
        covered_intents: Optional[List[str]] = None,
        covered_topics: Optional[List[str]] = None,
        previous_turns: Optional[List[Dict[str, Any]]] = None,
        average_prior_score: Optional[float] = None,
        practice_mode: Optional[str] = None,
    ) -> QuestionPlan:
        """Formulate a strategic QuestionPlan for the upcoming core question turn.
        
        Args:
            context: Verified CandidateContext containing resume, JD, and session data.
            planned_core_questions: Total core questions planned (3 for quick, 4 for staged system design, 6 for full).
            current_core_index: 0-indexed number of the core question to plan.
            covered_intents: List of previously executed question intents.
            covered_topics: List of previously covered topic titles/skills.
            previous_turns: History of turns for contextual awareness.
            average_prior_score: Optional average score across prior turns.
            practice_mode: Optional practice mode string (e.g. 'system_design_staged', 'quick', 'full').
        """
        intents_history = [str(i).lower() for i in (covered_intents or [])]
        topics_history = [str(t).lower() for t in (covered_topics or [])]

        # 1. Staged System Design Arc (4 Sequential Architectural Stages)
        is_staged = (
            practice_mode in ("system_design_staged", "PracticeMode.system_design_staged")
            or (planned_core_questions == 4 and context.interview_focus == "System Design")
        )
        if is_staged:
            return self._plan_system_design_staged_mode(
                context=context,
                current_core_index=current_core_index,
                topics_history=topics_history,
                previous_turns=previous_turns,
            )

        # 2. Quick Mode Arc (3 Core Questions)
        if planned_core_questions <= 3:
            return self._plan_quick_mode(
                context=context,
                current_core_index=current_core_index,
                intents_history=intents_history,
                topics_history=topics_history,
            )

        # 3. Full Mode Arc (6 Core Questions)
        return self._plan_full_mode(
            context=context,
            current_core_index=current_core_index,
            intents_history=intents_history,
            topics_history=topics_history,
            previous_turns=previous_turns,
            average_prior_score=average_prior_score,
        )

    def _plan_system_design_staged_mode(
        self,
        context: CandidateContext,
        current_core_index: int,
        topics_history: List[str],
        previous_turns: Optional[List[Dict[str, Any]]] = None,
    ) -> QuestionPlan:
        """Formulate stage-aware QuestionPlan for 4-stage System Design practice mode."""
        from app.services.reference_evaluator import (
            SYSTEM_DESIGN_BLUEPRINT_CATALOG,
            resolve_system_design_blueprint,
        )
        from app.services.system_design_stage_tracker import (
            STAGE_1_REQUIREMENTS,
            STAGE_2_ESTIMATION,
            STAGE_3_ARCHITECTURE,
            STAGE_4_DEFENSE,
            STAGE_DEFINITIONS,
            SystemDesignStage,
        )

        # 1. Resolve consistent scenario and blueprint
        established_scenario = None
        if previous_turns:
            for t in previous_turns:
                t_idx = t.get("turn_index", 0)
                if t_idx > 0 and t.get("question_text"):
                    q_text = t.get("question_text", "")
                    bp_prior = resolve_system_design_blueprint(question_text=q_text)
                    if bp_prior:
                        established_scenario = bp_prior.title
                        break

        bp = None
        if not established_scenario:
            context_text = f"{' '.join(context.skills)} {' '.join(context.matched_skills)} {context.jd_experience_summary or ''} {context.target_role}"
            bp = resolve_system_design_blueprint(question_text=context_text, primary_concept=context.interview_focus)
            if bp:
                established_scenario = bp.title

        if not established_scenario:
            established_scenario = "Distributed Rate Limiter & API Gateway"
            bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG.get("sys.sr.ratelimit.core.01")
        elif not bp:
            bp = resolve_system_design_blueprint(question_text=established_scenario)
            if not bp:
                bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG.get("sys.sr.ratelimit.core.01")

        # Map core question index (0..3) to Stage (1..4)
        stage_idx = min(4, max(1, current_core_index + 1))
        stage_def = STAGE_DEFINITIONS.get(stage_idx, STAGE_1_REQUIREMENTS)

        if stage_idx == 1:
            stage_key = SystemDesignStage.REQUIREMENTS.value
            grounding_snippet = (
                f"Scenario: {established_scenario}. Requirements Scope: {bp.description if bp else 'High-scale distributed service'}. "
                f"SLA target: High availability and low latency boundaries."
            )
            guidance = (
                f"Stage 1 ({stage_def.stage_name}): Ask the candidate to define the primary functional requirements, "
                f"traffic expectations, and latency/availability SLAs for {established_scenario}. "
                f"Keep question punchy, single-intent, 20-35 words with exactly 1 question mark."
            )
            primary_concept = f"{established_scenario}: Scope & Requirements Engineering"

        elif stage_idx == 2:
            stage_key = SystemDesignStage.ESTIMATION.value
            scale_desc = "QPS: ~10k-50k write QPS, 100M daily active entities, low-latency key-value lookups."
            grounding_snippet = (
                f"Scenario: {established_scenario}. Scale & Capacity: {scale_desc} "
                f"Entities & Data Model: Primary key-value mapping and access patterns."
            )
            guidance = (
                f"Stage 2 ({stage_def.stage_name}): Ask the candidate to estimate back-of-the-envelope capacity (QPS, storage) "
                f"or define the core database entity schema and access patterns for {established_scenario}. "
                f"Build on Stage 1. Keep question punchy, single-intent, 20-35 words with exactly 1 question mark."
            )
            primary_concept = f"{established_scenario}: Capacity Estimation & Entity Modeling"

        elif stage_idx == 3:
            stage_key = SystemDesignStage.ARCHITECTURE.value
            nodes_desc = ", ".join([n.label for n in (bp.nodes[:4] if bp else [])]) or "API Gateway, Cache Tier, Storage Layer, Worker Services"
            grounding_snippet = (
                f"Scenario: {established_scenario}. Component Architecture: {nodes_desc}. "
                f"Data Flow: End-to-end request routing and persistence."
            )
            guidance = (
                f"Stage 3 ({stage_def.stage_name}): Ask the candidate to walk through the high-level component architecture "
                f"for {established_scenario}, explaining how API gateway, cache, database, and backend workers coordinate. "
                f"Build on their previous estimation. Keep question punchy, single-intent, 20-35 words with exactly 1 question mark."
            )
            primary_concept = f"{established_scenario}: End-to-End Component Architecture"

        else:  # stage_idx == 4
            stage_key = SystemDesignStage.DEFENSE.value
            tradeoff_desc = (
                bp.failure_considerations[0]
                if (bp and bp.failure_considerations)
                else (bp.key_tradeoffs[0] if (bp and bp.key_tradeoffs) else "Cache failure and database saturation under spike")
            )
            grounding_snippet = (
                f"Scenario: {established_scenario}. Failure & Bottlenecks: {tradeoff_desc}. "
                f"Resilience: Cascading failure prevention, partition tolerance, and load shedding."
            )
            guidance = (
                f"Stage 4 ({stage_def.stage_name}): Provide realistic interviewer pushback on {established_scenario}. "
                f"Probe how their architecture handles a critical failure mode (e.g. cache outage, hot key saturation, or cascading failure) "
                f"and how they maintain consistency and availability. Keep question punchy, single-intent, 20-35 words with exactly 1 question mark."
            )
            primary_concept = f"{established_scenario}: Resilience & Failure Mode Defense"

        return QuestionPlan(
            intent=QuestionIntent.PRACTICAL_SCENARIO,
            topic=f"{established_scenario} - {stage_def.stage_name}",
            grounding_snippet=grounding_snippet,
            guidance=guidance,
            primary_concept=primary_concept,
            stage_index=stage_idx,
            stage_key=stage_key,
        )

    def _plan_quick_mode(
        self,
        context: CandidateContext,
        current_core_index: int,
        intents_history: List[str],
        topics_history: List[str],
    ) -> QuestionPlan:
        """Formulate plan for 3-turn Quick practice mode."""
        # Core Q1 (Index 0): Candidate Project or Work History or Opening Core Skill
        if current_core_index == 0:
            plan = self._try_plan_project(context, topics_history, stage_index=0)
            if plan:
                return plan
            plan = self._try_plan_work_experience(context, topics_history, stage_index=0)
            if plan:
                return plan
            return self._plan_core_skill_or_scenario(context, topics_history, stage_index=0)

        # Core Q2 (Index 1): JD Requirement / Missing Skill or Core Skill Deep Dive
        if current_core_index == 1:
            if context.missing_skills or context.jd_required_skills:
                plan = self._try_plan_jd_requirement(context, topics_history, stage_index=1)
                if plan:
                    return plan
            plan = self._try_plan_work_experience(context, topics_history, stage_index=1)
            if plan:
                return plan
            return self._plan_core_skill_or_scenario(context, topics_history, stage_index=1)

        # Core Q3 (Index 2): Practical System Design / Scenario Problem Solving
        return self._plan_scenario(context, topics_history, stage_index=2)

    def _plan_full_mode(
        self,
        context: CandidateContext,
        current_core_index: int,
        intents_history: List[str],
        topics_history: List[str],
        previous_turns: Optional[List[Dict[str, Any]]] = None,
        average_prior_score: Optional[float] = None,
    ) -> QuestionPlan:
        """Formulate plan for 6-turn Full practice mode."""
        # Core Q1 (Index 0): Resume Project or Work Experience Opening
        if current_core_index == 0:
            plan = self._try_plan_project(context, topics_history, stage_index=0)
            if plan:
                return plan
            plan = self._try_plan_work_experience(context, topics_history, stage_index=0)
            if plan:
                return plan
            return self._plan_core_skill_or_scenario(context, topics_history, stage_index=0)

        # Core Q2 (Index 1): Second Project, Work Experience, or Matched JD Skill
        if current_core_index == 1:
            plan = self._try_plan_work_experience(context, topics_history, stage_index=1)
            if plan:
                return plan
            plan = self._try_plan_project(context, topics_history, stage_index=1)
            if plan:
                return plan
            plan = self._try_plan_jd_requirement(context, topics_history, stage_index=1)
            if plan:
                return plan
            return self._plan_core_skill_or_scenario(context, topics_history, stage_index=1)

        # Core Q3 (Index 2): Technical Core Competency / Architecture Deep Dive
        if current_core_index == 2:
            return self._plan_core_skill_or_scenario(context, topics_history, stage_index=2)

        # Core Q4 (Index 3): JD Requirement, Gap Probe, or Practical Application
        if current_core_index == 3:
            plan = self._try_plan_jd_requirement(context, topics_history, stage_index=3)
            if plan:
                return plan
            return self._plan_core_skill_or_scenario(context, topics_history, stage_index=3)

        # Check if candidate has demonstrated strong mastery on prior turns
        is_strong_trajectory = False
        if average_prior_score is not None and average_prior_score >= 80.0:
            is_strong_trajectory = True
        elif previous_turns and len(previous_turns) >= 2:
            evaluated_scores = [t.get("turn_score") for t in previous_turns if t.get("turn_score") is not None]
            if evaluated_scores and (sum(evaluated_scores) / len(evaluated_scores)) >= 80.0:
                is_strong_trajectory = True

        # Core Q5 (Index 4): High Concurrency / Distributed Failure Scenario (escalated if strong)
        if current_core_index == 4:
            return self._plan_scenario(context, topics_history, stage_index=4, is_escalated=is_strong_trajectory)

        # Core Q6 (Index 5): Comprehensive System Design / Architectural Trade-offs
        return self._plan_advanced_architecture(context, topics_history, stage_index=5, is_escalated=is_strong_trajectory)

    def _try_plan_project(
        self, context: CandidateContext, topics_history: List[str], stage_index: int
    ) -> Optional[QuestionPlan]:
        """Attempt to plan a question grounded in an uncovered candidate project."""
        for p in context.projects:
            if p.title.lower() not in topics_history:
                tech_str = f" using {', '.join(p.technologies)}" if p.technologies else ""
                snippet = f"Project '{p.title}'{tech_str}."
                if p.description:
                    snippet += f" Description: {p.description}."
                if p.architecture_details:
                    snippet += f" Architecture: {p.architecture_details}."
                if p.challenges:
                    snippet += f" Challenges: {p.challenges}."

                guidance = (
                    f"Ask a technical question specifically about the candidate's project '{p.title}'. "
                    f"Inquire about the architectural design, how they integrated key technologies ({', '.join(p.technologies[:3]) if p.technologies else 'core stack'}), "
                    f"or how they overcame a key technical challenge. Do NOT ask a generic textbook question."
                )
                return QuestionPlan(
                    intent=QuestionIntent.RESUME_PROJECT,
                    topic=p.title,
                    grounding_snippet=snippet,
                    guidance=guidance,
                    primary_concept=f"System Architecture: {p.title}",
                    stage_index=stage_index,
                )
        return None

    def _try_plan_work_experience(
        self, context: CandidateContext, topics_history: List[str], stage_index: int
    ) -> Optional[QuestionPlan]:
        """Attempt to plan a question grounded in an uncovered work history entry."""
        for w in context.work_history:
            topic_key = f"work_{w.company}".lower()
            if topic_key not in topics_history and w.company.lower() not in topics_history:
                role_str = f" as {w.role}" if w.role else ""
                snippet = f"Work Experience at {w.company}{role_str}."
                if w.responsibilities:
                    snippet += f" Responsibilities: {'; '.join(w.responsibilities[:2])}."
                if w.technologies:
                    snippet += f" Technologies: {', '.join(w.technologies)}."

                guidance = (
                    f"Ask a technical question referencing the candidate's work at {w.company}. "
                    f"Focus on how they implemented systems or handled responsibilities with ({', '.join(w.technologies[:3]) if w.technologies else 'their technical stack'}). "
                    f"Do NOT invent unmentioned systems or clients."
                )
                return QuestionPlan(
                    intent=QuestionIntent.WORK_EXPERIENCE,
                    topic=w.company,
                    grounding_snippet=snippet,
                    guidance=guidance,
                    primary_concept=f"Engineering Experience at {w.company}",
                    stage_index=stage_index,
                )
        return None

    def _try_plan_jd_requirement(
        self, context: CandidateContext, topics_history: List[str], stage_index: int
    ) -> Optional[QuestionPlan]:
        """Attempt to plan a question grounded in JD-required skills or unevidenced gaps."""
        # Prioritize missing skills if any
        for skill in context.missing_skills:
            if skill.lower() not in topics_history:
                snippet = (
                    f"Job Description requires experience with '{skill}', "
                    f"which is not explicitly detailed in the candidate's resume."
                )
                guidance = (
                    f"The Job Description mandates '{skill}'. Ask the candidate about their practical experience "
                    f"or conceptual understanding of '{skill}', and how they would leverage their background to solve problems with it."
                )
                return QuestionPlan(
                    intent=QuestionIntent.JD_REQUIREMENT,
                    topic=skill,
                    grounding_snippet=snippet,
                    guidance=guidance,
                    primary_concept=f"JD Requirement Verification: {skill}",
                    stage_index=stage_index,
                )

        # Check other JD required skills
        for skill in context.jd_required_skills:
            if skill.lower() not in topics_history:
                snippet = f"Job Description requires key technical competency in '{skill}'."
                guidance = (
                    f"Ask an in-depth practical question testing the candidate's expertise in '{skill}' "
                    f"as required for this {context.target_role} role."
                )
                return QuestionPlan(
                    intent=QuestionIntent.JD_REQUIREMENT,
                    topic=skill,
                    grounding_snippet=snippet,
                    guidance=guidance,
                    primary_concept=f"Core JD Skill: {skill}",
                    stage_index=stage_index,
                )
        return None

    def _plan_core_skill_or_scenario(
        self, context: CandidateContext, topics_history: List[str], stage_index: int
    ) -> QuestionPlan:
        """Plan a question targeting a verified candidate skill or matched core competency aligned with the competency stage."""
        from app.services.question_bank import get_competency_stages

        stages = get_competency_stages(
            role=context.target_role,
            seniority=context.seniority_level,
            focus=context.interview_focus,
        )
        target_stage = stages[stage_index] if stages and stage_index < len(stages) else (stages[-1] if stages else None)
        stage_concept = target_stage.core_questions[0].primary_concept if target_stage and target_stage.core_questions else "System Architecture & Engineering Trade-offs"
        stage_title = target_stage.competency_title if target_stage else "Engineering Fundamentals"

        # Try unused candidate skills
        candidate_skills = [s for s in (context.matched_skills + context.skills) if s and len(s) > 1]
        unused_skills = [
            s for s in candidate_skills
            if not any(s.lower() in t.lower() for t in topics_history)
        ]

        if unused_skills:
            selected_skill = unused_skills[0]
            snippet = f"Candidate has verified hands-on background in '{selected_skill}' for competency area '{stage_title}'."
            guidance = (
                f"Ask an in-depth practical question exploring {stage_title.lower()} when working with '{selected_skill}' "
                f"in a {context.seniority_level} {context.target_role} context. Target concept: {stage_concept}."
            )
            return QuestionPlan(
                intent=QuestionIntent.CORE_SKILL,
                topic=selected_skill,
                grounding_snippet=snippet,
                guidance=guidance,
                primary_concept=stage_concept,
                stage_index=stage_index,
            )

        # Fallback to role-calibrated technical scenario for this stage
        return self._plan_scenario(context, topics_history, stage_index=stage_index)

    def _plan_scenario(
        self,
        context: CandidateContext,
        topics_history: List[str],
        stage_index: int,
        is_escalated: bool = False,
    ) -> QuestionPlan:
        """Plan a realistic practical problem-solving or system design scenario."""
        from app.services.question_bank import get_competency_stages

        role = context.target_role
        level = context.seniority_level
        stages = get_competency_stages(role=role, seniority=level, focus=context.interview_focus)
        target_stage = stages[stage_index] if stages and stage_index < len(stages) else None
        stage_concept = target_stage.core_questions[0].primary_concept if target_stage and target_stage.core_questions else "Production Failure Resilience & Scalability"
        stage_title = target_stage.competency_title if target_stage else "System Architecture"

        snippet = f"Practical architectural scenario for {level} {role} ({stage_title})."
        if is_escalated:
            guidance = (
                f"Candidate has demonstrated strong technical mastery. Present an advanced, high-stakes production failure scenario for a {level} {role} focusing on {stage_title.lower()}. "
                f"Probe how they would diagnose catastrophic failure, mitigate cascading outages, and maintain data consistency under degraded conditions."
            )
            primary_concept = f"Advanced Resilient Architecture: {stage_title}"
        else:
            guidance = (
                f"Present a realistic production scenario for a {level} {role} focusing on {stage_title.lower()}. "
                f"Ask the candidate to walk through their architectural mitigation strategy and trade-offs."
            )
            primary_concept = stage_concept

        return QuestionPlan(
            intent=QuestionIntent.PRACTICAL_SCENARIO,
            topic=f"{role} {stage_title} Scenario",
            grounding_snippet=snippet,
            guidance=guidance,
            primary_concept=primary_concept,
            stage_index=stage_index,
            is_escalated=is_escalated,
        )

    def _plan_advanced_architecture(
        self,
        context: CandidateContext,
        topics_history: List[str],
        stage_index: int,
        is_escalated: bool = False,
    ) -> QuestionPlan:
        """Plan an advanced system design or end-to-end integration question."""
        role = context.target_role
        level = context.seniority_level
        snippet = f"Advanced system design and trade-offs for {level} {role}."
        if is_escalated:
            guidance = (
                f"Candidate has demonstrated deep domain mastery. Ask an advanced end-to-end distributed system design question tailored to a {level} {role}. "
                f"Challenge them on CAP theorem compromises, multi-region replication lag, event-driven ordering guarantees, and cost vs latency trade-offs."
            )
            primary_concept = "Advanced Distributed Systems & Multi-Region Trade-offs"
        else:
            guidance = (
                f"Ask a comprehensive system design question tailored to {level} {role}. "
                f"Ask how they would design an end-to-end distributed system, ensure data consistency across microservices, "
                f"and evaluate the trade-offs between latency, consistency, and operational complexity."
            )
            primary_concept = "End-to-End System Design & Trade-offs"

        return QuestionPlan(
            intent=QuestionIntent.PRACTICAL_SCENARIO,
            topic=f"{role} Distributed Architecture Design",
            grounding_snippet=snippet,
            guidance=guidance,
            primary_concept=primary_concept,
            stage_index=stage_index,
            is_escalated=is_escalated,
        )


def get_question_planner() -> QuestionPlanner:
    """Dependency provider for QuestionPlanner."""
    return QuestionPlanner()
