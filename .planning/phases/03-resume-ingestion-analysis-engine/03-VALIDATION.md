---
phase: 03
phase_slug: resume-ingestion-analysis-engine
date: 2026-08-16
status: ready
---

# Phase 03: Validation Strategy (Nyquist Verification Matrix)

This document establishes the test harness, automated verification commands, and validation gates for Phase 3 (Resume Ingestion & Analysis Engine).

---

## 1. Test Harness & Environment

- **Framework**: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`
- **Database Fixture**: In-memory SQLite async engine (`sqlite+aiosqlite:///:memory:`) for integration tests
- **AI Mocking**: Unit tests monkeypatch/mock `google-genai` client calls (`from google import genai`) to verify parsing, retry logic, and HTTP 503 error handling without consuming live API credits.

---

## 2. Verification Gates & Requirement Mapping

| Requirement | Test File | Test Method | Description |
|---|---|---|---|
| **RESM-01** | `tests/test_resume_upload.py` | `test_upload_file_size_limit` | Enforces 5 MB file size limit with streaming chunk checks. |
| **RESM-02** | `tests/test_resume_upload.py` | `test_magic_bytes_validation_pdf_and_docx` | Validates `%PDF-` and `PK\x03\x04` zip header; rejects spoofed file extensions. |
| **RESM-03** | `tests/test_resume_extractor.py` | `test_extract_text_and_reject_empty_scanned_doc` | Extracts text with `pdfplumber` / `python-docx`; rejects empty/scanned PDFs (<50 chars) with HTTP 422. |
| **RESM-04** | `tests/test_resume_parser.py` | `test_gemini_structured_parsing_and_retry` | Validates Pydantic schema generation via `google-genai`, 1 automatic retry, and clean HTTP 503 on provider failure. |
| **RESM-05** | `tests/test_resume_endpoints.py` | `test_resume_crud_lifecycle_and_overrides` | Verifies `POST /upload` (atomic replacement & rollback guard), `GET /me`, `PUT /me/parsed`, and `DELETE /me`. |

---

## 3. Automated Verification Commands

```bash
# Run all Phase 3 tests
python -m pytest backend/tests/test_resume_upload.py backend/tests/test_resume_extractor.py backend/tests/test_resume_parser.py backend/tests/test_resume_endpoints.py -v

# Run full project test suite
python -m pytest backend/tests/ -v
```

---
*Validation strategy locked for Phase 3.*
