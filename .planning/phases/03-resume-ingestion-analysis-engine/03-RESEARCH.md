# Phase 03: Resume Ingestion & Analysis Engine - Technical Research

**Phase:** 03-resume-ingestion-analysis-engine  
**Status:** Complete  
**Date:** 2026-08-16  

---

## 1. Domain & Technical Objectives

Phase 3 implements a defensive, asynchronous document ingestion and AI extraction pipeline for candidate resumes.

### Key Requirements (MUST Address)
- **RESM-01:** Candidate can upload resume files in PDF (`.pdf`) or Word (`.docx`) format with strict 5 MB (`5,242,880 bytes`) size limits.
- **RESM-02:** System verifies magic bytes and file signatures (`%PDF-` for PDF, `PK\x03\x04` zip header with `[Content_Types].xml` for DOCX) to block spoofed or renamed binary files.
- **RESM-03:** Plain text extraction safely parses multi-column and standard document layouts using `pdfplumber` / `python-docx`, rejecting scanned/empty files (< 50 characters) with HTTP 422.
- **RESM-04:** Gemini structured schema extraction parses raw text into validated Pydantic models (`skills`, `experience_years`, `domains`, `education`, `summary`) with native JSON schema enforcement, 1 automatic retry, and clean HTTP 503 error handling on provider outages.
- **RESM-05:** Candidate can inspect, review, edit/override, or delete their active resume and parsed skills via secure REST endpoints (`/upload`, `/me`, `/me/parsed`, `/me`).

---

## 2. Technical Stack & Dependencies

### Ingestion & Text Extraction
1. **`python-multipart` (`>=0.0.9`)**: Handles streaming multipart form uploads in FastAPI `UploadFile`.
2. **`pdfplumber` (`>=0.11.0`)**: High-fidelity PDF text and character extraction.
3. **`python-docx` (`>=1.1.0`)**: Fast, pure-Python DOCX XML document parser.
4. **`google-genai` / `google-generativeai`**: Official Google AI SDK for invoking Gemini models with structured JSON schemas (`response_schema`).

---

## 3. Architecture & Security Invariants

### 3.1 Defensive File Ingestion
- **Streaming Size Check**: Read incoming file in chunks (e.g. 64 KB). If accumulated bytes exceed `5,242,880`, immediately abort and raise HTTP 422 (`ValidationError: File exceeds maximum allowed size of 5 MB`).
- **Magic Byte Verification**:
  - `application/pdf`: First 5 bytes MUST equal `b"%PDF-"`.
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`: First 4 bytes MUST equal `b"PK\x03\x04"`. The file is verified as a valid ZIP archive containing `[Content_Types].xml` or `word/document.xml`.
- **Isolated Storage**: Save validated files to `storage/resumes/<uuid>.<ext>` with non-guessable UUIDs and strict `0600` permissions. Single active resume per candidate: uploading a new resume deletes the old file from disk before writing the new one.

### 3.2 Safe Text Extraction & Sanitization
- **Threadpool Offloading**: Run CPU-bound `pdfplumber` and `python-docx` parsers inside `asyncio.to_thread` with a 15-second timeout to prevent ASGI event loop blocking.
- **Empty / Scanned PDF Rejection**: Extracted text must have at least 50 non-whitespace characters. Scanned PDFs with zero text layer are rejected with HTTP 422 (`"No extractable text found. Please upload a standard text-based PDF/DOCX resume."`).
- **Prompt Injection Defense**: Bounded at 30,000 characters (~6,000 words), stripped of null bytes (`\x00`) and control characters, and wrapped in `<resume_text>` tags during Gemini prompt construction.

### 3.3 Gemini Structured JSON Schema
- **Configurable Model**: Use `settings.GEMINI_MODEL` (defaulting to active Flash model e.g. `gemini-2.5-flash` in `.env`). Zero hard-coded obsolete model IDs.
- **Structured Schema**:
```python
class ParsedResumeData(BaseModel):
    skills: list[str] = Field(description="Extracted technical skills, languages, frameworks, libraries, and tools.")
    experience_years: float = Field(description="Total estimated years of professional software engineering experience.")
    domains: list[str] = Field(description="Primary technical domains e.g. Backend, Cloud, Distributed Systems.")
    education: list[dict[str, Any]] = Field(description="List of educational qualifications, degrees, institutions, and graduation years.")
    summary: str = Field(description="2-3 sentence executive career summary.")
```
- **Transient Failure Retry**: 1 automatic retry with 1s exponential backoff on network timeouts or rate limits. If still failing, return HTTP 503 Service Unavailable (`"AI evaluation service is temporarily unavailable. Please retry shortly."`).

---

## 4. Database Schema Contract

### `resumes` Table (matching `docs/BACKEND_SCHEMA.md` §2.5)
- `id`: `VARCHAR(36)` Primary Key (UUIDv4)
- `user_id`: `VARCHAR(36)` FK -> `users.id` ON DELETE CASCADE (Unique for single active resume per candidate)
- `file_name`: `VARCHAR(255)` Sanitized original filename
- `file_path`: `VARCHAR(500)` Absolute or relative isolated path
- `file_size_bytes`: `INTEGER` Enforced $\le 5,242,880$
- `mime_type`: `VARCHAR(100)` (`application/pdf` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- `raw_text`: `TEXT` Extracted plain text
- `parsed_data`: `JSONB` Structured JSON dictionary matching `ParsedResumeData`
- `created_at`: `TIMESTAMPTZ` (UTC)
- `updated_at`: `TIMESTAMPTZ` (UTC)

---

## 5. Validation Architecture

### Automated Verification Matrix
1. **Magic Byte & File Security Tests (`test_resume_upload.py`)**:
   - Valid PDF magic bytes (`%PDF-`) accepted.
   - Valid DOCX zip archive accepted.
   - Spoofed extension (e.g. `.exe` or `.txt` renamed to `.pdf`) rejected with HTTP 422.
   - Files > 5 MB rejected with HTTP 422.
2. **Text Extraction & Sanitization Tests (`test_resume_extractor.py`)**:
   - Extract plain text from multi-page PDF and formatted DOCX.
   - Reject empty/scanned PDF with < 50 characters with HTTP 422.
   - Text bounding at 30,000 characters and control character stripping.
3. **Gemini Structured Parsing Tests (`test_resume_parser.py`)**:
   - Mocked Gemini SDK returning structured JSON schema.
   - Transient failure triggers 1 retry; permanent failure returns HTTP 503.
   - Validates Pydantic response schema against real JSON payload.
4. **Resume CRUD & Overrides Tests (`test_resume_endpoints.py`)**:
   - `POST /api/v1/resumes/upload`: Replaces prior resume file on disk and DB record.
   - `GET /api/v1/resumes/me`: Returns active candidate resume metadata and parsed schema.
   - `PUT /api/v1/resumes/me/parsed`: Updates/overrides parsed skills, experience years, domains, and summary.
   - `DELETE /api/v1/resumes/me`: Deletes physical file and database row; subsequent `GET` returns 404.

---
*Research completed for Phase 3 planning.*
