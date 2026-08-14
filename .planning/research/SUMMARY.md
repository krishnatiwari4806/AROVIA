# Project Research Summary

**Project:** AROVIA — AI-Powered Interview Evaluation System
**Domain:** AI-Powered EdTech & Career Assessment Web Application
**Researched:** 2026-08-15
**Confidence:** HIGH

## Executive Summary

AROVIA is an AI-powered interview evaluation platform designed to conduct adaptive, structured mock interviews and deliver multi-dimensional candidate evaluation. Building a production-grade interview evaluation system requires harmonizing three core pillars: (1) robust and defensive backend architecture with secure authentication, role-based authorization, and resilient file handling, (2) reliable AI orchestration using structured schemas and prompt chaining via the Google Gemini API, and (3) a responsive, accessible browser interface featuring real-time audio interaction (Speech-to-Text & Text-to-Speech) with manual edit fallbacks and visual performance analytics.

The recommended architectural approach utilizes a **FastAPI** backend with asynchronous **SQLAlchemy 2.0** and **PostgreSQL** for relational persistence and flexible JSONB metric storage, paired with a **React + Vite** frontend. AI integration leverages the **Google Gemini API** (`gemini-2.0-flash` / `gemini-1.5-pro`) utilizing native structured schema output (`response_schema`) to guarantee deterministic evaluation data. Audio interaction is powered by the browser's **Web Speech API** for low-latency voice synthesis and transcription.

Key architectural risks include unvalidated LLM output formats, speech recognition connection drops, insecure PDF processing, and Insecure Direct Object Reference (IDOR) vulnerabilities. These risks are mitigated through Pydantic response models, defensive file verification (magic bytes + size limits), JWT-derived user identity verification, and multi-dimensional scoring pipelines.

## Key Findings

### Recommended Stack

- **Backend:** Python 3.11+, FastAPI (~0.115.0+), Pydantic v2, Pydantic-Settings, Uvicorn (ASGI).
- **Database & ORM:** PostgreSQL 16+, SQLAlchemy 2.0 (Async engine with `asyncpg`), Alembic migrations.
- **AI & NLP:** Google Gemini API (`google-genai` SDK), `pdfplumber` / `pypdf` for resume extraction.
- **Security & Utilities:** `passlib[bcrypt]`, `python-jose[cryptography]`, `slowapi` rate limiting.
- **Frontend:** React 18+/19, Vite, React Router DOM, Recharts / Chart.js, Lucide React icons, jsPDF.
- **Testing:** `pytest`, `pytest-asyncio`, `httpx.AsyncClient`.

### Expected Features

**Must Have (Table Stakes):**
- User registration, login, JWT authentication, and secure profile management.
- Secure resume upload (PDF/DOCX) with automated skill and experience extraction.
- Job role and target seniority configuration.
- Sequential, question-by-question interview progression.
- Audio speech synthesis (AI voice) and speech-to-text with editable text fallback.
- Multi-dimensional scoring (Relevance, Correctness, Keywords/Concepts, Clarity/Grammar, Sentiment/Confidence).
- Post-interview comprehensive report with visual charts and actionable suggestions.
- Session history dashboard to track performance trends over time.

**Should Have (Differentiators):**
- Adaptive follow-up probing based on candidate answers.
- Question-by-question review with ideal benchmark answers and key missed concepts.
- Visual radar charts and competency matrices.
- Downloadable PDF report card.
- Defensive security hardening (rate limiting, OWASP compliance, zero client trust).

**Defer (v2+):**
- Computer vision / webcam facial emotion tracking (unreliable and privacy-invasive).
- Multi-tenant recruiter portal and ATS batch integrations.
- Payment gateway / subscription billing.

### Architecture Approach

