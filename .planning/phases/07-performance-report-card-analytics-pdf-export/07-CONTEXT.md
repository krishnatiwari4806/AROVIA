# Phase 07: Performance Report Card, Analytics & PDF Export - Context

**Gathered:** 2026-08-19  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Phase 7 delivers the frontend and client-side performance report card, visual analytics, turn-by-turn question reviews, and downloadable PDF report generation for AROVIA. It visualizes candidate evaluation data produced in Phase 6, renders interactive multi-axis radar charts and dimensional progress meters, formats evidence-backed strengths and prioritized growth areas, presents collapsible turn-level Q&A reviews with concept matrix diffs and speech hesitation statistics, and exports professional branded multi-page A4 PDF documents directly in the candidate's browser at ₹0 cost.

</domain>

<decisions>
## Implementation Decisions

### Visual Charting & Radar Analytics
- **D-01 (Interactive Radar Polygon & Metric Bars):**
  - Interactive multi-axis Radar Chart displaying the 5 evaluation dimensions (Relevance, Correctness, Keywords, Clarity, Confidence) with a target seniority benchmark overlay (Senior: 80+, Mid: 70+, Junior: 60+).
  - Paired with 5 color-coded horizontal metric bars with exact numerical percentage badges and descriptive tooltips.

### Turn-by-Turn Q&A Review Layout
- **D-02 (Expandable Accordion Cards & Concept Diff):**
  - Collapsible turn cards with turn badges ("Turn 1: Core", "Turn 2: Follow-up") and composite turn score pills (e.g. "88/100").
  - Expanded view renders:
    1. Candidate's actual transcribed answer.
    2. Senior benchmark ideal answer.
    3. Concept Matrix: Green badges for `Covered Concepts` and Amber/Red badges for `Missed Concepts`.
    4. 5 Mini-Score Meters for turn-level dimensions.
    5. Speech Stats: Turn duration in seconds, filler word count, and filler percentage density.
    6. Constructive takeaway feedback banner.

### Score Grading & Readiness Badges
- **D-03 (4-Tier Competency Rubric):**
  - **85–100**: *Exceptional / Strong Hire* (Emerald Green badge) — Ready for top-tier technical loops.
  - **70–84**: *Proficient / Solid Hire* (Blue / Indigo badge) — Meets core expectations with minor polish needed.
  - **50–69**: *Developing / Needs Practice* (Amber badge) — Good foundation, gaps in edge cases or depth.
  - **<50**: *Needs Substantial Preparation* (Rose / Red badge) — Core conceptual gaps require structured study.

### Client-Side PDF Export Engine (₹0 Zero Cost)
- **D-04 (Client-Side Multi-Page PDF via jsPDF + html2canvas):**
  - Generates downloadable, styled A4 PDF reports directly in the browser using `jspdf` and `html2canvas` with zero server-side rendering fees.
  - PDF layout includes: AROVIA Header & Branding, Candidate Target Role & Seniority, Composite Score & Competency Badge, Radar Chart & Dimension Scores, Top Strengths & Actionable Growth Areas, and Turn-by-Turn Question Summary with pagination and timestamps.
  - Complementary CSS print media styles supporting `window.print()`.

### the agent's Discretion
- Clean React component hierarchy (`ReportCard.jsx`, `RadarChart.jsx`, `MetricBar.jsx`, `TurnAccordion.jsx`, `StrengthsImprovements.jsx`, `PDFExportButton.jsx`).
- Loading skeletons and smooth error states while fetching `/sessions/{id}/evaluation`.

</decisions>

<canonical_refs>
## Canonical References

### Backend Schemas & Data
- `backend/app/schemas/evaluation.py` — `SessionEvaluationReportResponse`, `TurnEvaluationResponse`, `StrengthItem`, `ImprovementItem`.
- `backend/app/api/v1/endpoints/interviews.py` — `GET /sessions/{session_id}/evaluation` endpoint.
- `.planning/PROJECT.md` — Hard Constraints (§ ₹0 Zero-Cost hard constraint, client-side PDF export).

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — Requirements `REPT-01`, `REPT-02`, `REPT-03`, `REPT-04`, `REPT-05`.
- `.planning/ROADMAP.md` — Phase 7 scope and success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/services/api.js`: Frontend API client ready to add `getSessionEvaluation(sessionId)` and `evaluateSession(sessionId)`.
- `frontend/src/index.css`: Design system tokens (colors, radii, cards, typography, glassmorphism, responsive grid).
- `frontend/src/components/interview/InterviewRoom.jsx`: Completion screen links directly into Report Card view.

### Integration Points
- Frontend route or view switch to `<ReportCard sessionId={sessionId} onRetake={() => ...} />`.
- PDF generation utility module in `frontend/src/utils/pdfExport.js`.

</code_context>

<specifics>
## Specific Ideas

- Pure SVG/Canvas Radar Chart component without bulky chart libraries to keep bundle fast and lightweight.
- High-contrast printable layout for PDF exports.

</specifics>

<deferred>
## Deferred Ideas

- Aggregated historical progress charts and trends over multiple interviews belong to Phase 8 (Candidate Dashboard & Historical Progress Tracking).

</deferred>

---

*Phase: 07-performance-report-card-analytics-pdf-export*  
*Context gathered: 2026-08-19*  
