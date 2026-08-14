# Architecture Research

**Domain:** AI-Powered Interview Evaluation System (Web Application)
**Researched:** 2026-08-15
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Frontend Layer (React + Vite)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Auth & User  │  │ Resume Setup │  │  Live Room   │  │ Report Views │ │
│  │  Components  │  │  Components  │  │ (Audio/STT)  │  │ & Visuals    │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │                 │         │
├─────────┴─────────────────┴─────────────────┴─────────────────┴─────────┤
│                   API Gateway & Security Layer (FastAPI)                │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │   CORS / Rate Limiter (SlowAPI) / JWT Auth & Security Middleware   │  │
│  └─────────────────────────────────┬─────────────────────────────────┘  │
│                                    │                                    │
├────────────────────────────────────┴────────────────────────────────────┤
│                       Application Services & Engines                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Auth Service │  │ Resume Parser│  │ AI Interview │  │ Evaluation   │ │
│  │ (bcrypt/JWT) │  │  & Extractor │  │ Orchestrator │  │ Scoring Eng. │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │                 │         │
├─────────┴─────────────────┴─────────────────┴─────────────────┴─────────┤
│                         Data & External AI Layer                        │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │  PostgreSQL Database │  │ Encrypted Local  │  │ Google Gemini API │  │
│  │ (SQLAlchemy/Alembic) │  │   File Storage   │  │ (Structured JSON) │  │
│  └──────────────────────┘  └──────────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Auth Service** | User registration, password hashing, JWT creation & validation | FastAPI dependency injection, `passlib[bcrypt]`, `PyJWT` |
| **Resume Parser Service** | Secure file upload validation, text extraction, semantic schema mapping | `pdfplumber` for layout-aware text extraction + Gemini structured schema extraction |
| **Interview Orchestrator** | Managing question sequence, tracking session state, adaptive follow-ups | State machine service querying Gemini with prompt templates & session context history |
| **Evaluation Engine** | Scoring candidate answers across 5 dimensions, generating strengths/weaknesses | Gemini with strict Pydantic JSON schema (`response_schema`), rule-based NLP aggregation |
| **Storage Service** | Persisting user data, sessions, question transcripts, evaluations | Async SQLAlchemy 2.0 sessions + PostgreSQL JSONB columns for flexible scoring metrics |
| **Frontend Live Room** | Rendering question prompt, audio playback (TTS), microphone capture (STT) | React custom hooks (`useSpeechRecognition`, `useSpeechSynthesis`), timer controls |
| **Analytics & Reports UI** | Interactive radar charts, detailed scores, question breakdowns, PDF export | Recharts / Chart.js, Lucide icons, jsPDF / html2canvas |

## Recommended Project Structure

```
arovia/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py          # /api/v1/auth (login, register, me)
│   │   │   │   │   ├── resumes.py       # /api/v1/resumes (upload, parse, get)
│   │   │   │   │   ├── interviews.py    # /api/v1/interviews (create, next, submit)
│   │   │   │   │   └── reports.py       # /api/v1/reports (get, export)
│   │   │   │   └── router.py            # Aggregated v1 API router
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic BaseSettings (env configs)
│   │   │   ├── security.py              # JWT, password hashing, auth dependencies
│   │   │   └── rate_limit.py            # SlowAPI limiter instance
│   │   ├── db/
│   │   │   ├── base.py                  # SQLAlchemy declarative base
│   │   │   ├── session.py               # Async engine & sessionmaker
│   │   │   └── migrations/              # Alembic migration scripts
│   │   ├── models/                      # SQLAlchemy ORM database models
│   │   │   ├── user.py
│   │   │   ├── resume.py
│   │   │   ├── interview.py
│   │   │   └── evaluation.py
│   │   ├── schemas/                     # Pydantic validation & response DTOs
│   │   │   ├── user.py
│   │   │   ├── resume.py
│   │   │   ├── interview.py
│   │   │   └── evaluation.py
│   │   ├── services/                    # Core business logic & AI orchestration
│   │   │   ├── resume_service.py        # PDF text extraction & schema parsing
│   │   │   ├── ai_service.py            # Gemini client wrapper, prompt templates
│   │   │   ├── interview_service.py     # Adaptive session state machine
│   │   │   └── evaluation_service.py    # Multi-dimensional scoring algorithms
│   │   └── main.py                      # FastAPI application factory & middleware
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_resumes.py
│   │   ├── test_interviews.py
│   │   └── test_evaluation.py
│   ├── requirements.txt
│   ├── alembic.ini
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── assets/                      # Static icons, logos, illustrations
│   │   ├── components/                  # Reusable UI components
│   │   │   ├── common/                  # Buttons, Cards, Inputs, Modals, Loaders
│   │   │   ├── layout/                  # Navbar, Footer, Sidebar, PageContainer
│   │   │   ├── audio/                   # VoiceWaveform, MicButton, AudioPlayer
│   │   │   └── charts/                  # RadarChart, ScoreBar, ProgressionChart
│   │   ├── context/                     # AuthContext, InterviewContext
│   │   ├── hooks/                       # Custom hooks (useAuth, useSpeech, useTimer)
│   │   ├── pages/                       # Route views
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ResumeUpload.jsx
│   │   │   ├── InterviewSetup.jsx
│   │   │   ├── LiveInterview.jsx
│   │   │   └── ReportView.jsx
│   │   ├── services/                    # API client layer (Axios / Fetch)
│   │   │   ├── api.js                   # Base API instance with interceptors
│   │   │   ├── authService.js
│   │   │   ├── resumeService.js
│   │   │   └── interviewService.js
│   │   ├── styles/                      # Design system tokens & CSS files
│   │   │   ├── index.css                # CSS variables, typography, reset
│   │   │   └── components.css           # Core component classes
│   │   ├── App.jsx                      # Router & context providers
│   │   └── main.jsx                     # Entry point
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
└── .planning/                           # GSD Project Management & Roadmap
```

