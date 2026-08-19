# Phase 06: Multi-Dimensional Evaluation & Scoring Engine - Technical Research

**Phase:** 06-multi-dimensional-evaluation-scoring-engine  
**Status:** Complete  
**Date:** 2026-08-19  

---

## 1. Domain & Technical Objectives

Phase 6 implements the server-side multi-dimensional evaluation and scoring pipeline for AROVIA. It evaluates candidate responses across 5 distinct dimensions, identifies key technical concepts covered versus missed, synthesizes comparisons against senior benchmark ideal answers, applies focus-adaptive dynamic weighting, generates prioritized actionable takeaways, and persistently stores all evaluations in PostgreSQL.

### Key Requirements (MUST Address)
- **EVAL-01:** Multi-Dimensional Scoring across 5 dimensions on a 0–100 scale:
  1. **Relevance** (Question context and prompt alignment)
  2. **Technical Correctness** (Architectural accuracy, factual correctness, algorithmic depth)
  3. **Key Concepts / Keywords Coverage** (Extraction of required technical terms and patterns)
  4. **Clarity & Structure** (Logical organization, articulation, conciseness)
  5. **Confidence & Tone Indicators** (Speech assertiveness, low hesitation, decisive engineering ownership)
- **EVAL-02:** Benchmark Ideal Answer Comparison: Turn-by-turn comparison highlighting specific gaps against senior model answers.
- **EVAL-03:** Strengths & Actionable Recommendations: 3–5 concrete engineering strengths and 3–5 prioritized growth areas with study advice.
- **EVAL-04:** Post-Session Evaluation Orchestrator: End-to-end evaluation execution transitioning session status from `'evaluating'` to `'completed'`.
- **EVAL-05:** Database Persistence & Schema: Persistent storage in `interview_sessions` and `interview_question_turns`.
- **EVAL-06:** Zero-Cost Hard Constraint (₹0): Local regex heuristic for filler-word analysis + Gemini 2.5 Flash free-tier for structured JSON evaluation.

---

## 2. Mathematical Scoring Formulas & Weighting Matrix

### 2.1 Confidence & Tone Blended Formula (₹0 Cost)
```python
# 1. Local Filler-Word Heuristic (40% weight)
# Regex detects: \b(um|uh|er|ah|like|you know|sort of|kind of|i guess|i think maybe|basically|honestly|actually|probably|not sure)\b
filler_density = (filler_count / max(1, total_words)) * 100
heuristic_score = max(0, min(100, 100 - (filler_density * 8)))

# 2. Gemini Semantic Assertiveness Score (60% weight)
# Evaluates engineering conviction, active voice, and decisive reasoning (0-100)

# 3. Blended Confidence Score
final_confidence_score = round((0.40 * heuristic_score) + (0.60 * gemini_confidence_score))
```

### 2.2 Focus-Adaptive Turn Composite Score
$$\text{Composite Turn Score} = \sum_{d \in \text{Dimensions}} (w_d \times S_d)$$

| Dimension | Technical Core | System Design | Behavioral |
|---|:---:|:---:|:---:|
| **Technical Correctness** | **35%** | **35%** | **10%** |
| **Relevance** | **25%** | **25%** | **30%** |
| **Key Concepts Coverage** | **20%** | **20%** | **10%** |
| **Clarity & Structure** | **10%** | **10%** | **30%** |
| **Confidence & Tone** | **10%** | **10%** | **20%** |

### 2.3 Session Aggregated Metrics
- **Dimension Averages**: Mean score for each dimension across all answered turns:
  $$\bar{S}_d = \frac{1}{N} \sum_{i=1}^{N} S_{d, i}$$
- **Overall Session Score**: Focus-weighted composite of the 5 session dimension averages, clamped to $[0, 100]$.

---

## 3. Database Schema & Migration (`004_add_evaluation_fields.py`)

### `interview_sessions`
- `overall_score`: Integer, nullable (0–100)
- `dimension_scores`: JSONB, nullable (`{"relevance": int, "correctness": int, "keywords": int, "clarity": int, "confidence": int}`)
- `evaluation_report`: JSONB, nullable (`top_strengths`, `top_improvements`, `executive_summary`)

### `interview_question_turns`
- `relevance_score`: Integer, nullable (0–100)
- `correctness_score`: Integer, nullable (0–100)
- `keywords_score`: Integer, nullable (0–100)
- `clarity_score`: Integer, nullable (0–100)
- `confidence_score`: Integer, nullable (0–100)
- `turn_score`: Integer, nullable (0–100)
- `evaluation_data`: JSONB, nullable (`covered_concepts`, `missed_concepts`, `ideal_answer_comparison`, `turn_feedback`)

---

## 4. Gemini Structured Evaluation Schema (`google-genai`)

```python
class TurnEvaluationItem(BaseModel):
    turn_index: int
    relevance_score: int = Field(..., ge=0, le=100)
    correctness_score: int = Field(..., ge=0, le=100)
    keywords_score: int = Field(..., ge=0, le=100)
    clarity_score: int = Field(..., ge=0, le=100)
    confidence_score: int = Field(..., ge=0, le=100)
    covered_concepts: List[str] = Field(default_factory=list)
    missed_concepts: List[str] = Field(default_factory=list)
    ideal_answer_comparison: str = Field(...)
    turn_feedback: str = Field(...)

class StrengthItem(BaseModel):
    title: str
    description: str
    evidence_turn_index: Optional[int] = None

class ImprovementItem(BaseModel):
    title: str
    description: str
    actionable_recommendation: str
    evidence_turn_index: Optional[int] = None

class SessionEvaluationReport(BaseModel):
    turns_evaluation: List[TurnEvaluationItem]
    top_strengths: List[StrengthItem]
    top_improvements: List[ImprovementItem]
    executive_summary: str
```

---

## 5. REST API Contract

- `POST /api/v1/interviews/sessions/{session_id}/evaluate`
  - Triggers complete post-interview evaluation pipeline.
  - Transitions session status to `completed`.
  - Returns `SessionEvaluationReportResponse`.
- `GET /api/v1/interviews/sessions/{session_id}/evaluation`
  - Retrieves saved evaluation scorecard and turn-by-turn breakdowns.
  - Returns `SessionEvaluationReportResponse`.

---
*Research completed for Phase 6 planning.*
