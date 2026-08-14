# Stack Research

**Domain:** AI-Powered Interview Evaluation System (Web Application)
**Researched:** 2026-08-15
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.11+ | Backend runtime | Robust AI/NLP ecosystem, native async support, strong typing with Pydantic v2 |
| **FastAPI** | ~0.115.0+ | Backend Web API Framework | High-throughput asynchronous ASGI performance, automatic OpenAPI/Swagger docs, native Pydantic validation |
| **PostgreSQL** | 16+ | Primary Relational Database | ACID compliance, JSONB support for flexible evaluation metric storage, relational integrity for sessions/users |
| **SQLAlchemy** | 2.0+ (Async) | Database ORM | Modern async 2.0 syntax, robust query builder, clean data models |
| **Alembic** | 1.13+ | Database Migrations | Version-controlled schema migrations ensuring safe database evolution |
| **React** | 18+ / 19 | Frontend UI Framework | Component modularity, mature ecosystem, declarative UI state management |
| **Vite** | 5.0+ | Frontend Build Tool | Blazing fast HMR, optimized build artifacts, zero-config modern ESM |
| **Google Gemini API (`google-genai`)** | Current SDK (`gemini-2.0-flash` / `gemini-1.5-pro`) | Question generation & multi-dimensional evaluation | High speed, cost efficiency, reliable native structured JSON schema enforcement (`response_schema`) |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Pydantic** | 2.9+ | Data validation & settings | Request/response DTOs, environment config (`pydantic-settings`), LLM output parsing |
| **pdfplumber** / **pypdf** | 0.11+ / 4.0+ | Resume PDF text & layout extraction | Ingesting candidate resume files securely without running untrusted binary parsers |
| **python-docx** | 1.1+ | DOCX resume text extraction | Ingesting Microsoft Word format resumes |
| **passlib[bcrypt]** / **bcrypt** | 4.0+ | Secure password hashing | User authentication credential storage |
| **python-jose[cryptography]** / **PyJWT** | 2.9+ | JWT token generation & verification | Stateless authentication & secure session authorization |
| **slowapi** | 0.1.9+ | Rate limiting | Protecting AI endpoints and authentication routes from brute force/DoS |
| **python-multipart** | 0.0.9+ | Multipart form file uploads | Secure resume file stream processing |
| **httpx** | 0.27+ | Async HTTP client | External API calls and testing asynchronous endpoints |
| **Lucide React** | 0.400+ | Modern Iconography | UI icons (microphone, speaker, charts, checkmarks) |
| **Chart.js / React-Chartjs-2** (or **Recharts**) | Current | Visual Data Analytics | Rendering radar charts (dimensions), bar charts (category scores), and score progression |
| **jsPDF / html2canvas** | Current | PDF Report Export | Generating client-side downloadable PDF summary report |

### Development & Testing Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** & **pytest-asyncio** | Backend testing | Unit and integration test suite with async test client (`httpx.AsyncClient`) |
| **ruff** / **black** / **isort** | Python linting & formatting | Enforce clean, standardized, and PEP 8 compliant code |
| **ESLint** & **Prettier** | Frontend linting & formatting | Enforce consistent JSX and TypeScript/JavaScript styles |
| **dotenv** (`python-dotenv`) | Environment variables management | Secure separation of local secrets (`.env`) |

## Installation

### Backend

```bash
# Core framework & server
pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "pydantic>=2.9.0" "pydantic-settings>=2.4.0"

# Database & ORM
pip install "sqlalchemy>=2.0.30" "asyncpg>=0.29.0" "psycopg2-binary>=2.9.9" "alembic>=1.13.0"

# AI / LLM & Document Parsing
pip install "google-genai>=0.1.0" "pdfplumber>=0.11.0" "pypdf>=4.0.0" "python-docx>=1.1.0"

# Security, Auth & Utilities
pip install "passlib[bcrypt]>=1.7.4" "bcrypt>=4.0.1" "python-jose[cryptography]>=3.3.0" "python-multipart>=0.0.9" "slowapi>=0.1.9" "httpx>=0.27.0"

# Testing & Quality
pip install -D pytest pytest-asyncio pytest-cov ruff
```

### Frontend

```bash
# Core & Router
npm install react react-dom react-router-dom

# Icons & UI Charts
npm install lucide-react recharts

# Utilities & PDF Export
npm install jspdf html2canvas

# Dev tools
npm install -D vite @vitejs/plugin-react eslint prettier
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **FastAPI** | Django / DRF | If building a monolithic app heavily reliant on Django Admin and built-in ORM |
| **FastAPI** | Express.js / Node.js | If team is purely JavaScript/TypeScript and does not need Python's native ML/NLP libraries |
| **Google Gemini API** | OpenAI GPT-4o-mini | If enterprise specifically mandates OpenAI API keys; our architecture keeps LLM calls modular |
| **Web Speech API** | Server-side Whisper / Deepgram | If strict cross-browser consistency or offline custom acoustic models are required |
| **PostgreSQL** | MongoDB | If interview schemas are completely schema-less; PostgreSQL with JSONB provides both relational integrity and document flexibility |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Raw `eval()` or unvalidated LLM string outputs** | Prompt injection vulnerabilities and runtime JSON parsing crashes | Pydantic response models + `response_schema` structured mode in Gemini |
| **Client-side only validation** | Easy to bypass; leads to corrupted database state and security exploits | Server-side Pydantic models + database foreign key/check constraints |
| **Storing raw passwords or plaintext API keys** | Severe credential leak and security violation | `bcrypt` hash algorithms and `.env` secret variables |
| **Direct local filesystem paths stored in database** | Brittle across environments, directory traversal risk | Normalized UUID-based storage filenames with strict root path validation |
| **Heavy synchronous blocking calls in FastAPI endpoints** | Freezes the ASGI event loop and throttles all concurrent requests | `async def` handlers with async DB/HTTP drivers, running CPU-heavy parsers in `asyncio.to_thread` |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `fastapi>=0.115` | `pydantic>=2.9.0` | Uses Pydantic v2 core for 5-10x faster serialization |
| `sqlalchemy>=2.0` | `asyncpg>=0.29.0` | Async engine `create_async_engine("postgresql+asyncpg://...")` |
| `google-genai` | Python 3.10+ | Google GenAI SDK with structured response support |

## Sources

- Official FastAPI Documentation: https://fastapi.tiangolo.com/
- Google AI SDK Python Docs: https://ai.google.dev/gemini-api/docs
- SQLAlchemy 2.0 Async Documentation: https://docs.sqlalchemy.org/
- OWASP API Security Top 10 Guidelines: https://owasp.org/www-project-api-security/

---
*Stack research for: AROVIA (AI-Powered Interview Evaluation System)*
*Researched: 2026-08-15*
