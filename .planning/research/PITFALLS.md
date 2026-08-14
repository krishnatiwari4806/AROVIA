# Pitfalls Research

**Domain:** AI-Powered Interview Evaluation System (Web Application)
**Researched:** 2026-08-15
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Unstructured or Flaky LLM Outputs Crashing the Backend

**What goes wrong:**
The LLM returns Markdown formatting around JSON (e.g. ` ```json ... ``` `), missing fields, malformed trailing commas, or conversational filler text, causing `json.loads()` or API response serialization to throw uncaught 500 errors mid-interview.

**Why it happens:**
Relying on standard freeform prompts without enforcing strict API response schemas or lacking fallback parsing logic.

**How to avoid:**
1. Use Gemini's native `response_schema` / structured output mode configured with Pydantic classes.
2. Wrap all LLM parsing in defensive try-except blocks with a clean deterministic fallback response.
3. Validate all extracted fields against strict Pydantic schemas before returning or saving to database.

**Warning signs:**
Occasional 500 Internal Server Errors on answer submission or report generation during integration testing.

**Phase to address:**
Phase 1 (AI & Core Services Setup) & Phase 4 (Interview Engine).

---

### Pitfall 2: Browser Speech Recognition Inconsistencies & Latency Freezes

**What goes wrong:**
Web Speech API (`webkitSpeechRecognition`) behaves differently across browsers (Chrome vs Safari vs Firefox), drops words on poor microphones, or abruptly disconnects after a short pause, causing candidate frustration and lost answers.

**Why it happens:**
Assuming Web Speech API is identical on every browser and failing to provide transcript state synchronization and manual text editing.

**How to avoid:**
1. Maintain real-time interim + final transcript state in React context.
2. Always provide an editable text area allowing the candidate to review, correct, or type their answer if voice recognition misses terms.
3. Detect browser capability on mount and show a clear indicator if speech recognition is unsupported.

**Warning signs:**
Empty transcripts submitted or users unable to start recording in non-Chromium browsers.

**Phase to address:**
Phase 5 (Interactive Interview Room UI & Audio Hooks).

---

### Pitfall 3: Malicious File Uploads & Insecure PDF Processing

**What goes wrong:**
Attackers upload disguised executables, oversized multi-gigabyte files (DoS), or polyglot PDF exploits that compromise the backend server or exhaust disk space.

**Why it happens:**
Validating files by extension only (e.g., checking `.pdf`) without checking magic bytes, MIME types, or enforcing file size limits.

**How to avoid:**
1. Enforce strict file size limits (e.g., max 5 MB).
2. Validate magic bytes (e.g., `%PDF-` header) and MIME type (`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).
3. Store uploaded files with sanitized UUID filenames in an isolated directory outside public document roots.
4. Catch parsing exceptions defensively when reading corrupted files.

**Warning signs:**
Backend hangs or crashes when processing non-standard PDF formats.

**Phase to address:**
Phase 3 (Resume Ingestion & Parsing Service).

---

### Pitfall 4: Monolithic Context Window Bloat & Slow LLM Response Times

**What goes wrong:**
Passing the candidate's entire multi-page resume text, complete job description, and entire interview conversation history into every question prompt causes massive latency (5-10+ seconds) and excessive token costs.

**Why it happens:**
Dumping raw unfiltered text into prompts instead of structured concise summaries.

**How to avoid:**
1. Pre-process and extract a compact structured profile (Top 10 skills, recent projects, target role) from the resume.
2. In interview turns, pass only the structured profile, current topic focus, and last 2 Q&A turns for immediate context.
3. Run evaluation as a single post-interview aggregation job rather than heavy multi-second operations on every micro-turn.

**Warning signs:**
Interview turns take more than 3 seconds to generate follow-up questions.

**Phase to address:**
Phase 4 (Interview Session Orchestrator) & Phase 6 (Evaluation Engine).

---

### Pitfall 5: Client-Side Security & Privilege Bypass

**What goes wrong:**
Client submits arbitrary user IDs, manipulated scores, or accesses another candidate's interview session/report directly by altering URL parameters (IDOR - Insecure Direct Object Reference).

**Why it happens:**
Relying on client-supplied parameters for authorization instead of deriving user identity directly from the verified JWT payload.

**How to avoid:**
1. Extract current user ID exclusively from the verified JWT token via FastAPI dependency (`get_current_user`).
2. Verify database ownership of all resources (resumes, interviews, reports) with `WHERE user_id = current_user.id`.
3. Set secure HTTP response headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).

**Warning signs:**
Endpoints accepting `user_id` as query parameters or request body fields.

**Phase to address:**
Phase 2 (Authentication & Security Baseline).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using SQLite instead of PostgreSQL in production | Zero setup locally | Concurrency locks, missing JSONB indexing, migration drift | Acceptable only in initial local development; PostgreSQL required for final deployment |
| Hardcoding prompt strings inside API endpoints | Fast to prototype | Untestable prompts, no versioning, difficult prompt engineering | Never — use centralized prompt template managers in `services/` |
| Storing evaluation scores as plain unstructured strings | Quick to build | Impossible to query trends, build radar charts, or compute aggregate analytics | Never — use structured Pydantic DTOs and JSONB columns |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous PDF parsing in ASGI handler | Request queue stalls | Run `pdfplumber` in background task / `asyncio.to_thread` | > 5 concurrent uploads |
| Un-indexed interview session queries | Dashboard loads slowly | Add database index on `interviews(user_id, created_at)` | > 500 session records |
| Fetching uncompressed full reports on list endpoints | High payload sizes | Separate list summaries (`/api/v1/interviews`) from full report details (`/api/v1/reports/{id}`) | > 50 completed interviews |

## "Looks Done But Isn't" Checklist

- [ ] **Resume Parsing:** Often misses multi-column layouts — verify parsing on 2-column resumes.
- [ ] **Speech Recognition:** Often cuts off during natural pauses — verify silence timeout settings.
- [ ] **JWT Auth:** Often fails to handle expired tokens gracefully — verify 401 interceptor & automatic logout in frontend.
- [ ] **Report PDF Export:** Often cuts off charts or overlaps text across page boundaries — verify multi-page PDF layout pagination.
- [ ] **Error Handling:** Often leaks internal traceback in 500 responses — verify global FastAPI exception handler returning clean error JSON.

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| IDOR & Auth Flaws | Phase 2 (Auth & Security) | Automated multi-user access control tests |
| PDF Parsing Exploit & File Validation | Phase 3 (Resume Engine) | Test uploads with invalid MIME, oversized files, and corrupt PDFs |
| LLM Response Parsing Crashes | Phase 4 (Interview Engine) | Mock malformed LLM responses and verify schema validation & retry/fallback |
| Speech-to-Text Disconnections | Phase 5 (Live Interview Room) | Test speech input with pauses, manual text corrections, and fallback mode |
| Token Overhead & Slow Latency | Phase 6 (Evaluation Engine) | Benchmark prompt token usage and end-to-end evaluation response times |

---
*Pitfalls research for: AROVIA (AI-Powered Interview Evaluation System)*
*Researched: 2026-08-15*
