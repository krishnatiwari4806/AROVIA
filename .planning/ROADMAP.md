# Roadmap: AROVIA (AI-Powered Interview Evaluation System)

## Overview

AROVIA is built incrementally as a high-security, full-stack AI interview evaluation system across 9 fine-grained Vertical MVP phases. Development begins with the core backend and database foundation, moves through defensive authentication, resume analysis, adaptive interview generation, multi-dimensional scoring, reporting and visual analytics, candidate history tracking, and culminates in comprehensive security hardening and end-to-end verification.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Core Foundation & Database Architecture** - FastAPI server setup, PostgreSQL async SQLAlchemy models, Alembic migrations, and testing baseline.
- [ ] **Phase 2: Authentication & Profile Management** - Secure user registration, bcrypt password hashing, JWT token issuance, and candidate profile management.
- [ ] **Phase 3: Resume Ingestion & Analysis Engine** - Secure PDF/DOCX upload, magic byte verification, text extraction, and Gemini structured skill parsing.
- [ ] **Phase 4: Interview Setup & Role Configuration** - Target role selection, seniority configuration, custom job description parsing, and session initialization.
- [ ] **Phase 5: Interactive Adaptive Interview Engine & Voice Flow** - Sequential question generation, dynamic follow-up probing, and speech synthesis/recognition.
- [ ] **Phase 6: Multi-Dimensional Evaluation & Scoring Engine** - 5-dimension scoring pipeline, keyword extraction, and benchmark ideal answer synthesis.
- [ ] **Phase 7: Performance Report Card, Analytics & PDF Export** - Comprehensive report views, radar/bar visual charts, strengths/weaknesses, and PDF download.
- [ ] **Phase 8: Candidate Dashboard, History & Progress Tracking** - Historical session list, past report viewer, and performance progression trends.
- [ ] **Phase 9: Security Hardening, Rate Limiting & Verification** - Rate limiting (SlowAPI), OWASP security headers, input sanitization audit, and integration tests.

---

## Phase Details

### Phase 1: Core Foundation & Database Architecture
**Goal**: Initialize FastAPI application, PostgreSQL async database connection, Alembic migration pipeline, and test harness.
**Mode**: mvp
**Depends on**: Nothing (first phase)
**Requirements**: SECR-01, SECR-04, SECR-05
**Success Criteria** (what must be TRUE):
  1. Backend API starts and returns 200 OK on health check with database connection verified.
  2. Database schemas and tables are initialized via Alembic migrations.
  3. Base configuration loads securely from `.env` via `pydantic-settings` with zero hardcoded credentials.
**Plans**: 2 plans

Plans:
- [ ] 01-01: Backend project setup, Pydantic settings, async database session, and health check endpoint.
- [ ] 01-02: SQLAlchemy base models, Alembic migration configuration, and automated test harness.

---

### Phase 2: Authentication & Profile Management
**Goal**: Implement secure user registration, bcrypt password hashing, JWT token authentication, and candidate profile management.
**Mode**: mvp
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, SECR-02
**Success Criteria** (what must be TRUE):
  1. Candidate can register with validated email/password and log in to receive a JWT access token.
  2. Protected endpoints derive user identity exclusively from the verified JWT token.
  3. Candidate can view and update their profile information and log out securely.
**Plans**: 2 plans

Plans:
- [ ] 02-01: User model, password hashing utility, JWT auth service, and register/login/logout endpoints.
- [ ] 02-02: Profile retrieval/update endpoints, authentication dependency middleware, and auth unit tests.

---

### Phase 3: Resume Ingestion & Analysis Engine
**Goal**: Implement defensive resume upload (PDF/DOCX), magic byte verification, text extraction, and Gemini structured skill parsing.
**Mode**: mvp
**Depends on**: Phase 2
**Requirements**: RESM-01, RESM-02, RESM-03, RESM-04, RESM-05
**Success Criteria** (what must be TRUE):
  1. Candidate can upload a resume file with server-side validation enforcing 5MB limit and valid magic bytes.
  2. System extracts plain text safely and parses structured skills and experience using Gemini structured JSON schemas.
  3. Candidate can review their parsed profile and extracted technical skills.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Defensive file upload validator, storage isolation, and `pdfplumber` / `python-docx` text extraction worker.
- [ ] 03-02: Gemini structured schema parser for skills/experience extraction, database persistence, and resume API endpoints.

---

### Phase 4: Interview Setup & Role Configuration
**Goal**: Implement target role selection, seniority configuration, custom job description parsing, and interview session initialization.
**Mode**: mvp
**Depends on**: Phase 3
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04
**Success Criteria** (what must be TRUE):
  1. Candidate can select standard technical roles or input custom titles and target seniority levels.
  2. Candidate can supply custom job descriptions to contextualize question generation.
  3. System creates and persists an initialized interview session record linked to the candidate.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Interview session models, configuration schemas, and session creation endpoints.
- [ ] 04-02: Role presets, job description parser service, and interview setup configuration API.

---

