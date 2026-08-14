# AROVIA — AI-Powered Interview Evaluation System

## What This Is

AROVIA is a secure, modular web application that conducts structured, adaptive AI-assisted interviews and evaluates candidates across multiple dimensions (relevance, correctness, key concepts, clarity/grammar, sentiment, and confidence indicators). Designed as a candidate self-practice and assessment platform, it simulates realistic technical and behavioral interviews with speech interaction, dynamic follow-up probing, and generates in-depth analytical performance reports with actionable improvement suggestions.

## Core Value

Delivering realistic, adaptive AI mock interviews with rigorous, multi-dimensional evaluation and actionable feedback, built on a robust, highly secure, and clean full-stack architecture.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **Authentication & User Profile Management**: Secure registration, login, JWT session management, bcrypt password hashing, input sanitization, and role/profile management.
- [ ] **Resume Ingestion & Analysis Engine**: Secure file upload (PDF/DOCX) with type/size validation and sanitization, text extraction (`pypdf`/`pdfplumber`), and Gemini structured schema parsing for skills, experience, and domain strengths/gaps.
- [ ] **Job Role & Target Profile Configuration**: Configurable target job titles, required skillsets, seniority levels, and custom job description inputs to calibrate question generation.
- [ ] **Adaptive Interview Question Engine**: Dynamic question generation powered by Google Gemini API; starts with core domain questions and intelligently probes deeper with follow-up questions based on candidate responses.
- [ ] **Interactive Audio & Visual Interview Room**: Professional browser-based interview experience with Text-to-Speech (AI voice synthesis via Web Speech API / browser speech synthesis), microphone capture, real-time Speech-to-Text with manual text edit fallback, and timer controls.
- [ ] **Multi-Dimensional Evaluation Engine**: Server-side structured scoring evaluating answers across relevance, technical correctness, keyword/concept mastery, clarity/grammar, sentiment, and confidence metrics.
- [ ] **Comprehensive Report & Analytics Dashboard**: Detailed post-interview report with aggregate/category scores, visual radar/bar charts, identified strengths, weaknesses, question-by-question breakdowns with ideal answers, and exportable PDF summary.
- [ ] **Session History & Progress Tracking**: Persistent dashboard tracking candidate interview history, score progression over time, and skill mastery trends.
- [ ] **Robust Security & Defensive Architecture**: Server-side validation (Pydantic), OWASP Top 10 mitigation, rate limiting, secure CORS/CSRF headers, safe file handling, environment secret isolation, and defensive error handling without leaking stack traces.

### Out of Scope

- **Real-time video/facial emotion computer vision processing** — Deferred to future milestones to prioritize core audio-verbal and NLP semantic accuracy.
- **Multi-tenant corporate HR ATS integration** — Focused on candidate self-assessment and mock interview practice for the initial release.
- **Paid payment gateway/subscription billing** — Out of scope for college major project / portfolio MVP.

## Context

- **Academic & Portfolio Milestone**: High-standard college major project demonstrating professional full-stack development, modern AI orchestration, and production-grade security practices.
- **Timeline**: Approximately 45 days of disciplined, phased development with small, verifiable tasks.
- **Design Philosophy**: Clean, function-driven, responsive UI with clear typography, intuitive flows, and micro-interactions. Zero tolerance for insecure client-side validation assumptions.

## Constraints

- **Backend Stack**: Python (FastAPI) — Chosen for native async support, performance, Pydantic type safety, and seamless Python AI/NLP ecosystem integration.
- **Frontend Stack**: React + Vite + Vanilla CSS / modern responsive styling — Chosen for speed, flexibility, component modularity, and high-performance browser audio APIs.
- **Database**: PostgreSQL with SQLAlchemy ORM & Alembic migrations — Chosen for relational integrity, schema migrations, and structured session/metric persistence.
- **AI & NLP Services**: Google Gemini API (structured JSON output, prompt chaining, fast inference) + Web Speech API for low-latency browser speech synthesis & recognition.
- **Timeline**: 45 days total development window structured into incremental, testable phases.
- **Security Standard**: Server-side defensive validation on all endpoints, zero trust for client data, strict input/file sanitization, secure secret storage via `.env`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI Backend + React/Vite Frontend | Clean separation of concerns; high performance async API with robust AI integration in Python | — Pending |
| PostgreSQL + SQLAlchemy + Alembic | Robust relational schema, transactional integrity for sessions/evaluations, production readiness | — Pending |
| Google Gemini API for Generation & Scoring | Fast latency, rich structured JSON schemas, multimodal capabilities, cost-effective | — Pending |
| Web Speech API with fallback editing | Low-latency audio-enabled experience without heavy server-side media processing bottlenecks | — Pending |
| Hybrid Resume Parser (pdfplumber + Gemini Schema) | Accurate text extraction paired with semantic LLM entity extraction for skills & experience | — Pending |
| Phase-by-Phase Task Execution | Ensures each milestone is small, testable, and verified before progressing | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-15 after initialization*
