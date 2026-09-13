"""Personal AI Coach context builder and longitudinal performance aggregator."""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coach import CoachConversation, CoachMessage
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.resume import Resume
from app.models.user import User
from app.schemas.progress import (
    ActionableCoachingPlanDTO,
    WeaknessResolutionStateDTO,
)
from app.services.progress_service import (
    CANONICAL_TOPIC_ALIASES,
    GENERIC_MODIFIERS,
    STABLE_DELTA_THRESHOLD,
    _classify_direction,
    _format_delta,
    aggregate_recurring_patterns,
    get_canonical_topic,
    get_progress_service,
    normalize_title,
    ProgressIntelligenceService,
)

logger = logging.getLogger(__name__)


def classify_pacing(duration_sec: Any) -> Optional[str]:
    """Classify interview turn pacing deterministically based on answer duration.

    Pacing Guidelines & Threshold Rationale:
    - 1-19s: Very concise (very brief answer, potentially lacking detail or structured depth)
    - 20-45s: Concise (punchy, focused response)
    - 46-120s: Moderate (standard target pacing for technical & behavioral turns; aligns with PACING_GUIDELINES=120s)
    - 121-180s: Long (comprehensive response; standard upper bound for System Design PACING_GUIDELINES=180s)
    - >180s: Very long (extended delivery beyond standard pacing guidelines)

    Returns None if duration is unrecorded or invalid (<=0 or not int).
    """
    if not isinstance(duration_sec, int) or isinstance(duration_sec, bool) or duration_sec <= 0:
        return None
    if duration_sec < 20:
        return "Very concise"
    elif duration_sec <= 45:
        return "Concise"
    elif duration_sec <= 120:
        return "Moderate"
    elif duration_sec <= 180:
        return "Long"
    else:
        return "Very long"


def _extract_filler_metrics(turn: Dict[str, Any]) -> Tuple[Optional[int], Optional[float]]:
    """Safely extract filler count and optional density from a turn dictionary."""
    if not isinstance(turn, dict):
        return None, None

    filler_count = turn.get("filler_count")
    filler_density = turn.get("filler_density")

    if filler_count is None and "filler_words" in turn:
        filler_count = turn.get("filler_words")

    # Check nested evaluation_data or filler_word_stats if not present at top level
    eval_d = turn.get("evaluation_data") if isinstance(turn.get("evaluation_data"), dict) else {}
    stats = turn.get("filler_word_stats") or eval_d.get("filler_word_stats")
    if isinstance(stats, dict):
        if filler_count is None and "count" in stats:
            filler_count = stats.get("count")
        if filler_density is None and "density" in stats:
            filler_density = stats.get("density")

    if filler_count is None and "filler_count" in eval_d:
        filler_count = eval_d.get("filler_count")
    if filler_count is None and "filler_words_detected" in eval_d and isinstance(eval_d.get("filler_words_detected"), list):
        filler_count = len(eval_d["filler_words_detected"])
    if filler_density is None and "filler_density" in eval_d:
        filler_density = eval_d.get("filler_density")

    # Validate filler_count
    if not isinstance(filler_count, int) or isinstance(filler_count, bool) or filler_count < 0:
        filler_count = None

    # Validate filler_density
    if not isinstance(filler_density, (int, float)) or isinstance(filler_density, bool) or filler_density < 0:
        filler_density = None
    elif filler_density is not None:
        filler_density = round(float(filler_density), 1)

    return filler_count, filler_density


def _truncate_text(text: Any, max_chars: int = 500) -> str:
    """Safely normalize whitespace and truncate text to bounded length."""
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "... [truncated]"
    return cleaned


