"""Curated role presets catalog service."""

from app.schemas.interview import (
    PresetsCatalogResponse,
    RolePresetItem,
)

ROLE_PRESETS: list[RolePresetItem] = [
    RolePresetItem(
        role_id="backend-engineer",
        title="Backend Engineer",
        description="Core backend server architectures, data modeling, API design, and performance optimization.",
        default_skills=[
            "Python",
            "FastAPI",
            "SQL",
            "PostgreSQL",
            "Docker",
            "Redis",
            "REST APIs",
            "Microservices",
        ],
        recommended_seniority=["junior", "mid", "senior"],
    ),
    RolePresetItem(
        role_id="frontend-engineer",
        title="Frontend Engineer",
        description="Modern web UI, component architecture, state management, and web performance.",
        default_skills=[
            "JavaScript",
            "TypeScript",
            "React",
            "HTML5/CSS3",
            "Next.js",
            "State Management",
            "Web Performance",
        ],
        recommended_seniority=["junior", "mid", "senior"],
    ),
    RolePresetItem(
        role_id="fullstack-engineer",
        title="Fullstack Engineer",
        description="End-to-end web applications combining robust backend APIs with responsive frontend user interfaces.",
        default_skills=[
            "React",
            "Node.js",
            "Python",
            "SQL",
            "REST APIs",
            "Docker",
            "Git",
            "CI/CD",
        ],
        recommended_seniority=["junior", "mid", "senior"],
    ),
    RolePresetItem(
        role_id="devops-cloud-engineer",
        title="DevOps / Cloud Engineer",
        description="Infrastructure as code, CI/CD automation, cloud architecture, and site reliability.",
        default_skills=[
            "AWS",
            "Docker",
            "Kubernetes",
            "Terraform",
            "CI/CD",
            "Linux",
            "Prometheus",
        ],
        recommended_seniority=["junior", "mid", "senior"],
    ),
    RolePresetItem(
        role_id="data-engineer",
        title="Data Engineer",
        description="Data pipelines, stream processing, warehousing, and distributed data computation.",
        default_skills=[
            "Python",
            "SQL",
            "Apache Spark",
            "Kafka",
            "ETL Pipelines",
            "Data Warehousing",
            "PostgreSQL",
        ],
        recommended_seniority=["junior", "mid", "senior"],
    ),
    RolePresetItem(
        role_id="ml-engineer",
        title="Machine Learning Engineer",
        description="Applied machine learning models, MLOps, deep learning pipelines, and LLM applications.",
        default_skills=[
            "Python",
            "PyTorch",
            "TensorFlow",
            "Scikit-Learn",
            "MLOps",
            "LLMs",
            "NLP",
        ],
        recommended_seniority=["junior", "mid", "senior"],
    ),
    RolePresetItem(
        role_id="mobile-engineer",
        title="Mobile Engineer",
        description="Cross-platform and native mobile applications with fluid UI and offline-first storage.",
        default_skills=[
            "Flutter",
            "React Native",
            "Swift",
            "Kotlin",
            "Mobile UI",
            "REST APIs",
            "State Management",
        ],
        recommended_seniority=["junior", "mid", "senior"],
    ),
]

SENIORITY_LEVELS = [
    {
        "id": "junior",
        "label": "Junior (0-2 years)",
        "description": "Focus on language fundamentals, syntax proficiency, and standard problem solving.",
    },
    {
        "id": "mid",
        "label": "Mid-Level (3-5 years)",
        "description": "Focus on clean architecture, design patterns, testing, error resilience, and optimization.",
    },
    {
        "id": "senior",
        "label": "Senior (5+ years)",
        "description": "Focus on high-level system design, trade-offs, scalability, failure domains, and leadership.",
    },
]

FOCUS_AREAS = [
    {
        "id": "Technical Core",
        "label": "Technical Core",
        "description": "Hands-on engineering fundamentals, domain algorithms, frameworks, and practical coding concepts.",
    },
    {
        "id": "System Design",
        "label": "System Design",
        "description": "Scalable architectural trade-offs, caching, partitioning, reliability, and concurrency.",
    },
    {
        "id": "Behavioral",
        "label": "Behavioral & STAR",
        "description": "Collaboration, conflict resolution, technical ownership, and structured STAR situation handling.",
    },
]

PRACTICE_MODES = [
    {
        "id": "full",
        "label": "Full Mock Interview",
        "description": "Comprehensive evaluation with 6 core questions and up to 3 dynamic follow-ups (9 max turns).",
        "core_questions": 6,
        "max_turns": 9,
    },
    {
        "id": "quick",
        "label": "Quick Practice",
        "description": "Fast practice run with 3 core questions and up to 2 dynamic follow-ups (5 max turns).",
        "core_questions": 3,
        "max_turns": 5,
    },
]

PACING_GUIDELINES = {
    "Technical Core": 120,
    "Behavioral": 120,
    "System Design": 180,
}


def get_presets_catalog() -> PresetsCatalogResponse:
    """Return complete curated presets catalog."""
    return PresetsCatalogResponse(
        roles=ROLE_PRESETS,
        seniority_levels=SENIORITY_LEVELS,
        focus_areas=FOCUS_AREAS,
        practice_modes=PRACTICE_MODES,
        pacing_guidelines=PACING_GUIDELINES,
    )
