---
phase: 07
phase_slug: performance-report-card-analytics-pdf-export
date: 2026-08-19
status: ready
---

# Phase 07: Validation Strategy (Nyquist Verification Matrix)

This document establishes the test harness, automated build commands, and validation gates for Phase 7 (Performance Report Card, Analytics & PDF Export).

---

## 1. Test Harness & Environment

- **Frontend**: Vite + React 18 component testing + production bundle verification (`npm run build`).
- **Backend API Integration**: `pytest` verifying `/api/v1/interviews/sessions/{id}/evaluation` endpoint returns valid payload for frontend rendering.
- **Client-Side PDF Generator**: Browser-native headless DOM check and export module verification.

---

## 2. Verification Gates & Requirement Mapping

| Requirement | Artifact / Component | Verification Criteria |
|---|---|---|
| **REPT-01** | `frontend/src/components/report/ReportHeader.jsx` | Renders candidate target role, seniority level, composite 0–100 score gauge, 4-tier competency badge, and executive summary. |
| **REPT-02** | `frontend/src/components/report/RadarChart.jsx` & `MetricBar.jsx` | Pure SVG Radar Polygon renders 5 axes with candidate polygon overlaying target seniority benchmark line, paired with 5 color-coded metric progress bars. |
| **REPT-03** | `frontend/src/components/report/TurnAccordion.jsx` | Expandable turn cards display question prompt, candidate transcribed answer, benchmark ideal answer diff, concept matrix pills (covered vs missed), 5 mini-scores, and filler word stats. |
| **REPT-04** | `frontend/src/components/report/StrengthsImprovements.jsx` | Displays top 3–5 evidence-backed strengths and 3–5 prioritized actionable growth areas with concrete study recommendations. |
| **REPT-05** | `frontend/src/utils/pdfExport.js` & `PDFExportButton.jsx` | Client-side multi-page A4 PDF export using `jspdf` and `html2canvas` at ₹0 cost, with print stylesheet fallback. |

---

## 3. Automated Verification Commands

```bash
# Verify frontend production build
cd frontend && npm run build

# Run backend regression tests
py -3.14 -m pytest backend/tests/ -v
```

---
*Validation strategy locked for Phase 7.*