class CoachContextPayload:
    """Enriched data container provided to the AI Coach reasoning engine."""

    def __init__(
        self,
        candidate_name: str,
        current_session: Dict[str, Any],
        transcript_turns: List[Dict[str, Any]],
        evaluation_report: Optional[Dict[str, Any]],
        historical_performance: List[Dict[str, Any]],
        recurring_weaknesses: List[str],
        recurring_strengths: List[str],
        conversation_history: List[Dict[str, str]],
        resume_context: Optional[Dict[str, Any]] = None,
        jd_context: Optional[Dict[str, Any]] = None,
        actionable_plan: Optional[ActionableCoachingPlanDTO] = None,
        weakness_resolutions: Optional[List[WeaknessResolutionStateDTO]] = None,
    ):
        self.candidate_name = candidate_name
        self.current_session = current_session
        self.transcript_turns = transcript_turns
        self.evaluation_report = evaluation_report
        self.historical_performance = historical_performance
        self.recurring_weaknesses = recurring_weaknesses
        self.recurring_strengths = recurring_strengths
        self.conversation_history = conversation_history
        self.resume_context = resume_context or {}
        self.jd_context = jd_context or {}
        self.actionable_plan = actionable_plan
        self.weakness_resolutions = weakness_resolutions or []

    def to_prompt_context(self) -> str:
        """Render a concise, high-signal formatted text prompt block for Gemini."""
        parts = []

        # 1. Candidate & Target Role
        parts.append(f"Candidate Name: {self.candidate_name}")
        parts.append(
            f"Target Role: {self.current_session.get('target_role', 'Software Engineer')} "
            f"({self.current_session.get('seniority_level', 'senior')})"
        )
        parts.append(f"Interview Focus: {self.current_session.get('interview_focus', 'Technical Core')}")
        parts.append(f"Practice Mode: {self.current_session.get('practice_mode', 'standard')}")

        # 2. Candidate Resume Context (Reference background)
        parts.append("\n--- CANDIDATE RESUME CONTEXT ---")
        if self.resume_context and isinstance(self.resume_context, dict):
            resume_lines = []

            # Summary
            summary = self.resume_context.get("summary")
            if summary and isinstance(summary, str) and summary.strip():
                resume_lines.append(f"Resume Summary: {_truncate_text(summary, 500)}")

            # Key Skills
            skills = self.resume_context.get("skills")
            if isinstance(skills, list) and skills:
                clean_skills = [str(s).strip() for s in skills if s and str(s).strip()]
                if clean_skills:
                    resume_lines.append(f"Key Skills: {', '.join(clean_skills[:30])}")
            elif isinstance(skills, str) and skills.strip():
                resume_lines.append(f"Key Skills: {_truncate_text(skills, 300)}")

            # Total Experience (years)
            exp_years = self.resume_context.get("experience_years")
            if isinstance(exp_years, (int, float)) and not isinstance(exp_years, bool) and exp_years > 0:
                resume_lines.append(f"Total Experience: {exp_years} years")

            # Relevant Experience (roles/work history)
            exp_items = self.resume_context.get("experience")
            if isinstance(exp_items, list) and exp_items:
                clean_exp = []
                for item in exp_items:
                    if isinstance(item, dict):
                        role = item.get("role") or item.get("title") or ""
                        company = item.get("company") or ""
                        dur = item.get("duration") or item.get("years") or ""
                        comp_str = f" at {company}" if company else ""
                        dur_str = f" ({dur})" if dur else ""
                        if role or company or dur:
                            clean_exp.append(f"{role or 'Role'}{comp_str}{dur_str}")
                    elif isinstance(item, str) and item.strip():
                        clean_exp.append(_truncate_text(item, 100))
                    if len(clean_exp) >= 3:
                        break
                if clean_exp:
                    resume_lines.append(f"Relevant Experience: {'; '.join(clean_exp)}")
            elif isinstance(exp_items, str) and exp_items.strip():
                resume_lines.append(f"Relevant Experience: {_truncate_text(exp_items, 300)}")

            # Relevant Projects
            projects = self.resume_context.get("projects")
            if isinstance(projects, list) and projects:
                clean_projs = []
                for p in projects:
                    if isinstance(p, dict):
                        p_name = p.get("name") or p.get("title")
                        p_desc = p.get("description") or ""
                        if p_name and p_desc:
                            clean_projs.append(f"{p_name} ({_truncate_text(p_desc, 80)})")
                        elif p_name:
                            clean_projs.append(str(p_name))
                    elif isinstance(p, str) and p.strip():
                        clean_projs.append(_truncate_text(p, 100))
                    if len(clean_projs) >= 3:
                        break
                if clean_projs:
                    resume_lines.append(f"Relevant Projects: {'; '.join(clean_projs)}")

            # Domains
            domains = self.resume_context.get("domains")
            if isinstance(domains, list) and domains:
                clean_doms = [str(d).strip() for d in domains if d and str(d).strip()]
                if clean_doms:
                    resume_lines.append(f"Domains: {', '.join(clean_doms)}")

            # Education
            education = self.resume_context.get("education")
            if isinstance(education, list) and education:
                clean_edu = []
                for edu in education:
                    if isinstance(edu, dict):
                        inst = edu.get("institution") or ""
                        deg = edu.get("degree") or ""
                        yr = edu.get("graduation_year") or ""
                        edu_parts = [str(p).strip() for p in (deg, inst, yr) if p and str(p).strip()]
                        if edu_parts:
                            clean_edu.append(", ".join(edu_parts))
                    elif isinstance(edu, str) and edu.strip():
                        clean_edu.append(_truncate_text(edu, 80))
                    if len(clean_edu) >= 2:
                        break
                if clean_edu:
                    resume_lines.append(f"Education: {'; '.join(clean_edu)}")

            # Fallback to raw_text if structured fields are completely absent
            if not resume_lines and self.resume_context.get("raw_text"):
                raw_t = _truncate_text(self.resume_context["raw_text"], 500)
                if raw_t:
                    resume_lines.append(f"Resume Text Summary: {raw_t}")

            if resume_lines:
                parts.extend(resume_lines)
            else:
                parts.append("Resume Context: Not available.")
        else:
            parts.append("Resume Context: Not available.")

        # 3. Target Job Description Context (Reference requirements)
        parts.append("\n--- TARGET JOB DESCRIPTION CONTEXT ---")
        if self.jd_context and isinstance(self.jd_context, dict):
            jd_lines = []

            # Target Role
            role = self.jd_context.get("job_title") or self.jd_context.get("target_role")
            if role and isinstance(role, str) and role.strip():
                jd_lines.append(f"Target Role: {role.strip()}")

            # Required / Focus Skills
            req_skills = self.jd_context.get("required_skills")
            focus_skills = self.jd_context.get("focus_skills")
            combined_skills = []
            if isinstance(req_skills, list):
                combined_skills.extend([str(s).strip() for s in req_skills if s and str(s).strip()])
            elif isinstance(req_skills, str) and req_skills.strip():
                combined_skills.append(req_skills.strip())
            if isinstance(focus_skills, list):
                for fs in focus_skills:
                    if fs and str(fs).strip() and str(fs).strip() not in combined_skills:
                        combined_skills.append(str(fs).strip())

            if combined_skills:
                jd_lines.append(f"Required Skills: {', '.join(combined_skills[:25])}")

            # Key Responsibilities
            responsibilities = self.jd_context.get("core_responsibilities") or self.jd_context.get("key_responsibilities")
            if isinstance(responsibilities, list) and responsibilities:
                clean_resp = []
                for r in responsibilities:
                    if r and str(r).strip():
                        clean_resp.append(_truncate_text(str(r), 120))
                    if len(clean_resp) >= 4:
                        break
                if clean_resp:
                    jd_lines.append(f"Key Responsibilities: {'; '.join(clean_resp)}")
            elif isinstance(responsibilities, str) and responsibilities.strip():
                jd_lines.append(f"Key Responsibilities: {_truncate_text(responsibilities, 300)}")

            # Key Technologies
            key_tech = self.jd_context.get("key_technologies")
            if isinstance(key_tech, list) and key_tech:
                clean_tech = [str(t).strip() for t in key_tech if t and str(t).strip()]
                if clean_tech:
                    jd_lines.append(f"Key Technologies: {', '.join(clean_tech[:20])}")
            elif isinstance(key_tech, str) and key_tech.strip():
                jd_lines.append(f"Key Technologies: {_truncate_text(key_tech, 200)}")

            # Relevant Requirements / Experience Requirements
            rel_req = self.jd_context.get("relevant_requirements") or self.jd_context.get("experience_summary")
            if isinstance(rel_req, list) and rel_req:
                clean_rr = []
                for r in rel_req:
                    if r and str(r).strip():
                        clean_rr.append(_truncate_text(str(r), 120))
                    if len(clean_rr) >= 4:
                        break
                if clean_rr:
                    jd_lines.append(f"Relevant Requirements: {'; '.join(clean_rr)}")
            elif isinstance(rel_req, str) and rel_req.strip():
                jd_lines.append(f"Relevant Requirements: {_truncate_text(rel_req, 150)}")

            # Fallback to raw custom_job_desc if parsed fields were empty
            if not jd_lines and self.jd_context.get("custom_job_desc"):
                raw_jd = _truncate_text(self.jd_context["custom_job_desc"], 500)
                if raw_jd:
                    jd_lines.append(f"Job Description Summary: {raw_jd}")

            if jd_lines:
                parts.extend(jd_lines)
            else:
                parts.append("Job Description Context: Not available.")
        else:
            parts.append("Job Description Context: Not available.")

        # 4. Evaluation Scores & Summary
        if self.current_session.get("overall_score") is not None:
            parts.append(f"Current Session Overall Score: {self.current_session.get('overall_score')}/100")

        dim_scores = self.current_session.get("dimension_scores") or {}
        if dim_scores:
            dim_str = ", ".join([f"{k.capitalize()}: {v}/100" for k, v in dim_scores.items()])
            parts.append(f"Dimension Scores: {dim_str}")

        if self.evaluation_report:
            exec_summary = self.evaluation_report.get("executive_summary")
            if exec_summary:
                parts.append(f"\nExecutive Evaluation Summary:\n{exec_summary}")

            strengths = self.evaluation_report.get("top_strengths") or []
            if strengths:
                parts.append("\nKey Evaluated Strengths:")
                for s in strengths[:4]:
                    title = s.get("title", "")
                    desc = s.get("description", "")
                    parts.append(f"- {title}: {desc}")

            improvements = self.evaluation_report.get("top_improvements") or []
            if improvements:
                parts.append("\nKey Evaluated Areas for Improvement:")
                for imp in improvements[:4]:
                    title = imp.get("title", "")
                    desc = imp.get("description", "")
                    rec = imp.get("actionable_recommendation", "")
                    parts.append(f"- {title}: {desc} (Recommended Action: {rec})")

        # 5. Turn-by-Turn Q&A & Scores
        parts.append("\n--- INTERVIEW TURNS & CANDIDATE ANSWERS ---")
        for turn in self.transcript_turns:
            t_idx = turn.get("turn_index", 0)
            q_text = turn.get("question_text", "")
            ans_text = turn.get("candidate_answer") or "(No answer recorded)"
            primary_concept = turn.get("primary_concept")
            covered = turn.get("covered_concepts")
            missed = turn.get("missed_concepts")
            ideal_comp = turn.get("ideal_answer_comparison") or ""
            feedback = turn.get("turn_feedback") or ""

            rel = turn.get("relevance_score")
            corr = turn.get("correctness_score")
            kw = turn.get("keywords_score")
            clar = turn.get("clarity_score")
            conf = turn.get("confidence_score")

            score_items = []
            if rel is not None:
                score_items.append(f"Relevance: {rel}/100")
            if corr is not None:
                score_items.append(f"Correctness: {corr}/100")
            if kw is not None:
                score_items.append(f"Keywords: {kw}/100")
            if clar is not None:
                score_items.append(f"Clarity: {clar}/100")
            if conf is not None:
                score_items.append(f"Confidence: {conf}/100")
            scores_str = f"Scores: [{', '.join(score_items)}]" if score_items else ""

            parts.append(f"\n[Turn {t_idx + 1}]")
            parts.append(f"Question: {q_text}")
            parts.append(f"Candidate Answer: {ans_text}")

            # Turn Duration & Pacing classification
            dur = turn.get("turn_duration_sec") if turn.get("turn_duration_sec") is not None else turn.get("duration_sec")
            if isinstance(dur, int) and not isinstance(dur, bool) and dur > 0:
                parts.append(f"Duration: {dur} seconds")
                pacing = classify_pacing(dur)
                if pacing:
                    parts.append(f"Pacing: {pacing}")
            else:
                parts.append("Duration: Not recorded")

            # Filler word speech metrics
            filler_count, filler_density = _extract_filler_metrics(turn)
            if filler_count is not None:
                if filler_density is not None:
                    parts.append(f"Filler Words: {filler_count} ({filler_density}% density)")
                else:
                    parts.append(f"Filler Words: {filler_count}")
            else:
                parts.append("Filler Words: Not recorded")

            if primary_concept and isinstance(primary_concept, str) and primary_concept.strip():
                parts.append(f"Primary Concept: {primary_concept.strip()}")

            if covered is not None:
                if isinstance(covered, list):
                    clean_cov = [str(c).strip() for c in covered if c and str(c).strip()]
                    parts.append(f"Covered Concepts: {', '.join(clean_cov) if clean_cov else 'None recorded'}")
                elif isinstance(covered, str) and covered.strip():
                    parts.append(f"Covered Concepts: {covered.strip()}")
                else:
                    parts.append("Covered Concepts: None recorded")

            if missed is not None:
                if isinstance(missed, list):
                    clean_miss = [str(c).strip() for c in missed if c and str(c).strip()]
                    parts.append(f"Missed Concepts: {', '.join(clean_miss) if clean_miss else 'None recorded'}")
                elif isinstance(missed, str) and missed.strip():
                    parts.append(f"Missed Concepts: {missed.strip()}")
                else:
                    parts.append("Missed Concepts: None recorded")

            if scores_str:
                parts.append(scores_str)
            if ideal_comp:
                parts.append(f"Benchmark Comparison: {ideal_comp}")
            if feedback:
                parts.append(f"Evaluator Feedback: {feedback}")

        # 6. Longitudinal Performance & Pattern Detection
        parts.append("\n--- HISTORICAL PERFORMANCE ACROSS PREVIOUS SESSIONS ---")
        if self.historical_performance:
            for h in self.historical_performance[:4]:
                h_role = h.get("target_role", "Software Engineer")
                h_score = h.get("overall_score")
                h_date = h.get("date", "Previous Session")
                parts.append(f"\n- Past Session ({h_date}): {h_role}")
                if h_score is not None:
                    parts.append(f"  Overall: {h_score}/100")

                h_dims = h.get("dimension_scores")
                if isinstance(h_dims, dict) and h_dims:
                    dim_items = []
                    for dim in ("relevance", "correctness", "keywords", "clarity", "confidence"):
                        if dim in h_dims and isinstance(h_dims[dim], (int, float)) and not isinstance(h_dims[dim], bool):
                            dim_items.append(f"{dim.capitalize()} {int(round(h_dims[dim]))}")
                    if dim_items:
                        parts.append(f"  Dimensions: {', '.join(dim_items)}")

            # Calculate deterministic score trends across historical sessions + current session
            all_points = []
            for h in self.historical_performance:
                all_points.append({
                    "overall_score": h.get("overall_score"),
                    "dimension_scores": h.get("dimension_scores") if isinstance(h.get("dimension_scores"), dict) else {},
                })

            # Append current session as the latest observation point
            current_overall = self.current_session.get("overall_score")
            current_dims = self.current_session.get("dimension_scores") if isinstance(self.current_session.get("dimension_scores"), dict) else {}
            all_points.append({
                "overall_score": current_overall,
                "dimension_scores": current_dims,
            })

            # Overall score trend
            valid_overalls = []
            for pt in all_points:
                v = pt.get("overall_score")
                if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 100:
                    valid_overalls.append(int(round(v)))

            if len(valid_overalls) >= 2:
                series_str = " → ".join(str(s) for s in valid_overalls)
                net_change = valid_overalls[-1] - valid_overalls[0]
                direction = _classify_direction(net_change)
                signed_change = _format_delta(net_change)
                parts.append(f"\nOverall Score Trend:\n{series_str}\nNet Change: {signed_change} points\nDirection: {direction}")
            else:
                parts.append("\nOverall Score Trend: Insufficient historical data.")

            # Dimension score trends
            dim_trend_lines = []
            for dim in ("relevance", "correctness", "keywords", "clarity", "confidence"):
                dim_scores = []
                for pt in all_points:
                    dims_dict = pt.get("dimension_scores") or {}
                    v = dims_dict.get(dim)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 100:
                        dim_scores.append(int(round(v)))

                if len(dim_scores) >= 2:
                    series_str = " → ".join(str(s) for s in dim_scores)
                    net_change = dim_scores[-1] - dim_scores[0]
                    direction = _classify_direction(net_change)
                    signed_change = _format_delta(net_change)
                    dim_trend_lines.append(f"- {dim.capitalize()}: {series_str} ({signed_change}, {direction})")

            if dim_trend_lines:
                parts.append("\nDimension Trends:")
                parts.extend(dim_trend_lines)

            if self.recurring_weaknesses:
                parts.append(f"\nDetected Recurring Weaknesses: {', '.join(self.recurring_weaknesses)}")
            if self.recurring_strengths:
                parts.append(f"\nConsistent Demonstrated Strengths: {', '.join(self.recurring_strengths)}")
        else:
            parts.append("Historical Performance: This is the candidate's first recorded interview session in AROVIA.")
            parts.append("Overall Score Trend: Insufficient historical data.")

        # 7. Deterministic Actionable Coaching Plan & Weakness Lifecycle
        parts.append("\n--- DETERMINISTIC COACHING ACTION PLAN ---")
        parts.append("<deterministic_coaching_plan>")
        if self.actionable_plan:
            plan = self.actionable_plan
            parts.append("CURRENT COACHING PRIORITY:")
            parts.append(f"- Focus Topic: {plan.focus_topic}")
            parts.append(f"- Category: {plan.category}")
            parts.append(f"- Priority Level: {plan.priority_level}")

            parts.append("\nREASON & EVIDENCE:")
            parts.append(f"- Reason: {plan.reason}")
            ev_val = plan.evidence
            if isinstance(ev_val, dict) and ev_val:
                ev_str = "; ".join([f"{k}: {v}" for k, v in ev_val.items()])
            elif isinstance(ev_val, str) and ev_val.strip():
                ev_str = ev_val.strip()
            else:
                ev_str = "Authoritative interview evaluation data."
            parts.append(f"- Evidence: {ev_str}")

            parts.append("\nPRACTICE ASSIGNMENT:")
            preset_focus = plan.practice_preset.get("focus", plan.category) if isinstance(plan.practice_preset, dict) else plan.category
            preset_topic = plan.practice_preset.get("topic", plan.focus_topic) if isinstance(plan.practice_preset, dict) else plan.focus_topic
            parts.append(f"- Practice Preset: Focus: {preset_focus}, Topic: {preset_topic}")
            parts.append("- Concrete Assigned Actions:")
            for act in plan.concrete_actions:
                parts.append(f"  * {act}")

            parts.append("\nMEASUREMENT & VERIFICATION:")
            parts.append(f"- Success Metric: {plan.success_metric}")
            parts.append(f"- Review Condition: {plan.review_condition}")

            if self.weakness_resolutions:
                parts.append("\nWEAKNESS LIFECYCLE STATES:")
                for wr in self.weakness_resolutions:
                    trend_note = " (frequency decreasing)" if wr.frequency_is_decreasing else ""
                    dim_note = f", Related Dimension: {wr.related_dimension.capitalize()}" if wr.related_dimension != "unknown" else ""
                    parts.append(f"- {wr.display_title}: Status: {wr.status.upper()}{trend_note} (Observed across {wr.sessions_observed_count} completed session{'s' if wr.sessions_observed_count != 1 else ''}{dim_note})")
        else:
            parts.append("No completed interview sessions on record. No active coaching plan generated.")
        parts.append("</deterministic_coaching_plan>")

        return "\n".join(parts)


