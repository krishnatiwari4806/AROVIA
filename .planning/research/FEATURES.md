# Feature Research

**Domain:** AI-Powered Interview Evaluation System (Web Application)
**Researched:** 2026-08-15
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features candidates and evaluators assume exist. Missing these = product feels incomplete or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **User Auth & Profiles** | Secure access, personalized history, session recovery | LOW | Registration, JWT login, profile editing, password change |
| **Resume Upload & Parsing** | Foundation for personalized questions and domain context | MEDIUM | PDF/DOCX upload, text extraction, skill & experience extraction |
| **Role & Job Description Setup** | Contextualizing the interview for target role/seniority | LOW | Preset roles (Frontend, Backend, Full Stack, Data Science, etc.) + custom job descriptions |
| **Question-by-Question Interview Flow** | Natural interview progression with clear pacing | MEDIUM | Clear question prompt, timer/duration indicator, audio playback |
| **Speech-to-Text & Text-to-Speech** | Simulates conversational speaking dynamic | MEDIUM | Web Speech API integration with real-time transcript visualization and edit fallback |
| **Multi-Dimensional Scoring** | Objective assessment beyond a single arbitrary score | HIGH | Dimensions: Relevance, Correctness, Keywords/Concepts, Clarity/Grammar, Sentiment/Confidence |
| **Final Evaluation Report** | Core takeaway of the mock interview session | MEDIUM | Overall score, dimensional breakdown, strengths, weaknesses, actionable recommendations |
| **Session History Dashboard** | Track personal growth across multiple practice attempts | LOW | List of previous interview attempts, score progression, past reports |

### Differentiators (Competitive Advantage)

Features that set AROVIA apart and deliver standout portfolio/academic value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Adaptive Follow-Up Probing** | AI dynamically digs deeper if an answer is vague or misses a crucial nuance | HIGH | Evaluates answer in flight and dynamically decides between asking a targeted follow-up or advancing |
| **Resume vs. Answer Consistency Cross-Check** | Detects if candidate answers contradict claims on their uploaded resume | HIGH | Contextual prompt chaining cross-referencing candidate claimed projects and tools |
| **Question-by-Question Deep Dive with Ideal Answers** | Immediate learning loop showing what an exemplary answer would look like | MEDIUM | Generates tailored ideal sample response and key missed points for each question |
| **Visual Radar & Competency Matrix Charts** | High-impact visual analytics for instant cognitive assessment | LOW | Radar charts showing dimensional balance + bar charts for topical mastery |
| **Exportable PDF Report Card** | Tangible artifact candidate can save, share, or review offline | MEDIUM | Client-side styled PDF generation matching the UI report card format |
| **Defensive Security & Rate Limiting** | Enterprise-grade safety against injection, abuse, and invalid inputs | MEDIUM | Strict Pydantic schemas, file content type verification, rate limits on LLM generation |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good on the surface but introduce high failure rates, privacy issues, or unnecessary complexity for v1.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time webcam computer vision / facial emotion detection** | Looks flashy in demos | Inaccurate, unreliable across lighting/hardware, high compute cost, pseudoscience risk | Focus on linguistic, semantic, and vocal confidence indicators |
| **Full live human peer-to-peer video streaming (WebRTC)** | Mimics Zoom/Meet | Massive server bandwidth and TURN/STUN infrastructure overhead | Direct browser-to-backend AI speech interaction |
| **Unbounded open-ended multi-hour interviews** | Feels realistic | Leads to candidate fatigue, massive LLM token costs, and context window drift | Structured 5–8 question focused sessions with dynamic follow-ups |
| **Paid subscriptions / payment gateway integrations** | Monetization | Unnecessary complexity for a college major project / portfolio showcase | Clean open access with local user accounts and rate limits |

## Feature Dependencies

```
[User Authentication]
     └──requires──> [Database & Schema Init]

[Resume Upload & Parsing]
     └──requires──> [User Authentication]
     └──requires──> [Secure File Storage]

[Interview Session Initialization]
     └──requires──> [Resume Analysis OR Target Role Selection]
     └──requires──> [Gemini API Orchestrator]

[Live Interactive Interview Room]
     └──requires──> [Interview Session Initialization]
     └──requires──> [Speech-to-Text / Web Speech API]
     └──requires──> [Adaptive Question Engine]

[Evaluation & Report Generation]
     └──requires──> [Live Interactive Interview Room]
     └──requires──> [Multi-Dimensional Scoring Pipeline]

[Analytics Dashboard & History]
     └──requires──> [Evaluation & Report Generation]
```

### Dependency Notes

- **Resume Upload requires Secure File Storage:** File uploads must be validated, scanned, and saved before background parsing runs.
- **Adaptive Question Engine requires Gemini API Orchestrator:** Prompt chaining passes previous turns to evaluate if follow-up probing is warranted.
- **Evaluation requires complete session transcripts:** Scores are calculated per question and aggregated into the final report.

## MVP Definition

### Launch With (v1 - Core Roadmap)

Minimum viable product — what is required to achieve complete functionality.

- [ ] Secure User Authentication & Profile Dashboard (JWT + bcrypt + PostgreSQL)
- [ ] Resume Upload & Parser (`pdfplumber` + Gemini structured skill/experience extraction)
- [ ] Target Job Role & Experience Level Configurator
- [ ] Adaptive Interview Session Orchestrator with Gemini prompt chaining
- [ ] Audio-enabled Interactive Interview Room (Web Speech API TTS/STT with text fallback)
- [ ] Multi-Dimensional Evaluation Engine (Relevance, Correctness, Keywords, Clarity, Sentiment)
- [ ] Detailed Report View with Radar Charts, Strengths, Weaknesses & Ideal Answers
- [ ] PDF Report Export & Session History Archive

### Add After Validation (v1.x)

Features to add once core is stable and verified.

- [ ] Code Editor widget for live coding questions (e.g. Monaco Editor embedded in interview)
- [ ] Custom Rubric builder for customized evaluation weights
- [ ] Company-specific interview presets (e.g., FAANG style, Startup style)

### Future Consideration (v2+)

- [ ] Multi-user Recruiter portal with candidate ranking and batch invites
- [ ] Video analysis for posture and eye contact

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| User Auth & Profile Management | HIGH | LOW | P1 |
| Resume Ingestion & Extraction | HIGH | MEDIUM | P1 |
| Target Role Configuration | HIGH | LOW | P1 |
| Adaptive AI Interview Engine | HIGH | HIGH | P1 |
| Audio/Speech Interface (STT/TTS) | HIGH | MEDIUM | P1 |
| Multi-Dimensional Evaluation Engine | HIGH | HIGH | P1 |
| Post-Interview Analytics & Report | HIGH | MEDIUM | P1 |
| Downloadable PDF Report Card | MEDIUM | LOW | P1 |
| Interview History & Trend Graphs | MEDIUM | LOW | P1 |
| Embedded Coding Sandbox | MEDIUM | HIGH | P2 |

---
*Feature research for: AROVIA (AI-Powered Interview Evaluation System)*
*Researched: 2026-08-15*
