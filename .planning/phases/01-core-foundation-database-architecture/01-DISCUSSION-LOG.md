# Phase 1: Core Foundation & Database Architecture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-15
**Phase:** 01-core-foundation-database-architecture
**Areas discussed:** Database Connection & Test Isolation, Configuration & Secret Management, Error Response Envelope & Health Check Format, Project Directory Layout & Dependency Management

---

## Database Connection & Test Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL (asyncpg) + SQLite (aiosqlite) | asyncpg for application runtime; in-memory aiosqlite for fast test isolation with transaction rollback | ✓ |
| Pure PostgreSQL for both app and tests | Requires dedicated running PostgreSQL container/instance during test execution | |

**User's choice:** PostgreSQL (asyncpg) for app + SQLite (aiosqlite in-memory) for lightning-fast unit tests with automatic transaction rollback.
**Notes:** Provides fast CI execution while maintaining full async PostgreSQL compatibility in development/production.

---

## Configuration & Secret Management

| Option | Description | Selected |
|--------|-------------|----------|
| Strict Pydantic-Settings | Fails fast at startup if SECRET_KEY, DATABASE_URL, or GEMINI_API_KEY is missing from .env | ✓ |
| Flexible Settings | Fallback defaults for missing secrets in non-production environments | |

**User's choice:** Strict Pydantic-Settings — App fails fast at startup if SECRET_KEY, DATABASE_URL, or GEMINI_API_KEY is missing from .env.
**Notes:** Ensures zero accidental deployments with unconfigured secrets or hardcoded defaults.

---

## Error Response Envelope & Health Check Format

| Option | Description | Selected |
|--------|-------------|----------|
| Clean standard JSON | Success responses return typed Pydantic models directly; errors return {"detail": message, "error_code": code} | ✓ |
| Uniform Envelope | Every response wrapped in {"success": bool, "data": ..., "error": ...} | |

**User's choice:** Clean standard JSON: success responses return typed Pydantic models directly; errors return {"detail": message, "error_code": code} without stack traces.
**Notes:** Clean OpenAPI documentation without double-wrapping, paired with live database health check at `/api/v1/health`.

---

## Project Directory Layout & Dependency Management

| Option | Description | Selected |
|--------|-------------|----------|
| Standard requirements.txt | Standard requirements.txt + requirements-dev.txt under backend/ with clear scripts and .env.example | ✓ |
| pyproject.toml package | Poetry / Flit / Hatch packaging | |

**User's choice:** Standard requirements.txt + requirements-dev.txt under backend/ with clear scripts and .env.example.
**Notes:** Simple, clean, transparent, and universally compatible across student and production environments.

---

## the agent's Discretion

- Exact logging library configuration and formatter.
- Base SQLAlchemy model mixin design and timestamp handling.
- Specific pytest fixture naming and helper factory methods in `tests/conftest.py`.

## Deferred Ideas

- None — all discussion remained focused on Phase 1 core architecture.

---

*Phase: 01-core-foundation-database-architecture*
*Discussion log generated: 2026-08-15*
