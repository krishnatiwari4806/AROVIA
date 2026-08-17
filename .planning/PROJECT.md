# AROVIA — AI-Powered Interview Evaluation System

## What This Is

AROVIA is a secure, modular web application that conducts structured, adaptive AI-assisted interviews and evaluates candidates across multiple dimensions (relevance, correctness, key concepts, clarity/grammar, sentiment, and confidence indicators). Designed as a candidate self-practice and assessment platform, it simulates realistic technical and behavioral interviews with speech interaction, dynamic follow-up probing, and generates in-depth analytical performance reports with actionable improvement suggestions.

## Core Value

Delivering realistic, adaptive AI mock interviews with rigorous, multi-dimensional evaluation and actionable feedback, built on a robust, highly secure, and clean full-stack architecture.

## Requirements

### Validated

- **Phase 1: Core Foundation & Database Architecture** (FastAPI, async PostgreSQL/SQLite SQLAlchemy engine, Alembic migrations, health check).
- **Phase 2: Authentication & Profile Management** (Bcrypt password hashing, JWT access/refresh tokens, Google OAuth verification, profile CRUD, password reset).
- **Phase 3: Resume Ingestion & Analysis Engine** (Magic byte verification, 5MB limit, `pdfplumber`/`python-docx` extraction, Gemini structured skill parsing, atomic replacement CRUD).

### Active

- [ ] **Job Role & Target Profile Configuration**: Configurable target job titles, required skillsets, seniority levels, and custom job description inputs to calibrate question generation.
- [ ] **Adaptive Interview Question Engine**: Dynamic question generation powered by Google Gemini API; starts with core domain questions and intelligently probes deeper with follow-up questions based on candidate responses.
- [ ] **Interactive Audio & Visual Interview Room**: Professional browser-based interview experience with Text-to-Speech (AI voice synthesis via Web Speech API / browser speech synthesis), microphone capture, real-time Speech-to-Text with manual text edit fallback, and timer controls.
- [ ] **Multi-Dimensional Evaluation Engine**: Server-side structured scoring evaluating answers across relevance, technical correctness, keyword/concept mastery, clarity/grammar, sentiment, and confidence metrics.
- [ ] **Comprehensive Report & Analytics Dashboard**: Detailed post-interview report with aggregate/category scores, visual radar/bar charts, identified strengths, weaknesses, question-by-question breakdowns with ideal answers, and exportable PDF summary.
- [ ] **Session History & Progress Tracking**: Persistent dashboard tracking candidate interview history, score progression over time, and skill mastery trends.
- [ ] **Robust Security & Defensive Architecture**: Server-side validation (Pydantic), OWASP Top 10 mitigation, rate limiting, secure CORS/CSRF headers, safe file handling, environment secret isolation, and defensive error handling without leaking stack traces.

### Out of Scope

- **Paid payment gateway/subscription billing / paid cloud APIs** — Total development and runtime cost must remain ₹0.
- **Real-time video/facial emotion computer vision processing** — Deferred to future milestones to prioritize core audio-verbal and NLP semantic accuracy.
- **Multi-tenant corporate HR ATS integration** — Focused on candidate self-assessment and mock interview practice for the initial release.

## Context

- **Academic & Portfolio Milestone**: High-standard college major project demonstrating professional full-stack development, modern AI orchestration, and production-grade security practices.
- **Timeline**: Approximately 45 days of disciplined, phased development with small, verifiable tasks.
- **Design Philosophy**: Clean, function-driven, responsive UI with clear typography, intuitive flows, and micro-interactions. Zero tolerance for insecure client-side validation assumptions.

## Constraints

- **HARD CONSTRAINT — ₹0 TOTAL COST**: Total development and runtime cost MUST remain exactly **₹0**.
  - **Zero Paid Services**: No paid APIs, paid tiers, subscriptions, credit card requirements, or auto-charging services.
  - **Priority Order**: Free / Open Source $\rightarrow$ Local / Browser Native $\rightarrow$ Free-Tier API $\rightarrow$ Paid Service (STRICTLY FORBIDDEN).
  - **AI / LLM**: Google Gemini API free-tier only (`google-genai` SDK with free API key, strictly within free rate limits). Never require billing accounts.
  - **Audio & Speech**: Browser-native Web Speech API (`webkitSpeechRecognition` & `speechSynthesis`) for zero-cost STT/TTS. Zero cloud audio/Whisper API costs.
  - **Document & Data Processing**: Local CPU processing via open-source libraries (`pdfplumber`, `python-docx`, local disk storage `storage/resumes/`).
  - **Email & Auth**: Local terminal/log verification links for dev/testing. Zero paid email/SMS services.
  - **Client-Side Visuals**: Chart.js / Lucide React / jsPDF for client-side rendering and PDF generation. Zero cloud PDF generation costs.
- **Backend Stack**: Python (FastAPI) — Chosen for native async support, performance, Pydantic type safety, and seamless Python AI/NLP ecosystem integration.
- **Frontend Stack**: React + Vite + Vanilla CSS / modern responsive styling — Chosen for speed, flexibility, component modularity, and high-performance browser audio APIs.
- **Database**: PostgreSQL / SQLite with SQLAlchemy ORM & Alembic migrations — Relational integrity, schema migrations, and structured session persistence.
- **Security Standard**: Server-side defensive validation on all endpoints, zero trust for client data, strict input/file sanitization, secure secret storage via `.env`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| ₹0 Zero-Cost Architecture | College major project requirement; relies exclusively on open-source, browser-native, and genuine free tiers | Locked |
| FastAPI Backend + React/Vite Frontend | Clean separation of concerns; high performance async API with robust AI integration in Python | Validated |
| PostgreSQL / SQLite + SQLAlchemy + Alembic | Robust relational schema, transactional integrity for sessions/evaluations, production readiness | Validated |
| Google Gemini API (Free Tier) for AI & Parsing | Fast latency, rich structured JSON schemas (`response_schema`), generous free tier | Validated |
| Web Speech API with fallback editing | Zero-cost, low-latency audio-enabled experience without heavy server-side media processing or paid STT/TTS | Locked |
| Local Document Parsing (`pdfplumber` + `python-docx`) | Local CPU extraction with zero cloud parsing cost | Validated |

---
*Last updated: 2026-08-18*
