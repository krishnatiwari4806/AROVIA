# AROVIA — UI/UX Design Brief & Design System Specification

**Version:** 1.1.0  
**Date:** 2026-08-16  
**Status:** Approved Design Baseline  
**Target Milestone:** 45-Day Full-Stack Implementation  

---

## Executive Summary

This document establishes the official visual identity, design tokens, layout hierarchy, responsive behavior, accessibility criteria, and screen-by-screen UX specifications for the **AROVIA** platform. 

AROVIA is engineered as a focused, high-standard mock interview and evaluation platform for software engineers. The design language emphasizes **clarity, composure, and analytical precision**, avoiding distracting decorative gimmicks, purple-on-dark clichés, or heavy 3D canvases in favor of crisp typography, structured cards, harmonious neutral depths, and intuitive audio-visual feedback loops.

---

## Table of Contents

1. [Visual Identity & Product Personality](#1-visual-identity--product-personality)
2. [Design System & Core Tokens](#2-design-system--core-tokens)
3. [Responsive Design & Breakpoints](#3-responsive-design--breakpoints)
4. [Global Layout Architecture](#4-global-layout-architecture)
5. [Screen-by-Screen UI Specification](#5-screen-by-screen-ui-specification)
6. [Live Interview Room UX Deep-Dive](#6-live-interview-room-ux-deep-dive)
7. [Evaluation & Report Card UX Deep-Dive](#7-evaluation--report-card-ux-deep-dive)
8. [Accessibility (a11y) Standards](#8-accessibility-a11y-standards)
9. [Universal UX States & Component Patterns](#9-universal-ux-states--component-patterns)
10. [Design Consistency Rules & Scope Control](#10-design-consistency-rules--scope-control)

---

## 1. Visual Identity & Product Personality

### 1.1 Product Personality
- **Composed & Professional:** Simulates a serious, authentic technical interview setting without inducing unnecessary anxiety.
- **Analytical & Transparent:** Every score, metric, and feedback item is grounded in clear criteria, visual breakdowns, and side-by-side ideal benchmarks.
- **Accessible & Low-Friction:** Audio synthesis (TTS) and voice transcription (STT) operate seamlessly in the browser with full manual text editing fallbacks.
- **Modern & Focused:** Clean contrast, generous whitespace, legible typographic hierarchy, and purposeful micro-interactions.

### 1.2 Anti-Patterns & Visual Clichés Avoided
To maintain a high-end engineering aesthetic, the following design tropes are strictly forbidden:
- **No Purple-on-Dark Neon Glows:** Uses clean neutral slate/navy depths with purposeful teal/indigo functional accents.
- **No Unreadable Gradient Text Keywords:** Headlines use solid, crisp text fills with balanced tracking.
- **No Icon-Stuffed Bento Boxes:** Cards only display icons when they communicate actionable state or clear category meaning.
- **No Heavy 3D Canvases or Laggy WebGL Backgrounds:** Prioritizes sub-second page rendering and responsive audio-visual feedback.
- **No Over-Nested Cards:** Maximum 2 levels of visual card nesting for visual clarity.

---

## 2. Design System & Core Tokens

This section defines the design tokens, values, and intended usage across the platform. The frontend implementation may organize and structure these tokens according to the final frontend architecture.

### 2.1 Color Palette Tokens (Tailored HSL)

```css
:root {
  /* Surface & Background Depths */
  --bg-app: hsl(222, 47%, 11%);          /* Deep Slate Base (#0F172A) */
  --bg-surface: hsl(217, 33%, 17%);      /* Card / Container Surface (#1E293B) */
  --bg-surface-elevated: hsl(215, 28%, 23%); /* Elevated Modals / Dropdowns */
  --bg-surface-hover: hsl(215, 25%, 27%);    /* Interactive Hover Surfaces */

  /* Border & Divider Tokens */
  --border-subtle: hsl(217, 20%, 25%);   /* Subtle Structural Dividers */
  --border-focus: hsl(217, 91%, 60%);    /* Active Input Focus Rings */

  /* Typography Colors */
  --text-primary: hsl(210, 40%, 98%);    /* Crisp White Primary Headings (#F8FAFC) */
  --text-secondary: hsl(215, 20%, 75%);  /* Readable Slate Subtext (#CBD5E1) */
  --text-muted: hsl(215, 16%, 55%);      /* Secondary Captions & Meta (#64748B) */

  /* Brand & Functional Accents */
  --accent-primary: hsl(199, 89%, 48%);  /* Tech Cyan / Teal (#0EA5E9) */
  --accent-primary-hover: hsl(199, 89%, 42%);
  --accent-secondary: hsl(226, 70%, 55%);/* Deep Indigo Focus Accent */

  /* Semantic Status Colors */
  --status-success: hsl(158, 64%, 45%);  /* Mint Emerald (#10B981) */
  --status-success-bg: hsl(160, 84%, 12%);
  --status-warning: hsl(38, 92%, 50%);   /* Amber (#F59E0B) */
  --status-warning-bg: hsl(38, 92%, 12%);
  --status-danger: hsl(0, 84%, 60%);     /* Crimson Red (#EF4444) */
  --status-danger-bg: hsl(0, 84%, 12%);
  --status-info: hsl(217, 91%, 60%);     /* Sky Blue */
  --status-info-bg: hsl(217, 91%, 12%);
}
```

### 2.2 Typography Scale
- **Primary Font Family:** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Monospace Code Family:** `'JetBrains Mono', 'Fira Code', monospace`

| Token | Size | Line Height | Weight | Tracking (Letter-Spacing) | Usage |
|---|---|---|---|---|---|
| `--text-xs` | `12px` (`0.75rem`) | `16px` | Regular (400) / Medium (500) | `+0.01em` | Metadata, badges, timestamps |
| `--text-sm` | `14px` (`0.875rem`) | `20px` | Regular (400) / Medium (500) | `0` | Form labels, secondary text |
| `--text-base` | `16px` (`1.0rem`) | `24px` | Regular (400) / Medium (500) | `-0.01em` | Standard body copy, inputs |
| `--text-lg` | `18px` (`1.125rem`) | `28px` | Medium (500) / SemiBold (600) | `-0.01em` | Card titles, subheadings |
| `--text-xl` | `20px` (`1.25rem`) | `28px` | SemiBold (600) | `-0.02em` | Section headers |
| `--text-2xl` | `24px` (`1.5rem`) | `32px` | Bold (700) | `-0.02em` | View titles, modal titles |
| `--text-3xl` | `30px` (`1.875rem`) | `36px` | Bold (700) | `-0.03em` | Major page headlines |
| `--text-4xl` | `36px` (`2.25rem`) | `44px` | ExtraBold (800) | `-0.03em` | Hero landing title |

### 2.3 Spacing & Grid System (4px Base Grid)
- `--space-1`: `4px`
- `--space-2`: `8px`
- `--space-3`: `12px`
- `--space-4`: `16px`
- `--space-5`: `20px`
- `--space-6`: `24px`
- `--space-8`: `32px`
- `--space-10`: `40px`
- `--space-12`: `48px`
- `--space-16`: `64px`

### 2.4 Border Radius & Elevation (Shadows)
- **Radii:**
  - `--radius-sm`: `6px` (Badges, tags, small controls)
  - `--radius-md`: `8px` (Inputs, buttons, dropdowns)
  - `--radius-lg`: `12px` (Cards, panels, popups)
  - `--radius-xl`: `16px` (Modals, main interview container)
  - `--radius-full`: `9999px` (Pill badges, audio pulse rings)
- **Shadows:**
  - `--shadow-sm`: `0 1px 2px rgba(0, 0, 0, 0.25)`
  - `--shadow-md`: `0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)`
  - `--shadow-lg`: `0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.25)`
  - `--shadow-focus`: `0 0 0 3px rgba(14, 165, 233, 0.35)`

### 2.5 Button & Control Styles
- **Primary Button (`.btn-primary`):** Solid `--accent-primary` background, white bold text, `--radius-md`, subtle active transform (`scale(0.98)`).
- **Secondary Button (`.btn-secondary`):** `--bg-surface-elevated` background, subtle border `--border-subtle`, hover brightness bump.
- **Ghost / Outline Button (`.btn-outline`):** Transparent background, border `--border-subtle`, `--text-primary`.
- **Danger Button (`.btn-danger`):** `--status-danger-bg` background, border `--status-danger`, white text.
- **Micro-interactions:** Hover transitions use `transition: all 150ms cubic-bezier(0.16, 1, 0.3, 1)`.

---

## 3. Responsive Design & Breakpoints

| Breakpoint | Viewport Range | Target Devices | Layout Behavior |
|---|---|---|---|
| **Mobile (`sm`)** | `< 640px` | Phones (portrait/landscape) | Single column layout, full-width buttons, collapsible hamburger navbar, sticky audio control bar at bottom. |
| **Tablet (`md`)** | `640px – 1024px` | Tablets & small laptops | 2-column dashboard grids, side-by-side question and transcription panel, standard navbar. |
| **Desktop (`lg`)** | `> 1024px` | Desktops & external monitors | Max width container (`1200px`), centered multi-column layouts, expanded radar analytics side-by-side with recommendations. |

---

## 4. Global Layout Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│ NAVBAR: Logo [AROVIA]  | Dashboard | Resume | History | [Start Mock] User ▼│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ PAGE CONTAINER (max-width: 1200px; margin: 0 auto; padding: 24px 16px)  │
│                                                                        │
│   ┌────────────────────────┐  ┌────────────────────────────────────┐  │
│   │ Left Content / Filters │  │ Main Analytical View / Live Room   │  │
│   └────────────────────────┘  └────────────────────────────────────┘  │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ FOOTER: © 2026 AROVIA · Candidate Practice · Privacy & Data Retention  │
└────────────────────────────────────────────────────────────────────────┘
```

- **Top Navigation Bar:** Sticky header with dark glass backdrop (`backdrop-filter: blur(8px)`), brand logo mark with clean typography, practice link, and candidate profile avatar menu.
- **Page Container:** Centered responsive container with standard horizontal and vertical gutters.
- **Footer:** Minimal, unobtrusive footer providing system version, privacy notes, and candidate data ownership assurance.

---

## 5. Screen-by-Screen UI Specification

### 5.1 Public Landing Page (`/`)
- **Purpose:** Informative introduction showcasing AROVIA's capabilities and inviting candidate practice.
- **Layout Hierarchy:**
  1. Sticky top navigation with "Sign In" and "Get Started" buttons.
  2. Hero Section: Catchy headline (*"Master Technical & Behavioral Interviews with Adaptive AI"*), clear value proposition, and prominent CTA (*"Start Free Mock Interview"*).
  3. Interactive Demo Visual: Sample report card preview with 5-dimension radar chart and audio waveform animation.
  4. Feature Grid (3 Columns): Real-time speech interaction, dynamic follow-up probing, and benchmark senior ideal answers.
- **Primary CTA:** `"Start Free Mock Interview"` $\rightarrow$ navigates to `/register` or `/dashboard`.
- **States:** Standard responsive render with progressive image/vector loading.

### 5.2 Registration View (`/register`)
- **Purpose:** Onboard new candidates securely.
- **Layout Hierarchy:** Centered authentication card (`max-w-md`) with AROVIA branding.
- **Components:**
  - Full Name, Email, and Password (min 12 characters) input fields.
  - Live password strength / length indicator meter.
  - Primary button: `"Create Account"`.
  - Divider: *"or continue with"*.
  - Google Sign-In button (Google Identity Services standard branding).
  - Footer link: *"Already have an account? Sign In"*.
- **Error State:** Inline alert banner displaying validation errors or duplicate email warning with quick link to login.

### 5.3 Login View (`/login`)
- **Purpose:** Authenticate returning candidates with rate-limiting feedback.
- **Components:**
  - Email and Password inputs with "Forgot Password?" anchor.
  - Primary button: `"Sign In"`.
  - Google Sign-In button.
- **Collision Flow (Google on Local Email):**
  - Displays inline notice: *"This email is already registered with email/password. Please sign in with your password first."*
  - Upon successful password login, triggers confirmation modal: *"Would you like to link your Google account to AROVIA?"* (`[Yes, Link Account]` / `[Cancel]`).
- **Error States:**
  - Generic `"Invalid email or password"` alert.
  - Rate limit/lockout alert: *"Too many attempts. Account temporarily locked for 15 minutes."*

### 5.4 Password Reset Views (`/forgot-password`, `/reset-password`)
- **Purpose:** Request reset link and update credentials.
- **Components:**
  - `/forgot-password`: Single email input with `"Send Reset Link"` CTA.
  - Development Mode Notice (when `ENVIRONMENT=development`): Notice badge explaining reset link is logged to console.
  - `/reset-password?token=...`: New password input (min 12 chars) with confirm password input and `"Update Password"` CTA.

### 5.5 Onboarding & Profile Setup (`/onboarding`)
- **Purpose:** Configure target role and seniority immediately after signup.
- **Components:**
  - Role Select Radio Cards (Frontend, Backend, Full Stack, DevOps, Data Science).
  - Seniority Level Toggle (Junior, Mid, Senior).
  - Primary CTA: `"Save & Go to Dashboard"`.

### 5.6 Candidate Dashboard (`/dashboard`)
- **Purpose:** Central command center displaying readiness metrics, practice launcher, and recent reports.
- **Components:**
  - **Welcome Banner:** Candidate name with target role badge.
  - **Quick Action Card:** Primary button `"Start Mock Interview"` (`/interview/setup`).
  - **Resume Widget:** Shows active uploaded resume name and parsed skills, or `"Upload Resume"` CTA.
  - **Score Progression Chart:** Multi-session historical trendline rendered with Chart.js.
  - **Recent Interviews Table:** Last 5 sessions with role, date, score badge, and `"View Report"` link.
- **Empty State:** Illustrated 3-step walkthrough card for first-time candidates.

### 5.7 Resume Management (`/resume`)
- **Purpose:** Ingest candidate resumes, inspect extracted skills, and manage retention.
- **Components:**
  - Drag-and-drop file upload zone supporting `.pdf` and `.docx` (max 5 MB).
  - Upload progress bar with animated parsing indicator.
  - **Parsed Competencies Panel:** Extracted skills displayed as removable/editable interactive tags.
  - **Data Retention & Privacy Controls:** Prominent `"Delete Resume"` danger button triggering confirmation modal.
- **Error State:** Rejection banner for invalid magic bytes, password-protected files, or files > 5 MB.

### 5.8 Interview Setup (`/interview/setup`)
- **Purpose:** Calibrate interview parameters before starting.
- **Components:**
  - Role Selector dropdown.
  - Seniority Level segment control (`Junior`, `Mid`, `Senior`).
  - Focus Area segment control (`Technical Core`, `System Design`, `Behavioral`).
  - Custom Job Description textarea (optional).
  - Toggle: *"Incorporate uploaded resume context"*.
  - Structure summary card: *"6 Planned Core Questions · Max 9 Turns · ~15 Minutes"*.
  - Primary CTA: `"Start Interview"`.

### 5.9 Evaluation Processing View (`/interview/evaluating/:sessionId`)
- **Purpose:** Informative, variable asynchronous processing state while the backend executes the evaluation pipeline.
- **Components:**
  - Centered glowing geometric radar scanner graphic.
  - Dynamic status notice: *"Evaluation is being processed..."*
  - Current processing stage when available (e.g. *"Analyzing Technical Accuracy & Key Concepts..."*, *"Synthesizing Benchmark Ideal Answers..."*).
  - Rotating carousel of interview performance tips to keep the candidate engaged.
- **State Transition:** Automatically redirects to `/reports/:sessionId` as soon as the backend reports `status='completed'`.
- **Error State:** Displays clear card: *"Evaluation encountered an issue. Click below to retry scoring."* with a `"Retry Evaluation"` button.

---

## 6. Live Interview Room UX Deep-Dive

The live interview room (`/interview/live/:sessionId`) is the core interactive space. It is designed to be calm, distraction-free, and accessible.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Question 2 of 6 (Core)                           [Finish Early]  02:45 │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ AI QUESTION CARD                                                 │  │
│  │ "Explain how PostgreSQL handles MVCC and what happens during     │  │
│  │ a concurrent row update."                                        │  │
│  │                                                                  │  │
│  │ [ ▶ Play Audio ]  [ ⏸ Pause ]  [ ↺ Replay ]    Voice: Natural English│  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ CANDIDATE RESPONSE BOX                                           │  │
│  │                                                                  │  │
│  │ [ 🎙 Start Speaking ]  ● Listening... (Waveform Pulse)            │  │
│  │                                                                  │  │
│  │ Textarea: Real-time STT transcription stream...                  │  │
│  │ [Candidate can edit or format text freely]                       │  │
│  │                                                                  │  │
│  │ Words: 84 | Characters: 520             [ Submit Response → ]   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Question Presentation & Audio Bar
- **Question Card:** Elevated surface with `--text-2xl` readable font, high contrast, and clean line spacing.
- **Turn Badge:**
  - Core Questions: Teal pill badge: `Question 2 of 6 (Core)`.
  - Dynamic Follow-Ups: Amber pill badge: `Follow-Up on Question 2`.
- **Text-to-Speech (TTS) Controls:**
  - Auto-reads question aloud upon turn load.
  - Audio control buttons (`Play`, `Pause`, `Replay`) with volume slider and natural voice selector.

### 6.2 Microphone & STT Transcription Area
- **Microphone Action Button:** Prominent circular recording button with pulsating emerald ring when actively listening.
- **Waveform Animation:** CSS-based 5-bar responsive volume visualizer.
- **Transcript Textarea:** Real-time Web Speech STT streaming into editable textarea.
- **Manual Edit Guarantee:** Candidate can pause recording at any time to type, edit typos, or reorganize thoughts before submitting.
- **Fallback Banner (Unsupported Browser):** Displays informational banner: *"Web Speech API unavailable in this browser — text input mode active"*.

### 6.3 Submission & Turn Progression
- **Primary CTA:** `"Submit Response"` with turn transition loader.
- **Dynamic Follow-Up Notification:** If follow-up is triggered, question card smoothly updates with an amber indicator: *"Let's drill down deeper on that concept..."*
- **Finish Early Action:** Secondary button in top header (*"Finish & Submit Early"*), enabled after at least 3 questions are answered.

---

## 7. Evaluation & Report Card UX Deep-Dive

### 7.1 Asynchronous Evaluation Processing
- **Variable Processing State:** Represents an asynchronous processing pipeline without assuming or promising a fixed evaluation duration.
- **Progress Engagement:** Renders current stage feedback (`"Aggregating interview turns..."`, `"Evaluating multi-dimensional criteria..."`, `"Synthesizing benchmark ideal answers..."`) and rotating coaching tips.
- **Automatic Transition:** Navigates automatically to the completed report as soon as the background task finishes.

### 7.2 Final Report Card Layout (`/reports/:sessionId`)

```
┌────────────────────────────────────────────────────────────────────────┐
│ REPORT CARD: Full Stack Developer (Senior) · Completed Aug 16, 2026    │
│ Overall Score: [ 86 / 100 ]  Tier: Exceptional Readiness   [Download PDF]│
├──────────────────────────────────┬─────────────────────────────────────┤
│ 5-DIMENSION COMPETENCY RADAR     │ KEY STRENGTHS & IMPROVEMENTS        │
│                                  │                                     │
│  - Relevance (20%):     90/100   │ ✓ Excellent architectural depth     │
│  - Correctness (30%):   88/100   │ ✓ Covered database indexing trade-offs│
│  - Key Concepts (20%):  85/100   │                                     │
│  - Clarity/Grammar(15%):82/100   │ ⚠ Omitted cache invalidation logic  │
│  - Delivery (15%):      85/100   │ ⚠ Clarify edge-case error codes     │
├──────────────────────────────────┴─────────────────────────────────────┤
│ ACTIONABLE STUDY RECOMMENDATIONS                                       │
│ 1. Study PostgreSQL MVCC VACUUM internals                              │
│ 2. Practice structured STAR method for distributed design trade-offs    │
├────────────────────────────────────────────────────────────────────────┤
│ TURN-BY-TURN DETAILED BREAKDOWN (6 Core + 1 Follow-up)                 │
│ ▼ Turn 1: PostgreSQL MVCC & Concurrent Writes                          │
│   Candidate Answer: "PostgreSQL uses row versioning..."                │
│   Key Concepts Covered: [MVCC] [xmin/xmax]  Missed: [HOT optimization] │
│   ★ Benchmark Senior Ideal Answer: "PostgreSQL implements MVCC by..."   │
│   Coaching Tip: "Mention heap-only tuples (HOT) to elevate response."  │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Visual Analytics & Ideal Benchmark Display
- **Competency Radar Chart:** Built with Chart.js, rendering all 5 evaluation dimensions on a polygon grid with cyan accent fill.
- **Dimension 5 Reframe:** Labelled **"Communication & Delivery Indicators"** with helper tooltip: *"Observable verbal indicators including answer completeness, structure, and pacing. (Interview performance metric; not a psychological diagnosis.)"*
- **Benchmark Ideal Answers:** Expandable turn accordions with side-by-side comparison of candidate text vs. AI-synthesized senior model answer.
- **Client-Side PDF Generation:** `"Download PDF Report"` button triggers `html2canvas` + `jsPDF` compiling an optimized, multi-page downloadable PDF.

---

## 8. Accessibility (a11y) Standards

AROVIA is designed to target **WCAG 2.1 Level AA** accessibility standards:

1. **Color Contrast Verification:**
   - Text, interactive controls, icons, borders, and focus indicators must meet the applicable WCAG 2.1 AA contrast requirements (minimum 4.5:1 for normal body text, 3:1 for large text/headings, and 3:1 for active UI components and graphical objects).
   - Exact contrast ratios must be verified and validated against the final rendered UI during frontend implementation and accessibility auditing.
2. **Keyboard Navigation & Visible Focus:**
   - All interactive elements (buttons, inputs, audio controls, accordion headers) are accessible via `Tab` and `Shift+Tab`.
   - Global high-contrast focus indicator: `outline: 2px solid var(--accent-primary); outline-offset: 2px;`.
3. **Screen Reader Support (ARIA):**
   - Live Speech updates and turn status use `aria-live="polite"`.
   - Audio recording button includes `aria-pressed="true/false"` and descriptive `aria-label="Start recording speech"`.
   - Expandable turn accordions use `aria-expanded` and `aria-controls`.
4. **Non-Color Reliance:**
   - Error fields combine red borders with explicit exclamation icons (`AlertCircle`) and descriptive helper text.
   - Question types combine color badges with textual labels (*"Core Question"* vs *"Follow-Up"*).

---

## 9. Universal UX States & Component Patterns

### 9.1 Loading States
- **Skeleton Shimmers:** Replaces raw loading spinners on dashboard cards, report analytics, and table rows with CSS linear-gradient pulse animations.
- **Button Loading:** Replaces button text with a centered SVG spinner while preserving button width and setting `disabled=true`.

### 9.2 Empty States
- **Standard Layout:** Centered container with clean SVG illustration, clear headline (*"No Completed Interviews Yet"*), descriptive subtext, and a single prominent primary CTA button (*"Launch Mock Interview"*).

### 9.3 Error & Validation Feedback
- **Form Errors:** Stacked directly below the relevant input field in `--text-sm` font with `--status-danger` coloring.
- **Global API Errors:** Auto-dismissing toast notifications or inline card alerts featuring retry buttons for network interruptions.
- **Unauthorized / Session Expired:** Modal dialog alerting the candidate that their session has expired with a 1-click `"Sign In Again"` button that preserves their current route.

---

## 10. Design Consistency Rules & Scope Control

### 10.1 Reusable Component Architecture
To ensure UI uniformity across all views, all React components consume predefined class names and shared tokens:
- **Card Container:** `.arovia-card` (standard background, `--border-subtle`, `--radius-lg`, padding `--space-6`).
- **Input Field:** `.arovia-input` (standard height `44px`, background `--bg-surface`, `--radius-md`).
- **Badge:** `.arovia-badge` (standard height `24px`, `--radius-full`, `--text-xs`, font-weight 500).

### 10.2 MVP Scope Guardrails
- **No Complex Animation Frameworks:** Uses native lightweight CSS transitions ($\le 200\text{ms}$).
- **No Heavy Vector Libraries:** Leverages standard Lucide React icons.
- **No WebGL / 3D Canvas Code:** Guarantees instant load times and zero interference with browser audio streaming.

---

*AROVIA UI/UX Design Brief — Approved Design Baseline for Frontend Implementation.*
