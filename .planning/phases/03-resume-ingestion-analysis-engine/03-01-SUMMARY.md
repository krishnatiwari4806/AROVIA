---
phase: 03-resume-ingestion-analysis-engine
plan: 01
status: complete
date: 2026-08-16
tests_passed: 11/11 (50/50 overall)
---

# Phase 03: Plan 01 — Document Ingestion & Safe Text Extraction Summary

## Summary of Accomplishments

1. **Dependency Ingestion & Storage Layout**:
   - Added `python-multipart`, `pdfplumber`, `python-docx`, and `google-genai` to `backend/requirements.txt`.
   - Updated `backend/app/core/config.py` with `RESUME_STORAGE_DIR`, `MAX_RESUME_SIZE_BYTES` (5 MB), and `GEMINI_MODEL` (`"gemini-2.5-flash"`).
   - Created `backend/storage/resumes/` storage directory.

2. **Resume ORM Model & Migration**:
   - Implemented `Resume` model in `backend/app/models/resume.py` with UUID PK, cascade delete to `User`, `file_path`, `raw_text`, and JSON/JSONB `parsed_data`.
   - Linked `User.resume` relationship in `backend/app/models/user.py`.
   - Registered `Resume` in `backend/app/db/base.py` and generated Alembic migration `002_create_resume_table.py`.

3. **Defensive Extraction & Sanitization**:
   - Implemented `backend/app/services/document_extractor.py`.
   - Magic byte validation for `%PDF-` and `PK\x03\x04` zip headers with standard Word XML structure verification (`[Content_Types].xml`).
   - Threadpool offloading via `asyncio.to_thread` for CPU-bound `pdfplumber` and `python-docx` text extraction.
   - Enforced minimum 50 non-whitespace characters (rejecting scanned/empty documents with HTTP 422).
   - Sanitized control characters and capped extracted text length at 30,000 characters.

4. **Testing & Verification**:
   - `test_resume_upload.py`: Verified PDF/DOCX magic bytes, spoofed extensions, extension mismatches, empty files.
   - `test_resume_extractor.py`: Verified multi-page PDF & DOCX text extraction, scanned/empty doc rejection (< 50 chars), and control character sanitization.
   - All 50 test cases passed.
