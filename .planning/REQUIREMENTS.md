# Requirements: AROVIA (AI-Powered Interview Evaluation System)

**Defined:** 2026-08-15
**Core Value:** Delivering realistic, adaptive AI mock interviews with rigorous, multi-dimensional evaluation and actionable feedback, built on a robust, highly secure, and clean full-stack architecture.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### 1. Authentication & Profile Management

- [ ] **AUTH-01**: User can register an account with name, email, and password validated server-side and hashed with bcrypt
- [ ] **AUTH-02**: User can securely log in with email and password to receive a JWT access token
- [ ] **AUTH-03**: User authentication session persists across browser page reloads via secure token storage
- [ ] **AUTH-04**: User can view and update their profile details (target role, bio, experience level)
- [ ] **AUTH-05**: User can log out securely from any page, clearing client-side session tokens

### 2. Resume Ingestion & Analysis Engine

- [ ] **RESM-01**: User can upload a resume file in PDF or DOCX format (enforcing a maximum 5 MB file size limit)
- [ ] **RESM-02**: Server defensively validates file magic bytes, MIME types, and file structure, rejecting non-matching or corrupt files
- [ ] **RESM-03**: System safely extracts plain text from uploaded resumes in background worker threads using `pdfplumber` / `pypdf` / `python-docx`
- [ ] **RESM-04**: System parses extracted resume text into structured skills, experience summary, and past projects via Gemini structured JSON schema
- [ ] **RESM-05**: User can inspect and verify their extracted skills and profile summary on the web interface

### 3. Interview Configuration & Role Targeting

- [ ] **CONF-01**: User can select a target job role from standard categories (Frontend, Backend, Full Stack, Data Science, DevOps, Mobile) or provide a custom title
- [ ] **CONF-02**: User can configure target seniority level (Junior, Mid, Senior) and interview focus (Technical Core, System Design, Behavioral)
- [ ] **CONF-03**: User can optionally provide a target job description to customize interview question generation
- [ ] **CONF-04**: User can create a new interview session initialized with their target configuration and resume context

### 4. Interactive Interview Experience

- [ ] **INTV-01**: User can view the active interview question with a real-time turn indicator (e.g., Question 1 of 6) and session timer
- [ ] **INTV-02**: User can optionally listen to the AI question read aloud via browser Text-to-Speech (Web Speech API)
- [ ] **INTV-03**: User can type their response into a text answer box with optional microphone Speech-to-Text input
- [ ] **INTV-04**: User can review and edit their transcribed response before submitting
- [ ] **INTV-05**: System dynamically evaluates answers in flight and issues targeted follow-up probing questions when appropriate before moving to the next core topic
- [ ] **INTV-06**: User can complete all interview turns and submit the session for final evaluation

### 5. Multi-Dimensional Evaluation & Scoring Engine

- [ ] **EVAL-01**: System scores candidate answers for Relevance to the specific question and target job context (0–100 scale)
- [ ] **EVAL-02**: System scores candidate answers for Technical Correctness and accuracy of explained concepts (0–100 scale)
- [ ] **EVAL-03**: System identifies and scores Key Technical Concepts and keywords covered versus missed (0–100 scale)
- [ ] **EVAL-04**: System scores candidate response Clarity, Structure, and Grammar (0–100 scale)
- [ ] **EVAL-05**: System assesses Confidence and Delivery indicators based on response depth, completeness, and sentiment (0–100 scale)
- [ ] **EVAL-06**: System synthesizes tailored benchmark ideal answers and key learning points for each question asked

### 6. Performance Reports & Analytics

- [ ] **REPT-01**: User can view a comprehensive post-interview report card displaying overall score and individual dimensional breakdowns
- [ ] **REPT-02**: User can interact with visual radar charts and dimensional performance bars representing candidate competencies
- [ ] **REPT-03**: User can review highlighted Top Strengths, Areas for Improvement, and actionable learning recommendations
- [ ] **REPT-04**: User can inspect turn-by-turn question reviews comparing submitted responses against benchmark ideal answers
- [ ] **REPT-05**: User can export and download a clean PDF copy of their interview report card

