# Phase 3: Resume Ingestion & Analysis Engine - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers secure, defensive candidate resume ingestion (PDF and DOCX formats), multi-layer validation (size limits, MIME types, magic bytes), plain-text extraction (`pdfplumber` / `python-docx`), Google Gemini structured skill & career summary extraction, and candidate profile review/editing endpoints.

</domain>

<decisions>
## Implementation Decisions

### 1. Resume Multiplicity & Storage
- **D-01 (Single Active Resume):** A candidate maintains a single active resume in the system. Uploading a new resume cleanly replaces the previous resume file on disk and its corresponding database record.
- **D-02 (Flat Storage Layout):** Uploaded files are stored in a flat, isolated filesystem directory (`storage/resumes/<uuid>.<ext>`) with strict UUID-based non-guessable filenames and restrictive filesystem permissions (`0600`).

### 2. Text Extraction, Sanitization & Length Boundaries
- **D-03 (Magic Byte & Size Enforcement):** Strictly enforce 5 MB (`5,242,880 bytes`) file size limit. Validate file signatures via magic bytes: `%PDF-` for PDF, and zip header `PK\x03\x04` verifying `[Content_Types].xml` for DOCX.
- **D-04 (Scanned/Empty PDF Rejection):** If extracted text is fewer than 50 characters or empty, fail closed and reject the upload with HTTP 422 (`"No extractable text found. Please upload a standard text-based PDF/DOCX resume."`).
- **D-05 (Sanitization & Bounding):** Extracted plain text is bounded at 30,000 characters (~6,000 words), stripped of null bytes/control characters, and wrapped in `<resume_text>` tags to prevent LLM prompt injection.

### 3. Gemini Structured Schema & Resilience
- **D-06 (Rich Extracted Schema):** The structured schema extracted by Gemini must include:
  - `skills`: List of technical skills, languages, frameworks, and developer tools.
  - `experience_years`: Estimated total years of professional experience (float).
  - `domains`: List of primary engineering domains (e.g. `["Backend", "Cloud Infrastructure"]`).
  - `education`: List of degrees, institutions, and graduation years.
  - `summary`: Concise executive career summary (2–3 sentences).
- **D-07 (Configurable Model & Native Structured Output):** Use Google GenAI SDK with native Pydantic schema validation (`response_schema`). Model ID is configurable via `settings.GEMINI_MODEL` (e.g., current active Flash model from Google AI API in `.env`). Zero hard-coded obsolete model IDs.
- **D-08 (Retry & Fault Tolerance):** Implement 1 automatic retry with exponential backoff on transient network/API failures. Unrecoverable provider outages return a clean HTTP 503 Service Unavailable error without crashing the server.

### 4. Candidate Review & Overrides API
- **D-09 (Full CRUD Lifecycle):** Candidates have full control over their resume and parsed profile via 4 endpoints:
  - `POST /api/v1/resumes/upload`: Uploads resume file, validates magic bytes/size, extracts text, invokes Gemini structured parser, and saves record.
  - `GET /api/v1/resumes/me`: Retrieves current candidate's active resume metadata, raw text snippet, and parsed schema.
  - `PUT /api/v1/resumes/me/parsed`: Enables candidate to review, add, edit, or override parsed skills, experience years, domains, and summary before interviews.
  - `DELETE /api/v1/resumes/me`: Deletes resume file from disk and purges the database record.

### the agent's Discretion
- Exact extraction worker timeout handling (e.g. 15-second worker timeout for `pdfplumber` / `python-docx` execution in thread pool via `asyncio.to_thread`).
- Helper utility structure and Pydantic DTO definitions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Database Schema
- `docs/BACKEND_SCHEMA.md` §2.5 — Complete `resumes` table definition, JSONB `parsed_data` structure, foreign key cascading constraints (`user_id -> users.id ON DELETE CASCADE`).
- `docs/TRD.md` §4.2 — Resume Ingestion Architecture & Security Validation rules.
- `docs/APP_FLOW.md` §2.2 — Onboarding & Resume Upload flow.

### Security & Dependencies
- `backend/app/api/deps.py` — `get_current_user` Bearer authentication guard.
- `backend/app/core/config.py` — Settings configuration including `GEMINI_API_KEY`, `GEMINI_MODEL`, and storage directories.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/api/deps.py`: `get_current_user` for securing all `/api/v1/resumes/*` routes.
- `app/core/exceptions.py`: `AppError`, `ValidationError`, `NotFoundError`, `ConflictError` for consistent HTTP error formats.
- `app/core/rate_limit.py`: SlowAPI limiter for rate limiting upload endpoints (e.g. `5/minute`).
- `app/db/base.py` & `CommonModelMixin`: UUID primary keys and UTC audit timestamps.

### Established Patterns
- SQLAlchemy 2.0 async ORM models with Pydantic v2 DTO schemas.
- Defensive server-side validation on all incoming data.
- Atomic database sessions via `get_db`.

### Integration Points
- `app/models/resume.py`: New `Resume` model linking to `User`.
- `app/api/v1/endpoints/resumes.py`: Mounted under `/api/v1/resumes` in `app/api/v1/router.py`.

</code_context>

<specifics>
## Specific Ideas

- In dev/testing mode, file storage path defaults to `backend/storage/resumes` or configurable local path.
- Upload stream reads chunks defensively to enforce the 5MB size limit before writing the full payload to disk.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed strictly within Phase 3 scope.

</deferred>

---

*Phase: 03-resume-ingestion-analysis-engine*  
*Context gathered: 2026-08-16*  
