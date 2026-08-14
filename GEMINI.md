<!-- GSD:project-start source:PROJECT.md -->
## Project

**AROVIA — AI-Powered Interview Evaluation System**

AROVIA is a secure, modular web application that conducts structured, adaptive AI-assisted interviews and evaluates candidates across multiple dimensions (relevance, correctness, key concepts, clarity/grammar, sentiment, and confidence indicators). Designed as a candidate self-practice and assessment platform, it simulates realistic technical and behavioral interviews with speech interaction, dynamic follow-up probing, and generates in-depth analytical performance reports with actionable improvement suggestions.

**Core Value:** Delivering realistic, adaptive AI mock interviews with rigorous, multi-dimensional evaluation and actionable feedback, built on a robust, highly secure, and clean full-stack architecture.

### Constraints

- **Backend Stack**: Python (FastAPI) — Chosen for native async support, performance, Pydantic type safety, and seamless Python AI/NLP ecosystem integration.
- **Frontend Stack**: React + Vite + Vanilla CSS / modern responsive styling — Chosen for speed, flexibility, component modularity, and high-performance browser audio APIs.
- **Database**: PostgreSQL with SQLAlchemy ORM & Alembic migrations — Chosen for relational integrity, schema migrations, and structured session/metric persistence.
- **AI & NLP Services**: Google Gemini API (structured JSON output, prompt chaining, fast inference) + Web Speech API for low-latency browser speech synthesis & recognition.
- **Timeline**: 45 days total development window structured into incremental, testable phases.
- **Security Standard**: Server-side defensive validation on all endpoints, zero trust for client data, strict input/file sanitization, secure secret storage via `.env`.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
# Core framework & server
# Database & ORM
# AI / LLM & Document Parsing
# Security, Auth & Utilities
# Testing & Quality
### Frontend
# Core & Router
# Icons & UI Charts
# Utilities & PDF Export
# Dev tools
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
