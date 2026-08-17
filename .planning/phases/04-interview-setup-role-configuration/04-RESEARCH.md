# Phase 04: Interview Setup & Role Configuration - Technical Research

**Phase:** 04-interview-setup-role-configuration  
**Status:** Complete  
**Date:** 2026-08-18  

---

## 1. Domain & Technical Objectives

Phase 4 implements the interview setup, role/seniority calibration, custom job description parsing, and session initialization engine.

### Key Requirements (MUST Address)
- **CONF-01:** Candidate can select from curated standard technical role presets (Backend, Frontend, Fullstack, DevOps, Data, ML, Mobile) or enter an arbitrary custom role title with customizable baseline focus skills.
- **CONF-02:** Candidate can configure target seniority tier (`junior`, `mid`, `senior`) and interview focus dimension (`Technical Core`, `System Design`, `Behavioral`).
- **CONF-03:** Candidate can supply optional custom Job Description (JD) text up to 10,000 characters with control-character sanitization, parsed into structured key requirements via `GeminiService` (`google-genai` SDK).
- **CONF-04:** Candidate can initialize an interview session linked to their account and active resume (if present), persisting configured turn pacing parameters (`planned_core_questions`, `max_total_turns`, `in_progress` status).

---

## 2. Technical Stack & Architecture

### 2.1 Presets Catalog & Role Calibration
- **Presets Catalog**: Hardcoded high-fidelity preset roles with recommended primary focus skill tags:
  - `Backend Engineer`: `["Python", "FastAPI", "SQL", "PostgreSQL", "Docker", "Redis", "REST APIs", "Microservices"]`
  - `Frontend Engineer`: `["JavaScript", "TypeScript", "React", "HTML5/CSS3", "Next.js", "State Management", "Web Performance"]`
  - `Fullstack Engineer`: `["React", "Node.js", "Python", "SQL", "REST APIs", "Docker", "Git", "CI/CD"]`
  - `DevOps / Cloud Engineer`: `["AWS", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Prometheus"]`
  - `Data Engineer`: `["Python", "SQL", "Apache Spark", "Kafka", "ETL Pipelines", "Data Warehousing", "PostgreSQL"]`
  - `Machine Learning Engineer`: `["Python", "PyTorch", "TensorFlow", "Scikit-Learn", "MLOps", "LLMs", "NLP"]`
  - `Mobile Engineer`: `["Flutter", "React Native", "Swift", "Kotlin", "Mobile UI", "REST APIs", "State Management"]`
- **Practice Modes**:
  - `full`: 6 core questions, max 9 turns (6 core + max 3 dynamic follow-ups).
  - `quick`: 3 core questions, max 5 turns (3 core + max 2 dynamic follow-ups).
- **Pacing Time Guidance**:
  - `Technical Core` & `Behavioral`: 120 seconds (2 mins) suggested answer duration.
  - `System Design`: 180 seconds (3 mins) suggested answer duration.

### 2.2 Job Description (JD) Ingestion & AI Parsing
- **Sanitization**: Maximum 10,000 characters (~1,500-2,000 words), stripped of null bytes and non-printable control characters.
- **AI Extraction Schema (`google-genai` SDK)**:
```python
class ParsedJobDescription(BaseModel):
    job_title: Optional[str] = Field(None, description="Extracted or inferred job title from JD.")
    required_skills: list[str] = Field(default_factory=list, description="Mandatory technical and engineering skills.")
    core_responsibilities: list[str] = Field(default_factory=list, description="Primary duties and responsibilities.")
    key_technologies: list[str] = Field(default_factory=list, description="Specific frameworks, languages, databases, or cloud tools.")
    experience_summary: str = Field("", description="Summary of expected experience and qualification level.")
```

### 2.3 Single Active Session Policy & Lifecycle Rules
- **Anti-Fragmentation Rule**: A candidate can only have ONE `in_progress` session at a time.
- If a candidate calls `POST /api/v1/interviews/sessions` while an active `in_progress` session exists:
  - System raises `ConflictError("An active interview session is already in progress.", error_code="ACTIVE_SESSION_EXISTS", details={"active_session_id": existing.id})`.
- The candidate can:
  - Resume the active session via live interview room.
  - Abandon the session via `POST /api/v1/interviews/sessions/{session_id}/abandon` (transitions status to `'abandoned'`).

---

## 3. Database Schema Contract

### `interview_sessions` Table (`docs/BACKEND_SCHEMA.md` §2.6)
- `id`: `VARCHAR(36)` Primary Key (UUIDv4)
- `user_id`: `VARCHAR(36)` FK -> `users.id` ON DELETE CASCADE
- `resume_id`: `VARCHAR(36)` FK -> `resumes.id` ON DELETE SET NULL (Nullable)
- `target_role`: `VARCHAR(100)`
- `seniority_level`: `VARCHAR(50)` (`'junior'`, `'mid'`, `'senior'`)
- `interview_focus`: `VARCHAR(50)` (`'Technical Core'`, `'System Design'`, `'Behavioral'`)
- `custom_job_desc`: `TEXT` (Nullable)
- `parsed_jd_data`: `JSONB` / `JSON` (Nullable)
- `focus_skills`: `JSONB` / `JSON` (Nullable, list of strings)
- `practice_mode`: `VARCHAR(50)` Default `'full'`
- `planned_core_questions`: `INTEGER` Default `6`
- `max_total_turns`: `INTEGER` Default `9`
- `current_turn_index`: `INTEGER` Default `0`
- `status`: `VARCHAR(50)` Default `'in_progress'` (`'in_progress'`, `'evaluating'`, `'completed'`, `'abandoned'`)
- `started_at`: `TIMESTAMPTZ` UTC
- `completed_at`: `TIMESTAMPTZ` UTC (Nullable)

### `interview_question_turns` Table (`docs/BACKEND_SCHEMA.md` §2.7)
- `id`: `VARCHAR(36)` Primary Key (UUIDv4)
- `session_id`: `VARCHAR(36)` FK -> `interview_sessions.id` ON DELETE CASCADE
- `turn_index`: `INTEGER`
- `question_type`: `VARCHAR(50)` Default `'core'`
- `question_text`: `TEXT`
- `candidate_answer`: `TEXT` (Nullable)
- `is_follow_up`: `BOOLEAN` Default `FALSE`
- `parent_turn_id`: `VARCHAR(36)` FK -> `interview_question_turns.id` (Nullable, self-ref)
- `ideal_answer`: `TEXT` (Nullable)
- `turn_duration_sec`: `INTEGER` (Nullable)
- `created_at`: `TIMESTAMPTZ` UTC

---

## 4. REST Endpoints Contract

- `GET /api/v1/interviews/presets`: Return role presets, seniority levels, focus options, practice modes, and pacing suggestions.
- `POST /api/v1/interviews/sessions`: Initialize a new interview session (enforces single active session check, optionally parses JD via Gemini).
- `GET /api/v1/interviews/sessions/active`: Retrieve the current candidate's active `in_progress` session (or 404 if none).
- `GET /api/v1/interviews/sessions/{session_id}`: Retrieve session metadata and configuration by ID (guarded to session owner).
- `POST /api/v1/interviews/sessions/{session_id}/abandon`: Explicitly mark an active session as `abandoned`.

---
*Research completed for Phase 4 planning.*
