# Phase 04: Interview Setup & Role Configuration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.  
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17  
**Phase:** 04-interview-setup-role-configuration  
**Areas discussed:** Role Presets & Custom Roles, Job Description (JD) Parsing & Context Integration, Session Calibration & Turn Pacing, Session Concurrency & Lifecycle Rules  

---

## Role Presets & Custom Role Input

| Option | Description | Selected |
|--------|-------------|----------|
| Curated presets with editable baseline skills | Offer top presets (Backend, Frontend, Fullstack, DevOps, Data/ML, Mobile) with default focus skills that auto-populate and can be adjusted, plus custom freeform role support | ✓ |
| Static presets with AI dynamic inference | Offer preset roles with fixed names, and let the AI automatically infer key skills and evaluation criteria from the role name, seniority, and resume without manual skill tags | |
| Purely freeform role selection | Candidate types or selects any title with custom focus areas only | |

**User's choice:** Curated presets with editable baseline skills  
**Notes:** Provides quick standard setup while leaving room for candidate adjustments and custom titles.

---

## Job Description (JD) Parsing & Context Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Store sanitized raw JD and extract structured requirements on setup | Validate max 10,000 chars, parse key requirements into structured metadata, and prioritize JD for target criteria while using resume for personalized probing | ✓ |
| Store raw sanitized JD only without pre-parsing | Validate max 10,000 chars and pass the raw text directly to the Phase 5 Gemini prompt chain without intermediate setup extraction | |
| Strict requirement match filter | Reject JD if it does not contain standard technical sections | |

**User's choice:** Store sanitized raw JD and extract structured requirements (skills/responsibilities) on setup  
**Notes:** 10,000 char limit, control characters stripped, structured extraction of skills/responsibilities for prompt tailoring.

---

## Session Calibration & Turn Pacing

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable practice modes with focus-specific time pacing guidance | Full 6-core/9-turn default vs Quick 3-core/5-turn practice with recommended response times (120s for Technical/Behavioral, 180s for System Design) | ✓ |
| Fixed standard format only | 6 core questions, max 9 turns with uniform 2-minute answer timer | |
| Fully custom question count | Candidate enters any integer between 3 and 10 questions | |

**User's choice:** Configurable practice modes (Full 6-core/9-turn default vs Quick 3-core/5-turn practice) with focus-specific time pacing guidance  
**Notes:** Provides flexibility between quick practice sessions and comprehensive full interviews.

---

## Session Concurrency & Lifecycle Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Single active session with resume/abandon choice | If an unfinished session exists, return its active status with endpoints to resume or explicitly abandon it before starting a new one | ✓ |
| Automatic prior abandonment on new setup | Automatically mark any prior in-progress session as 'abandoned' when a new session is created | |
| Unrestricted concurrent sessions | Allow candidates to create and run multiple simultaneous mock interviews concurrently | |

**User's choice:** Single active session with resume/abandon choice  
**Notes:** Prevents accidental session fragmentation and ensures candidate consciously closes or completes in-flight interviews.

---

## the agent's Discretion

- ORM models and schema types for `interview_sessions` strictly adhering to `docs/BACKEND_SCHEMA.md` §2.6 and §2.7.
- Default skill tag lists for role presets.

---

## Deferred Ideas

- Live speech synthesis and question prompt chaining are scheduled for Phase 5.