### 7. Session History & Progress Tracking

- [ ] **HIST-01**: User can view a historical list of all past completed and in-progress interview sessions on their dashboard
- [ ] **HIST-02**: User can open and review the full evaluation report from any previous interview attempt
- [ ] **HIST-03**: User can view score progression trends over time across multiple practice interview attempts

### 8. Security, Hardening & Defensive Controls

- [ ] **SECR-01**: Server validates and sanitizes all incoming payloads using strict Pydantic v2 schemas, never relying on client-side validation
- [ ] **SECR-02**: All protected endpoints derive authenticated user identity strictly from verified JWT tokens, preventing IDOR vulnerabilities
- [ ] **SECR-03**: System enforces rate limiting on authentication and AI generation endpoints using `slowapi`
- [ ] **SECR-04**: All secrets, database credentials, and Gemini API keys are loaded exclusively from `.env` via `pydantic-settings` and never committed
- [ ] **SECR-05**: Global exception middleware catches unexpected errors and returns clean, uniform JSON error responses without leaking internal stack traces

---

## v2 Requirements

Deferred to future releases. Tracked but not in current 45-day roadmap.

- **V2-CODE-01**: In-browser code editor sandbox (Monaco Editor) for live coding syntax and execution questions
- **V2-RUBR-01**: Custom scoring rubric builder allowing candidates to set custom category weights
- **V2-RECR-01**: Multi-tenant recruiter portal for managing job openings and reviewing candidate assessment submissions

---

## Out of Scope

Explicitly excluded. Documented to prevent scope creep and maintain strict project focus.

| Feature | Reason |
|---------|--------|
| **Webcam computer vision / facial emotion detection** | High false-positive rate, hardware/lighting sensitivity, privacy concerns; verbal/linguistic confidence indicators are superior for technical evaluation |
| **Real-time WebRTC peer-to-peer video streaming** | Unnecessary infrastructure overhead; direct browser-to-backend AI speech interaction meets all mock interview requirements |
| **Paid subscriptions / payment gateway integrations** | Out of scope for a college major project / portfolio platform |
| **Direct third-party corporate ATS integrations** | Focus is candidate self-practice and assessment; corporate ATS integration adds heavy enterprise sync complexity |

---

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| RESM-01 | Phase 3 | Pending |
| RESM-02 | Phase 3 | Pending |
| RESM-03 | Phase 3 | Pending |
| RESM-04 | Phase 3 | Pending |
| RESM-05 | Phase 3 | Pending |
| CONF-01 | Phase 4 | Pending |
| CONF-02 | Phase 4 | Pending |
| CONF-03 | Phase 4 | Pending |
| CONF-04 | Phase 4 | Pending |
| INTV-01 | Phase 5 | Pending |
| INTV-02 | Phase 5 | Pending |
| INTV-03 | Phase 5 | Pending |
| INTV-04 | Phase 5 | Pending |
| INTV-05 | Phase 5 | Pending |
| INTV-06 | Phase 5 | Pending |
| EVAL-01 | Phase 6 | Pending |
| EVAL-02 | Phase 6 | Pending |
| EVAL-03 | Phase 6 | Pending |
| EVAL-04 | Phase 6 | Pending |
| EVAL-05 | Phase 6 | Pending |
| EVAL-06 | Phase 6 | Pending |
| REPT-01 | Phase 7 | Pending |
| REPT-02 | Phase 7 | Pending |
| REPT-03 | Phase 7 | Pending |
| REPT-04 | Phase 7 | Pending |
| REPT-05 | Phase 7 | Pending |
| HIST-01 | Phase 8 | Pending |
| HIST-02 | Phase 8 | Pending |
| HIST-03 | Phase 8 | Pending |
| SECR-01 | Phase 1 & Phase 9 | Pending |
| SECR-02 | Phase 2 & Phase 9 | Pending |
| SECR-03 | Phase 9 | Pending |
| SECR-04 | Phase 1 | Pending |
| SECR-05 | Phase 1 & Phase 9 | Pending |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-15*
*Last updated: 2026-08-15 after user verification review*
