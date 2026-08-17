# Phase 04: Interview Setup & Role Configuration - Context

**Gathered:** 2026-08-17  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 4 delivers the interview configuration and session initialization layer. It enables candidates to configure their mock interview environment by choosing curated role presets or custom roles, setting seniority tiers, defining focus dimensions (`Technical Core`, `System Design`, `Behavioral`), optionally submitting and parsing Job Description text, and creating an initialized interview session state (`in_progress`) linked to their candidate account and active resume.

</domain>

<decisions>
## Implementation Decisions

### Role Presets & Custom Roles
- **D-01 (Role Presets):** Offer curated top presets (`Backend Engineer`, `Frontend Engineer`, `Fullstack Engineer`, `DevOps / Cloud Engineer`, `Data Engineer`, `Machine Learning Engineer`, `Mobile Engineer`) with default focus skills that auto-populate and can be adjusted by the candidate.
- **D-02 (Custom Roles):** Support arbitrary custom role titles entered as free-text (e.g. "Site Reliability Engineer", "Security Engineer").

### Job Description (JD) Ingestion & AI Parsing
- **D-03 (JD Validation & Sanitization):** Enforce a strict 10,000 character limit on pasted Job Descriptions. Strip null bytes and non-printable control characters.
- **D-04 (Structured JD Parsing):** If a Job Description is provided, invoke `GeminiService` (`google-genai` SDK) to extract structured key requirements (`required_skills`, `core_responsibilities`, `key_technologies`).
- **D-05 (Context Priority):** The Job Description sets the target role expectations and question topics, while the candidate's resume provides background projects/experience for personalized probing.

### Session Calibration & Turn Pacing
- **D-06 (Practice Modes):** Support two configurable practice modes during session setup:
  - **Full Mock Interview (Default):** 6 core questions, max 9 turns (6 core + up to 3 dynamic follow-ups).
  - **Quick Practice:** 3 core questions, max 5 turns (3 core + up to 2 dynamic follow-ups).
- **D-07 (Focus Types & Seniority):** Support 3 focus dimensions (`Technical Core`, `System Design`, `Behavioral`) and 3 seniority tiers (`junior`, `mid`, `senior`).
- **D-08 (Turn Time Guidance):** Provide recommended response time budgets in setup metadata: 120 seconds (2 mins) for `Technical Core` and `Behavioral`, and 180 seconds (3 mins) for `System Design`.

### Session Concurrency & Lifecycle Rules
- **D-09 (Single Active Session Policy):** Prevent silent abandonment or duplicate active sessions. If a candidate has an unfinished session (`in_progress`), return an explicit status with metadata to either resume the existing session or mark it `abandoned` before starting a new one.
- **D-10 (Session Status Lifecycle):** Maintain structured session statuses: `'in_progress'`, `'evaluating'`, `'completed'`, `'abandoned'`.
- **D-11 (Resume Association):** Store `resume_id` on the session with `ON DELETE SET NULL` foreign key behavior so deleting a resume does not purge interview records.

### the agent's Discretion
- Database schema implementation for `interview_sessions` (and stub `interview_question_turns` if needed for foreign keys) strictly adhering to `docs/BACKEND_SCHEMA.md` §2.6 and §2.7.
- Default skill tag suggestions per role preset.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Schema & Architecture
- `docs/BACKEND_SCHEMA.md` §2.6 — `interview_sessions` table specification and lifecycle state definition.
- `docs/BACKEND_SCHEMA.md` §2.7 — `interview_question_turns` table specification.
- `docs/BACKEND_SCHEMA.md` §4.2 — Privacy & Data Retention (resume link `ON DELETE SET NULL`).

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — Requirements `CONF-01`, `CONF-02`, `CONF-03`, `CONF-04`.
- `.planning/ROADMAP.md` — Phase 4 scope and deliverables.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app.services.gemini_service.GeminiService`: Reuse `google-genai` SDK wrapper with structured response schema and automatic retry logic for JD parsing.
- `app.api.deps.get_current_user`: Bearer JWT token authentication dependency to secure session initialization endpoints.
- `app.db.base.Base` & `CommonModelMixin`: Standard UUIDv4 primary keys and UTC audit timestamps.
- `app.core.rate_limit.limiter`: SlowAPI rate limiter for session setup endpoints.

### Established Patterns
- Pydantic v2 schemas with `ConfigDict(from_attributes=True)` and strict validation.
- Centralized exception handling via `app.core.exceptions` (`AppError`, `ValidationError`, `NotFoundError`, `ConflictError`).
- Alembic database migration versioning (`003_create_interview_tables.py`).

### Integration Points
- Mount `/api/v1/interviews` router into `app/api/v1/router.py`.
- Link active candidate resume (`Resume` model) via `session.resume_id`.

</code_context>

<specifics>
## Specific Ideas

- Setup payload allows candidate to provide: `target_role`, `seniority_level`, `interview_focus`, `practice_mode` (Full vs Quick), optional `custom_job_desc`, and optional `focus_skills` tags.
- Dedicated endpoints:
  - `GET /api/v1/interviews/presets`: Return preset roles, focus skills, seniority tiers, and pacing guidelines.
  - `POST /api/v1/interviews/sessions`: Initialize new session (with active session check).
  - `GET /api/v1/interviews/sessions/active`: Retrieve active pending session if one exists.
  - `POST /api/v1/interviews/sessions/{id}/abandon`: Explicitly abandon an active session.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed strictly within Phase 4 configuration scope. Live question generation and audio synthesis are scheduled for Phase 5.

</deferred>

---

*Phase: 04-interview-setup-role-configuration*  
*Context gathered: 2026-08-17*  
