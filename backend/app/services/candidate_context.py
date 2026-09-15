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
    "grpc": "grpc",
    "gRPC": "grpc",
    "power bi": "power bi",
    "powerbi": "power bi",
    "tableau": "tableau",
    "spark": "spark",
    "apache spark": "spark",
    "airflow": "airflow",
    "apache airflow": "airflow",
    "spring boot": "spring boot",
    "springboot": "spring boot",
    "spring": "spring",
    "microservices": "microservices",
    "microservice": "microservices",
    "distributed systems": "distributed systems",
    "distributed system": "distributed systems",
    "terraform": "terraform",
    "linux": "linux",
    "bash": "bash",
    "shell": "bash",
    "rust": "rust",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "scala": "scala",
    "dart": "dart",
    "cassandra": "cassandra",
    "dynamodb": "dynamodb",
    "elasticsearch": "elasticsearch",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
}

# Canonical Display Names for Identified Technologies & Architecture Concepts
KNOWN_TECH_SIGNALS: Dict[str, str] = {
    # Programming Languages
    "python": "Python",
    "python3": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "golang": "Go",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "sql": "SQL",
    "scala": "Scala",
    "dart": "Dart",
    "html": "HTML",
    "css": "CSS",
    "bash": "Bash",
    "shell": "Bash",
    # Frameworks & Libraries
    "react": "React",
    "reactjs": "React",
    "react native": "React Native",
    "angular": "Angular",
    "angularjs": "Angular",
    "vue": "Vue",
    "vuejs": "Vue",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Express.js",
    "expressjs": "Express.js",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "asp.net": "ASP.NET",
    "dotnet": ".NET",
    ".net": ".NET",
    "flutter": "Flutter",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    # Databases & Caches
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "psql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "elasticsearch": "Elasticsearch",
    "elastic": "Elasticsearch",
    "sqlite": "SQLite",
    "snowflake": "Snowflake",
    "bigquery": "BigQuery",
    "neo4j": "Neo4j",
    "oracle": "Oracle",
    "mariadb": "MariaDB",
    "supabase": "Supabase",
    "firebase": "Firebase",
    # Message Streaming, DevOps & Cloud
    "kafka": "Kafka",
    "apache kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "jenkins": "Jenkins",
    "linux": "Linux",
    # Analytics & Big Data
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "spark": "Apache Spark",
    "apache spark": "Apache Spark",
    "airflow": "Apache Airflow",
    "apache airflow": "Apache Airflow",
    "databricks": "Databricks",
    "hadoop": "Hadoop",
    "postman": "Postman",
    # Architecture & Domain Specialties
    "microservices": "Microservices",
    "microservice": "Microservices",
    "distributed systems": "Distributed Systems",
    "distributed system": "Distributed Systems",
    "rest apis": "REST APIs",
    "rest api": "REST APIs",
    "restful": "REST APIs",
    "event driven architecture": "Event-Driven Architecture",
    "event-driven architecture": "Event-Driven Architecture",
    "event driven": "Event-Driven Architecture",
    "system design": "System Design",
    "machine learning": "Machine Learning",
    "data engineering": "Data Engineering",
    "cloud architecture": "Cloud Architecture",
    "backend": "Backend Systems",
    "frontend": "Frontend Development",
    "full stack": "Full Stack",
    "fullstack": "Full Stack",
    "devops": "DevOps",
}

# Domain classifications mapped from keyword triggers
DOMAIN_KEYWORDS: Dict[str, str] = {
    "distributed systems": "Distributed Systems",
    "distributed system": "Distributed Systems",
    "microservices": "Microservices",
    "microservice": "Microservices",
    "machine learning": "Machine Learning",
    "data engineering": "Data Engineering",
    "cloud architecture": "Cloud Architecture",
    "system design": "System Design",
    "backend": "Backend Systems",
    "frontend": "Frontend Development",
    "full stack": "Full Stack",
    "fullstack": "Full Stack",
    "devops": "DevOps",
}

