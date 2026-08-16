# Phase 3: Resume Ingestion & Analysis Engine - Discussion Log

**Date:** 2026-08-16  
**Phase:** 03-resume-ingestion-analysis-engine  

## Discussion Areas Covered

### Area 1: Resume Multiplicity & Storage
- **Options Presented:**
  1. Single active resume per candidate with automatic replacement (Recommended)
  2. Multiple resumes supported per candidate
  3. Flat isolated storage (`storage/resumes/<uuid>.<ext>`) with `0600` permissions (Recommended)
  4. User-partitioned storage (`storage/resumes/<user_id>/<uuid>.<ext>`)
- **User Selection:** Single active resume per candidate with automatic replacement; Flat isolated storage (`storage/resumes/<uuid>.<ext>`).

### Area 2: Text Extraction & Sanitization
- **Options Presented:**
  1. Reject empty/scanned resumes with HTTP 422 (Recommended)
  2. Accept empty text resumes and return empty schema
  3. Strict 30,000 character cap with sanitized delimiters (Recommended)
  4. 50,000 character cap with basic whitespace normalization
- **User Selection:** Reject empty/scanned PDFs (< 50 chars) with HTTP 422; Strict 30,000 character cap with XML prompt wrapping and control char stripping.

### Area 3: Gemini Schema & Parsing Resilience
- **Options Presented:**
  1. Rich structured schema (skills, experience_years, domains, education, summary) (Recommended)
  2. Minimal schema (skills and experience_years only)
  3. Gemini model configuration and resilience
- **User Selection:** Rich structured schema. User specified requirement that Gemini model ID must be configurable (`settings.GEMINI_MODEL`), zero hard-coded obsolete model strings, with 1 automatic retry on transient error and clean HTTP 503 on unrecoverable outage.

### Area 4: Candidate Skill Review & Overrides
- **Options Presented:**
  1. Full CRUD: Upload (`POST /resumes/upload`), View active (`GET /resumes/me`), Override parsed data (`PUT /resumes/me/parsed`), and Delete (`DELETE /resumes/me`) (Recommended)
  2. Read-only with re-upload
- **User Selection:** Full CRUD with upload, view, edit/override, and delete endpoints.

---
*Log generated during Phase 3 discussion.*