### Structure Rationale

- **`backend/app/services/`:** Isolates external API interaction (Gemini) and complex business logic (adaptive state machine, scoring) from HTTP routing endpoints.
- **`backend/app/schemas/` vs `models/`:** Strict separation between database persistence models (SQLAlchemy) and input/output API contracts (Pydantic).
- **`frontend/src/hooks/`:** Encapsulates browser speech APIs (`useSpeechRecognition`, `useSpeechSynthesis`) so UI components remain purely declarative.
- **`frontend/src/services/`:** Centralizes all HTTP calls and token attachment logic in one place.

## Architectural Patterns

### Pattern 1: Structured LLM Output with Pydantic Schemas

**What:** Direct Gemini response mapping into strict Pydantic models using `google-genai` structured outputs.
**When to use:** All question generation, resume entity extraction, and multi-dimensional evaluation calls.
**Trade-offs:** Guarantees valid JSON without brittle regex parsing; adds minimal prompt token overhead.

### Pattern 2: Adaptive Interview State Machine

**What:** The backend maintains an explicit session state (`INITIALIZING`, `QUESTION_ACTIVE`, `FOLLOW_UP_ACTIVE`, `COMPLETED`).
**When to use:** During live interview sessions to decide whether an answer needs elaboration or the session moves to the next core question.
**Trade-offs:** Provides predictable interview pacing while enabling natural, personalized drill-downs.

### Pattern 3: Defense-in-Depth File Upload Pipeline

**What:** Multi-stage file verification (MIME type check, magic number header verification, file size cap, secure UUID renaming, isolated temporary processing).
**When to use:** Resume upload endpoint.
**Trade-offs:** Prevents malicious file execution and path traversal attacks completely.

## Data Flow

### 1. Resume Ingestion Flow
```
User uploads file (PDF/DOCX)
    ↓
FastAPI endpoint verifies size, MIME type & magic bytes
    ↓
pdfplumber extracts raw text & layout blocks
    ↓
Gemini extracts structured skills, experience & role profile (JSON schema)
    ↓
Database persists Resume record & extracted profile metadata
```

### 2. Live Interview Turn Flow
```
Frontend requests current/next question
    ↓
FastAPI constructs prompt with Resume context + target Job Description + past Q&A
    ↓
Gemini generates Question & key evaluation criteria
    ↓
Frontend speaks question (TTS) & displays prompt
    ↓
Candidate records response (STT transcript + audio duration)
    ↓
Frontend submits answer text to Backend
    ↓
Backend evaluates answer (Relevance & depth check)
    ↓
Backend returns: [Next Question] OR [Targeted Follow-up Question]
```

### 3. Final Scoring & Report Flow
```
Session reaches terminal question
    ↓
Backend Evaluation Engine processes all Q&A pairs
    ↓
Gemini evaluates multi-dimensional metrics (0-100 per dimension) + qualitative feedback
    ↓
Backend persists Evaluation & Report record (scores, radar points, strengths, weaknesses)
    ↓
Frontend renders interactive Report Card with visual charts & PDF download
```

---
*Architecture research for: AROVIA (AI-Powered Interview Evaluation System)*
*Researched: 2026-08-15*
