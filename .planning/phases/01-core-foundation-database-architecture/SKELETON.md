# Walking Skeleton — AROVIA

**Phase:** 1
**Generated:** 2026-08-15

## Capability Proven End-to-End

An authenticated client or developer can query the FastAPI backend health status (`/api/v1/health`), verifying that the async database connection is alive and executing real SQL transactions against PostgreSQL (or in-memory SQLite in test mode) with structured Pydantic response models and global exception masking.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | FastAPI (0.115+) on Uvicorn ASGI | Asynchronous, typed with Pydantic v2, automatic OpenAPI documentation, ideal for AI/NLP pipelines |
| Data Layer | PostgreSQL 16+ via SQLAlchemy 2.0 Async (`asyncpg`) | Modern async SQL ORM syntax, robust pooling, JSONB capabilities for evaluation metrics |
| Test Isolation | SQLite (`aiosqlite`) in-memory fixtures | Instant test execution with transaction rollback without needing running local PostgreSQL |
| Configuration | Pydantic v2 Settings (`pydantic-settings`) | Fail-fast validation of required secrets (`SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`) from `.env` |
| Migrations | Alembic (Async runner configuration) | Version-controlled DDL migrations |
| Directory Layout | Modular package layout under `backend/app/` (`api/v1/`, `core/`, `db/`, `models/`, `schemas/`, `services/`) | Clean separation of concerns matching enterprise standards |

## Stack Touched in Phase 1

- [ ] Project scaffold (FastAPI app factory, `requirements.txt`, `pytest.ini`, `.env.example`)
- [ ] Routing — `/api/v1/health` endpoint returning live status
- [ ] Database — Async connection pool, session lifecycle dependency (`get_db`), ping query (`SELECT 1`)
- [ ] Error Handling — Global exception middleware masking internal stack traces
- [ ] Test Harness — Pytest with async client fixtures and database isolation

## Out of Scope (Deferred to Later Slices)

- User authentication & JWT issuance (Phase 2)
- Resume upload & parsing engine (Phase 3)
- Interview session generation & Gemini AI integration (Phase 4 & 5)
- Multi-dimensional evaluation engine (Phase 6)
- Frontend UI interface & React application (Phases 5, 7, 8)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: User Authentication & Profile Management (JWT + bcrypt + User ORM)
- Phase 3: Resume Ingestion & Analysis Engine (PDF parsing + Gemini structured extraction)
- Phase 4: Interview Setup & Role Configuration (Role catalog + session initialization)
- Phase 5: Interactive Adaptive Interview Engine & Voice Flow (Gemini prompt chaining + Speech API)
- Phase 6: Multi-Dimensional Evaluation & Scoring Engine (5-dimension evaluation metrics)
- Phase 7: Performance Report Card, Analytics & PDF Export (Analytics DTOs + UI charts)
- Phase 8: Candidate Dashboard, History & Progress Tracking (Session archive + trends)
- Phase 9: Security Hardening, Rate Limiting & Verification (SlowAPI + security headers)