class CoachContextBuilder:
    """Builds controlled, relevant, and privacy-isolated context for AI Coach reasoning."""

    def __init__(self, progress_service: Optional[ProgressIntelligenceService] = None):
        self.progress_service = progress_service or get_progress_service()

    async def build_context(
        self,
        db: AsyncSession,
        current_user: User,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        max_history_messages: int = 10,
    ) -> CoachContextPayload:
        """Gather current session, evaluation report, turns, historical performance, and conversation history."""
        # 1. Fetch Current Interview Session
        current_session_dict: Dict[str, Any] = {}
        transcript_turns: List[Dict[str, Any]] = []
        evaluation_report: Optional[Dict[str, Any]] = None
        jd_context: Dict[str, Any] = {}
        resume_context: Dict[str, Any] = {}

        interview_session = None
        if session_id:
            session_stmt = (
                select(InterviewSession)
                .where(
                    InterviewSession.id == session_id,
                    InterviewSession.user_id == current_user.id,
                )
                .options(
                    selectinload(InterviewSession.turns),
                    selectinload(InterviewSession.resume),
                )
            )
            session_res = await db.execute(session_stmt)
            interview_session = session_res.scalar_one_or_none()

            if interview_session:
                current_session_dict = {
                    "id": interview_session.id,
                    "target_role": interview_session.target_role,
                    "seniority_level": interview_session.seniority_level,
                    "interview_focus": interview_session.interview_focus,
                    "practice_mode": interview_session.practice_mode,
                    "status": interview_session.status,
                    "overall_score": interview_session.overall_score,
                    "dimension_scores": interview_session.dimension_scores,
                    "started_at": str(interview_session.started_at),
                    "completed_at": str(interview_session.completed_at) if interview_session.completed_at else None,
                }
                evaluation_report = interview_session.evaluation_report

                # Extract Job Description context
                if interview_session.parsed_jd_data and isinstance(interview_session.parsed_jd_data, dict):
                    jd_context.update(interview_session.parsed_jd_data)
                if interview_session.focus_skills and isinstance(interview_session.focus_skills, list):
                    jd_context["focus_skills"] = interview_session.focus_skills
                if interview_session.custom_job_desc and isinstance(interview_session.custom_job_desc, str):
                    jd_context["custom_job_desc"] = interview_session.custom_job_desc
                if "target_role" not in jd_context and interview_session.target_role:
                    jd_context["target_role"] = interview_session.target_role

                # Sort turns chronologically
                sorted_turns = sorted(interview_session.turns, key=lambda t: t.turn_index)
                for t in sorted_turns:
                    eval_d = t.evaluation_data if isinstance(t.evaluation_data, dict) else {}
                    filler_stats = eval_d.get("filler_word_stats") if isinstance(eval_d.get("filler_word_stats"), dict) else {}

                    filler_count = None
                    filler_density = None

                    if "count" in filler_stats and isinstance(filler_stats["count"], int) and not isinstance(filler_stats["count"], bool) and filler_stats["count"] >= 0:
                        filler_count = filler_stats["count"]
                    elif "filler_count" in eval_d and isinstance(eval_d["filler_count"], int) and not isinstance(eval_d["filler_count"], bool) and eval_d["filler_count"] >= 0:
                        filler_count = eval_d["filler_count"]
                    elif "filler_words_detected" in eval_d and isinstance(eval_d["filler_words_detected"], list):
                        filler_count = len(eval_d["filler_words_detected"])
                    elif "filler_words" in eval_d and isinstance(eval_d["filler_words"], int) and not isinstance(eval_d["filler_words"], bool) and eval_d["filler_words"] >= 0:
                        filler_count = eval_d["filler_words"]

                    if "density" in filler_stats and isinstance(filler_stats["density"], (int, float)) and not isinstance(filler_stats["density"], bool) and filler_stats["density"] >= 0:
                        filler_density = round(float(filler_stats["density"]), 1)
                    elif "filler_density" in eval_d and isinstance(eval_d["filler_density"], (int, float)) and not isinstance(eval_d["filler_density"], bool) and eval_d["filler_density"] >= 0:
                        filler_density = round(float(eval_d["filler_density"]), 1)

                    transcript_turns.append(
                        {
                            "id": t.id,
                            "turn_index": t.turn_index,
                            "question_text": t.question_text,
                            "ideal_answer": t.ideal_answer,
                            "primary_concept": eval_d.get("primary_concept", ""),
                            "candidate_answer": t.candidate_answer,
                            "turn_duration_sec": t.turn_duration_sec,
                            "filler_count": filler_count,
                            "filler_density": filler_density,
                            "relevance_score": t.relevance_score,
                            "correctness_score": t.correctness_score,
                            "keywords_score": t.keywords_score,
                            "clarity_score": t.clarity_score,
                            "confidence_score": t.confidence_score,
                            "covered_concepts": eval_d.get("covered_concepts", []),
                            "missed_concepts": eval_d.get("missed_concepts", []),
                            "ideal_answer_comparison": eval_d.get("ideal_answer_comparison", ""),
                            "turn_feedback": eval_d.get("turn_feedback", ""),
                        }
                    )

        # 2. Extract Candidate Resume Context (User-scoped)
        resume_record = None
        if interview_session and interview_session.resume:
            if interview_session.resume.user_id == current_user.id:
                resume_record = interview_session.resume

        if not resume_record:
            resume_stmt = select(Resume).where(Resume.user_id == current_user.id)
            resume_res = await db.execute(resume_stmt)
            resume_record = resume_res.scalar_one_or_none()

        if resume_record:
            if isinstance(resume_record.parsed_data, dict):
                resume_context.update(resume_record.parsed_data)
            if resume_record.raw_text and isinstance(resume_record.raw_text, str):
                resume_context["raw_text"] = resume_record.raw_text

        # 3. Gather Historical Performance (other completed sessions for this user)
        history_stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.user_id == current_user.id,
                InterviewSession.status == "completed",
                InterviewSession.overall_score.isnot(None),
            )
            .order_by(InterviewSession.started_at.desc())
            .limit(6)
        )
        if session_id:
            history_stmt = history_stmt.where(InterviewSession.id != session_id)

        history_res = await db.execute(history_stmt)
        past_sessions = list(history_res.scalars().all())

        historical_performance: List[Dict[str, Any]] = []
        all_eval_reports: List[Optional[Dict[str, Any]]] = []

        for ps in reversed(past_sessions):
            raw_dims = ps.dimension_scores if isinstance(ps.dimension_scores, dict) else {}
            sanitized_dims = {}
            for k in ("relevance", "correctness", "keywords", "clarity", "confidence"):
                v = raw_dims.get(k)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 100:
                    sanitized_dims[k] = int(round(v))

            historical_performance.append(
                {
                    "id": ps.id,
                    "target_role": ps.target_role,
                    "overall_score": ps.overall_score if (isinstance(ps.overall_score, (int, float)) and not isinstance(ps.overall_score, bool) and 0 <= ps.overall_score <= 100) else None,
                    "dimension_scores": sanitized_dims,
                    "date": str(ps.started_at)[:10] if ps.started_at else "Unknown Date",
                }
            )
            if ps.evaluation_report and isinstance(ps.evaluation_report, dict):
                all_eval_reports.append(ps.evaluation_report)

        # Include current session's evaluation report in recurrence aggregation
        if evaluation_report and isinstance(evaluation_report, dict):
            all_eval_reports.append(evaluation_report)

        recurring_weaknesses, recurring_strengths = aggregate_recurring_patterns(all_eval_reports)

        # 4. Gather Deterministic Actionable Coaching Plan and Weakness Resolutions (User-scoped)
        all_completed_stmt = (
            select(InterviewSession)
            .options(selectinload(InterviewSession.turns))
            .where(
                InterviewSession.user_id == current_user.id,
                InterviewSession.status == "completed",
                InterviewSession.overall_score.isnot(None),
            )
            .order_by(InterviewSession.started_at.asc())
        )
        all_completed_res = await db.execute(all_completed_stmt)
        user_completed_sessions = list(all_completed_res.scalars().all())

        actionable_plan = self.progress_service.generate_actionable_coaching_plan(user_completed_sessions)
        weakness_resolutions = self.progress_service.compute_weakness_resolution_states(user_completed_sessions)

        # 5. Gather Recent Conversation History
        conversation_history: List[Dict[str, str]] = []
        if conversation_id:
            msg_stmt = (
                select(CoachMessage)
                .where(CoachMessage.conversation_id == conversation_id)
                .order_by(CoachMessage.created_at.desc())
                .limit(max_history_messages)
            )
            msg_res = await db.execute(msg_stmt)
            recent_messages = list(reversed(msg_res.scalars().all()))
            for m in recent_messages:
                conversation_history.append(
                    {
                        "role": "user" if m.sender == "user" else "assistant",
                        "content": m.message_text,
                    }
                )

        candidate_name = current_user.full_name or "Candidate"

        return CoachContextPayload(
            candidate_name=candidate_name,
            current_session=current_session_dict,
            transcript_turns=transcript_turns,
            evaluation_report=evaluation_report,
            historical_performance=historical_performance,
            recurring_weaknesses=recurring_weaknesses,
            recurring_strengths=recurring_strengths,
            conversation_history=conversation_history,
            resume_context=resume_context,
            jd_context=jd_context,
            actionable_plan=actionable_plan,
            weakness_resolutions=weakness_resolutions,
        )


def get_coach_context_builder() -> CoachContextBuilder:
    """Dependency provider for CoachContextBuilder."""
    return CoachContextBuilder()
