# Technical Requirements Document (TRD)
# AROVIA — AI-Powered Interview Evaluation System

**Version:** 1.1.0  
**Date:** 2026-08-16  
**Status:** Architecture Baseline — Revised for Review  
**Target Milestone:** 45-Day Full-Stack Implementation  

---

## Executive Summary

**AROVIA** is a secure, modular, full-stack web application that conducts realistic, adaptive mock interviews and provides multi-dimensional performance evaluation. Designed primarily as a candidate self-practice and assessment platform, AROVIA bridges the gap between static interview preparation and high-stakes technical/behavioral interviews.

The system ingests candidate resumes, extracts core competencies and experiences, calibrates tailored interview sessions based on target roles and job descriptions, conducts dynamic conversational interview turns with real-time Speech-to-Text (STT) and Text-to-Speech (TTS), dynamically generates follow-up probing questions, and evaluates candidate responses across five core dimensions.

This document establishes the technical, architectural, and security requirements governing the implementation of AROVIA.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Frontend Technology and Structure](#2-frontend-technology-and-structure)
3. [Backend Technology and Structure](#3-backend-technology-and-structure)
4. [PostgreSQL Database Architecture](#4-postgresql-database-architecture)
5. [Authentication Architecture](#5-authentication-architecture)
6. [AI Integration Architecture](#6-ai-integration-architecture)
7. [Resume Processing Architecture](#7-resume-processing-architecture)
8. [Interview Engine Architecture](#8-interview-engine-architecture)
9. [Evaluation Engine Architecture](#9-evaluation-engine-architecture)
10. [Reports and History Architecture](#10-reports-and-history-architecture)
11. [API Design and Communication](#11-api-design-and-communication)
12. [Validation and Sanitization](#12-validation-and-sanitization)
13. [File Upload Security](#13-file-upload-security)
14. [Authorization and Data Ownership](#14-authorization-and-data-ownership)
15. [Error Handling and Logging](#15-error-handling-and-logging)
16. [Security Requirements](#16-security-requirements)
17. [Testing Strategy](#17-testing-strategy)
18. [Environment and Secret Management](#18-environment-and-secret-management)
19. [Development and Deployment Architecture](#19-development-and-deployment-architecture)
20. [Performance and Scalability Considerations](#20-performance-and-scalability-considerations)
21. [45-Day MVP Scope Control & Simplicity Rules](#21-45-day-mvp-scope-control--simplicity-rules)
22. [Architecture Decision Records & Roadmap Alignment](#22-architecture-decision-records--roadmap-alignment)

---

## 1. System Architecture

### 1.1 High-Level Architecture Overview

AROVIA is structured as a decoupled client-server architecture:
- **Client Tier:** Single Page Application (SPA) built with React 18+ and Vite, utilizing standard browser Web APIs for low-latency audio interaction.
- **API & Application Tier:** Asynchronous Python service powered by FastAPI and Uvicorn, enforcing strict Pydantic v2 data contracts and defensive security middleware.
- **Persistence Tier:** PostgreSQL 16+ relational database managed via SQLAlchemy 2.0 Async ORM and Alembic migration version control.
- **External AI Tier:** Google Gemini API communicating via HTTPS using native structured JSON schemas (`response_schema`), with model IDs dynamically configured via environment variables.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Client Tier (React + Vite SPA)                    │
│  - Candidate Dashboard, Resume Setup, Live Interview Room, Report Card │
│  - Browser Web Speech API (STT Transcription & TTS Speech Synthesis)   │
│  - In-Memory Access Token Storage + HttpOnly Refresh Cookie Sync       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTPS / REST JSON
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     API Gateway & Security Layer (FastAPI)              │
│  - CORS Middleware, SlowAPI Rate Limiter, Global Exception Handler     │
│  - JWT Bearer Authentication & Dependency Injection Security Guards     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Auth & Profile │         │ Resume Ingestion│         │ Interview &     │
│  Service        │         │ Service         │         │ Scoring Service │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Persistence & External AI Layer                   │
│  - PostgreSQL 16+ (SQLAlchemy 2.0 Async via asyncpg driver)             │
│  - Restricted Local File Storage (/storage/resumes/ with 0600 perms)    │
│  - Google Gemini API (Configurable Model IDs via google-genai SDK)      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Architectural Principles
- **Defensive Validation First:** Server-side Pydantic models validate every input; client-side validation is strictly treated as a UX affordance.
- **Zero Trust Data Ownership:** Every protected query filters by the authenticated user's ID extracted directly from the verified JWT payload.
- **Fail-Fast Configuration:** Application refuses to initialize if critical secrets or connection strings are missing or malformed.
- **Low-Latency Speech Architecture:** Audio synthesis and transcription occur locally via browser Web Speech API with manual text editing fallbacks, avoiding heavy server-side streaming bottlenecks.
- **Controlled Background Evaluation:** In-process asynchronous task execution via FastAPI `BackgroundTasks` for report generation, avoiding external queue infrastructure (e.g., Celery/Redis) in the MVP.

---

## 2. Frontend Technology and Structure

### 2.1 Technology Selection
| Technology | Version | Purpose | Architectural Rationale |
|---|---|---|---|
| **React** | 18+ / 19 | UI Component Framework | Declarative UI state management, mature ecosystem, predictable component lifecycles |
| **Vite** | 5.0+ | Build Tool & Dev Server | Sub-second Hot Module Replacement (HMR) and optimized ESM production bundling |
| **Vanilla CSS / Custom Tokens** | CSS3 | Styling & Design System | Complete control over CSS variables, zero Tailwind compilation bloat, lightweight bundle |
| **Lucide React** | 0.400+ | UI Icons | Consistent, lightweight SVG iconography |
| **Chart.js / Recharts** | Current | Visual Data Analytics | Rendering radar charts (competency dimensions) and progression bar charts |
| **jsPDF & html2canvas** | Current | Client-Side PDF Export | Instant report generation and download without server-side rendering overhead |

### 2.2 Directory Structure (`frontend/src/`)
```
frontend/src/
├── assets/                  # Static SVG assets, branding logos, illustrations
├── components/
│   ├── common/              # Button, Card, Modal, Input, Badge, Loader, Alert
│   ├── layout/              # Navbar, Sidebar, Footer, PageContainer
│   ├── audio/               # VoiceWaveform, MicButton, SpeechSettings, AudioPlayer
│   └── charts/              # RadarChart, ScoreBar, ScoreProgressionChart
├── context/
│   ├── AuthContext.jsx      # Authentication state (in-memory access token, user profile)
│   └── InterviewContext.jsx # Live session state machine, timer, turn manager
├── hooks/
│   ├── useAuth.js           # Auth context consumer hook
│   ├── useSpeechRecognition.js # Web Speech STT hook with browser fallback
│   ├── useSpeechSynthesis.js   # Web Speech TTS hook with voice selection
│   └── useTimer.js          # Countdown and turn duration tracking
├── pages/
│   ├── Home.jsx             # Landing page and platform overview
│   ├── Login.jsx            # Email/password & Google Sign-In view
│   ├── Register.jsx         # Candidate registration view
│   ├── Dashboard.jsx        # Candidate dashboard & practice history
│   ├── ResumeUpload.jsx     # Resume file upload & parsed skill verification
│   ├── InterviewSetup.jsx   # Role, seniority, and JD configuration
│   ├── LiveInterview.jsx    # Audio/visual interactive mock interview room
│   └── ReportView.jsx       # Multi-dimensional report card & analytics
├── services/
│   ├── api.js               # Axios instance with auth interceptor & refresh handling
│   ├── authService.js       # Login, register, logout, refresh, profile API calls
│   ├── resumeService.js     # Resume upload, parse status, skill retrieval API
│   ├── interviewService.js  # Create session, fetch question, submit turn API
│   └── reportService.js     # Fetch evaluation report, session history API
├── styles/
│   ├── index.css            # CSS variables, typography tokens, layout resets
│   └── components.css       # Reusable component utility styles
├── App.jsx                  # React Router configuration and route guards
└── main.jsx                 # Application DOM mount
```

---

## 3. Backend Technology and Structure

### 3.1 Technology Selection
| Technology | Version | Purpose | Architectural Rationale |
|---|---|---|---|
| **Python** | 3.11+ / 3.14 | Runtime Engine | Standard runtime for AI/NLP libraries with native async support |
| **FastAPI** | >=0.115.0 | ASGI Web API Framework | High-throughput asynchronous performance, automatic OpenAPI docs, native Pydantic validation |
| **Uvicorn** | >=0.30.0 | ASGI Production Web Server | Lightning-fast asynchronous server implementation |
| **Pydantic & Settings** | >=2.9.0 / >=2.4.0 | Schema Validation & Config | Strict C-core validation, environment variable type safety |
| **SQLAlchemy** | >=2.0.30 | Async Database ORM | Modern 2.0 async syntax, robust query builder, clean model mappings |
| **asyncpg** | >=0.29.0 | PostgreSQL Async Driver | High-speed binary async database communication |
| **Alembic** | >=1.13.0 | Schema Migrations | Version-controlled DDL tracking and automated migrations |
| **pdfplumber & pypdf** | >=0.11.0 | PDF Text Extraction | Secure, layout-aware textual extraction without native OS dependencies |
| **python-docx** | >=1.1.0 | DOCX Text Extraction | Clean extraction of structured text from Microsoft Word documents |
| **passlib[bcrypt] / bcrypt** | >=4.0.0 | Password Hashing | Industry standard salted bcrypt cryptographic password hashing |
| **PyJWT** | >=2.9.0 | JWT Token Management | Cryptographically signed stateless JWT authorization tokens |
| **slowapi** | >=0.1.9 | Rate Limiting | Rate-limiting protection on login, registration, and AI endpoints |

### 3.2 Directory Structure (`backend/`)
```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py          # /api/v1/auth (register, login, google, refresh, me, reset)
│   │       │   ├── resumes.py       # /api/v1/resumes (upload, get, delete, parse-status)
│   │       │   ├── configurations.py# /api/v1/configurations (roles, seniority levels, topics)
│   │       │   ├── interviews.py    # /api/v1/interviews (create, turn, submit, complete)
│   │       │   ├── reports.py       # /api/v1/reports (get-by-id, status, history)
│   │       │   └── health.py        # /api/v1/health (live database ping)
│   │       └── router.py            # Aggregated v1 API router
│   ├── core/
│   │   ├── config.py                # Pydantic BaseSettings (.env loading & validation)
│   │   ├── security.py              # Password hashing, JWT creation/decoding, token cookies
│   │   ├── logging.py               # Structured application logger
│   │   ├── exceptions.py            # AppError hierarchy & global exception handlers
│   │   └── rate_limit.py            # SlowAPI rate limiter configuration
│   ├── db/
│   │   ├── base.py                  # DeclarativeBase & CommonModelMixin (UUID, timestamps)
│   │   └── session.py               # AsyncEngine & request-scoped get_db dependency
│   ├── models/                      # SQLAlchemy ORM persistent database entities
│   │   ├── user.py                  # User, PasswordResetToken, RefreshToken
│   │   ├── resume.py                # Resume entity
│   │   ├── interview.py             # InterviewSession, InterviewQuestionTurn
│   │   └── report.py                # EvaluationReport entity
│   ├── schemas/                     # Pydantic v2 Request/Response contracts
│   │   ├── auth.py                  # UserCreate, UserLogin, TokenResponse, UserResponse
│   │   ├── resume.py                # ResumeUploadResponse, ParsedResumeSchema
│   │   ├── interview.py             # SessionCreate, QuestionTurnResponse, AnswerSubmitRequest
│   │   ├── report.py                # EvaluationReportResponse, DimensionScoreSchema
│   │   └── health.py                # HealthCheckResponse
│   ├── services/                    # Domain logic & third-party integrations
│   │   ├── auth_service.py          # Registration, credential validation, Google OAuth verification
│   │   ├── resume_service.py        # File validation, text extraction, schema parsing, deletion
│   │   ├── ai_service.py            # Gemini API wrapper, configurable model IDs, prompt templates
│   │   ├── interview_service.py     # State machine, question generation, follow-up logic
│   │   └── evaluation_service.py    # Multi-dimensional scoring & background task runner
│   └── main.py                      # FastAPI application factory, CORS, exception handlers
├── alembic/
│   ├── env.py                       # Async migration runner
│   ├── script.py.mako               # Migration template
│   └── versions/                    # Migration revision scripts
├── tests/
│   ├── conftest.py                  # SQLite in-memory fixtures, AsyncClient
│   ├── test_config.py               # Configuration & fail-fast tests
│   ├── test_auth.py                 # Registration, login, password hashing tests
│   ├── test_health.py               # Health check & exception handler tests
│   ├── test_resumes.py              # File upload validation & extraction tests
│   ├── test_interviews.py           # Interview state machine & question turns tests
│   └── test_evaluation.py           # Scoring calculations & dimension tests
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── .env.example
```

---

## 4. PostgreSQL Database Architecture

### 4.1 Relational Schema Diagram (ERD)

```
┌──────────────────────────┐             ┌──────────────────────────┐
│          users           │ 1         * │         resumes          │
├──────────────────────────┼────────────┼──────────────────────────┤
│ id: VARCHAR(36) PK [UUID]│             │ id: VARCHAR(36) PK [UUID]│
│ email: VARCHAR(255) UNIQ │             │ user_id: VARCHAR(36) FK  │
│ hashed_password: VARCHAR │             │ file_name: VARCHAR(255)  │
│ full_name: VARCHAR(150)  │             │ file_path: VARCHAR(500)  │
│ auth_provider: VARCHAR   │             │ file_size_bytes: INTEGER │
│ target_role: VARCHAR     │             │ raw_text: TEXT           │
│ experience_level: VARCHAR│             │ parsed_data: JSONB       │
│ failed_login_attempts:INT│             │ created_at: TIMESTAMPTZ  │
│ lockout_until:TIMESTAMPTZ│             │ updated_at: TIMESTAMPTZ  │
│ created_at: TIMESTAMPTZ  │             └──────────────────────────┘
│ updated_at: TIMESTAMPTZ  │
└────────────┬─────────────┘
             │ 1
             │
             │ *
┌────────────▼─────────────┐             ┌──────────────────────────┐
│    interview_sessions    │ 1         * │ interview_question_turns │
├──────────────────────────┼────────────┼──────────────────────────┤
│ id: VARCHAR(36) PK [UUID]│             │ id: VARCHAR(36) PK [UUID]│
│ user_id: VARCHAR(36) FK  │             │ session_id: VARCHAR(36)FK│
│ resume_id: VARCHAR(36)FK │             │ turn_index: INTEGER      │
│ target_role: VARCHAR(100)│             │ question_text: TEXT      │
│ seniority_level: VARCHAR │             │ question_type: VARCHAR   │
│ interview_focus: VARCHAR │             │ candidate_answer: TEXT   │
│ custom_job_desc: TEXT    │             │ is_follow_up: BOOLEAN    │
│ total_questions: INTEGER │             │ parent_turn_id: VARCHAR  │
│ status: VARCHAR(50)      │             │ ideal_answer: TEXT       │
│ started_at: TIMESTAMPTZ  │             │ turn_duration_sec: INT   │
│ completed_at: TIMESTAMPTZ│             │ created_at: TIMESTAMPTZ  │
└────────────┬─────────────┘             └──────────────────────────┘
             │ 1
             │
             │ 1
┌────────────▼─────────────┐
│    evaluation_reports    │
├──────────────────────────┤
│ id: VARCHAR(36) PK [UUID]│
│ session_id: VARCHAR(36)FK│
│ user_id: VARCHAR(36) FK  │
│ status: VARCHAR(50)      │ -- 'pending', 'processing', 'completed', 'failed'
│ overall_score: FLOAT     │
│ relevance_score: FLOAT   │
│ correctness_score: FLOAT │
│ key_concepts_score: FLOAT│
│ clarity_grammar_score:FLT│
│ delivery_score: FLOAT    │ -- Renamed from confidence_score
│ strengths: JSONB         │
│ weaknesses: JSONB        │
│ recommendations: JSONB   │
│ detailed_turn_eval: JSONB│
│ error_message: TEXT      │
│ created_at: TIMESTAMPTZ  │
└──────────────────────────┘
```

### 4.2 Entity Definitions & Column Specifications

#### 1. `users` Table
- `id` (VARCHAR(36), PK): UUIDv4 primary key.
- `email` (VARCHAR(255), UNIQUE, NOT NULL, INDEX): Normalized lowercase email address.
- `hashed_password` (VARCHAR(255), NULLABLE): Salted bcrypt password hash (nullable for pure OAuth2 users).
- `full_name` (VARCHAR(150), NOT NULL): Candidate's full display name.
- `auth_provider` (VARCHAR(50), NOT NULL, DEFAULT 'local'): `'local'` or `'google'`.
- `target_role` (VARCHAR(100), NULLABLE): Candidate's primary target job title.
- `experience_level` (VARCHAR(50), NULLABLE): `'junior'`, `'mid'`, `'senior'`.
- `failed_login_attempts` (INTEGER, NOT NULL, DEFAULT 0): Consecutive failed password attempts counter.
- `lockout_until` (TIMESTAMPTZ, NULLABLE): Temporary lockout expiration timestamp.
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): UTC creation timestamp.
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): UTC update timestamp.

#### 2. `refresh_tokens` Table
- `id` (VARCHAR(36), PK): UUIDv4 identifier.
- `user_id` (VARCHAR(36), FK -> `users.id` ON DELETE CASCADE, INDEX): Candidate account owner.
- `token_hash` (VARCHAR(255), NOT NULL, UNIQUE, INDEX): SHA-256 hash of the refresh token.
- `expires_at` (TIMESTAMPTZ, NOT NULL): Refresh token expiration timestamp (7 days).
- `revoked` (BOOLEAN, NOT NULL, DEFAULT FALSE): Invalidation status flag.
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Generation timestamp.

#### 3. `password_reset_tokens` Table
- `id` (VARCHAR(36), PK): UUIDv4 token identifier.
- `user_id` (VARCHAR(36), FK -> `users.id` ON DELETE CASCADE, INDEX): Associated candidate.
- `token_hash` (VARCHAR(255), NOT NULL, INDEX): SHA-256 hash of the one-time reset token.
- `expires_at` (TIMESTAMPTZ, NOT NULL): Expiration time (15-minute window).
- `used` (BOOLEAN, NOT NULL, DEFAULT FALSE): Single-use consumption flag.
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Generation timestamp.

#### 4. `resumes` Table
- `id` (VARCHAR(36), PK): UUIDv4 resume identifier.
- `user_id` (VARCHAR(36), FK -> `users.id` ON DELETE CASCADE, INDEX): Associated candidate.
- `file_name` (VARCHAR(255), NOT NULL): Original uploaded filename (sanitized).
- `file_path` (VARCHAR(500), NOT NULL): Local restricted filesystem path (`storage/resumes/<uuid>.<ext>`).
- `file_size_bytes` (INTEGER, NOT NULL): Uploaded file size (max 5 MB).
- `mime_type` (VARCHAR(100), NOT NULL): Verified MIME type (`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).
- `raw_text` (TEXT, NOT NULL): Extracted sanitized plain text.
- `parsed_data` (JSONB, NOT NULL): Structured JSON containing:
  - `skills`: Array of strings (e.g., `["React", "PostgreSQL", "FastAPI"]`)
  - `experience_years`: Estimated numeric years of experience
  - `domains`: Array of domain strengths (e.g., `["Backend", "Distributed Systems"]`)
  - `education`: Summary array of educational degrees
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Upload timestamp.
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Timestamp of parsed schema updates.

#### 5. `interview_sessions` Table
- `id` (VARCHAR(36), PK): UUIDv4 session identifier.
- `user_id` (VARCHAR(36), FK -> `users.id` ON DELETE CASCADE, INDEX): Candidate conducting interview.
- `resume_id` (VARCHAR(36), FK -> `resumes.id` ON DELETE SET NULL, NULLABLE): Resume context used.
- `target_role` (VARCHAR(100), NOT NULL): Configured job title (e.g., "Full Stack Developer").
- `seniority_level` (VARCHAR(50), NOT NULL): `"Junior"`, `"Mid"`, `"Senior"`.
- `interview_focus` (VARCHAR(50), NOT NULL): `"Technical Core"`, `"System Design"`, `"Behavioral"`.
- `custom_job_desc` (TEXT, NULLABLE): Optional job description text pasted by candidate.
- `total_questions` (INTEGER, NOT NULL, DEFAULT 6): Planned core question count.
- `current_turn_index` (INTEGER, NOT NULL, DEFAULT 0): Active question index.
- `status` (VARCHAR(50), NOT NULL, DEFAULT 'in_progress', INDEX): `'in_progress'`, `'evaluating'`, `'completed'`, `'abandoned'`.
- `started_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Session start timestamp.
- `completed_at` (TIMESTAMPTZ, NULLABLE): Session completion timestamp.

#### 6. `interview_question_turns` Table
- `id` (VARCHAR(36), PK): UUIDv4 question turn identifier.
- `session_id` (VARCHAR(36), FK -> `interview_sessions.id` ON DELETE CASCADE, INDEX): Parent session.
- `turn_index` (INTEGER, NOT NULL): Zero-based sequential turn order (0, 1, 2...).
- `question_text` (TEXT, NOT NULL): The AI-generated question prompt.
- `question_type` (VARCHAR(50), NOT NULL): `"core"` or `"follow_up"`.
- `candidate_answer` (TEXT, NULLABLE): Candidate's submitted text answer.
- `is_follow_up` (BOOLEAN, NOT NULL, DEFAULT FALSE): Indicates if this was a dynamic follow-up probe.
- `parent_turn_id` (VARCHAR(36), FK -> `interview_question_turns.id`, NULLABLE): References parent question if follow-up.
- `ideal_answer` (TEXT, NULLABLE): Benchmark ideal answer synthesized by evaluation service.
- `turn_duration_sec` (INTEGER, NULLABLE): Time taken by candidate to answer in seconds.
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Turn generation timestamp.

#### 7. `evaluation_reports` Table
- `id` (VARCHAR(36), PK): UUIDv4 report identifier.
- `session_id` (VARCHAR(36), FK -> `interview_sessions.id` ON DELETE CASCADE, UNIQUE, INDEX): 1-to-1 session mapping.
- `user_id` (VARCHAR(36), FK -> `users.id` ON DELETE CASCADE, INDEX): Candidate identifier for fast history queries.
- `status` (VARCHAR(50), NOT NULL, DEFAULT 'pending', INDEX): `'pending'`, `'processing'`, `'completed'`, `'failed'`.
- `overall_score` (FLOAT, NULLABLE): Composite score (0.0 to 100.0).
- `relevance_score` (FLOAT, NULLABLE): Dimensional score (0.0 to 100.0).
- `correctness_score` (FLOAT, NULLABLE): Dimensional score (0.0 to 100.0).
- `key_concepts_score` (FLOAT, NULLABLE): Dimensional score (0.0 to 100.0).
- `clarity_grammar_score` (FLOAT, NULLABLE): Dimensional score (0.0 to 100.0).
- `delivery_score` (FLOAT, NULLABLE): Dimensional score (0.0 to 100.0) reflecting communication & delivery indicators.
- `strengths` (JSONB, NULLABLE): Array of strings highlighting candidate strengths.
- `weaknesses` (JSONB, NULLABLE): Array of strings highlighting areas for improvement.
- `recommendations` (JSONB, NULLABLE): Array of actionable study recommendations and resources.
- `detailed_turn_eval` (JSONB, NULLABLE): Array of turn evaluations with criteria breakdown.
- `error_message` (TEXT, NULLABLE): Internal error description if status is `'failed'`.
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Report creation timestamp.
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()): Report completion/update timestamp.

---

## 5. Authentication Architecture

### 5.1 Security-First Browser Token Strategy
AROVIA avoids storing sensitive, long-lived authentication credentials in browser `localStorage` (which is vulnerable to XSS exfiltration). Instead, the system implements a dual-token architecture:

1. **Short-Lived Access Token (In-Memory):**
   - Stored strictly in React memory (via `AuthContext` state).
   - Lifetime: **15 minutes**.
   - Passed via HTTP header: `Authorization: Bearer <access_token>`.
   - Never written to `localStorage`, `sessionStorage`, or unencrypted client storage.
   - Cleared automatically on page refresh or browser close.

2. **Long-Lived Refresh Token (HttpOnly Cookie):**
   - Issued upon successful login or registration.
   - Lifetime: **7 days**.
   - Stored in an `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict` for cross-site isolation) cookie named `refresh_token`.
   - Inaccessible to JavaScript, completely mitigating XSS token theft.
   - SHA-256 hash of the active refresh token is stored in the `refresh_tokens` database table to enable instantaneous server-side session revocation.

3. **Silent Token Refresh Flow:**
   - On initial React application load or when an API request returns `401 Unauthorized`, the frontend calls `POST /api/v1/auth/refresh`.
   - The browser automatically attaches the `HttpOnly` refresh cookie.
   - The backend validates the refresh cookie against the database, checks expiration, rotates the refresh token, and returns a new 15-minute access token in the JSON response body.

4. **CSRF Protection:**
   - For all state-changing endpoints relying on cookies, `SameSite=Lax` / `Strict` is enforced.
   - The frontend sets a custom header `X-Requested-With: XMLHttpRequest` on all Axios requests, which standard cross-origin simple requests cannot forge without triggering CORS preflight checks.

```
Candidate Login ──► Backend returns: [Access Token in JSON] + [HttpOnly Refresh Cookie]
                          │                                           │
                          ▼                                           ▼
                 Stored in React Memory                     Stored in Secure Cookie
                 (Used for Bearer Auth)                     (Used for /auth/refresh)
```

### 5.2 Password Policy
- **Length Bounds:** Minimum **12 characters**, maximum **128 characters** (to support memorable multi-word passphrases).
- **Usability-Focused Rule:** Encourages long passphrases (e.g., `correct horse battery staple`) rather than arbitrary special-character mandates that reduce candidate usability without adding entropy.
- **Common Password Rejection:** Passwords matching top known breached/common lists (e.g., `password123456`, `qwerty123456`) are rejected server-side during registration and reset.
- **Hashing Standard:** Salted `bcrypt` hashing with cost factor / salt rounds = `12`.
- **Timing Attack Defense:** All password comparisons use constant-time verification functions (`passlib.context.CryptContext.verify()`).

### 5.3 Layered Login Brute-Force Protection
To defend against automated credential stuffing without enabling denial-of-service against legitimate users, AROVIA implements layered rate limiting:

1. **IP-Level Rate Limiting:** Enforced via `slowapi` on `/api/v1/auth/login` allowing maximum **10 requests per minute per IP address**.
2. **Account-Level Failure Tracking:** Tracks `failed_login_attempts` in the `users` table per email address.
3. **Progressive Backoff Delay:** After 3 consecutive failed attempts on an email address, the API artificially adds a progressive 2-second sleep delay before returning failure.
4. **Temporary Account Lockout (Non-Permanent):** If 5 consecutive failed attempts occur on an account within a 15-minute window, the account is temporarily locked for **15 minutes** (`lockout_until = now() + interval '15 minutes'`).
   - *Anti-DoS Design:* Accounts are **never permanently locked** via login failures, preventing attackers from locking out arbitrary candidates.
5. **Account Enumeration Defense:** All authentication failures (unknown email, invalid password, locked account) return a uniform HTTP 401 response:
   ```json
   {
     "detail": "Invalid email or password",
     "error_code": "INVALID_CREDENTIALS"
   }
   ```

### 5.4 Google Sign-In & Account Linking Architecture
1. **Google ID Token Verification:**
   - The frontend utilizes Google Identity Services to obtain a signed JWT `id_token`.
   - The frontend sends the `id_token` to `POST /api/v1/auth/google`.
   - The backend validates the token using `google-auth` / PyJWT verifying:
     - Cryptographic signature against Google's live public keys (`https://www.googleapis.com/oauth2/v3/certs`).
     - Issuer (`iss`) equals `accounts.google.com` or `https://accounts.google.com`.
     - Audience (`aud`) matches the server's configured `GOOGLE_CLIENT_ID`.
     - Token is within expiration bounds (`exp`).

2. **Account Creation vs Existing Account Collision:**
   - **New Candidate:** If no account exists with the verified Google email, a new `users` record is created with `auth_provider='google'`, `hashed_password=NULL`, and `email_verified=True`.
   - **Existing Local Account (Anti-Silent Merge):** If a local account (`auth_provider='local'`) already exists with the same email address, the backend **does not silently merge** the accounts without verification. The system prompts the candidate: *"An account with this email already exists. Please log in with your password to link Google Sign-In."*
   - **Adding a Password to OAuth Account:** Candidates who register via Google may optionally set a local password later via their authenticated profile settings (`POST /api/v1/auth/set-password`) or password reset flow.
   - **Duplicate Identity Prevention:** The `email` column in PostgreSQL has a unique constraint, preventing duplicate account records for the same verified email.

### 5.5 Password Reset Security
- **Reset Flow:** Candidate requests reset at `POST /api/v1/auth/password-reset/request`.
- **Token Generation:** Backend generates a high-entropy cryptographically secure random token (32 bytes via `secrets.token_urlsafe()`).
- **Token Storage:** Only the SHA-256 hash of the token is saved in `password_reset_tokens` with a strict **15-minute expiration window**.
- **Execution:** Token is transmitted via simulated console logging or SMTP email link.
- **Consumption:** Candidate submits new password + token to `POST /api/v1/auth/password-reset/confirm`. The token is marked `used = True` immediately upon successful reset.
- **Generic Response:** Password reset request always returns `"If an account with that email exists, a reset link has been dispatched"` to prevent email probing.

---

## 6. AI Integration Architecture

### 6.1 Provider and Model Version Flexibility
- **AI Provider:** Google Gemini API (`google-genai` Python SDK).
- **Configurable Model IDs:** Model versions are never hardcoded in application logic. They are loaded strictly from environment configuration:
  - `GEMINI_MODEL_FAST`: Configurable inference model for real-time question generation and turn evaluation (e.g., `gemini-2.0-flash`).
  - `GEMINI_MODEL_DEEP`: Configurable model for comprehensive report synthesis and deep reasoning (e.g., `gemini-1.5-pro` or latest equivalent).
- **Model Availability Verification:** The engineering team verifies currently supported and active model IDs in the Google AI Studio console prior to deployment.
- **Structured Schema Mode:** Native `response_schema` parameter passing Pydantic models directly to Gemini to guarantee valid JSON formatting without post-hoc regex parsing failures.

### 6.2 Architectural Isolation of AI Services
To prevent vendor lock-in and decouple application routes from raw LLM prompts, all Gemini interactions are encapsulated in `app/services/ai_service.py`:
- `generate_resume_structure(raw_text: str) -> ParsedResumeSchema`
- `generate_interview_question(context: InterviewTurnContext) -> QuestionResponseSchema`
- `evaluate_answer_turn(context: TurnEvalContext) -> TurnEvaluationSchema`
- `generate_final_evaluation(session_summary: SessionSummaryContext) -> FullReportSchema`

```
┌─────────────────────────────────────────────────────────────┐
│                 API Router (interviews.py)                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ High-level method call
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Domain Service (interview_service.py)          │
│  - Builds session context, manages turns, persists state   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Typed context DTO
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 AI Service (ai_service.py)                  │
│  - Formats Jinja/F-string prompt templates                  │
│  - Enforces Pydantic response_schema                        │
│  - Executes google-genai client call with retries          │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / TLS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Google Gemini API                       │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Prompt Injection Defense & Evaluation Reliability
1. **System Instruction Isolation:** Fixed system instructions define the persona (`"You are an expert technical interviewer and evaluator for AROVIA..."`) in the immutable system prompt block.
2. **Context Delimitation:** Candidate responses and resume inputs are placed inside strict XML delimiter blocks (`<candidate_response>...</candidate_response>`) to prevent prompt injection attacks attempting to alter scoring criteria.
3. **Structured Output & Score Range Enforcement:**
   - All AI output schemas inherit from Pydantic `BaseModel` with `@field_validator` asserting that all returned scores are strictly between `0.0` and `100.0`.
   - The composite `overall_score` is computed and enforced mathematically by the Python backend service, rather than trusting raw LLM math.
4. **Malformed Output Rejection & Retry:** If Gemini returns malformed output or fails schema constraints, the AI service executes one automatic retry with increased temperature damping. If the retry fails, the error is caught safely without leaking prompt templates or API keys.

---

## 7. Resume Processing Architecture

### 7.1 File Ingestion and Storage Security
1. **Client Upload:** Multipart form POST (`multipart/form-data`) containing candidate file (PDF or DOCX).
2. **Pre-Processing Validation:**
   - Enforce `Content-Length <= 5 * 1024 * 1024` (5 MB max).
   - Validate file extension against allowed whitelist (`.pdf`, `.docx`).
   - Read initial 2048 bytes to verify magic numbers (`%PDF-` for PDF, `PK\x03\x04` for DOCX).
3. **Restricted Local Filesystem Storage:**
   - Uploaded files are saved to an isolated local directory outside the web server's public document root: `storage/resumes/<uuid>.<ext>`.
   - File permissions are set to restrictive OS permissions (`0600` — read/write strictly by the backend application process user).
   - Path traversal characters (`../`, `\`, `/`) are stripped from original filenames.
4. **Text Extraction:**
   - PDF: Executed in threadpool via `asyncio.to_thread` using `pdfplumber` to extract layout-aware text without blocking the ASGI event loop.
   - DOCX: Executed via `python-docx` iterating through document paragraphs and tables.
5. **Sanitization:** Strip null bytes, non-printable control characters, and excess whitespace from extracted raw text.
6. **Structured Parsing:** Pass sanitized text to `ai_service.generate_resume_structure()` using Gemini structured schema to extract skills, experience years, domain strengths, and education.
7. **Persistence:** Store `raw_text` and `parsed_data` (JSONB) in the `resumes` table.

### 7.2 Resume Privacy and Data Retention Policy
- **Candidate Ownership:** The candidate retains full ownership of their uploaded resume and parsed career data.
- **Explicit Deletion Endpoint:** Candidates can delete their resume at any time via `DELETE /api/v1/resumes/{id}`.
- **Deletion Cascade:**
  1. The physical file is permanently removed from `storage/resumes/<uuid>.<ext>`.
  2. The `resumes` record, raw text, and parsed JSONB metadata are deleted from PostgreSQL.
  3. Associated `interview_sessions.resume_id` foreign keys are set to `NULL` (preserving interview history without retaining the deleted resume).
- **Log Privacy Guarantee:** Application loggers are strictly forbidden from logging raw resume text, candidate contact details, or PII.

---

## 8. Interview Engine Architecture

### 8.1 State Machine Pacing
The interview engine operates as a deterministic state machine per session:

```
                  ┌──────────────────────┐
                  │     INITIALIZING     │
                  └──────────┬───────────┘
                             │ Candidate starts session
                             ▼
                  ┌──────────────────────┐
           ┌─────►│   QUESTION_ACTIVE    │◄────────┐
           │      └──────────┬───────────┘         │
           │                 │ Candidate submits   │
           │                 ▼ answer              │
           │      ┌──────────────────────┐         │
           │      │  EVALUATING_ANSWER   │         │
           │      └──────────┬───────────┘         │
           │                 │                     │
           │   Is follow-up  │   Is complete       │
           │   needed?       │   answer?           │
           │      ┌──────────┴──────────┐          │
           │      ▼                     ▼          │
           │ ┌──────────┐         ┌───────────┐    │
           │ │FOLLOW_UP │         │ NEXT_CORE │────┘
           │ │  ACTIVE  │         │ QUESTION  │
           │ └────┬─────┘         └───────────┘
           │      │
           └──────┘ (Candidate answers follow-up)
                  │
                  │ All core turns completed
                  ▼
         ┌───────────────────┐
         │    EVALUATING     │ ──► Background evaluation task launched
         └────────┬──────────┘
                  │
                  ▼
         ┌───────────────────┐
         │     COMPLETED     │ ──► Report ready for viewing
         └───────────────────┘
```

### 8.2 Question Generation Calibration
Each generated question is calibrated dynamically against:
1. **Target Role:** (e.g., Backend Developer vs DevOps Engineer).
2. **Seniority Level:**
   - *Junior:* Focuses on core syntax, language fundamentals, basic data structures, and standard libraries.
   - *Mid:* Focuses on system architecture, database optimization, error handling, and API design.
   - *Senior:* Focuses on distributed scalability, trade-off analysis, failure modes, security, and concurrency.
3. **Resume Context:** Questions cross-reference skills and projects claimed in the candidate's parsed resume.
4. **Job Description (Optional):** Emphasizes specific requirements and frameworks provided in the custom JD.

### 8.3 Dynamic Follow-Up Probing Logic
When a candidate submits an answer to a core question:
1. The backend runs an in-flight depth check:
   - If the candidate's answer is overly brief, mentions a key term without explanation, or exhibits ambiguity, the engine flags `needs_follow_up = True`.
   - Maximum 1 follow-up question per core question to maintain session timing and pacing.
2. The engine generates a targeted follow-up question (e.g., *"You mentioned using Redis for caching; how did you handle cache invalidation during updates?"*).
3. If the answer was thorough, the engine immediately transitions to the next core question.

### 8.4 Audio & Speech Interaction
- **Speech Synthesis (TTS):** The frontend uses `window.speechSynthesis` with pre-configured natural English voice selections. Questions are synthesized locally in the browser with play/pause/replay controls.
- **Speech Recognition (STT):** The frontend uses `window.webkitSpeechRecognition` / `SpeechRecognition` to transcribe microphone audio in real time into the answer textarea.
- **Manual Edit Fallback:** Candidates can freely edit, format, or type their answer text before submitting, guaranteeing that speech recognition inaccuracies do not penalize candidate scores.

---

## 9. Evaluation Engine Architecture

### 9.1 Multi-Dimensional Scoring Dimensions
Every interview is evaluated across five distinct dimensions on a normalized `0 to 100` scale:

| Dimension | Weight | Definition & Evaluation Criteria |
|---|:---:|---|
| **1. Relevance** | 20% | How directly and effectively the candidate's response answers the specific prompt asked, staying on topic without irrelevant tangents. |
| **2. Technical Correctness** | 30% | The technical accuracy, truthfulness, and depth of the concepts, algorithms, tools, and principles explained. |
| **3. Key Concepts & Keywords** | 20% | Coverage of essential industry-standard terminology, core mechanisms, and architectural concepts expected for the target role. |
| **4. Clarity & Grammar** | 15% | The structural flow, articulateness, clarity of explanation, and grammatical coherence of the candidate's communication. |
| **5. Communication & Delivery Indicators** | 15% | Observable delivery indicators including answer completeness, decisive phrasing, lack of excessive hesitation markers (filler words), and structural flow. *(Disclaimer: This is an observable interview-performance signal, NOT a psychological diagnosis or definitive measure of emotional/mental confidence.)* |

### 9.2 Score Aggregation Formula
The composite `overall_score` is computed deterministically by the backend service as the weighted sum of the five dimension scores:

$$\text{Overall Score} = (0.20 \times \text{Relevance}) + (0.30 \times \text{Correctness}) + (0.20 \times \text{KeyConcepts}) + (0.15 \times \text{Clarity}) + (0.15 \times \text{Delivery})$$

### 9.3 Benchmark Ideal Answer Synthesis
For every question asked during the interview:
1. The evaluation service synthesizes a structured **Benchmark Ideal Answer** demonstrating how a senior engineer in the target role would answer the question.
2. The report highlights:
   - **Key Concepts Covered:** Terms and ideas successfully explained by the candidate.
   - **Key Concepts Missed:** Essential technical points the candidate omitted.
   - **Turn-Level Feedback:** Specific, actionable tips on how to elevate the answer.

---

## 10. Reports and History Architecture

### 10.1 Asynchronous Report Generation Architecture
To maintain maximum reliability and avoid timeout issues during LLM evaluation—without adding complex message broker infrastructure (e.g., Celery, RabbitMQ, Redis)—AROVIA uses FastAPI's built-in asynchronous task execution:

1. **Trigger:** When the candidate completes the final turn, the client calls `POST /api/v1/interviews/{id}/complete`.
2. **Immediate Response:**
   - The backend updates `interview_sessions.status = 'evaluating'`.
   - Creates an `evaluation_reports` record with `status = 'pending'`.
   - Dispatches a background coroutine via `BackgroundTasks(evaluation_service.generate_full_report, session_id)`.
   - Returns immediate HTTP 200 with `{ "session_id": id, "status": "evaluating" }`.
3. **Background Processing:**
   - Background task sets report status to `'processing'`.
   - Aggregates all question turns, sends evaluation prompt to Gemini, validates Pydantic schema output, computes mathematical scores, and updates `evaluation_reports.status = 'completed'`.
   - If an error occurs, sets status to `'failed'` and logs the internal error safely.
4. **Client Polling:**
   - Frontend polls `GET /api/v1/reports/{session_id}/status` every 2.5 seconds.
   - Shows an animated progress indicator with tips.
   - When status transitions to `'completed'`, automatically navigates to `/reports/{session_id}`.

### 10.2 Client-Side PDF Report Generation
To maintain speed and avoid heavy headless browser dependencies (like Puppeteer or Chromium) on the backend:
- The frontend renders a dedicated, print-optimized report template.
- `html2canvas` captures the high-resolution vector layout including Chart.js charts.
- `jsPDF` compiles the captured elements into a multi-page downloadable PDF document (`AROVIA_Interview_Report_<session_id>.pdf`).

### 10.3 Historical Progression Analytics
The candidate dashboard (`/dashboard`) aggregates historical session reports:
- **Score Progression Chart:** Line chart tracking `overall_score` over consecutive interview dates.
- **Skill Mastery Trends:** Category-level performance trends (e.g., System Design vs Technical Core).
- **Historical Session Archive:** Searchable and filterable list of all completed mock interviews with instant access to past detailed reports.

---

## 11. API Design and Communication

### 11.1 API Standards & Protocols
- **Protocol:** HTTP/1.1 and HTTP/2 over TLS (HTTPS).
- **URI Prefix:** All API endpoints are versioned under `/api/v1/`.
- **Payload Format:** JSON (`application/json`) for all requests and responses; `multipart/form-data` for file uploads.
- **Authentication:** HTTP Authorization header using `Bearer <access_token>` paired with `HttpOnly` refresh cookies.

### 11.2 Core Endpoint Specification

| Method | Endpoint | Description | Auth Required | Rate Limit |
|---|---|---|:---:|:---:|
| `POST` | `/api/v1/auth/register` | Register new candidate account | No | 3/min |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain tokens | No | 10/min |
| `POST` | `/api/v1/auth/google` | Authenticate via Google ID Token | No | 10/min |
| `POST` | `/api/v1/auth/refresh` | Exchange refresh cookie for access token | Cookie | 30/min |
| `POST` | `/api/v1/auth/logout` | Revoke refresh token and clear cookie | Yes | 30/min |
| `GET` | `/api/v1/auth/me` | Fetch authenticated candidate profile | Yes | 60/min |
| `PUT` | `/api/v1/auth/me` | Update candidate target role & bio | Yes | 30/min |
| `POST` | `/api/v1/auth/password-reset/request` | Request password reset token | No | 3/min |
| `POST` | `/api/v1/auth/password-reset/confirm` | Reset password using one-time token | No | 3/min |
| `POST` | `/api/v1/resumes/upload` | Upload and parse candidate resume | Yes | 5/min |
| `GET` | `/api/v1/resumes/latest` | Fetch candidate's active parsed resume | Yes | 60/min |
| `DELETE` | `/api/v1/resumes/{id}` | Delete resume file and parsed data | Yes | 10/min |
| `POST` | `/api/v1/interviews` | Initialize new interview session | Yes | 10/min |
| `GET` | `/api/v1/interviews/{id}/current-turn` | Fetch active question for session | Yes | 60/min |
| `POST` | `/api/v1/interviews/{id}/submit-turn` | Submit answer and get next turn | Yes | 30/min |
| `POST` | `/api/v1/interviews/{id}/complete` | Finish interview & trigger background eval | Yes | 5/min |
| `GET` | `/api/v1/reports/{session_id}` | Fetch detailed evaluation report card | Yes | 60/min |
| `GET` | `/api/v1/reports/{session_id}/status` | Poll report generation status | Yes | 60/min |
| `GET` | `/api/v1/reports/history` | Fetch candidate interview history list | Yes | 60/min |
| `GET` | `/api/v1/health` | Live system and database health check | No | None |

---

## 12. Validation and Sanitization

### 12.1 Server-Side Pydantic v2 Enforcement
Every incoming JSON payload is parsed and validated against strict Pydantic v2 models:
- **Strict Data Types:** Strings, integers, booleans, and floats are strictly typed; extra unexpected fields are stripped or rejected.
- **String Sanitization:** All text inputs (user names, job descriptions, answers) are stripped of leading/trailing whitespace and validated for length bounds.
- **Email Normalization:** Validated via Pydantic `EmailStr` and stored in lowercase.

### 12.2 Injection & XSS Prevention
- **SQL Injection:** 100% prevented through parameterized queries generated by SQLAlchemy 2.0 ORM; raw string SQL concatenation is strictly forbidden.
- **Cross-Site Scripting (XSS):** React automatically escapes text rendered in JSX; server-side sanitization strips HTML tags (`<script>`, `<iframe>`, `<img>`) from raw text fields before persistence.

---

## 13. File Upload Security

### 13.1 Defense-in-Depth File Validation Pipeline
Resume file uploads adhere to strict multi-layer defensive validation:
1. **File Size Capping:** Immediate rejection of uploads exceeding 5 MB (`5,242,880 bytes`).
2. **Extension Whitelisting:** Only `.pdf` and `.docx` extensions allowed.
3. **Magic Byte Verification:** Inspect first 2048 bytes of binary stream:
   - PDF signature: `%PDF-` (`0x25 0x50 0x44 0x46 0x2D`)
   - DOCX signature: `PK\x03\x04` (`0x50 0x4B 0x03 0x04`)
4. **Filename Normalization & UUID Storage:** Original filenames are stripped of path traversal characters (`../`, `\`, `/`). Stored files are written to disk using UUID filenames (e.g., `storage/resumes/9fe0980e-3b21-4f8a-a9e1.pdf`).
5. **Restricted Storage Location & Permissions:** Stored outside web server document roots in `storage/resumes/` with OS-level `0600` permissions (readable/writable strictly by the application service account).

---

## 14. Authorization and Data Ownership

### 14.1 Tenant Isolation by User ID
AROVIA enforces strict candidate-level data isolation:
- **Zero-Trust Client Identifiers:** Client requests cannot specify or override the `user_id` query parameter for accessing resources.
- **JWT Context Binding:** The authenticated `user_id` is extracted strictly from the validated JWT claims.
- **Query Ownership Verification:** Every database query for resumes, interview sessions, question turns, and evaluation reports includes an explicit ownership clause:
  ```python
  stmt = select(InterviewSession).where(
      InterviewSession.id == session_id,
      InterviewSession.user_id == current_user.id
  )
  ```
- **Insecure Direct Object Reference (IDOR) Defense:** If a user attempts to access a `session_id` or `report_id` belonging to another candidate, the API returns `404 Not Found` (rather than 403 Forbidden) to prevent resource ID enumeration.

---

## 15. Error Handling and Logging

### 15.1 Unified JSON Error Envelope
All error responses conform to a predictable, uniform JSON structure:
```json
{
  "detail": "Descriptive error message",
  "error_code": "RESOURCE_NOT_FOUND",
  "errors": []
}
```

### 15.2 Exception Hierarchy (`app/core/exceptions.py`)
- `AppError` (Base application exception, 400 Bad Request)
  - `NotFoundError` (404 Not Found)
  - `UnauthorizedError` (401 Unauthorized)
  - `ForbiddenError` (403 Forbidden)
  - `ConflictError` (409 Conflict)
  - `ValidationError` (422 Unprocessable Entity)

### 15.3 Global Exception Handlers & Information Leakage Masking
- **`global_exception_handler`:** Intercepts unhandled Python exceptions (`500 Internal Server Error`). It logs the full traceback internally with context, but masks the client response to return:
  ```json
  {
    "detail": "Internal server error",
    "error_code": "INTERNAL_ERROR"
  }
  ```
- No database queries, table names, file system paths, or Python stack traces are ever exposed to the client.

### 15.4 Structured Application Logging
- Configured in `app/core/logging.py` using Python's standard `logging` library.
- Log format: `%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s`.
- Secrets, passwords, API keys, JWT tokens, and resume body contents are strictly redacted from log outputs.

---

## 16. Security Requirements

### 16.1 OWASP Top 10 Mitigation Matrix

| Vulnerability | Threat Description | AROVIA Mitigation Strategy |
|---|---|---|
| **A01: Broken Access Control** | Unauthorized access to other candidates' interview transcripts or reports | Strict user isolation in SQLAlchemy queries; user ID derived exclusively from verified JWT token. |
| **A02: Cryptographic Failures** | Credential theft, plaintext passwords, weak secrets | Salted bcrypt hashing (12 rounds); mandatory 32-char SECRET_KEY; HTTPS encryption in transit; HttpOnly token cookies. |
| **A03: Injection** | SQL injection via inputs; LLM prompt injection | SQLAlchemy parameterized queries; strict XML context delimiters in LLM prompts; Pydantic type validation. |
| **A04: Insecure Design** | Unbounded AI token consumption; brute-force attacks | SlowAPI rate limiting; layered lockout backoff; maximum turns per interview (6-8); fail-fast configuration. |
| **A05: Security Misconfiguration** | Stack trace leakage; permissive CORS; default credentials | Global exception handler masking 500 tracebacks; strict CORS origin whitelist; zero fallback default passwords. |
| **A06: Vulnerable Components** | Vulnerabilities in Python or JS packages | Pinned library dependencies in `requirements.txt`; regular automated vulnerability auditing. |
| **A07: Identification & Auth Failures** | Brute-force credential stuffing; session hijacking | Multi-layer rate limiting; temporary 15-min lockout; in-memory access tokens; 7-day HttpOnly refresh cookies. |
| **A08: Software & Data Integrity** | Malicious file upload execution; MIME tampering | Magic byte binary validation; file size limits (5 MB); non-executable local file storage with UUID naming. |
| **A09: Security Logging Failures** | Undetected intrusion attempts or authorization bypasses | Structured logging of authentication failures and anomalous requests with internal logging. |
| **A10: SSRF** | Server-side request forgery through external web requests | Backend does not fetch arbitrary candidate-supplied URLs; all external calls are strictly routed to Gemini API. |

---

## 17. Testing Strategy

### 17.1 Testing Pyramid
- **Unit Tests:** Validate individual functions, Pydantic schemas, password hashing, and model mixins.
- **Integration Tests:** Validate FastAPI endpoints, database session rollbacks, exception handlers, and business logic.
- **Mock AI Tests:** Mock Google Gemini API responses using deterministic fixture JSON to enable instant, zero-cost CI test runs without active API keys.

### 17.2 In-Memory Testing Architecture
- Tests run against in-memory SQLite using `aiosqlite` (`sqlite+aiosqlite:///:memory:`).
- Tables are created dynamically via `Base.metadata.create_all` and torn down after each test suite execution.
- `httpx.AsyncClient` with `ASGITransport(raise_app_exceptions=False)` executes asynchronous HTTP requests against the FastAPI app.
- Execution speed: Entire backend test suite executes in < 1 second.

---

## 18. Environment and Secret Management

### 18.1 Configuration Variables
All configuration is loaded via `pydantic-settings` from `.env`:

```env
# Application Settings
PROJECT_NAME="AROVIA API"
VERSION="1.0.0"
ENVIRONMENT="development"
API_V1_PREFIX="/api/v1"

# Security & Secrets
SECRET_KEY="change-this-to-a-secure-random-32-character-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Configuration
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/arovia"

# Google Gemini AI Configuration
GEMINI_API_KEY="your-gemini-api-key-here"
GEMINI_MODEL_FAST="gemini-2.0-flash"
GEMINI_MODEL_DEEP="gemini-1.5-pro"

# Google OAuth2 Configuration (Phase 2)
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"

# CORS Configuration
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

### 18.2 Fail-Fast Principle
If any required variable (`SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`) is missing or invalid, the backend halts immediately upon process launch with an explicit `ValidationError` describing the missing variable, preventing insecure operation.

---

## 19. Development and Deployment Architecture

### 19.1 Local Development Workflow
- **Backend:** `uvicorn app.main:app --reload --port 8000`
- **Frontend:** `npm run dev` (Vite dev server running on `http://localhost:5173`)
- **Database:** Local PostgreSQL instance or Docker container (`docker run -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16`)

### 19.2 Production Deployment Architecture
- **Backend Service:** Deployed on containerized platforms (e.g., Render, Railway, AWS ECS) running Uvicorn ASGI workers behind an Nginx reverse proxy.
- **Frontend Static Hosting:** Built via `npm run build` and served from a global CDN (e.g., Vercel, Netlify, Cloudflare Pages).
- **Managed Database:** Cloud-managed PostgreSQL instance (e.g., Supabase, Neon, AWS RDS) with automated backups and SSL connection enforcement (`sslmode=require`).

---

## 20. Performance and Scalability Considerations

### 20.1 Performance Optimization Targets
| Metric | Target | Strategy |
|---|---|---|
| **API Health Ping** | < 20 ms | Lightweight async database connection verification (`SELECT 1`) |
| **Question Generation** | < 1.5 s | Low-latency configurable fast Gemini model with structured JSON schema |
| **Speech STT / TTS** | < 100 ms | Browser Web Speech API local execution; zero server audio streaming latency |
| **Resume Text Extraction** | < 500 ms | Background threadpool execution via `asyncio.to_thread` with `pdfplumber` |
| **Report Generation** | < 3.0 s | Background task evaluation with Pydantic structured output validation |
| **Database Queries** | < 15 ms | Indexed foreign keys, indexed email lookups, and JSONB document storage |

### 20.2 Database Connection Pooling
- Production async pool: `pool_size = 10`, `max_overflow = 20`, `pool_pre_ping = True`.
- `pool_pre_ping` validates connection vitality before query execution, preventing stale connection dropouts.

---

## 21. 45-Day MVP Scope Control & Simplicity Rules

To guarantee successful delivery within the 45-day development window as a high-standard major project and portfolio centerpiece, AROVIA adheres to strict architectural discipline:

1. **Modular Monolith Over Microservices:** All backend services live within the structured `backend/app/` repository sharing one database and async event loop.
2. **In-Process Tasks Over Distributed Queues:** Report evaluation runs via FastAPI `BackgroundTasks` without introducing Redis, Celery, or Kafka clusters.
3. **Browser Audio Over Server Codecs:** Speech synthesis and recognition leverage the native Web Speech API with text editing fallbacks, avoiding heavy server-side Whisper or FFmpeg pipelines.
4. **Client-Side Export Over Headless Browsers:** PDF summary reports are compiled via `jsPDF`/`html2canvas` directly in the candidate's browser, eliminating headless Chromium server dependencies.
5. **Direct Relational Persistence Over Cache Layers:** PostgreSQL with indexed columns and JSONB documents handles all data storage with sub-15ms latency, avoiding redundant Redis caching complexity.

---

## 22. Architecture Decision Records & Roadmap Alignment

### 22.1 Documented Decisions & Revisions
1. **Dual-Token Authentication Strategy:** Replaced localStorage token storage with 15-minute in-memory access tokens and 7-day `HttpOnly` `Secure` `SameSite=Lax` refresh cookies.
2. **Password Policy Modernization:** Adopted 12-character minimum passphrase policy with common password rejection and bcrypt (cost 12), dropping arbitrary special-character rules.
3. **Layered Brute-Force Defense:** Implemented IP rate limiting, account-level tracking, progressive backoff delays, and 15-minute temporary lockouts.
4. **Verified Google OAuth & Anti-Silent Linking:** Defined strict Google ID token verification and explicit confirmation requirements before linking existing local accounts.
5. **Reframed Delivery Scoring:** Renamed Dimension 5 to "Communication & Delivery Indicators", emphasizing observable verbal signals (filler words, completeness, flow) while explicitly disclaiming psychological diagnoses.
6. **Configurable AI Models:** Decoupled Gemini model IDs to environment variables (`GEMINI_MODEL_FAST`, `GEMINI_MODEL_DEEP`) with Pydantic structured score validation.
7. **Filesystem Security & Retention:** Documented restricted OS-level `0600` filesystem storage for resumes and full candidate deletion cascades without logging PII.
8. **In-Process Async Report Generation:** Specified polling-based report generation via FastAPI `BackgroundTasks`.
9. **Document Status:** Updated to `Architecture Baseline — Revised for Review`.

### 22.2 9-Phase Roadmap Traceability
- **Phase 1 (Completed):** Core Foundation & Database Architecture (FastAPI, Async DB, Alembic, Base Models, Test Harness).
- **Phase 2:** Authentication & Profile Management (Registration, bcrypt, In-memory JWT + HttpOnly Refresh Cookie, Google OAuth, Profile API).
- **Phase 3:** Resume Ingestion & Analysis Engine (PDF/DOCX validation, text extraction, Gemini skill parsing, deletion cascade).
- **Phase 4:** Interview Setup & Role Configuration (Role catalog, seniority calibration, JD context).
- **Phase 5:** Interactive Adaptive Interview Engine & Voice Flow (Question generation, follow-up state machine, speech hooks).
- **Phase 6:** Multi-Dimensional Evaluation & Scoring Engine (5-dimension scoring, keyword analysis, benchmark ideal answers, background task runner).
- **Phase 7:** Performance Report Card, Analytics & PDF Export (Visual charts, study recommendations, client PDF generation).
- **Phase 8:** Candidate Dashboard, History & Progress Tracking (Session archive, score progression line charts).
- **Phase 9:** Security Hardening, Rate Limiting & Final Verification (SlowAPI, OWASP audit, end-to-end integration tests).

---

*AROVIA Technical Requirements Document — Architecture Baseline Revised for Review.*
