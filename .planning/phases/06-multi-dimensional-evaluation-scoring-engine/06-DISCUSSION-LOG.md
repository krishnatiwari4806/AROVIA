# Phase 06: Multi-Dimensional Evaluation & Scoring Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.  
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-19  
**Phase:** 06-multi-dimensional-evaluation-scoring-engine  
**Areas discussed:** Dimension Weighting & Composite Overall Score, Evaluation Execution Pipeline, Confidence & Tone Analysis Heuristic, Actionable Recommendations & Gap Specificity  

---

## Dimension Weighting & Composite Overall Score

| Option | Description | Selected |
|--------|-------------|----------|
| Focus-Adaptive Dynamic Weighting | Technical/Design interviews weigh Correctness & Concepts higher (35% Correctness, 25% Relevance, 20% Concepts, 10% Clarity, 10% Confidence); Behavioral interviews weigh Clarity & Relevance higher (30% Relevance, 30% Clarity, 20% Confidence, 10% Correctness, 10% Concepts) | ✓ |
| Fixed Technical Weighting | Fixed across all interviews: Correctness 35%, Relevance 25%, Key Concepts 20%, Clarity 10%, Confidence 10% | |
| Equal Weighting | All 5 dimensions contribute exactly 20% each to the overall score | |

**User's choice:** Focus-Adaptive Dynamic Weighting  
**Notes:** Dynamically adjusts to the interview focus so behavioral interviews reward communication structure while technical sessions prioritize factual architectural correctness.

---

## Evaluation Execution Pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Orchestrated Post-Session Batch with Immediate Finalization | When interview concludes, server evaluates all turns and generates the executive session scorecard in one structured Gemini pass with local filler-word heuristics, updating status to 'completed' | ✓ |
| Incremental Turn-by-Turn Live Scoring | Score each turn immediately on answer submission, then finalize summary on last turn | |
| Async Background Worker with Polling | Return immediately and evaluate asynchronously in the background while client polls /evaluation-status | |

**User's choice:** Orchestrated Post-Session Batch with Immediate Finalization  
**Notes:** Provides atomic completion transition and avoids unnecessary LLM latency during the live interview response turns.

---

## Confidence & Tone Analysis Heuristic (₹0 Zero Cost)

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid Local Filler-Word Heuristic (40%) + Gemini Assertiveness & Technical Certainty (60%) | Local regex parses filler words and hedging markers ('um', 'uh', 'i guess', 'sort of', 'maybe') combined with Gemini's assessment of architectural authority and conviction | ✓ |
| Pure Gemini Semantic Tone Scoring | Let Gemini evaluate candidate confidence and clarity purely through structured prompt criteria | |
| Strict Mathematical Filler Penalty | Score confidence purely based on filler word density formula (100 minus penalty per filler instance) | |

**User's choice:** Hybrid Local Filler-Word Heuristic (40%) + Gemini Assertiveness & Technical Certainty (60%)  
**Notes:** 100% free-tier zero-cost architecture combining fast local string processing with LLM semantic tone analysis.

---

## Actionable Recommendations & Gap Specificity

| Option | Description | Selected |
|--------|-------------|----------|
| Structured Concept Matrix & Concrete Actionable Recommendations | Turn-level covered vs missed concepts + benchmark comparison; Session-level top 3–5 evidence-backed strengths and 3–5 prioritized growth areas with study advice and executive summary | ✓ |
| General Competency Summary | High-level paragraph on strengths and weaknesses without granular concept lists or turn-by-turn diffs | |
| Hiring Rubric Style (Strong Hire / Lean Hire / No Hire) | Categorical hiring recommendation with score breakdown | |

**User's choice:** Structured Concept Matrix & Concrete Actionable Recommendations  
**Notes:** Gives candidates maximum educational value with specific engineering topics to study.

---

## the agent's Discretion

- Database migration for `interview_sessions` and `interview_question_turns` evaluation columns.
- Gemini prompt templates and fallback scoring algorithms.

---

## Deferred Ideas

- Visual Radar charts, score breakdowns, and PDF downloads belong to Phase 7 (Report Card).
- Historical progress trend lines across multiple interviews belong to Phase 8 (Dashboard).
