# Phase 06: Multi-Dimensional Evaluation & Scoring Engine - Context

**Gathered:** 2026-08-19  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 6 delivers the server-side multi-dimensional evaluation, scoring, and feedback synthesis engine. It analyzes candidate responses across all interview question turns, scores them on 5 distinct dimensions (Relevance, Correctness, Key Concepts, Clarity/Structure, Confidence/Tone), compares against benchmark ideal answers, extracts covered vs. missed concepts, computes composite session scores with focus-adaptive weighting, generates prioritized actionable improvements, and persists evaluation records to PostgreSQL.

</domain>

<decisions>
## Implementation Decisions

### Dimension Weighting & Composite Score Calculation
- **D-01 (Focus-Adaptive Dynamic Weighting):**
  - **Technical Core & System Design Focus**:
    - Technical Correctness: **35%**
    - Relevance & Context Alignment: **25%**
    - Key Concepts & Keywords Coverage: **20%**
    - Clarity & Structure: **10%**
    - Confidence & Tone: **10%**
  - **Behavioral Focus**:
    - Relevance & STAR Alignment: **30%**
    - Clarity & Communication Structure: **30%**
    - Confidence & Tone: **20%**
    - Technical/Domain Correctness: **10%**
    - Key Concepts: **10%**
  - Overall Composite Score is clamped to integer range **0–100**.

### Evaluation Execution Pipeline
- **D-02 (Orchestrated Post-Session Batch):**
  - When the final turn is answered (or explicit session completion endpoint is called), the evaluation orchestrator executes a coordinated evaluation pipeline:
    1. Runs local text analysis (filler words, word counts, response pacing).
    2. Runs Gemini multi-dimensional structured evaluation (`google-genai` with `response_schema=SessionEvaluationReport`).
    3. Blends local heuristics + AI scores.
    4. Computes turn scores and aggregated session radar averages.
    5. Updates turn records and session records in the database, transitioning session `status` from `'evaluating'` to `'completed'`.

### Confidence & Tone Analysis Heuristic (₹0 Zero Cost)
- **D-03 (Hybrid Local NLP + Gemini Assertiveness):**
  - **Local Rule-Based Heuristic (40% weight)**: Scans for filler words and hedging markers (`um`, `uh`, `like`, `sort of`, `kind of`, `i guess`, `i think maybe`, `probably`, `not sure`, `basically`) and computes hesitation density penalty.
  - **Gemini Semantic Assertiveness (60% weight)**: Evaluates active voice, ownership of engineering decisions, and technical conviction.
  - Blended into a clean 0–100 Confidence score with zero external API fees.

### Structured Concept Matrix & Actionable Feedback
- **D-04 (Turn & Session Level Feedback Contract):**
  - **Turn Level**:
    - `relevance_score`, `correctness_score`, `keywords_score`, `clarity_score`, `confidence_score`, `turn_score` (0–100 each).
    - `covered_concepts`: List of technical skills/concepts demonstrated.
    - `missed_concepts`: List of critical architectural/edge-case concepts omitted.
    - `ideal_answer_comparison`: Concise gap analysis vs senior benchmark response.
    - `turn_feedback`: 1-2 sentence feedback takeaway for this specific question.
  - **Session Level**:
    - `overall_score`: 0–100 composite score.
    - `dimension_scores`: Dictionary with average score for each of the 5 dimensions (ready for Radar Chart visualization).
    - `top_strengths`: 3–5 concrete, evidence-backed engineering strengths.
    - `top_improvements`: 3–5 prioritized growth areas, each with a concrete study recommendation.
    - `executive_summary`: 3–4 sentence executive summary of candidate performance.

### the agent's Discretion
- Database schema migration for evaluation storage: Add `evaluation_data` JSONB / structured columns to `interview_question_turns` and `evaluation_report` / `overall_score` / `dimension_scores` to `interview_sessions`.
- Fallback heuristic evaluator in case of temporary Gemini timeout so evaluations never crash.

</decisions>

<canonical_refs>
## Canonical References

### Schema & Architecture
- `docs/BACKEND_SCHEMA.md` §2.6 — `interview_sessions` model and lifecycle (`in_progress` -> `evaluating` -> `completed`).
- `docs/BACKEND_SCHEMA.md` §2.7 — `interview_question_turns` schema.
- `.planning/PROJECT.md` — Hard Constraints (§ ₹0 Zero-Cost hard constraint, Gemini structured mode).

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — Requirements `EVAL-01`, `EVAL-02`, `EVAL-03`, `EVAL-04`, `EVAL-05`, `EVAL-06`.
- `.planning/ROADMAP.md` — Phase 6 scope and success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app.models.interview.InterviewSession` & `InterviewQuestionTurn`: Ready for evaluation fields.
- `app.services.gemini_service.GeminiService`: `google-genai` SDK async wrapper with structured JSON response mode.
- `app.services.interview_service.InterviewService`: Session transition lifecycle and transcript fetchers.

### Integration Points
- `POST /api/v1/interviews/sessions/{session_id}/evaluate`: Explicitly triggers evaluation if session is in `evaluating` state, returning full `SessionEvaluationReportResponse`.
- `GET /api/v1/interviews/sessions/{session_id}/evaluation`: Retrieves completed session evaluation scorecard.

</code_context>

<specifics>
## Specific Ideas

- Fast local regex scanner for filler words and hedge markers.
- Structured Gemini schema `SessionEvaluationReport` containing both per-turn scores and session-level executive insights.

</specifics>

<deferred>
## Deferred Ideas

- Visual Radar Charts, Bar Charts, and PDF Download UI are scheduled for Phase 7 (Performance Report Card & Analytics).
- Historical session comparison trends over time are scheduled for Phase 8 (Candidate Dashboard).

</deferred>

---

*Phase: 06-multi-dimensional-evaluation-scoring-engine*  
*Context gathered: 2026-08-19*  
