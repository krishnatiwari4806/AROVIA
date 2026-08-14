# Phase 1: Core Foundation & Database Architecture - Research

**Researched:** 2026-08-15
**Domain:** FastAPI Async Architecture, SQLAlchemy 2.0 Async ORM, Alembic Migrations, and Pydantic v2 Settings
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use PostgreSQL with `asyncpg` (`postgresql+asyncpg://...`) for development and production async database operations.
- **D-02:** Use SQLite in-memory with `aiosqlite` (`sqlite+aiosqlite:///:memory:`) for fast, isolated unit and integration testing in `pytest` with automatic per-test transaction rollback.
- **D-03:** Configure connection pooling with sensible defaults (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`) for async engine resilience.
- **D-04:** Use `pydantic-settings` (`BaseSettings`) loading configuration securely from `.env` with strict type validation.
- **D-05:** Implement fail-fast validation on startup if required secrets (`SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`) are missing.
- **D-06:** Provide a safe `.env.example` template with non-sensitive placeholder variables and clear configuration instructions.
- **D-07:** Success responses return typed Pydantic DTOs directly without redundant wrapping envelopes, enabling clean OpenAPI schema generation.
- **D-08:** Global exception middleware catches uncaught exceptions and returns a sanitized JSON error format `{"detail": "...", "error_code": "..."}` without leaking server tracebacks.
- **D-09:** Provide an explicit `/api/v1/health` endpoint that checks live database connectivity and returns `{"status": "healthy", "database": "connected", "version": "1.0.0"}`.
- **D-10:** Structure backend inside `backend/` directory with `requirements.txt` (core) and `requirements-dev.txt` (pytest, ruff).
- **D-11:** Structure backend code under `backend/app/` with modular packages: `api/v1/`, `core/`, `db/`, `models/`, `schemas/`, and `services/`.
- **D-12:** Configure Alembic with async SQLAlchemy template in `backend/alembic/` and `backend/alembic.ini`.

### the agent's Discretion
- Exact logger configuration (`logging`) and log formatting.
- Specific pytest fixture naming and helper factory functions in `tests/conftest.py`.
- Base SQLAlchemy model mixin design (`id`, `created_at`, `updated_at` timestamps).

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed strictly within Phase 1 foundation scope.
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| App Config & Secret Loading | Backend Core (`core/config.py`) | Environment (`.env`) | Single source of truth for runtime variables with strict validation |
| Async Database Connection | Database Tier (`db/session.py`) | PostgreSQL (`asyncpg`) | High performance async connection pooling with session lifecycles |
| Schema Evolution & Migrations | Migration Engine (`alembic/`) | PostgreSQL DDL | Version-controlled deterministic database schema changes |
| API Routing & Health Probing | API Gateway (`api/v1/`) | Database (`db/session.py`) | HTTP routing, request parsing, and database health verification |
| Test Harness & Isolation | Test Tier (`tests/conftest.py`) | In-Memory SQLite (`aiosqlite`) | Isolated, zero-dependency fast test execution with rollback |
</architectural_responsibility_map>

<research_summary>
## Summary

Phase 1 establishes the production-grade foundation of the AROVIA backend. The standard modern Python web stack utilizes **FastAPI (0.115+)** running on **Uvicorn**, typed data modeling with **Pydantic v2**, and asynchronous database persistence powered by **SQLAlchemy 2.0** with the **asyncpg** driver for PostgreSQL.

A key architectural insight is the clean separation between synchronous schema migration tooling (**Alembic**) and runtime asynchronous database sessions (`AsyncSession`). To ensure lightning-fast CI and local unit testing without requiring an active PostgreSQL daemon, the test harness is configured with `aiosqlite` and SQLite in-memory databases with automatic nested transaction rollbacks per test case.

**Primary recommendation:** Build a modular `app/` architecture where `core/config.py` enforces strict type checking at startup, `db/session.py` manages the async engine and sessionmaker, `db/base.py` provides the declarative ORM base, and `main.py` wires CORS, exception handlers, and the versioned API router.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | >=0.115.0 | Async ASGI web framework | High throughput, native OpenAPI docs, Pydantic integration |
| `uvicorn[standard]` | >=0.30.0 | ASGI web server | High-performance event loop implementation (uvloop) |
| `pydantic` | >=2.9.0 | Data parsing and validation | Fast C-core validation, robust type enforcement |
| `pydantic-settings` | >=2.4.0 | Environment settings management | Type-safe `.env` loading and validation |
| `sqlalchemy` | >=2.0.30 | Database ORM & SQL toolkit | Industry standard 2.0 typed async syntax (`select`, `execute`) |
| `asyncpg` | >=0.29.0 | PostgreSQL async database driver | Fastest async driver for PostgreSQL in Python |
| `alembic` | >=1.13.0 | Database migration tool | Official migration tool for SQLAlchemy |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `aiosqlite` | >=0.20.0 | Async SQLite driver | Fast in-memory unit tests |
| `httpx` | >=0.27.0 | Async HTTP client | `AsyncClient` for testing FastAPI endpoints asynchronously |
| `pytest` | >=8.2.0 | Testing framework | Running unit and integration tests |
| `pytest-asyncio` | >=0.23.0 | Pytest async fixture support | Testing async endpoints and database sessions |
| `python-dotenv` | >=1.0.1 | `.env` file parsing | Supporting local environment loading |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncpg` | `psycopg3` (async) | `asyncpg` is significantly faster in benchmarks; `psycopg3` has newer type support but slightly higher latency |
| `pydantic-settings` | `dynaconf` / `decouple` | `pydantic-settings` integrates natively with FastAPI and Pydantic v2 models |
| `aiosqlite` for tests | Docker PostgreSQL container | `aiosqlite` runs tests in milliseconds without Docker daemon prerequisites |

**Installation:**
```bash
# Core dependencies (backend/requirements.txt)
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.9.0
pydantic-settings>=2.4.0
sqlalchemy>=2.0.30
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
alembic>=1.13.0
python-dotenv>=1.0.1

# Dev dependencies (backend/requirements-dev.txt)
pytest>=8.2.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
aiosqlite>=0.20.0
ruff>=0.5.0
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                 Client Request (HTTP / REST)                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI ASGI App (main.py)                  │
│  - CORS Middleware                                          │
│  - Global Exception Handler (Sanitized JSON Error Envelope) │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 API Router (/api/v1/router.py)              │
│  - /health (Database ping & system status)                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           Dependency Injection (get_db in session.py)       │
│  - AsyncSession lifecycle management (commit / rollback)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            SQLAlchemy 2.0 Async Engine (session.py)         │
│  - Connection Pool (asyncpg for App / aiosqlite for Tests)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 PostgreSQL / SQLite Database                │
└─────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py          # /api/v1/health
│   │       └── router.py              # Aggregated v1 API router
│   ├── core/
│   │   ├── config.py                  # Pydantic BaseSettings
│   │   └── logging.py                 # Structured logger setup
│   ├── db/
│   │   ├── base.py                    # Base model & CommonModelMixin
│   │   └── session.py                 # Async engine & get_db dependency
│   ├── models/                        # SQLAlchemy ORM models package
│   │   └── __init__.py
│   ├── schemas/                       # Pydantic validation & response DTOs
│   │   ├── __init__.py
│   │   └── health.py                  # HealthCheckResponse schema
│   ├── services/                      # Business logic layer
│   │   └── __init__.py
│   └── main.py                        # Application factory & exception handlers
├── alembic/
│   ├── env.py                         # Async Alembic migration runner
│   ├── script.py.mako
│   └── versions/                      # Migration revisions
├── tests/
│   ├── conftest.py                    # Pytest async client & test DB fixtures
│   ├── test_config.py                 # Settings loading tests
│   └── test_health.py                 # Health check integration tests
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── .env.example
```

### Pattern 1: Async Session Dependency Injection (`get_db`)
**What:** Generator yielding an `AsyncSession` per HTTP request, closing it safely in a `finally` block.
**When to use:** All database-backed endpoints.
**Example:**
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Pattern 2: Strict Pydantic Settings with Fail-Fast Startup
**What:** Loads environment variables and validates presence of critical secrets.
**When to use:** Initializing `core/config.py`.
**Example:**
```python
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AROVIA API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    SECRET_KEY: str = Field(..., min_length=32)
    DATABASE_URL: str = Field(...)
    GEMINI_API_KEY: str = Field(...)
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
```

### Pattern 3: Isolated SQLite In-Memory Pytest Fixture with `httpx.AsyncClient`
**What:** Overrides `get_db` in tests to connect to `sqlite+aiosqlite:///:memory:` and seeds tables dynamically.
**When to use:** Unit and API integration tests.
**Example:**
```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### Anti-Patterns to Avoid
- **Hardcoding DB credentials or fallback default secrets:** Never provide a fallback default for `SECRET_KEY` or `GEMINI_API_KEY`.
- **Mixing sync `Session` and async `AsyncSession`:** Keep all application queries async using `select(...)` and `await session.execute(...)`.
- **Returning raw internal exceptions in HTTP responses:** Global exception handlers must sanitize 500 errors into standard JSON payloads.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Environment Variable Parsing | Custom `os.getenv` parser | `pydantic-settings` | Handles type casting, validation, nested structs, and clear error messages |
| Schema Migrations | Custom SQL scripts | `alembic` | Automatic diffing, reversible migrations, transaction-safe schema upgrades |
| Async Connection Pooling | Custom connection queue | SQLAlchemy `create_async_engine` pooling | Handles reconnection, health checks (`pool_pre_ping`), overflow management |
| Global Exception Translation | Repetitive `try-except` in every route | FastAPI `@app.exception_handler` | Uniform API error responses, zero traceback leakage |

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Alembic Failing to Import Async Models
**What goes wrong:** Alembic cannot run autogenerate or execute async drivers properly.
**Why it happens:** Standard Alembic template generates synchronous engine calls (`engine_from_config`).
**How to avoid:** Configure `alembic/env.py` using `asyncio.run(run_async_migrations())` and `connectable = async_engine_from_config(...)`.
**Warning signs:** `TypeError: object AsyncEngine can't be used in 'await' expression` or blocking connection errors during `alembic upgrade head`.

### Pitfall 2: SQLite vs PostgreSQL Incompatible Column Types in Tests
**What goes wrong:** PostgreSQL-specific types (e.g. `JSONB`, `UUID`) fail when tested on SQLite.
**Why it happens:** SQLite lacks native JSONB or UUID types.
**How to avoid:** Use SQLAlchemy `JSON` (which resolves to JSONB in PostgreSQL and JSON/TEXT in SQLite) or create custom TypeDecorators if needed.
**Warning signs:** `OperationalError: near "JSONB": syntax error` in pytest runs.

### Pitfall 3: Event Loop Conflicts in `pytest-asyncio`
**What goes wrong:** `RuntimeError: Task attached to a different loop` or closed event loop errors in pytest.
**Why it happens:** Default pytest-asyncio settings creating mismatched event loops between fixtures and test functions.
**How to avoid:** Set `asyncio_mode = auto` in `pytest.ini` and use `pytest_asyncio.fixture`.
**Warning signs:** Warnings about deprecated async fixture scopes in pytest output.
</common_pitfalls>

<validation_architecture>
## Validation Architecture

### Automated Verification Plan
- **Configuration Tests (`tests/test_config.py`):**
  - Verify settings load correctly from `.env`.
  - Verify missing `SECRET_KEY` or `DATABASE_URL` raises `ValidationError`.
- **Health Check API Tests (`tests/test_health.py`):**
  - Verify `GET /api/v1/health` returns `200 OK` with `{"status": "healthy", "database": "connected", "version": "1.0.0"}`.
  - Verify database ping query (`SELECT 1`) executes cleanly within health handler.
- **Exception Handler Tests (`tests/test_health.py`):**
  - Verify intentional uncaught exception returns `500` with clean JSON `{"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}` and no traceback.
- **Alembic Migration Verification:**
  - Execute `alembic check` / `alembic upgrade head` to confirm clean migration scripts.

### Quick Run Command
```bash
pytest tests/ -v
```
</validation_architecture>

<sources>
## Sources

### Primary (HIGH confidence)
- Official FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 Asyncio Guide: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Pydantic Settings Documentation: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Alembic Async Cookbook: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic

### Secondary (MEDIUM confidence)
- Pytest Asyncio Configuration Guide: https://pytest-asyncio.readthedocs.io/
</sources>

<metadata>
## Metadata

**Research scope:** FastAPI, SQLAlchemy 2.0 Async, Pydantic v2 Settings, Alembic Async, Pytest Asyncio
**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: HIGH
- Code examples: HIGH

**Research date:** 2026-08-15
**Valid until:** 2026-09-15
</metadata>

---

*Phase: 01-core-foundation-database-architecture*
*Research completed: 2026-08-15*
*Ready for planning: yes*