### Phase 5: Interactive Adaptive Interview Engine & Voice Flow
**Goal**: Implement sequential question generation with Gemini prompt chaining, dynamic follow-up probing, and speech synthesis/recognition.
**Mode**: mvp
**Depends on**: Phase 4
**Requirements**: INTV-01, INTV-02, INTV-03, INTV-04, INTV-05, INTV-06
**Success Criteria** (what must be TRUE):
  1. Candidate receives context-aware interview questions one turn at a time with active turn indicators and timers.
  2. Candidate can submit responses via text or microphone transcription, with manual text editing prior to submission.
  3. AI dynamically generates targeted follow-up probing questions when responses warrant depth before moving forward.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Gemini interview prompt chaining service and adaptive follow-up state machine.
- [ ] 05-02: Question retrieval, answer submission endpoints, and turn transition handlers.
- [ ] 05-03: Frontend interactive interview room with Web Speech API audio synthesis/recognition and manual edit fallback.

---

### Phase 6: Multi-Dimensional Evaluation & Scoring Engine
**Goal**: Implement server-side evaluation pipeline scoring candidate answers across 5 dimensions and synthesizing benchmark ideal answers.
**Mode**: mvp
**Depends on**: Phase 5
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06
**Success Criteria** (what must be TRUE):
  1. System scores answers across Relevance, Correctness, Keywords, Clarity, and Confidence indicators (0–100 scale).
  2. System extracts key technical concepts covered vs. missed and synthesizes benchmark ideal answers.
  3. Evaluations and scores are persistently stored in database session records.
**Plans**: 2 plans

Plans:
- [ ] 06-01: Multi-dimensional scoring algorithms and Gemini structured JSON evaluation schemas.
- [ ] 06-02: Post-session evaluation orchestrator, ideal answer generator, and evaluation persistence service.

---

### Phase 7: Performance Report Card, Analytics & PDF Export
**Goal**: Implement comprehensive post-interview performance reporting with dimensional breakdowns, radar/bar visual charts, strengths/weaknesses, and PDF download.
**Mode**: mvp
**Depends on**: Phase 6
**Requirements**: REPT-01, REPT-02, REPT-03, REPT-04, REPT-05
**Success Criteria** (what must be TRUE):
  1. Candidate can view overall score, category breakdown, strengths, and areas for improvement.
  2. Candidate can inspect interactive visual radar charts and turn-by-turn question reviews.
  3. Candidate can download an exportable PDF copy of their interview report card.
**Plans**: 2 plans

Plans:
- [ ] 07-01: Report data aggregation API endpoint and score summary DTOs.
- [ ] 07-02: Frontend Report Card UI with radar/bar visual charts, question breakdowns, and client-side PDF export.

---

### Phase 8: Candidate Dashboard, History & Progress Tracking
**Goal**: Implement candidate dashboard displaying past interview sessions, historical score trends over time, and profile settings.
**Mode**: mvp
**Depends on**: Phase 7
**Requirements**: HIST-01, HIST-02, HIST-03
**Success Criteria** (what must be TRUE):
  1. Candidate can view a list of all past practice interview attempts with scores and timestamps.
  2. Candidate can reopen and view any historical interview report.
  3. Candidate can view visual progression charts tracking improvement across multiple sessions.
**Plans**: 2 plans

Plans:
- [ ] 08-01: Session history and progress trend aggregation API endpoints.
- [ ] 08-02: Frontend Candidate Dashboard with past interview archive and performance trend analytics.

---

### Phase 9: Security Hardening, Rate Limiting & Verification
**Goal**: Implement rate limiting (SlowAPI), OWASP security headers, defense-in-depth sanitization audit, end-to-end integration tests, and deployment verification.
**Mode**: mvp
**Depends on**: Phase 8
**Requirements**: SECR-01, SECR-02, SECR-03, SECR-05
**Success Criteria** (what must be TRUE):
  1. Rate limiting throttles brute force auth and spam AI generation requests.
  2. Security headers (HSTS, CSP, X-Frame-Options) and input sanitizers pass security audit.
  3. End-to-end integration test suite verifies full candidate interview workflow.
**Plans**: 2 plans

Plans:
- [ ] 09-01: SlowAPI rate limiting configuration, security middleware headers, and defensive error handler hardening.
- [ ] 09-02: End-to-end integration test suite, security vulnerability scan, and project verification sign-off.

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

| Phase | Mode | Plans Complete | Status | Completed |
|-------|------|----------------|--------|-----------|
| 1. Core Foundation & Database Architecture | mvp | 0/2 | Not started | - |
| 2. Authentication & Profile Management | mvp | 0/2 | Not started | - |
| 3. Resume Ingestion & Analysis Engine | mvp | 0/2 | Not started | - |
| 4. Interview Setup & Role Configuration | mvp | 0/2 | Not started | - |
| 5. Interactive Adaptive Interview Engine & Voice Flow | mvp | 0/3 | Not started | - |
| 6. Multi-Dimensional Evaluation & Scoring Engine | mvp | 0/2 | Not started | - |
| 7. Performance Report Card, Analytics & PDF Export | mvp | 0/2 | Not started | - |
| 8. Candidate Dashboard, History & Progress Tracking | mvp | 0/2 | Not started | - |
| 9. Security Hardening, Rate Limiting & Verification | mvp | 0/2 | Not started | - |