# Adversarial prompt-injection detection pattern
PROMPT_INJECTION_PATTERN = re.compile(
    r"(?i)\b(ignore\s+(?:all\s+|previous\s+|prior\s+)?(?:instructions?|prompts?|rules?)|"
    r"system\s+prompt|you\s+are\s+now|pretend\s+you\s+are|act\s+as\s+a|"
    r"disregard\s+(?:all\s+|previous\s+|prior\s+)|"
    r"say\s+(?:i|that\s+i)\s+(?:know|have|am|mastered))\b"
)

# Number-word conversion for experience statements (English & Hindi/Hinglish)
WORD_TO_NUMBER: Dict[str, float] = {
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "ek": 1.0,
    "do": 2.0,
    "teen": 3.0,
    "char": 4.0,
    "paanch": 5.0,
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


def extract_candidate_signals_from_intro(
    text: Optional[str],
    max_skills: int = 8,
    max_domains: int = 3,
) -> Dict[str, Any]:
    """Extract explicit candidate-provided skills, technologies, domains, and experience years from Turn 0 intro.
    
    Deterministic, conservative, and resistant to prompt injection and hallucination.
    Supports English, Hindi, and Hinglish.
    """
    if not text or not text.strip():
        return {"skills": [], "domains": [], "experience_years": None}

    raw = text.strip()

    # 1. Security Check: Reject prompt injection or adversarial command overrides
    if PROMPT_INJECTION_PATTERN.search(raw):
        logger.warning("Prompt injection pattern detected in Turn 0 introduction. Bypassing dynamic signal extraction.")
        return {"skills": [], "domains": [], "experience_years": None}

    norm_text = f" {raw.lower()} "

    extracted_skills: List[str] = []
    extracted_domains: List[str] = []
    extracted_experience_years: Optional[float] = None
    seen_norm_skills: Set[str] = set()

    # 2. Extract Explicit Experience Duration (English / Hindi / Hinglish)
    exp_digit_match = re.search(
        r"(?i)\b(?:with\s+|having\s+|i\s+have\s+|mujhe\s+|maine\s+)?(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?|saal|sal)(?:\s+of|\s+ka)?\s+(?:experience|anubhav|exp|working|backend|frontend|software|engineering)\b",
        raw,
    )
    if not exp_digit_match:
        # Check Hindi/Hinglish clause structure: "Maine 3 saal Python ... pe kaam kiya"
        exp_digit_match = re.search(
            r"(?i)\b(?:maine|mujhe)?\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:saal|sal|years?|yrs?)\b.*?(?:pe\s+kaam\s+kiya|kaam\s+kiya|ka\s+experience|experience\s+hai|worked)",
            raw,
        )

    if exp_digit_match:
        try:
            extracted_experience_years = float(exp_digit_match.group(1))
        except ValueError:
            pass

    if extracted_experience_years is None:
        exp_word_match = re.search(
            r"(?i)\b(?:with\s+|having\s+|i\s+have\s+|mujhe\s+|maine\s+)?(one|two|three|four|five|six|seven|eight|nine|ten|ek|do|teen|char|paanch)\s*(?:\+)?\s*(?:years?|yrs?|saal|sal)(?:\s+of|\s+ka)?\s+(?:experience|anubhav|exp|working|backend|frontend|software|engineering)\b",
            raw,
        )
        if not exp_word_match:
            exp_word_match = re.search(
                r"(?i)\b(?:maine|mujhe)?\s*(one|two|three|four|five|six|seven|eight|nine|ten|ek|do|teen|char|paanch)\s*(?:\+)?\s*(?:saal|sal|years?|yrs?)\b.*?(?:pe\s+kaam\s+kiya|kaam\s+kiya|ka\s+experience|experience\s+hai|worked)",
                raw,
            )
        if exp_word_match:
            word_key = exp_word_match.group(1).lower()
            if word_key in WORD_TO_NUMBER:
                extracted_experience_years = WORD_TO_NUMBER[word_key]

    if extracted_experience_years is None:
        exp_reverse_match = re.search(
            r"(?i)\b(?:experience|anubhav|exp)\s+(?:of\s+|ka\s+)?(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?|saal|sal)\b",
            raw,
        )
        if exp_reverse_match:
            try:
                extracted_experience_years = float(exp_reverse_match.group(1))
            except ValueError:
                pass

    # 3. Multi-word and Compound Technology / Concept Matching (Priority Order)
    multi_word_technologies = [k for k in KNOWN_TECH_SIGNALS.keys() if " " in k or "." in k or "-" in k]
    # Sort longest phrase first to ensure specific matches precede substrings
    multi_word_technologies.sort(key=len, reverse=True)

    for phrase in multi_word_technologies:
        if len(extracted_skills) >= max_skills:
            break
        # Match with word boundaries
        pattern = r"(?i)\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, raw):
            canonical_name = KNOWN_TECH_SIGNALS[phrase]
            norm_k = normalize_skill(canonical_name)
            if norm_k not in seen_norm_skills:
                extracted_skills.append(canonical_name)
                seen_norm_skills.add(norm_k)

            # Check if phrase maps to domain
            if phrase in DOMAIN_KEYWORDS:
                dom = DOMAIN_KEYWORDS[phrase]
                if dom not in extracted_domains and len(extracted_domains) < max_domains:
                    extracted_domains.append(dom)

    # 4. Context-Aware Extraction for Ambiguous Short Tokens (e.g., 'Go', 'Spring', 'R', 'C')
    # Go / Golang
    if "golang" not in seen_norm_skills and "go" not in seen_norm_skills and len(extracted_skills) < max_skills:
        if re.search(r"(?i)\bgolang\b", raw) or re.search(
            r"(?i)\b(?:with|using|in|on|and|use|built\s+with|experience\s+with|pe\s+kaam)\s+go\b|\bgo\s+(?:microservices?|developer|programming|backend|services?|code|concurrency|and|with|,|/)\b",
            raw,
        ):
            extracted_skills.append("Go")
            seen_norm_skills.add("golang")
            seen_norm_skills.add("go")

    # Spring Framework (distinguish from seasonal 'spring')
    if "spring" not in seen_norm_skills and "spring boot" not in seen_norm_skills and len(extracted_skills) < max_skills:
        if re.search(r"(?i)\bspring\s+(?:framework|boot|mvc|cloud|backend|java)\b|\b(?:using|with|in)\s+spring\b", raw):
            extracted_skills.append("Spring")
            seen_norm_skills.add("spring")

    # C++
    if "c++" not in seen_norm_skills and len(extracted_skills) < max_skills:
        if re.search(r"(?i)\b(c\+\+|cpp)\b", raw):
            extracted_skills.append("C++")
            seen_norm_skills.add("c++")

    # C#
    if "c#" not in seen_norm_skills and len(extracted_skills) < max_skills:
        if re.search(r"(?i)\b(c#|csharp)\b", raw):
            extracted_skills.append("C#")
            seen_norm_skills.add("c#")

    # 5. Standard Single-Word Technology Tokens
    single_word_technologies = [
        k for k in KNOWN_TECH_SIGNALS.keys()
        if " " not in k and "." not in k and "-" not in k and k not in ("go", "spring", "c++", "c#", "cpp", "csharp")
    ]
    single_word_technologies.sort(key=len, reverse=True)

    for word in single_word_technologies:
        if len(extracted_skills) >= max_skills:
            break
        pattern = r"(?i)\b" + re.escape(word) + r"\b"
        if re.search(pattern, raw):
            canonical_name = KNOWN_TECH_SIGNALS[word]
            norm_k = normalize_skill(canonical_name)
            if norm_k not in seen_norm_skills:
                extracted_skills.append(canonical_name)
                seen_norm_skills.add(norm_k)

            if word in DOMAIN_KEYWORDS:
                dom = DOMAIN_KEYWORDS[word]
                if dom not in extracted_domains and len(extracted_domains) < max_domains:
                    extracted_domains.append(dom)

    return {
        "skills": extracted_skills[:max_skills],
        "domains": extracted_domains[:max_domains],
        "experience_years": extracted_experience_years,
    }


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
    """Complete, verified candidate and interview configuration context with provenance tracking."""

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
    
    # Turn 0 Introduction Answer & Dynamic Signals
    introduction_response: Optional[str] = None
    introduction_skills: List[str] = Field(default_factory=list)
    introduction_domains: List[str] = Field(default_factory=list)
    introduction_experience_years: Optional[float] = None
    skill_provenance: Dict[str, str] = Field(default_factory=dict)

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
            intro_skills_str = f"\n- Candidate-Declared Skills (from intro): {', '.join(self.skills)}" if self.skills else ""
            exp_str = f"\n- Stated Experience: {self.experience_years} years" if self.experience_years > 0 else ""
            return (
                f"- Candidate Target: {self.seniority_level.capitalize()} {self.target_role}\n"
                f"- Focus Area: {self.interview_focus}\n"
                f"- Resume Status: No uploaded resume attached (evaluating on candidate-declared background & role fundamentals).{intro_skills_str}{exp_str}{intro_snippet}"
            )

        lines: List[str] = [
            f"- Target Role & Level: {self.seniority_level.capitalize()} {self.target_role}",
            f"- Experience: {self.experience_years} years estimated",
        ]
        if self.domains:
            lines.append(f"- Domains: {', '.join(self.domains)}")
        if self.skills:
            lines.append(f"- Verified Skills: {', '.join(self.skills[:15])}")
        if self.introduction_skills:
            lines.append(f"- Intro-Declared Additional Skills: {', '.join(self.introduction_skills)}")
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
    """Build a validated, non-hallucinated CandidateContext instance from session, resume, and Turn 0 signals."""
    # 1. Parse Resume Data if provided
    has_resume = bool(resume_data and isinstance(resume_data, dict))
    skills: List[str] = []
    skill_provenance: Dict[str, str] = {}
    experience_years = 0.0
    domains: List[str] = []
    education: List[Dict[str, Any]] = []
    summary: Optional[str] = None
    projects: List[CandidateProjectContext] = []
    work_history: List[CandidateWorkContext] = []

    if has_resume and resume_data:
        raw_skills = list(resume_data.get("skills") or [])
        for s in raw_skills:
            if s and s.strip():
                clean_s = s.strip()
                if clean_s not in skills:
                    skills.append(clean_s)
                    skill_provenance[clean_s] = "resume"

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
                skill_provenance[fs] = "session_preset"

    # 3. Dynamic Signal Extraction from Turn 0 Introduction Response
    intro_skills: List[str] = []
    intro_domains: List[str] = []
    intro_exp_years: Optional[float] = None

    if introduction_response and introduction_response.strip():
        extracted = extract_candidate_signals_from_intro(introduction_response)
        extracted_skills_list = extracted.get("skills", [])
        intro_domains = extracted.get("domains", [])
        intro_exp_years = extracted.get("experience_years")

        # Merge extracted skills without duplicating normalized resume skills
        norm_existing = {normalize_skill(s) for s in skills}
        for iskill in extracted_skills_list:
            norm_iskill = normalize_skill(iskill)
            if norm_iskill not in norm_existing:
                skills.append(iskill)
                intro_skills.append(iskill)
                norm_existing.add(norm_iskill)
                skill_provenance[iskill] = "introduction"

        # Merge extracted domains
        for idom in intro_domains:
            if idom not in domains:
                domains.append(idom)

        # Enforce experience years if candidate provided explicit experience and resume had 0.0
        if intro_exp_years is not None:
            if experience_years == 0.0:
                experience_years = intro_exp_years

    # 4. Parse JD Data if provided
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

    # Combine all JD skill requirements for matching against enriched candidate skills
    all_jd_skills = list(dict.fromkeys(jd_required + jd_tech))
    matched_skills, missing_skills = compute_matched_and_missing_skills(
        resume_skills=skills, jd_skills=all_jd_skills
    )

    # 5. Formulate high-priority areas
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
        introduction_skills=intro_skills,
        introduction_domains=intro_domains,
        introduction_experience_years=intro_exp_years,
        skill_provenance=skill_provenance,
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

