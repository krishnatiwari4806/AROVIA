# Phase 1: Core Foundation & Database Architecture - Context

**Gathered:** 2026-08-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Initialize the production-ready FastAPI backend foundation, PostgreSQL asynchronous database connection with SQLAlchemy 2.0 async engine, Alembic migration pipeline, strict configuration management with Pydantic v2 Settings, standardized health checks, defensive error handlers, and automated test fixtures. This phase establishes the foundation upon which all subsequent vertical MVP slices will build.

</domain>

<decisions>
## Implementation Decisions

### Database Connection & Test Isolation
- **D-01:** Use PostgreSQL with `asyncpg` (`postgresql+asyncpg://...`) for development and production async database operations.
- **D-02:** Use SQLite in-memory with `aiosqlite` (`sqlite+aiosqlite:///:memory:`) for fast, isolated unit and integration testing in `pytest` with automatic per-test transaction rollback.
- **D-03:** Configure connection pooling with sensible defaults (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`) for async engine resilience.

### Configuration & Secret Management
- **D-04:** Use `pydantic-settings` (`BaseSettings`) loading configuration securely from `.env` with strict type validation.
- **D-05:** Implement fail-fast validation on startup if required secrets (`SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`) are missing.
- **D-06:** Provide a safe `.env.example` template with non-sensitive placeholder variables and clear configuration instructions.

### API Response & Error Formatting
- **D-07:** Success responses return typed Pydantic DTOs directly without redundant wrapping envelopes, enabling clean OpenAPI schema generation.
- **D-08:** Global exception middleware catches uncaught exceptions and returns a sanitized JSON error format `{"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}` without leaking server tracebacks.
- **D-09:** Provide an explicit `/api/v1/health` endpoint that checks live database connectivity and returns `{"status": "healthy", "database": "connected", "version": "1.0.0"}`.

### Project Layout & Dependencies
- **D-10:** Structure backend inside `backend/` directory with `requirements.txt` (core) and `requirements-dev.txt` (pytest, ruff).
- **D-11:** Structure backend code under `backend/app/` with modular packages: `api/v1/`, `core/`, `db/`, `models/`, `schemas/`, and `services/`.
- **D-12:** Configure Alembic with async SQLAlchemy template in `backend/alembic/` and `backend/alembic.ini`.

### the agent's Discretion
- Exact logger configuration (`logging` / `loguru`) and log formatting.
- Specific pytest fixture naming and helper factory functions in `tests/conftest.py`.
- Base SQLAlchemy model mixin design (`id`, `created_at`, `updated_at` timestamps).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Stack Standards
- `.planning/PROJECT.md` — Project specification, constraints, and security standards.
- `.planning/REQUIREMENTS.md` §1 & §8 — Core requirements (SECR-01, SECR-04, SECR-05).
- `.planning/research/STACK.md` — Prescribed libraries, versions, and compatibility table.
- `.planning/research/ARCHITECTURE.md` — Standard directory structure and component boundaries.
- `.planning/research/PITFALLS.md` — Pitfall 1 (LLM/Schema validation) & Pitfall 5 (Authorization/Defensive headers).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None (Greenfield phase — establishing the base project assets).

### Established Patterns
- Modular FastAPI application factory pattern with router mounting.
- Declarative Base class for SQLAlchemy ORM models with `mapped_column` type annotations.
- Async session dependency injection (`get_db`) yielding sessions per request.

### Integration Points
- `backend/app/main.py`: Entrypoint for FastAPI ASGI application, CORS middleware, exception handlers, and API router.
- `backend/app/db/session.py`: Async engine and sessionmaker instance used by all database endpoints.
- `backend/app/core/config.py`: Central settings instance imported across all services.

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed strictly within Phase 1 foundation scope.

</deferred>

---

*Phase: 01-core-foundation-database-architecture*
*Context gathered: 2026-08-15*
