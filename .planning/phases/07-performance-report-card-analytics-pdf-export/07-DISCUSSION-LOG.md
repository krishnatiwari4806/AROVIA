# Phase 07: Performance Report Card, Analytics & PDF Export - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.  
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-19  
**Phase:** 07-performance-report-card-analytics-pdf-export  
**Areas discussed:** Visual Charting & Radar Analytics, Turn-by-Turn Q&A Review Layout, Score Grading & Readiness Badges, Client-Side PDF Export Engine  

---

## Visual Charting & Radar Analytics

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive Radar Chart + Horizontal Metric Bars | Multi-axis Radar Polygon displaying the 5 dimensions with a target benchmark overlay, plus 5 color-coded horizontal progress bars showing exact scores and descriptions | ✓ |
| Horizontal Bar Charts Only | 5 separate bar charts with score percentages without the radar polygon | |
| Circular Ring Dials Only | 5 separate circular percentage meters side-by-side | |

**User's choice:** Interactive Radar Chart + Horizontal Metric Bars  
**Notes:** Provides both an intuitive spatial polygon overview of dimensional balance and detailed linear progress bars.

---

## Turn-by-Turn Q&A Review Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Expandable Accordion with Side-by-Side Comparison & Concept Badges | Collapsible turn cards with turn score badges; expanded view shows candidate answer, benchmark ideal answer diff, green covered / amber missed concept tags, 5 mini-scores, and filler word stats | ✓ |
| Tabbed Turn Navigator | Left-hand turn list sidebar with right-hand active turn detail pane | |
| Flat Continuous Scroll | All turns fully expanded in a long continuous page view | |

**User's choice:** Expandable Accordion with Side-by-Side Comparison & Concept Badges  
**Notes:** Keeps the page compact while allowing deep drill-down into specific questions.

---

## Score Grading & Readiness Badges

| Option | Description | Selected |
|--------|-------------|----------|
| 4-Tier Competency Rubric | 85–100: Exceptional / Strong Hire (Emerald), 70–84: Proficient / Solid Hire (Blue), 50–69: Developing / Needs Practice (Amber), <50: Needs Substantial Preparation (Rose) with descriptive guidance | ✓ |
| Letter Grading System (A+, A, B, C, D, F) | Academic style letter grade with score breakdown | |
| Binary Status (Readiness Cleared vs Needs Practice) | Simple pass/practice badge without granular tiers | |

**User's choice:** 4-Tier Competency Rubric  
**Notes:** Aligns with standard industry engineering interview leveling and gives clear, encouraging guidance.

---

## Client-Side PDF Export Engine (₹0 Zero Cost)

| Option | Description | Selected |
|--------|-------------|----------|
| Client-Side Multi-Page PDF Export (jsPDF + html2canvas) | Generates a downloadable branded A4 PDF report with score badge, radar chart, strengths/improvements, and turn summary with zero server cost (₹0), plus window.print() support | ✓ |
| Pure Browser Print Dialog (window.print()) | CSS print media query styling opened directly via the browser print dialog | |
| Markdown / JSON Export | Allow candidate to download raw report data as a .md or .json file | |

**User's choice:** Client-Side Multi-Page PDF Export (jsPDF + html2canvas)  
**Notes:** Zero server cost while delivering a polished, downloadable PDF report.

---

## the agent's Discretion

- Component modularity in React.
- Pure SVG/Canvas implementation for Radar Chart to avoid heavy dependencies and ensure crisp PDF rendering.

---

## Deferred Ideas

- Aggregated historical progress charts and candidate dashboards belong to Phase 8.
