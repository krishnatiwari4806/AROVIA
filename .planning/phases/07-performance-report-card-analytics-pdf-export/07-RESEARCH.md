# Phase 07: Performance Report Card, Analytics & PDF Export - Technical Research

**Phase:** 07-performance-report-card-analytics-pdf-export  
**Status:** Complete  
**Date:** 2026-08-19  

---

## 1. Domain & Technical Objectives

Phase 7 implements the comprehensive post-interview visual performance scorecard, interactive dimensional analytics, turn-by-turn question reviews, actionable strengths/weaknesses breakdowns, and client-side multi-page A4 PDF export for AROVIA at ₹0 cost.

### Key Requirements (MUST Address)
- **REPT-01:** Executive Report Card Header & Summary (Target role, seniority, overall 0-100 score, 4-tier competency badge, timestamps, executive summary).
- **REPT-02:** Multi-Dimensional Visual Radar / Bar Analytics (5 dimensions visual breakdown: Relevance, Correctness, Keywords, Clarity, Confidence with comparison against target seniority benchmark).
- **REPT-03:** Turn-by-Turn Question Breakdown (Accordion / expandable cards showing question prompt, candidate transcribed answer, benchmark ideal answer diff, covered vs missed concepts tags, turn score breakdown, and speech hesitation stats).
- **REPT-04:** Concrete Strengths & Prioritized Actionable Growth Takeaways (Evidence-backed strengths cards, prioritized improvement cards with study resources/patterns).
- **REPT-05:** Client-Side PDF Export (₹0 Zero Cost) — Client-side multi-page styled PDF generator (`jspdf` + `html2canvas` + print CSS) allowing candidates to download a professional formatted report with zero cloud rendering fees.

---

## 2. Geometry & Math for Pure SVG Radar Chart

To avoid heavy external chart libraries and ensure crisp vector rendering in both desktop UI and PDF exports, we use a pure SVG polygon radar calculation:

$$\theta_i = -\frac{\pi}{2} + i \times \frac{2\pi}{5}, \quad i \in \{0, 1, 2, 3, 4\}$$
$$x_i = cx + \left(R \times \frac{S_i}{100}\right) \times \cos(\theta_i)$$
$$y_i = cy + \left(R \times \frac{S_i}{100}\right) \times \sin(\theta_i)$$

Where:
- Center $(cx, cy) = (150, 150)$, Max Radius $R = 100$.
- Grid rings at $20\%$, $40\%$, $60\%$, $80\%$, $100\%$.
- 5 Axes: Relevance ($0^\circ$), Technical Correctness ($72^\circ$), Key Concepts ($144^\circ$), Clarity ($216^\circ$), Confidence ($288^\circ$).
- Benchmark Polygon: Overlays target seniority baseline ($85$ for Senior, $70$ for Mid, $55$ for Junior).

---

## 3. 4-Tier Competency Rubric

| Score Range | Competency Tier | Color Token | Description |
|---|---|---|---|
| **85–100** | **Exceptional / Strong Hire** | `#10b981` (Emerald) | Demonstrates deep mastery, architectural trade-offs, and strong clarity. |
| **70–84** | **Proficient / Solid Hire** | `#3b82f6` (Blue) | Meets core expectations with solid fundamentals and minor polish needed. |
| **50–69** | **Developing / Needs Practice** | `#f59e0b` (Amber) | Good foundation; gaps in distributed edge cases, recovery, or conciseness. |
| **<50** | **Needs Substantial Preparation** | `#f43f5e` (Rose) | Core conceptual gaps require structured study of key fundamentals. |

---

## 4. Client-Side PDF Export Strategy (₹0 Cost)

```javascript
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

export async function exportReportToPDF(elementId, fileName) {
  const element = document.getElementById(elementId);
  if (!element) return false;

  const canvas = await html2canvas(element, {
    scale: 2, // High-DPI crispness
    useCORS: true,
    logging: false,
    backgroundColor: "#090d16", // Dark theme background
  });

  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF("p", "mm", "a4");
  const imgWidth = 210; // A4 width in mm
  const pageHeight = 297; // A4 height in mm
  const imgHeight = (canvas.height * imgWidth) / canvas.width;
  let heightLeft = imgHeight;
  let position = 0;

  pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
  heightLeft -= pageHeight;

  while (heightLeft > 0) {
    position = heightLeft - imgHeight;
    pdf.addPage();
    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;
  }

  pdf.save(fileName);
  return true;
}
```

---

## 5. Component Hierarchy

```
ReportCard (Container)
├── ReportHeader (Role, Seniority, Overall Score Gauge, Tier Badge, Timestamps)
├── DimensionalAnalytics
│   ├── PureSVGRadarChart (Candidate Polygon vs Seniority Benchmark Polygon)
│   └── MetricBarList (5 Dimensional Progress Bars with %, tooltips)
├── StrengthsAndImprovements
│   ├── TopStrengthsList (Evidence-backed cards with turn index tags)
│   └── PrioritizedImprovementsList (Gap descriptions + concrete study advice)
├── TurnByTurnAccordion
│   └── TurnCard (Collapsible: Q&A diff, Concept Matrix pills, Mini-Scores, Filler stats, Takeaway)
└── ActionFooter (Download PDF Button, Retake Practice Button, Print Button)
```

---
*Research completed for Phase 7 planning.*
