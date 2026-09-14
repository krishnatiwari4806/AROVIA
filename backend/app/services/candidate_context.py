"""Structured Candidate Context Domain Model, Skill Normalization, and Extraction Service.

Provides an authoritative, hallucination-free representation of candidate resume evidence,
job description requirements, matched vs. missing skills, and interview turn history.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Common technology synonyms/aliases for deterministic matching
TECH_ALIASES: Dict[str, str] = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "psql": "postgresql",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react native": "react native",
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "next": "nextjs",
    "nextjs": "nextjs",
    "next.js": "nextjs",
    "vue": "vue",
    "vuejs": "vue",
    "vue.js": "vue",
    "angular": "angular",
    "angularjs": "angular",
    "py": "python",
    "python": "python",
    "python3": "python",
    "python 3": "python",
    "python 2": "python",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "go": "golang",
    "golang": "golang",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "docker": "docker",
    "vue 3": "vue",
    "vue 2": "vue",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "redis": "redis",
    "kafka": "kafka",
    "apache kafka": "kafka",
    "rabbitmq": "rabbitmq",
    "graphql": "graphql",
    "rest": "rest",
    "restful": "rest",
    "rest api": "rest",
    "rest apis": "rest",
    "sql": "sql",
    "nosql": "nosql",
    "git": "git",
    "github": "github",
    "ci/cd": "ci/cd",
    "cicd": "ci/cd",
    "pandas": "pandas",
    "numpy": "numpy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
}


def normalize_skill(skill_name: Optional[str]) -> str:
    """Normalize a skill or technology name for deterministic matching.
    
    Strips leading/trailing whitespace, converts to lowercase, removes punctuation (except + and #),
    and maps common tech aliases to a canonical form.
    """
    if not skill_name:
        return ""
    raw = skill_name.strip().lower()
    # Replace dots in frameworks like node.js, vue.js, react.js
    raw = raw.replace(".js", "js")
    # Clean non-alphanumeric except +, #, /
    cleaned = re.sub(r"[^\w\+#/ ]", "", raw).strip()
    return TECH_ALIASES.get(cleaned, cleaned)


def compute_matched_and_missing_skills(
    resume_skills: List[str], jd_skills: List[str]
) -> Tuple[List[str], List[str]]:
    """Deterministically categorize JD skills into matched vs missing against candidate resume skills.
    
    Returns:
        (matched_skills, missing_skills) preserving the original JD naming where possible.
    """
    if not jd_skills:
        return [], []

    # Map normalized resume skills to their original tokens
    norm_resume_skills: Set[str] = {
        normalize_skill(s) for s in resume_skills if s and s.strip()
    }

    matched: List[str] = []
    missing: List[str] = []

    for jd_skill in jd_skills:
        if not jd_skill or not jd_skill.strip():
            continue
        norm_jd = normalize_skill(jd_skill)
        if norm_jd in norm_resume_skills:
            if jd_skill not in matched:
                matched.append(jd_skill)
        else:
            # Check for substring inclusion if length >= 3 to handle compound names
            found_sub = False
            for rs_norm in norm_resume_skills:
                if (len(norm_jd) >= 4 and norm_jd in rs_norm) or (
                    len(rs_norm) >= 4 and rs_norm in norm_jd
                ):
                    found_sub = True
                    break
            if found_sub:
                if jd_skill not in matched:
                    matched.append(jd_skill)
            else:
                if jd_skill not in missing:
                    missing.append(jd_skill)

    return matched, missing


class CandidateProjectContext(BaseModel):
    """Structured project context extracted from candidate's resume."""

    title: str = Field(..., description="Project title.")
    description: Optional[str] = Field(None, description="Project summary.")
    technologies: List[str] = Field(default_factory=list, description="Technologies used.")
    responsibilities: Optional[str] = Field(None, description="Candidate responsibilities.")
    architecture_details: Optional[str] = Field(None, description="Architecture notes.")
    challenges: Optional[str] = Field(None, description="Technical challenges.")
    outcomes: Optional[str] = Field(None, description="Measurable outcomes.")


class CandidateWorkContext(BaseModel):
    """Structured professional work experience extracted from candidate's resume."""

    company: str = Field(..., description="Company name.")
    role: Optional[str] = Field(None, description="Job title.")
    duration: Optional[str] = Field(None, description="Employment duration.")
    responsibilities: List[str] = Field(default_factory=list, description="Key duties.")
    technologies: List[str] = Field(default_factory=list, description="Technologies used.")
    achievements: List[str] = Field(default_factory=list, description="Key achievements.")


class CandidateContext(BaseModel):
    """Complete, verified candidate and interview configuration context."""

    target_role: str
    seniority_level: str
    interview_focus: str
    preferred_language: str = "en"
    
    # Candidate Resume Evidence
    has_resume: bool = False
    skills: List[str] = Field(default_factory=list)
    experience_years: float = 0.0
    domains: List[str] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[str] = None
    projects: List[CandidateProjectContext] = Field(default_factory=list)
    work_history: List[CandidateWorkContext] = Field(default_factory=list)
    
    # Turn 0 Introduction Answer
    introduction_response: Optional[str] = None

    # Job Description Evidence
    has_jd: bool = False
    jd_title: Optional[str] = None
    jd_required_skills: List[str] = Field(default_factory=list)
    jd_core_responsibilities: List[str] = Field(default_factory=list)
    jd_key_technologies: List[str] = Field(default_factory=list)
    jd_experience_summary: Optional[str] = None

    # Derived Analytics
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    high_priority_areas: List[str] = Field(default_factory=list)

    def format_candidate_summary(self) -> str:
        """Produce a clean, factual summary of candidate evidence for LLM prompt grounding."""
        if not self.has_resume:
            intro_snippet = f"\n- Intro Statement: {self.introduction_response}" if self.introduction_response else ""
            return (
                f"- Candidate Target: {self.seniority_level.capitalize()} {self.target_role}\n"
                f"- Focus Area: {self.interview_focus}\n"
                f"- Resume Status: No uploaded resume attached (evaluating on role fundamentals).{intro_snippet}"
            )

        lines: List[str] = [
            f"- Target Role & Level: {self.seniority_level.capitalize()} {self.target_role}",
            f"- Experience: {self.experience_years} years estimated",
        ]
        if self.domains:
            lines.append(f"- Domains: {', '.join(self.domains)}")
        if self.skills:
            lines.append(f"- Verified Skills: {', '.join(self.skills[:15])}")
        if self.summary:
            lines.append(f"- Summary: {self.summary}")

        if self.projects:
            lines.append("\n  Candidate Projects:")
            for p in self.projects:
                techs = f" (Tech: {', '.join(p.technologies)})" if p.technologies else ""
                lines.append(f"  • {p.title}{techs}")
                if p.description:
                    lines.append(f"    Description: {p.description}")
                if p.architecture_details:
                    lines.append(f"    Architecture: {p.architecture_details}")
                if p.responsibilities:
                    lines.append(f"    Responsibilities: {p.responsibilities}")
                if p.challenges:
                    lines.append(f"    Challenges: {p.challenges}")

        if self.work_history:
            lines.append("\n  Work Experience:")
            for w in self.work_history:
                dur = f" ({w.duration})" if w.duration else ""
                role = f" - {w.role}" if w.role else ""
                lines.append(f"  • {w.company}{role}{dur}")
                if w.responsibilities:
                    lines.append(f"    Responsibilities: {'; '.join(w.responsibilities[:3])}")
                if w.technologies:
                    lines.append(f"    Tech: {', '.join(w.technologies)}")

        if self.introduction_response:
            lines.append(f"\n- Turn 0 Introduction Response: \"{self.introduction_response}\"")

        return "\n".join(lines)

    def format_jd_summary(self) -> str:
        """Produce a clean summary of Job Description context for LLM prompt grounding."""
        if not self.has_jd:
            return "No Job Description provided (evaluating standard role competency curriculum)."

        lines: List[str] = []
        if self.jd_title:
            lines.append(f"- Job Title: {self.jd_title}")
        if self.jd_required_skills:
            lines.append(f"- Required Skills: {', '.join(self.jd_required_skills)}")
        if self.jd_core_responsibilities:
            lines.append(f"- Core Responsibilities: {'; '.join(self.jd_core_responsibilities[:3])}")
        if self.jd_key_technologies:
            lines.append(f"- Key Technologies: {', '.join(self.jd_key_technologies)}")
        if self.matched_skills:
            lines.append(f"- Matched Candidate Skills: {', '.join(self.matched_skills)}")
        if self.missing_skills:
            lines.append(f"- Unevidenced / Missing JD Skills: {', '.join(self.missing_skills)}")
        return "\n".join(lines)


def build_candidate_context(
    target_role: str,
    seniority_level: str,
    interview_focus: str,
    preferred_language: str = "en",
    resume_data: Optional[Dict[str, Any]] = None,
    parsed_jd_data: Optional[Dict[str, Any]] = None,
    focus_skills: Optional[List[str]] = None,
    introduction_response: Optional[str] = None,
) -> CandidateContext:
    """Build a validated, non-hallucinated CandidateContext instance from session and resume data."""
    # 1. Parse Resume Data if provided
    has_resume = bool(resume_data and isinstance(resume_data, dict))
    skills: List[str] = []
    experience_years = 0.0
    domains: List[str] = []
    education: List[Dict[str, Any]] = []
    summary: Optional[str] = None
    projects: List[CandidateProjectContext] = []
    work_history: List[CandidateWorkContext] = []

    if has_resume and resume_data:
        skills = list(resume_data.get("skills") or [])
        experience_years = float(resume_data.get("experience_years") or 0.0)
        domains = list(resume_data.get("domains") or [])
        education = list(resume_data.get("education") or [])
        summary = resume_data.get("summary")

        raw_projects = resume_data.get("projects") or []
        for p in raw_projects:
            if isinstance(p, dict) and p.get("title"):
                projects.append(
                    CandidateProjectContext(
                        title=str(p.get("title", "")).strip(),
                        description=p.get("description"),
                        technologies=list(p.get("technologies") or []),
                        responsibilities=p.get("responsibilities"),
                        architecture_details=p.get("architecture_details"),
                        challenges=p.get("challenges"),
                        outcomes=p.get("outcomes"),
                    )
                )

        raw_work = resume_data.get("work_history") or []
        for w in raw_work:
            if isinstance(w, dict) and w.get("company"):
                work_history.append(
                    CandidateWorkContext(
                        company=str(w.get("company", "")).strip(),
                        role=w.get("role"),
                        duration=w.get("duration"),
                        responsibilities=list(w.get("responsibilities") or []),
                        technologies=list(w.get("technologies") or []),
                        achievements=list(w.get("achievements") or []),
                    )
                )

    # 2. Add focus_skills if provided and not already in skills
    if focus_skills:
        for fs in focus_skills:
            if fs and fs not in skills:
                skills.append(fs)

    # 3. Parse JD Data if provided
    has_jd = bool(parsed_jd_data and isinstance(parsed_jd_data, dict))
    jd_title: Optional[str] = None
    jd_required: List[str] = []
    jd_resp: List[str] = []
    jd_tech: List[str] = []
    jd_exp_summary: Optional[str] = None

    if has_jd and parsed_jd_data:
        jd_title = parsed_jd_data.get("job_title")
        jd_required = list(parsed_jd_data.get("required_skills") or [])
        jd_resp = list(parsed_jd_data.get("core_responsibilities") or [])
        jd_tech = list(parsed_jd_data.get("key_technologies") or [])
        jd_exp_summary = parsed_jd_data.get("experience_summary")

    # Combine all JD skill requirements for matching
    all_jd_skills = list(dict.fromkeys(jd_required + jd_tech))
    matched_skills, missing_skills = compute_matched_and_missing_skills(
        resume_skills=skills, jd_skills=all_jd_skills
    )

    # 4. Formulate high-priority areas
    high_priority: List[str] = []
    if projects:
        high_priority.append("candidate_projects")
    if work_history:
        high_priority.append("work_experience")
    if matched_skills:
        high_priority.append("matched_core_competency")
    if missing_skills:
        high_priority.append("jd_gap_verification")
    high_priority.append("system_design_or_scenario")

    return CandidateContext(
        target_role=target_role,
        seniority_level=seniority_level,
        interview_focus=interview_focus,
        preferred_language=preferred_language,
        has_resume=has_resume,
        skills=skills,
        experience_years=experience_years,
        domains=domains,
        education=education,
        summary=summary,
        projects=projects,
        work_history=work_history,
        introduction_response=introduction_response.strip() if introduction_response else None,
        has_jd=has_jd,
        jd_title=jd_title,
        jd_required_skills=jd_required,
        jd_core_responsibilities=jd_resp,
        jd_key_technologies=jd_tech,
        jd_experience_summary=jd_exp_summary,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        high_priority_areas=high_priority,
    )