The application is structured into decoupled frontend and backend layers. The backend exposes a versioned REST API (`/api/v1`) with isolated service modules:
1. **Auth & Security Module:** Manages credentials, tokens, rate limits, and security headers.
2. **Resume Ingestion Engine:** Validates file magic bytes and extracts structured entities.
3. **Interview Orchestrator:** Manages session state machine, prompt generation, and adaptive follow-up logic.
4. **Evaluation Engine:** Computes dimensional metrics and qualitative review cards via Gemini structured JSON.
5. **Persistence Layer:** PostgreSQL with async SQLAlchemy and Alembic schema management.

### Critical Pitfalls

1. **Flaky LLM Responses:** Enforce strict Pydantic `response_schema` mode on all Gemini calls.
2. **Speech Recognition Interruptions:** Implement real-time transcript caching and an inline editable textarea.
3. **Insecure PDF Uploads:** Validate file magic bytes (`%PDF-`), limit size (5MB), and rename with secure UUIDs.
4. **Authorization Bypasses (IDOR):** Derive user identity strictly from verified JWT tokens on every endpoint.
5. **Token Bloat & Latency:** Use compact structured resume profiles and Q&A windows rather than raw full-text dumps.

## Implications for Roadmap

Based on the fine-grained, sequential execution preference and domain dependencies, the project is organized into logical, verifiable phases:

### Phase 1: Project Foundation, Database Schema & Core Security Infrastructure
- Setup FastAPI ASGI server, async SQLAlchemy engine, PostgreSQL connection, Alembic migrations, and Pydantic configuration.
- Setup base error handlers, CORS, and logging.

### Phase 2: User Authentication & Profile Management API
- Implement password hashing (bcrypt), JWT token issuance/verification, registration/login endpoints, and current user auth dependencies.

### Phase 3: Defensive File Handling & Resume Analysis Engine
- Implement secure file upload validation (magic bytes, MIME, size caps), `pdfplumber` text extraction, and Gemini structured skill parsing.

### Phase 4: Interview Configuration & Adaptive Question Generation Engine
- Implement interview session state models, target role configuration, and Gemini-powered adaptive question generation with follow-up probing.

### Phase 5: Multi-Dimensional Evaluation & Scoring Engine
- Implement answer scoring pipeline across 5 dimensions (Relevance, Correctness, Keywords, Clarity, Sentiment), strengths/weaknesses generation, and ideal answer synthesis.

### Phase 6: Session Management, History & Report APIs
- Implement endpoints for completing interviews, fetching session history, aggregating performance metrics, and generating comprehensive report DTOs.

### Phase 7: Frontend Design System, Auth & Navigation Shell
- Initialize Vite + React frontend, CSS design tokens, responsive layout (Navbar, Sidebar), Auth Context, and Login/Register pages.

### Phase 8: Resume Upload & Interview Setup UI
- Build drag-and-drop resume uploader with parsing status visualizer, role selector, and interview preview screen.

### Phase 9: Interactive Live Interview Room & Audio Integration
- Build live interview room with AI voice playback (TTS), microphone recording (STT), editable transcript area, timer countdown, and adaptive question transitions.

### Phase 10: Performance Report, Analytics Dashboard & PDF Export
- Build post-interview report view with interactive radar/bar charts, question-by-question deep dives, actionable recommendations, and PDF export.

### Phase 11: Candidate Dashboard, History & Trend Analytics
- Build candidate hub displaying past interview sessions, aggregate progress graphs, and profile settings.

### Phase 12: End-to-End Security Hardening, Rate Limiting & Production Readiness
- Implement SlowAPI rate limiting on sensitive routes, OWASP security header validation, comprehensive test suite verification, and deployment documentation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | FastAPI + PostgreSQL + React + Gemini is a proven, high-performance architecture for modern AI web apps |
| Features | HIGH | Comprehensive scope matching academic and industry portfolio standards |
| Architecture | HIGH | Clean service layer separation, async DB operations, and strict Pydantic schema contracts |
| Pitfalls | HIGH | Specific domain pitfalls mapped directly to mitigation phases |

**Overall confidence:** HIGH

---
*Research completed: 2026-08-15*
*Ready for roadmap: yes*
