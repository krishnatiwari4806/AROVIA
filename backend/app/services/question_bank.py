"""AROVIA Structured Question Bank and Competency Progression Architecture.

Provides role-specific, seniority-calibrated competency stages, core question archetypes,
follow-up probing patterns, and deterministic fallbacks for the interview engine.
"""

from dataclasses import dataclass, field
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FollowUpTemplate:
    """Targeted follow-up probing question archetype linked to a competency."""

    id: str
    prompt: str
    target_probe: str
    ideal_focus: str


@dataclass(frozen=True)
class QuestionTemplate:
    """Core question archetype with benchmark ideal answer and primary evaluated concept."""

    id: str
    question_text: str
    ideal_answer: str
    primary_concept: str
    stage_name: str
    difficulty: str  # "foundational", "intermediate", "advanced"
    follow_ups: List[FollowUpTemplate] = field(default_factory=list)


@dataclass(frozen=True)
class CompetencyStage:
    """A progressive competency evaluation stage for an interview role."""

    stage_index: int
    stage_name: str
    competency_title: str
    description: str
    core_questions: List[QuestionTemplate]


# ---------------------------------------------------------------------------
# GLOBAL UNIVERSAL PROBING ARCHETYPES (When concept-specific probe is unavailable)
# ---------------------------------------------------------------------------
UNIVERSAL_FOLLOWUPS: List[FollowUpTemplate] = [
    FollowUpTemplate(
        id="univ.probe.tradeoff.01",
        prompt="What specific technical trade-offs did you consider with that approach, and what was the main drawback?",
        target_probe="Technical trade-offs and decision justification",
        ideal_focus="Clear articulation of pros vs cons and rationale for the chosen pattern.",
    ),
    FollowUpTemplate(
        id="univ.probe.failure.02",
        prompt="How does that solution handle unexpected edge cases or downstream component failures in production?",
        target_probe="Failure resilience and graceful degradation",
        ideal_focus="Discussion of timeouts, error boundaries, retries, and data protection.",
    ),
    FollowUpTemplate(
        id="univ.probe.scaling.03",
        prompt="If the traffic volume or data throughput increased by 100x, where would the first bottleneck emerge in your design?",
        target_probe="Scalability bottlenecks and resource limits",
        ideal_focus="Identification of CPU/memory/DB connection/network limits and horizontal scaling options.",
    ),
    FollowUpTemplate(
        id="univ.probe.validation.04",
        prompt="How would you test and validate that implementation to guarantee zero regression before shipping?",
        target_probe="Automated testing and observability",
        ideal_focus="Unit, integration, end-to-end testing strategies and production metrics.",
    ),
]


# ---------------------------------------------------------------------------
# 1. BACKEND ENGINEER QUESTION BANK
# ---------------------------------------------------------------------------
BACKEND_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: API & Protocol Fundamentals",
            competency_title="HTTP & REST API Design",
            description="Foundations of RESTful APIs, HTTP verbs, status codes, and payload validation.",
            core_questions=[
                QuestionTemplate(
                    id="be.jr.api.core.01",
                    question_text="Could you explain the difference between PUT and PATCH HTTP methods, and when you would choose one over the other in a RESTful API?",
                    ideal_answer="PUT replaces the entire resource representation idempotently, while PATCH applies partial updates to specific fields.",
                    primary_concept="HTTP Semantics & Idempotency",
                    stage_name="API Fundamentals",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.jr.api.probe.01",
                            prompt="How do you ensure a PATCH request handles validation for missing or null fields properly?",
                            target_probe="Partial payload schema validation",
                            ideal_focus="Using schema validators (like Pydantic/Joi) with optional fields and exclude_unset.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Database Operations & CRUD",
            competency_title="Relational Queries & Transactions",
            description="Writing reliable queries, handling database connections, and managing basic transactions.",
            core_questions=[
                QuestionTemplate(
                    id="be.jr.db.core.01",
                    question_text="How do database transactions work, and why is the concept of ACID important when saving related records across multiple tables?",
                    ideal_answer="ACID ensures Atomicity (all-or-nothing), Consistency, Isolation, and Durability, preventing corrupted state during partial failures.",
                    primary_concept="Database Transactions & ACID",
                    stage_name="Database Operations",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.jr.db.probe.01",
                            prompt="What happens to the database if an unhandled exception occurs in the middle of a transaction?",
                            target_probe="Transaction rollback handling",
                            ideal_focus="Rollback cleans up pending uncommitted writes, returning the database to its prior consistent state.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=2,
            stage_name="Stage 3: Error Handling & Middleware",
            competency_title="Exception Management & Validation",
            description="Centralized error handling, input sanitization, and structured HTTP error responses.",
            core_questions=[
                QuestionTemplate(
                    id="be.jr.err.core.01",
                    question_text="How do you handle unhandled exceptions in a backend server so that clients receive clean JSON error responses instead of crashing or leaking stack traces?",
                    ideal_answer="Using centralized exception middleware and global error handlers to catch unexpected exceptions and return uniform JSON payloads with appropriate HTTP status codes.",
                    primary_concept="Centralized Exception Handling",
                    stage_name="Error Handling",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.jr.err.probe.01",
                            prompt="Why is it dangerous to return raw internal exception messages or tracebacks to public clients?",
                            target_probe="Information leakage and security",
                            ideal_focus="Raw stack traces leak internal paths, database table names, and library versions to attackers.",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Modular Architecture & Service Layer",
            competency_title="Clean Architecture & Dependency Injection",
            description="Decoupling routing, business logic, data access, and external services.",
            core_questions=[
                QuestionTemplate(
                    id="be.mid.arch.core.01",
                    question_text="How do you structure a backend application into distinct layers (controllers, services, repositories) to keep business logic isolated and testable?",
                    ideal_answer="Controllers handle HTTP transport and validation, Service layer orchestrates pure business rules and domain logic, and Repository/ORM layer handles database persistence.",
                    primary_concept="Layered Architecture & Separation of Concerns",
                    stage_name="Modular Architecture",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.mid.arch.probe.01",
                            prompt="How does using Dependency Injection help when writing unit tests for your service layer?",
                            target_probe="Testability through dependency mocking",
                            ideal_focus="Allows passing mock database sessions or test clients without spinning up real databases or external APIs.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Asynchronous Concurrency & Background Processing",
            competency_title="Async IO & Task Queues",
            description="Handling non-blocking I/O, event loops, and offloading heavy tasks to asynchronous workers.",
            core_questions=[
                QuestionTemplate(
                    id="be.mid.async.core.01",
                    question_text="How does the asynchronous event loop work in Python or Node.js, and what happens when a synchronous blocking call is executed inside an async handler?",
                    ideal_answer="Async event loop executes tasks concurrently on a single thread by suspending on I/O. A synchronous blocking call blocks the entire event loop, freezing all concurrent requests.",
                    primary_concept="Asynchronous Event Loop & Concurrency",
                    stage_name="Async Processing",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.mid.async.probe.01",
                            prompt="How would you safely execute a CPU-bound computation or synchronous file parsing task without blocking the ASGI event loop?",
                            target_probe="Thread pool offloading and worker queues",
                            ideal_focus="Using asyncio.to_thread / run_in_executor or background Celery/Redis worker queues.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=2,
            stage_name="Stage 3: Relational Modeling & Indexing",
            competency_title="Database Index Internals & Query Optimization",
            description="B-tree index mechanics, composite indexing, and eliminating N+1 query bottlenecks.",
            core_questions=[
                QuestionTemplate(
                    id="be.mid.db.core.01",
                    question_text="How do B-tree indexes speed up SQL lookups, and what causes the N+1 query problem when querying relational models with an ORM?",
                    ideal_answer="B-trees allow O(log N) lookups by sorting index keys. N+1 queries occur when an ORM issues 1 query for parent records and N separate queries for child relationships instead of eager loading with joins/selectinload.",
                    primary_concept="Database Indexing & N+1 Prevention",
                    stage_name="Database Modeling",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.mid.db.probe.01",
                            prompt="What are the trade-offs of adding too many indexes to a high-write database table?",
                            target_probe="Write amplification and index maintenance overhead",
                            ideal_focus="Every insert/update/delete requires updating index B-trees and increases storage overhead.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=3,
            stage_name="Stage 4: Caching & Query Optimization",
            competency_title="Cache Strategies & Redis Invalidation",
            description="Cache-aside patterns, TTL jitter, and mitigating cache invalidation issues.",
            core_questions=[
                QuestionTemplate(
                    id="be.mid.cache.core.01",
                    question_text="Walk me through how you implement the Cache-Aside pattern with Redis, and how you manage cache invalidation when underlying records are updated.",
                    ideal_answer="App checks cache on read; on cache miss, reads from DB and populates cache with a TTL. On write, update DB and delete/evict cache key to prevent stale reads.",
                    primary_concept="Cache-Aside Pattern & Invalidation",
                    stage_name="Caching & Optimization",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.mid.cache.probe.01",
                            prompt="What is a cache stampede, and how do you prevent thousands of concurrent requests from overwhelming your database when a popular key expires?",
                            target_probe="Cache stampede mitigation",
                            ideal_focus="Using distributed mutex locks, probabilistic early expiration (XFetch), or background cache warmers.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=4,
            stage_name="Stage 5: Reliability & Resiliency Patterns",
            competency_title="Rate Limiting, Retries & Circuit Breakers",
            description="Protecting backend systems from cascading failures and traffic surges.",
            core_questions=[
                QuestionTemplate(
                    id="be.mid.resil.core.01",
                    question_text="How would you design a retry strategy for calling a flaky third-party external API to ensure transient errors don't cause widespread system downtime?",
                    ideal_answer="Use exponential backoff with randomized jitter, set strict HTTP request timeouts, limit maximum retry attempts, and wrap with a circuit breaker to fail fast if the provider is down.",
                    primary_concept="Exponential Backoff & Circuit Breakers",
                    stage_name="Resiliency Patterns",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.mid.resil.probe.01",
                            prompt="Why is adding random jitter essential when multiple servers retry requests simultaneously?",
                            target_probe="Thundering herd prevention",
                            ideal_focus="Jitter desynchronizes retry waves, preventing pulsed traffic spikes from knocking the recovering service offline.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Distributed Architecture & Domain Boundaries",
            competency_title="System Decomposition & Boundary Design",
            description="Decomposing complex monoliths into resilient event-driven microservices.",
            core_questions=[
                QuestionTemplate(
                    id="be.sr.arch.core.01",
                    question_text="When migrating a monolithic backend to microservices, how do you define service domain boundaries and handle distributed transactions without introducing tight synchronous coupling?",
                    ideal_answer="Use Domain-Driven Design (bounded contexts), adopt event-driven choreography/orchestration via message brokers, and implement the Saga pattern for eventual consistency instead of distributed 2PC locks.",
                    primary_concept="Domain Decomposition & Saga Pattern",
                    stage_name="Distributed Architecture",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.sr.arch.probe.01",
                            prompt="How do you handle compensating transactions in a Saga if the 4th step in a 5-step workflow fails?",
                            target_probe="Saga compensation and rollback orchestration",
                            ideal_focus="Execute compensating reverse events in reverse order to semantically undo committed changes.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Event Streaming & Message Processing",
            competency_title="Idempotency & Outbox Pattern",
            description="Publishing reliable events and processing distributed message streams with at-least-once delivery.",
            core_questions=[
                QuestionTemplate(
                    id="be.sr.event.core.01",
                    question_text="How does the Transactional Outbox pattern solve the dual-write problem between an SQL database and a message broker like Kafka or RabbitMQ?",
                    ideal_answer="Persist the entity and event message in the same local DB transaction (Outbox table). A separate background CDC process/poller reads the Outbox table and publishes to Kafka with at-least-once guarantees.",
                    primary_concept="Transactional Outbox Pattern & Dual Writes",
                    stage_name="Event Streaming",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.sr.event.probe.01",
                            prompt="Since Kafka provides at-least-once delivery, how do downstream consumers guarantee idempotency against duplicate message deliveries?",
                            target_probe="Consumer idempotency keys and deduplication",
                            ideal_focus="Store processed message IDs with unique DB constraints or Redis deduplication keys within the processing transaction.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=2,
            stage_name="Stage 3: Distributed Data Consistency & Sharding",
            competency_title="Data Partitioning & Replication Topologies",
            description="Horizontal database sharding, replication lag, and partition keys.",
            core_questions=[
                QuestionTemplate(
                    id="be.sr.data.core.01",
                    question_text="How do you choose a partition key when horizontally sharding an SQL database, and how do you handle cross-shard queries and replication lag in read-replicas?",
                    ideal_answer="Choose high-cardinality partition keys that distribute traffic evenly (e.g., tenant_id/user_id). Minimize cross-shard joins by co-locating related tables; route critical read-after-write requests to primary while handling replica lag with session tokens.",
                    primary_concept="Database Sharding & Replication Topologies",
                    stage_name="Distributed Data",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.sr.data.probe.01",
                            prompt="What occurs when a hotspot develops on a specific shard, and how do you rebalance shard partitions dynamically?",
                            target_probe="Hotspot mitigation and consistent hashing",
                            ideal_focus="Use consistent hashing with virtual nodes and re-shard hot partition ranges.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=3,
            stage_name="Stage 4: High-Throughput Performance & Tail Latencies",
            competency_title="p99 Latency Tuning & Lock Contention",
            description="Optimizing p99 latencies, connection pooling, and eliminating DB lock contention.",
            core_questions=[
                QuestionTemplate(
                    id="be.sr.perf.core.01",
                    question_text="In a system processing 50,000 requests/sec, your p50 latency is 15ms but p99 spikes to 1200ms. How would you systematically diagnose and resolve the root cause of tail latency?",
                    ideal_answer="Trace distributed spans via OpenTelemetry to isolate the bottleneck (DB lock contention, garbage collection pauses, connection pool exhaustion, slow I/O, or cache misses). Tune connection pool sizing, index hot queries, and decouple synchronous calls.",
                    primary_concept="Tail Latency (p99) Optimization & Diagnostics",
                    stage_name="High-Throughput Performance",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.sr.perf.probe.01",
                            prompt="How does database connection pool starvation cause non-linear latency spikes during sudden traffic surges?",
                            target_probe="Connection pool saturation and queue buildup",
                            ideal_focus="When all pool connections are occupied, incoming requests queue up waiting for an open connection, causing exponential wait times.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=4,
            stage_name="Stage 5: High Availability & Disaster Recovery",
            competency_title="Multi-Region Failover & Cascading Failure Prevention",
            description="Designing active-active multi-region architectures, mitigating split-brain, and load shedding.",
            core_questions=[
                QuestionTemplate(
                    id="be.sr.ha.core.01",
                    question_text="How do you design an active-active multi-region backend service to prevent data corruption during regional network partitions (split-brain scenarios)?",
                    ideal_answer="Use consensus algorithms (Raft/Paxos) for quorum writes, conflict-free replicated data types (CRDTs) or strict deterministic timestamp ordering (LWW) where applicable, and health-checked DNS/BGP routing with automated load shedding.",
                    primary_concept="Active-Active Failover & Split-Brain Mitigation",
                    stage_name="High Availability",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="be.sr.ha.probe.01",
                            prompt="What is load shedding, and how does it differ from standard rate limiting during severe backend degradation?",
                            target_probe="Adaptive load shedding vs rate limiting",
                            ideal_focus="Rate limiting drops requests based on caller quotas; load shedding dynamically drops low-priority requests based on internal CPU/latency saturation to preserve core server health.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 2. FRONTEND ENGINEER QUESTION BANK
# ---------------------------------------------------------------------------
FRONTEND_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: DOM & JavaScript Core",
            competency_title="Event Bubbling & Closures",
            description="JavaScript language fundamentals, event delegation, and DOM interactions.",
            core_questions=[
                QuestionTemplate(
                    id="fe.jr.dom.core.01",
                    question_text="Could you explain how event bubbling works in the DOM and how event delegation allows handling events efficiently on dynamically created lists?",
                    ideal_answer="Events propagate from the target element up through its parent hierarchy. Event delegation attaches a single listener on a parent container to catch events from all child elements using event.target.",
                    primary_concept="Event Bubbling & Event Delegation",
                    stage_name="DOM Fundamentals",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.jr.dom.probe.01",
                            prompt="What is the difference between event.stopPropagation() and event.preventDefault()?",
                            target_probe="Event control flow",
                            ideal_focus="stopPropagation stops bubbling up the DOM; preventDefault cancels the browser default action.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: React State & Lifecycle",
            competency_title="Hooks & Re-render Lifecycle",
            description="Managing local state with useState, useEffect dependency arrays, and avoiding unnecessary renders.",
            core_questions=[
                QuestionTemplate(
                    id="fe.jr.state.core.01",
                    question_text="How does the useEffect dependency array work in React, and what happens if you forget to include a state variable that is referenced inside the effect?",
                    ideal_answer="The dependency array tells React when to re-execute the effect. Omitting dependencies creates stale closures where the effect captures outdated variable values across renders.",
                    primary_concept="React Hooks & Stale Closures",
                    stage_name="React State & Lifecycle",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.jr.state.probe.01",
                            prompt="How do cleanup functions in useEffect help prevent memory leaks when subscribing to events or timers?",
                            target_probe="Effect cleanup and memory management",
                            ideal_focus="Cleanup function runs before the component unmounts or before the effect re-runs, unbinding listeners.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=2,
            stage_name="Stage 3: Responsive Layouts & CSS",
            competency_title="Flexbox vs CSS Grid & Accessibility",
            description="Building fluid layouts, responsive breakpoints, and semantic HTML elements.",
            core_questions=[
                QuestionTemplate(
                    id="fe.jr.css.core.01",
                    question_text="When would you choose CSS Grid over Flexbox, and how do you ensure custom buttons and modals remain keyboard accessible?",
                    ideal_answer="Flexbox is ideal for 1D layouts (rows or columns); Grid is ideal for 2D structured layouts. Accessibility requires semantic elements (<button>), ARIA roles, focus management, and keydown listeners for Enter/Escape.",
                    primary_concept="CSS Layouts & Web Accessibility",
                    stage_name="Responsive Layouts",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.jr.css.probe.01",
                            prompt="Why is it bad practice to use a <div> with an onClick handler instead of a real <button> tag?",
                            target_probe="Semantic HTML and keyboard accessibility",
                            ideal_focus="Div tags are not focusable by default, cannot be triggered by Space/Enter keys, and are not announced as buttons to screen readers.",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Component Architecture & State Modeling",
            competency_title="Component Patterns & Custom Hooks",
            description="Designing reusable compound components and isolating stateful logic in custom hooks.",
            core_questions=[
                QuestionTemplate(
                    id="fe.mid.arch.core.01",
                    question_text="How do you architect reusable UI components using patterns like Compound Components or Render Props, and when should component state be extracted into a custom hook?",
                    ideal_answer="Compound components (e.g. Select, Select.Option) share implicit state via React Context for flexible composition. Custom hooks extract and share reusable stateful logic and side effects without altering component hierarchy.",
                    primary_concept="Compound Components & Custom Hooks",
                    stage_name="Component Architecture",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.mid.arch.probe.01",
                            prompt="How do you prevent unnecessary re-renders in child components when context value changes?",
                            target_probe="Context re-render optimization",
                            ideal_focus="Split state and dispatcher into separate contexts, memoize context values with useMemo, or use atomic state libraries.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Client Performance & Core Web Vitals",
            competency_title="LCP, INP & Bundle Optimization",
            description="Measuring and optimizing Largest Contentful Paint, Interaction to Next Paint, and code splitting.",
            core_questions=[
                QuestionTemplate(
                    id="fe.mid.perf.core.01",
                    question_text="How do you diagnose and improve a poor Interaction to Next Paint (INP) score on a web page with complex interactive widgets?",
                    ideal_answer="INP measures user interaction responsiveness. Diagnose using Chrome DevTools Performance panel to identify long tasks (>50ms). Fix by yielding to the main thread with scheduler.yield()/setTimeout, debouncing inputs, and offloading heavy computations to Web Workers.",
                    primary_concept="Core Web Vitals (INP) & Main Thread Optimization",
                    stage_name="Web Performance",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.mid.perf.probe.01",
                            prompt="How does React 18's useTransition or startTransition hook help maintain UI responsiveness during heavy rendering?",
                            target_probe="Concurrent React and non-blocking transitions",
                            ideal_focus="Marks state updates as non-urgent transitions, allowing urgent user inputs to interrupt background rendering.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=2,
            stage_name="Stage 3: Client State Management & Server Synchronization",
            competency_title="Server State vs Client State (React Query / SWR)",
            description="Caching asynchronous server data, optimistic UI updates, and cache invalidation.",
            core_questions=[
                QuestionTemplate(
                    id="fe.mid.state.core.01",
                    question_text="Why is server state (data fetched from APIs) conceptually different from local client state, and how do libraries like TanStack Query (React Query) manage caching and optimistic updates?",
                    ideal_answer="Server state is asynchronous, remote, and owned by other clients. TanStack Query manages background fetching, deduping requests, caching with staleTime/gcTime, and enables optimistic updates by updating client cache before network confirmation.",
                    primary_concept="Server State Caching & Optimistic UI",
                    stage_name="State Management",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.mid.state.probe.01",
                            prompt="If an optimistic update fails on the server, how do you safely roll back the UI to the previous state?",
                            target_probe="Optimistic mutation rollback handling",
                            ideal_focus="Save context snapshot on onMutate and restore previous cache state in onError callback.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=3,
            stage_name="Stage 4: Frontend Security & Data Protection",
            competency_title="XSS, CSRF & Content Security Policy",
            description="Mitigating Cross-Site Scripting, securing authentication tokens, and CSP implementation.",
            core_questions=[
                QuestionTemplate(
                    id="fe.mid.sec.core.01",
                    question_text="Where should JWT access tokens and refresh tokens be stored on the client to balance security against XSS and CSRF attacks?",
                    ideal_answer="Store refresh tokens in HttpOnly, Secure, SameSite=Strict cookies to block XSS access; store short-lived access tokens in memory (or protected storage) to prevent unauthorized script theft.",
                    primary_concept="Token Storage Security & XSS Mitigation",
                    stage_name="Frontend Security",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.mid.sec.probe.01",
                            prompt="How does a Content Security Policy (CSP) header protect modern React SPAs from malicious script injections?",
                            target_probe="Content Security Policy headers",
                            ideal_focus="Restricts allowed sources for executable scripts, fonts, and network connections, blocking inline scripts without valid nonces.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Large-Scale Frontend Architecture & Microfrontends",
            competency_title="Module Federation & Shared Design Systems",
            description="Monorepos, Module Federation, and scalable component governance.",
            core_questions=[
                QuestionTemplate(
                    id="fe.sr.arch.core.01",
                    question_text="How do you design a shared design system and microfrontend architecture using Webpack/Vite Module Federation while ensuring consistent styling and avoiding version mismatch runtime crashes?",
                    ideal_answer="Use design tokens (CSS variables) for strict visual consistency across apps, configure shared singleton dependencies (React, router) with semantic version constraints in Module Federation, and establish clear contract boundaries.",
                    primary_concept="Module Federation & Design System Architecture",
                    stage_name="Frontend Architecture",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.sr.arch.probe.01",
                            prompt="How do you handle shared authentication state and routing navigation across independently deployed microfrontends?",
                            target_probe="Cross-app communication and router sync",
                            ideal_focus="Use a shell host container providing custom event buses, shared auth context, and synced browser history.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Advanced Rendering Strategies & Hydration",
            competency_title="SSR, SSG, Streaming SSR & Island Architecture",
            description="Evaluating rendering paradigms, streaming HTML, selective hydration, and edge rendering.",
            core_questions=[
                QuestionTemplate(
                    id="fe.sr.render.core.01",
                    question_text="Compare Streaming Server-Side Rendering with Selective Hydration (React 18 / Next.js App Router) against traditional Client-Side Rendering in terms of Time to First Byte (TTFB) and First Input Delay.",
                    ideal_answer="Streaming SSR streams HTML chunks with Suspense boundaries, delivering fast TTFB. Selective hydration hydrates interactive islands as they become visible or interacted with, eliminating massive blocking JS hydration passes.",
                    primary_concept="Streaming SSR & Selective Hydration",
                    stage_name="Rendering Strategies",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.sr.render.probe.01",
                            prompt="What causes hydration mismatch errors between server-rendered HTML and client VDOM, and how do you resolve them cleanly?",
                            target_probe="Hydration mismatch resolution",
                            ideal_focus="Mismatches happen from browser-only globals (window, localStorage) or non-deterministic dates; fix by deferring client-only logic to useEffect or suppressHydrationWarning.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=2,
            stage_name="Stage 3: Deep Performance Profiling & Memory Leaks",
            competency_title="DOM Virtualization & Heap Snapshot Analysis",
            description="Virtualizing large datasets, diagnosing detached DOM node memory leaks, and frame rate optimization.",
            core_questions=[
                QuestionTemplate(
                    id="fe.sr.perf.core.01",
                    question_text="How do you build or configure a virtualized list to render 100,000 live data items at a steady 60 FPS, and how do you diagnose memory leaks caused by detached DOM nodes in Chrome DevTools?",
                    ideal_answer="List virtualization renders only visible items in the viewport using absolute positioning and calculated offsets. Memory leaks are identified using Chrome DevTools Memory Heap Snapshots by filtering for 'Detached HTML elements' held in closure references.",
                    primary_concept="DOM Virtualization & Memory Leak Diagnostics",
                    stage_name="Performance & Memory",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fe.sr.perf.probe.01",
                            prompt="Why do uncleared event listeners or closures inside global stores frequently cause detached DOM node leaks?",
                            target_probe="Closure references and garbage collection retention",
                            ideal_focus="The garbage collector cannot reclaim DOM nodes because the closure retains a reference to the element or its parent component.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 3. FULLSTACK ENGINEER QUESTION BANK
# ---------------------------------------------------------------------------
FULLSTACK_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: API Integration & Form Handling",
            competency_title="Frontend-to-Backend HTTP Contracts",
            description="Consuming backend APIs from frontend clients, error mapping, and form validation.",
            core_questions=[
                QuestionTemplate(
                    id="fs.jr.api.core.01",
                    question_text="When building a form that submits data to a REST API, how do you handle client-side vs server-side validation and display error messages cleanly to the user?",
                    ideal_answer="Perform instant client validation for basic formats (email, required fields) and enforce strict server-side validation. Parse structured 422/400 validation error responses and map them back to corresponding form fields.",
                    primary_concept="Fullstack Form Validation & Error Handling",
                    stage_name="API Integration",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fs.jr.api.probe.01",
                            prompt="Why can you never rely solely on client-side validation in a web application?",
                            target_probe="Defensive backend validation",
                            ideal_focus="Client-side validation can be bypassed easily with curl, Postman, or script execution.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Fullstack State & Authentication Basics",
            competency_title="Session vs JWT Authentication",
            description="Handling user login state across React frontend and backend API endpoints.",
            core_questions=[
                QuestionTemplate(
                    id="fs.jr.auth.core.01",
                    question_text="How does JWT-based user authentication work across a React frontend and a FastAPI/Node backend, from login submission to authenticated API calls?",
                    ideal_answer="User submits credentials -> Backend validates and returns JWT -> Frontend stores token (or cookie) and sends it in Authorization: Bearer header -> Backend dependency validates token signature and injects user object.",
                    primary_concept="Fullstack Authentication Flow",
                    stage_name="Authentication Basics",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fs.jr.auth.probe.01",
                            prompt="What should the frontend do automatically when an API request returns a 401 Unauthorized response?",
                            target_probe="Token expiry and redirect handling",
                            ideal_focus="Trigger a refresh token rotation or clear local state and redirect to login page.",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: End-to-End Type Safety & Data Contracts",
            competency_title="OpenAPI / TypeScript Schema Synchronization",
            description="Generating types from backend schemas and maintaining API contract integrity.",
            core_questions=[
                QuestionTemplate(
                    id="fs.mid.contract.core.01",
                    question_text="How do you establish end-to-end type safety between a Python FastAPI backend and a TypeScript React frontend to prevent runtime schema drift?",
                    ideal_answer="Use OpenAPI/JSON Schema generated automatically from Pydantic models, and utilize tools like openapi-typescript-codegen to generate strongly-typed TypeScript interfaces and fetch clients.",
                    primary_concept="End-to-End Type Safety & API Contracts",
                    stage_name="API Contracts",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fs.mid.contract.probe.01",
                            prompt="How do you enforce in your CI/CD pipeline that frontend builds fail if backend API schemas change breakingly?",
                            target_probe="Contract testing in CI/CD",
                            ideal_focus="Generate OpenAPI schema in CI, run typecheck against generated contracts, and alert on breaking schema diffs.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Optimistic UI & Relational Persistence",
            competency_title="Optimistic Mutations & Transaction Rollbacks",
            description="Coordinating instant frontend UI updates with reliable backend ACID persistence.",
            core_questions=[
                QuestionTemplate(
                    id="fs.mid.optimistic.core.01",
                    question_text="How do you implement an optimistic UI update for a 'Like' or 'Save' button in React, and how does the backend ensure atomicity and race-condition safety?",
                    ideal_answer="Frontend instantly increments count and renders active state while sending async POST; on network failure, it reverts to previous snapshot. Backend uses DB unique constraints or atomic UPDATE ... WHERE to prevent duplicate likes.",
                    primary_concept="Optimistic UI & Database Atomicity",
                    stage_name="Optimistic Persistence",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fs.mid.optimistic.probe.01",
                            prompt="How do you handle rapid multiple clicks on an optimistic action button?",
                            target_probe="Debouncing and idempotent requests",
                            ideal_focus="Debounce or throttle clicks and send idempotent mutation requests with client-generated UUIDs.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Backend-for-Frontend (BFF) & Gateway Architecture",
            competency_title="BFF Pattern & Data Aggregation",
            description="Designing dedicated BFF layers to aggregate microservice data for diverse client platforms.",
            core_questions=[
                QuestionTemplate(
                    id="fs.sr.bff.core.01",
                    question_text="When should an engineering organization adopt the Backend-For-Frontend (BFF) pattern over a single general-purpose REST or GraphQL API gateway?",
                    ideal_answer="When different client platforms (Web, Mobile, Desktop) have distinct data formatting, network bandwidth, and auth requirements. BFF optimizes payload shapes and orchestrates downstream service calls without bloating core domain services.",
                    primary_concept="Backend-For-Frontend (BFF) Architecture",
                    stage_name="BFF Architecture",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fs.sr.bff.probe.01",
                            prompt="How do you avoid duplicating shared business domain logic across multiple platform BFFs?",
                            target_probe="Domain logic vs presentation orchestration",
                            ideal_focus="BFFs only handle view aggregation and auth forwarding; core business logic resides strictly in downstream domain services.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Fullstack Observability & Distributed Tracing",
            competency_title="End-to-End Tracing (OpenTelemetry)",
            description="Propagating trace context from browser clicks down to database query execution.",
            core_questions=[
                QuestionTemplate(
                    id="fs.sr.trace.core.01",
                    question_text="How do you design an end-to-end distributed tracing pipeline that correlates a user click in React with frontend network spans, backend ASGI middleware, and slow SQL queries in PostgreSQL?",
                    ideal_answer="Inject W3C Trace Context (traceparent header) in frontend HTTP requests via OpenTelemetry SDK. Backend ASGI middleware extracts the header, creates child spans for DB queries/external calls, and exports telemetry to Tempo/Jaeger.",
                    primary_concept="Fullstack Distributed Tracing & W3C TraceContext",
                    stage_name="Fullstack Observability",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="fs.sr.trace.probe.01",
                            prompt="How do you sample high-volume traces to minimize storage costs without losing error and slow transaction traces?",
                            target_probe="Tail-based vs head-based trace sampling",
                            ideal_focus="Use tail-based sampling in collector agents to retain 100% of error traces and slow outliers (p95+) while sampling 1% of nominal 200 OK traffic.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 4. DEVOPS & CLOUD ENGINEER QUESTION BANK
# ---------------------------------------------------------------------------
DEVOPS_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Containerization & Docker Fundamentals",
            competency_title="Dockerfiles, Multi-Stage Builds & Layers",
            description="Building minimal, secure container images and managing container lifecycle.",
            core_questions=[
                QuestionTemplate(
                    id="devops.jr.docker.core.01",
                    question_text="How do multi-stage Docker builds reduce the final image size and improve security for a compiled or Python application?",
                    ideal_answer="Multi-stage builds separate the build environment (with compilers, headers, build tools) from the final minimal runtime image (e.g. Alpine/distroless), leaving no build tools or dev dependencies for attackers.",
                    primary_concept="Multi-Stage Docker Builds & Image Hardening",
                    stage_name="Container Fundamentals",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="devops.jr.docker.probe.01",
                            prompt="Why should containers never run with the default root user in production?",
                            target_probe="Container privilege escalation risks",
                            ideal_focus="Running as root allows container-breakout vulnerabilities to compromise the host kernel.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: CI/CD Automation & Git Workflows",
            competency_title="Automated Testing & Build Pipelines",
            description="Designing GitHub Actions/GitLab CI workflows for linting, testing, and artifact publishing.",
            core_questions=[
                QuestionTemplate(
                    id="devops.jr.cicd.core.01",
                    question_text="How do you design a GitHub Actions pipeline that ensures pull requests only merge when unit tests pass, linting succeeds, and Docker images build without errors?",
                    ideal_answer="Define distinct workflow jobs for lint, test, and build with branch protection rules enforcing required status checks on 'main' before allowing squash merges.",
                    primary_concept="CI/CD Status Checks & Branch Protection",
                    stage_name="CI/CD Automation",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="devops.jr.cicd.probe.01",
                            prompt="How do you securely manage production deployment secrets in GitHub Actions without exposing them in logs?",
                            target_probe="Secrets masking and environment protection",
                            ideal_focus="Use encrypted GitHub repository secrets, restricted deployment environments with manual approval, and ensure secrets are masked in logs.",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Kubernetes Workloads & Traffic Routing",
            competency_title="Deployments, Services & Ingress Controllers",
            description="Managing pod replicas, rolling updates, liveness/readiness probes, and Ingress routing.",
            core_questions=[
                QuestionTemplate(
                    id="devops.mid.k8s.core.01",
                    question_text="What is the difference between Kubernetes Liveness and Readiness probes, and what happens if an unhandled slow startup triggers a false Liveness failure?",
                    ideal_answer="Liveness probe checks if the container needs restarting; Readiness probe checks if it is ready to receive traffic. A premature Liveness failure causes continuous restart crash-loops before the app finishes initializing.",
                    primary_concept="Kubernetes Probes & Pod Lifecycle",
                    stage_name="Kubernetes Orchestration",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="devops.mid.k8s.probe.01",
                            prompt="How do Startup Probes solve the slow-initialization crash loop problem in Kubernetes?",
                            target_probe="Startup probe configuration",
                            ideal_focus="Startup probes disable liveness and readiness checks until the container has completed its initial boot phase.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Infrastructure as Code (Terraform)",
            competency_title="Terraform State & Modular Cloud Provisioning",
            description="Managing AWS/GCP resources using Terraform modules, state locking, and drift detection.",
            core_questions=[
                QuestionTemplate(
                    id="devops.mid.tf.core.01",
                    question_text="How does Terraform manage remote state and state locking with S3 and DynamoDB, and how do you handle configuration drift when someone modifies cloud resources manually in the console?",
                    ideal_answer="Remote state stores infrastructure mapping in S3, while DynamoDB provides mutex locks during terraform apply. Drift is detected with terraform plan/refresh, which compares real cloud state with desired state in .tf files.",
                    primary_concept="Terraform Remote State & Drift Management",
                    stage_name="Infrastructure as Code",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="devops.mid.tf.probe.01",
                            prompt="What are the risks of storing sensitive database credentials in plain Terraform state files?",
                            target_probe="Secrets management in IaC state",
                            ideal_focus="State files store variables in plaintext; use KMS encryption for S3 buckets and integrate HashiCorp Vault or AWS Secrets Manager.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Zero-Downtime Deployment & Progressive Delivery",
            competency_title="Canary Releases, Blue-Green & ArgoCD GitOps",
            description="Automating canary rollouts with automated rollbacks using Prometheus metric analysis.",
            core_questions=[
                QuestionTemplate(
                    id="devops.sr.gitops.core.01",
                    question_text="How do you architect a progressive canary deployment system using Argo Rollouts or Flagger where traffic is incrementally shifted based on real-time HTTP error rates and p99 latency metrics?",
                    ideal_answer="Configure Argo Rollouts with AnalysisTemplates that query Prometheus metrics (e.g. 5xx rate < 0.5%, p99 latency < 200ms) at each traffic step (10%, 25%, 50%). If metric thresholds breach, the controller automatically aborts and rolls back traffic.",
                    primary_concept="Progressive Canary Delivery & Automated Metric Analysis",
                    stage_name="Progressive Delivery",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="devops.sr.gitops.probe.01",
                            prompt="How do you coordinate backward-incompatible database schema migrations with a running canary deployment?",
                            target_probe="Expand-Contract migration pattern",
                            ideal_focus="Use Expand and Contract pattern: add nullable column/views first (expand), deploy canary, update consumers, then remove old columns (contract).",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Multi-Cluster Resilience & Disaster Recovery",
            competency_title="Service Mesh & Cross-Region Failover",
            description="Designing Istio/Linkerd service mesh federation and cross-region RTO/RPO disaster recovery.",
            core_questions=[
                QuestionTemplate(
                    id="devops.sr.dr.core.01",
                    question_text="How do you design an automated disaster recovery strategy for a multi-region Kubernetes platform to achieve an RTO of under 5 minutes and an RPO of under 1 minute during a primary cloud region outage?",
                    ideal_answer="Maintain warm standby Kubernetes clusters in secondary regions synced via GitOps, use cross-region asynchronous database replication with automated failover orchestration, and utilize Route 53 latency-based DNS routing with health-checked endpoint switching.",
                    primary_concept="Disaster Recovery (RTO/RPO) & Multi-Region Failover",
                    stage_name="Disaster Recovery",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="devops.sr.dr.probe.01",
                            prompt="How do you prevent split-brain DNS switching when a transient network glitch briefly disrupts health checks to the primary region?",
                            target_probe="Health check thresholds and consensus",
                            ideal_focus="Require consecutive multi-prober health check failures across multiple geographical vantage points before initiating automatic failover.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 5. DATA ENGINEER QUESTION BANK
# ---------------------------------------------------------------------------
DATA_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: SQL Aggregations & Window Functions",
            competency_title="Analytical SQL & Partition Queries",
            description="Writing advanced SQL queries using ROW_NUMBER, RANK, and cumulative aggregations.",
            core_questions=[
                QuestionTemplate(
                    id="data.jr.sql.core.01",
                    question_text="Could you explain the difference between ROW_NUMBER(), RANK(), and DENSE_RANK() in SQL, and provide an example of when you would use ROW_NUMBER() OVER (PARTITION BY ...)?",
                    ideal_answer="ROW_NUMBER assigns unique sequential integers. RANK skips ranks on ties (1, 2, 2, 4), while DENSE_RANK does not skip (1, 2, 2, 3). PARTITION BY computes rankings independently within subsets (e.g. top 3 sales per department).",
                    primary_concept="SQL Window Functions & Partitioning",
                    stage_name="Analytical SQL",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="data.jr.sql.probe.01",
                            prompt="How do window functions differ from standard GROUP BY aggregations in terms of output row count?",
                            target_probe="Window functions vs GROUP BY",
                            ideal_focus="GROUP BY collapses multiple rows into a single summary row, whereas window functions retain all original individual rows.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: ETL Pipeline & Storage Formats",
            competency_title="Columnar Formats (Parquet) & Batch Processing",
            description="Comparing row-oriented (CSV) vs columnar (Parquet) storage and designing basic Python ETLs.",
            core_questions=[
                QuestionTemplate(
                    id="data.jr.etl.core.01",
                    question_text="Why is Apache Parquet significantly more efficient than CSV or JSON for large-scale analytical queries in data warehouses?",
                    ideal_answer="Parquet uses columnar storage, allowing queries to read only required columns (projection pushdown) and benefits from high compression ratios (Snappy/ZSTD) and dictionary encoding.",
                    primary_concept="Columnar Storage Formats & Compression",
                    stage_name="ETL Fundamentals",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="data.jr.etl.probe.01",
                            prompt="What is predicate pushdown, and how does it speed up queries on Parquet files?",
                            target_probe="Predicate pushdown optimization",
                            ideal_focus="Filters are evaluated at the storage reader level using row group metadata (min/max values), skipping unneeded data blocks entirely.",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Distributed Batch Processing (Apache Spark)",
            competency_title="Spark Execution Plan & Shuffle Optimization",
            description="Tuning Spark jobs, broadcast joins, and avoiding costly data shuffles.",
            core_questions=[
                QuestionTemplate(
                    id="data.mid.spark.core.01",
                    question_text="How does Apache Spark execute joins across large distributed DataFrames, and when should you use a Broadcast Hash Join instead of a Sort-Merge Join?",
                    ideal_answer="Sort-Merge Join requires shuffling both datasets across network partitions by join key. A Broadcast Join sends a copy of the small dataset (<10MB default) to all executor nodes, eliminating expensive network shuffles entirely.",
                    primary_concept="Distributed Joins & Spark Shuffle Optimization",
                    stage_name="Distributed Batch Processing",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="data.mid.spark.probe.01",
                            prompt="What happens if a broadcast join is forced on a dataset that exceeds available executor driver memory?",
                            target_probe="Driver OutOfMemory errors in Spark",
                            ideal_focus="Causes Driver or Executor OutOfMemory (OOM) fatal crashes because the serialized dataset cannot fit into heap memory.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Stream Processing & Watermarking (Kafka / Flink)",
            competency_title="Event Time, Processing Time & Late Data Handling",
            description="Handling streaming data pipelines with out-of-order events and stateful stream joins.",
            core_questions=[
                QuestionTemplate(
                    id="data.mid.stream.core.01",
                    question_text="In event streaming with Kafka and Flink/Spark Streaming, what is the difference between Event Time and Processing Time, and how do Watermarks handle late-arriving events?",
                    ideal_answer="Event Time is when the event occurred on the producer device; Processing Time is when the stream engine receives it. Watermarks act as a progress metric in event time, defining how long the engine waits before closing a time window on late data.",
                    primary_concept="Streaming Watermarks & Event Time Semantics",
                    stage_name="Stream Processing",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="data.mid.stream.probe.01",
                            prompt="How do you handle events that arrive after the allowed watermark delay has already passed?",
                            target_probe="Dead-letter side outputs for late events",
                            ideal_focus="Route dropped late events to side outputs (dead letter queues) for retrospective batch reconciliation.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Lakehouse Architecture & Transactional Tables",
            competency_title="Apache Iceberg / Delta Lake & ACID Semantics",
            description="Designing modern lakehouses with schema evolution, time travel, and file compaction.",
            core_questions=[
                QuestionTemplate(
                    id="data.sr.lakehouse.core.01",
                    question_text="How do table formats like Apache Iceberg and Delta Lake provide ACID transactions and snapshot isolation on top of cloud object storage like AWS S3?",
                    ideal_answer="They maintain immutable metadata manifest files and transaction logs (commit logs). Writes commit atomically by swapping the root metadata pointer; readers read consistent point-in-time snapshots, enabling time travel and concurrent writes.",
                    primary_concept="Lakehouse Table Formats (Iceberg/Delta) & ACID Storage",
                    stage_name="Lakehouse Architecture",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="data.sr.lakehouse.probe.01",
                            prompt="How do you mitigate the 'small files problem' in streaming ingestion on a Lakehouse table?",
                            target_probe="Automated compaction and rewriteDataFiles",
                            ideal_focus="Schedule background compaction jobs (e.g. Iceberg rewriteDataFiles) to combine small files into optimal 128MB-512MB parquet files.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Data Governance, Lineage & Quality Frameworks",
            competency_title="Great Expectations, OpenLineage & Data Contracts",
            description="Automating data quality validation, lineage tracking, and enforcing upstream data contracts.",
            core_questions=[
                QuestionTemplate(
                    id="data.sr.gov.core.01",
                    question_text="How do you design a company-wide Data Contract framework that prevents upstream product engineers from releasing database migrations that silently break downstream analytical models?",
                    ideal_answer="Implement CI/CD contract tests (using Great Expectations or JSON Schema) against producer schemas, enforce explicit schema definitions in central registries (e.g. Protobuf/Avro), and publish automated lineage alerts via OpenLineage/DataHub.",
                    primary_concept="Data Contracts & Automated Data Quality Gateways",
                    stage_name="Data Governance",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="data.sr.gov.probe.01",
                            prompt="How do you handle automated quarantine when a pipeline detects anomalous null spikes or invalid data distributions?",
                            target_probe="Automated circuit breaking and quarantine zones",
                            ideal_focus="Halt pipeline progression via automated circuit breakers and route corrupt batches into an isolated quarantine table.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 6. MACHINE LEARNING ENGINEER QUESTION BANK
# ---------------------------------------------------------------------------
ML_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Model Evaluation & Validation Techniques",
            competency_title="Cross-Validation & Metric Selection",
            description="Selecting appropriate evaluation metrics (Precision, Recall, F1, ROC-AUC) for imbalanced data.",
            core_questions=[
                QuestionTemplate(
                    id="ml.jr.eval.core.01",
                    question_text="Why is raw Accuracy a misleading metric for evaluating a fraud detection model where only 0.1% of transactions are fraudulent, and which metrics should you use instead?",
                    ideal_answer="A naive model predicting 'no fraud' achieves 99.9% accuracy but catches zero fraud. Use Precision (minimizing false alarms), Recall (catching all fraud), PR-AUC (Precision-Recall AUC), or F1-score.",
                    primary_concept="Imbalanced Classification Metrics & Precision-Recall",
                    stage_name="Model Evaluation",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="ml.jr.eval.probe.01",
                            prompt="How does stratified k-fold cross-validation help prevent data leakage and maintain target class distribution?",
                            target_probe="Stratified sampling and validation splits",
                            ideal_focus="Stratification guarantees each fold maintains the exact minority-class percentage as the full dataset.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Overfitting, Regularization & Bias-Variance",
            competency_title="L1/L2 Regularization & Feature Preprocessing",
            description="Diagnosing high bias vs high variance and applying Lasso/Ridge regularization.",
            core_questions=[
                QuestionTemplate(
                    id="ml.jr.reg.core.01",
                    question_text="How do L1 (Lasso) and L2 (Ridge) regularization prevent overfitting in linear and neural network models, and why does L1 lead to sparse feature weights?",
                    ideal_answer="L2 penalizes squared weight magnitudes (shrinking weights smoothly towards zero). L1 penalizes absolute weights, driving non-informative feature weights strictly to zero due to the sharp diamond geometry of its constraint boundary.",
                    primary_concept="L1/L2 Regularization & Feature Sparsity",
                    stage_name="Regularization Techniques",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="ml.jr.reg.probe.01",
                            prompt="Why must feature scaling (like StandardScaler) be fitted only on training splits and not the test split?",
                            target_probe="Data leakage prevention during normalization",
                            ideal_focus="Fitting on the test set leaks global distribution statistics (mean, variance) into training, artificially inflating validation performance.",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Production Inference & Model Serving",
            competency_title="ONNX, TensorRT & Low-Latency REST/gRPC Serving",
            description="Optimizing PyTorch/TensorFlow models for low-latency production inference using ONNX and batching.",
            core_questions=[
                QuestionTemplate(
                    id="ml.mid.serve.core.01",
                    question_text="How do you convert and optimize a PyTorch deep learning model with ONNX Runtime or TensorRT to reduce inference latency from 150ms to under 15ms in production?",
                    ideal_answer="Export the PyTorch computation graph to ONNX format, apply graph optimizations (operator fusion, constant folding), perform FP16/INT8 quantization, and execute on TensorRT or ONNX Runtime with dynamic batching.",
                    primary_concept="Model Compilation, ONNX & TensorRT Optimization",
                    stage_name="Model Serving",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="ml.mid.serve.probe.01",
                            prompt="What is dynamic batching in Triton Inference Server, and how does it increase GPU throughput without blowing up latency?",
                            target_probe="Dynamic inference batching",
                            ideal_focus="Collects individual incoming requests over a tiny time window (e.g. 5ms) into a single batch, maximizing GPU core parallelism.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: MLOps & Drift Monitoring",
            competency_title="Data Drift, Concept Drift & Evidently AI",
            description="Detecting statistical feature drift (PSI/KS test) and automating model retraining triggers.",
            core_questions=[
                QuestionTemplate(
                    id="ml.mid.drift.core.01",
                    question_text="What is the difference between Data Drift and Concept Drift in a deployed recommendation or pricing model, and how do you detect them statistically in real time?",
                    ideal_answer="Data drift is a shift in input feature distribution P(X) (detected with Kolmogorov-Smirnov test or Population Stability Index). Concept drift is a shift in the underlying relationship P(Y|X) (detected via degradation in live ground-truth metrics).",
                    primary_concept="Data Drift vs Concept Drift & Statistical Detection",
                    stage_name="MLOps & Drift",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="ml.mid.drift.probe.01",
                            prompt="When ground truth labels are delayed by 30 days, how do you know if your model's accuracy is degrading today?",
                            target_probe="Unsupervised performance monitoring",
                            ideal_focus="Monitor input data drift (PSI) and prediction confidence distribution shifts as proxy indicators of performance degradation.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: LLM System Architecture & Retrieval-Augmented Generation (RAG)",
            competency_title="Vector Search, Hybrid Retrieval & Chunking Strategies",
            description="Designing scalable enterprise RAG systems with dense vector indexing, hybrid BM25 search, and rerankers.",
            core_questions=[
                QuestionTemplate(
                    id="ml.sr.rag.core.01",
                    question_text="How do you design a production-grade enterprise RAG system that eliminates LLM hallucinations over 10 million internal documents with sub-second response times?",
                    ideal_answer="Use semantic chunking with document metadata filtering, combine dense embeddings (HNSW index in Qdrant/Pinecone) with sparse BM25 keyword search (hybrid search), pass top 50 candidates to a Cross-Encoder Reranker (Cohere/BGE), and format prompt with strict context grounding and citation constraints.",
                    primary_concept="Enterprise RAG Architecture & Hybrid Retrieval",
                    stage_name="RAG & LLM Systems",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="ml.sr.rag.probe.01",
                            prompt="How do you evaluate RAG generation quality programmatically using frameworks like Ragas or TruLens?",
                            target_probe="RAG triangulation metrics (Faithfulness, Relevance, Groundedness)",
                            ideal_focus="Measure Faithfulness (factual grounding against retrieved chunks), Answer Relevance, and Context Recall using synthetic eval datasets.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Distributed Training & Fine-Tuning Optimization",
            competency_title="LoRA, QLoRA, DeepSpeed ZeRO & Model Parallelism",
            description="Fine-tuning large language models using Parameter-Efficient Fine-Tuning (PEFT) and ZeRO stage 3.",
            core_questions=[
                QuestionTemplate(
                    id="ml.sr.train.core.01",
                    question_text="How do LoRA and QLoRA enable fine-tuning a 70B parameter model on a single GPU node, and how does DeepSpeed ZeRO-3 partition model states across distributed clusters?",
                    ideal_answer="LoRA freezes pre-trained weights and injects trainable low-rank decomposition matrices (A and B). QLoRA quantizes the base model to 4-bit NormalFloat with double quantization. ZeRO-3 partitions optimizer states, gradients, and model weights across all GPUs.",
                    primary_concept="Parameter-Efficient Fine-Tuning (LoRA/QLoRA) & ZeRO-3",
                    stage_name="Distributed Training",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="ml.sr.train.probe.01",
                            prompt="What is the trade-off of using QLoRA 4-bit weights compared to full 16-bit LoRA fine-tuning in terms of training speed vs memory?",
                            target_probe="Dequantization overhead in QLoRA",
                            ideal_focus="QLoRA drastically saves VRAM allowing larger models on consumer GPUs, but adds computation overhead for on-the-fly dequantization during forward/backward passes.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 7. MOBILE ENGINEER QUESTION BANK
# ---------------------------------------------------------------------------
MOBILE_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Mobile UI & Widget Tree Lifecycle",
            competency_title="Stateless vs Stateful Widgets & Layout Renders",
            description="Building mobile user interfaces, understanding widget rebuilds, and responsive screen adaptation.",
            core_questions=[
                QuestionTemplate(
                    id="mobile.jr.ui.core.01",
                    question_text="In Flutter or React Native, how does the UI rendering tree work, and what practices prevent unnecessary full-screen re-renders during local state updates?",
                    ideal_answer="Break complex screens into smaller isolated stateful widgets/components, push state as low in the tree as possible, and use const constructors or React.memo to prevent subtrees from rebuilding when parent state changes.",
                    primary_concept="Widget Tree Optimization & Selective Rebuilds",
                    stage_name="Mobile UI Fundamentals",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="mobile.jr.ui.probe.01",
                            prompt="What causes UI frame drops (jank) on 60Hz/120Hz mobile screens during list scrolling?",
                            target_probe="UI thread blocking and layout calculation costs",
                            ideal_focus="Executing heavy synchronous computations or allocating large objects on the main UI thread during frame rendering.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Local Storage & Network Resilience",
            competency_title="Async HTTP & Local Key-Value Persistence",
            description="Fetching REST API payloads, handling offline connectivity, and local storage (SharedPreferences / SecureStorage).",
            core_questions=[
                QuestionTemplate(
                    id="mobile.jr.net.core.01",
                    question_text="How do you handle unstable mobile network connectivity gracefully in an app, including displaying offline banners and caching GET requests?",
                    ideal_answer="Monitor connectivity state via network listeners, cache HTTP responses locally using SQLite or Hive, and display non-blocking snackbars or cached fallback screens when offline.",
                    primary_concept="Mobile Network Resilience & Local Caching",
                    stage_name="Local Storage & Networking",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="mobile.jr.net.probe.01",
                            prompt="Why should sensitive data like OAuth refresh tokens never be stored in plain SharedPreferences or AsyncStorage?",
                            target_probe="Mobile secure storage security",
                            ideal_focus="Plain preferences are unencrypted XML/JSON files accessible on rooted/jailbroken devices; use Keychain (iOS) or EncryptedSharedPreferences/KeyStore (Android).",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Offline-First Architecture & Sync Engines",
            competency_title="Local Database Sync & Conflict Resolution",
            description="Building offline-first mobile apps with local SQLite/Room/Isar databases and two-way sync.",
            core_questions=[
                QuestionTemplate(
                    id="mobile.mid.offline.core.01",
                    question_text="How do you architect an offline-first mobile application where users can create and edit records offline, and sync them seamlessly with the backend server upon reconnecting?",
                    ideal_answer="Writes save immediately to a local SQLite/Room database with an 'is_synced: false' flag and a pending action queue. A background sync service reads the queue upon reconnect, posts to backend, and resolves conflicts using Last-Write-Wins or server timestamps.",
                    primary_concept="Offline-First Mobile Architecture & Mutation Queue",
                    stage_name="Offline-First Architecture",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="mobile.mid.offline.probe.01",
                            prompt="How do you handle sync conflicts if the same record was edited on another device while this device was offline?",
                            target_probe="Mobile sync conflict resolution",
                            ideal_focus="Use version timestamps, revision hashes, or prompt the user with a 3-way visual merge dialog for non-trivial conflicting fields.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: App Performance & Memory Management",
            competency_title="Image Caching, Memory Leaks & Background Tasks",
            description="Optimizing memory footprints, managing large bitmap decoding, and background services.",
            core_questions=[
                QuestionTemplate(
                    id="mobile.mid.perf.core.01",
                    question_text="How do you diagnose and fix Out-Of-Memory (OOM) crashes in a mobile app caused by displaying thousands of high-resolution images in a feed?",
                    ideal_answer="Downsample/resize image bitmaps at decode time to the exact display dimensions, implement disk and memory caching with LRU eviction (CachedNetworkImage/Glide), and ensure image memory caches are cleared on OS memory pressure warnings.",
                    primary_concept="Mobile Bitmap Memory & LRU Image Caching",
                    stage_name="Mobile Performance",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="mobile.mid.perf.probe.01",
                            prompt="How do OS-level background execution limits (Android WorkManager vs iOS BackgroundTasks) restrict continuous sync?",
                            target_probe="Mobile OS background task lifecycle",
                            ideal_focus="Mobile operating systems suspend background threads to save battery; apps must use OS-managed schedulers with opportunistic execution.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Native Platform Interop & Method Channels",
            competency_title="Custom C++ / Java / Swift Native Plugins",
            description="Bridging cross-platform Flutter/React Native layers with native iOS/Android SDKs and hardware APIs.",
            core_questions=[
                QuestionTemplate(
                    id="mobile.sr.native.core.01",
                    question_text="How do you design high-performance native platform channels in Flutter or TurboModules in React Native when streaming real-time sensor or camera byte streams?",
                    ideal_answer="Avoid JSON serialization overhead on the standard method channel. Use binary messaging channels, shared memory buffers (Direct ByteBuffers / FFI pointers), or native texture registries to stream raw frames directly into the GPU rendering pipeline.",
                    primary_concept="Native Platform Channels & Zero-Copy FFI Interop",
                    stage_name="Native Platform Interop",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="mobile.sr.native.probe.01",
                            prompt="How do you ensure memory safety and prevent native memory leaks when passing pointers across the Dart/JS to C++ boundary?",
                            target_probe="Native pointer lifecycle and finalizers",
                            ideal_focus="Use NativeFinalizer (Dart FFI) or smart pointers in C++ to automatically free heap allocations when the wrapper object is garbage collected.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Modular Mobile Architecture & Dynamic Features",
            competency_title="Feature Modules, Dynamic Delivery & Security Sandboxing",
            description="Architecting enterprise multi-repo mobile apps with dynamic feature modules and app hardening.",
            core_questions=[
                QuestionTemplate(
                    id="mobile.sr.arch.core.01",
                    question_text="How do you architect a modular mobile application with dynamic on-demand feature downloads (Play Feature Delivery / App Clips) while maintaining strict dependency inversion?",
                    ideal_answer="Decompose the codebase into Core (auth, networking, DB), Feature Modules (checkout, search), and dynamic loadable plugins. Feature modules depend only on Core interfaces via a Service Locator/DI container, preventing circular module dependencies.",
                    primary_concept="Dynamic Feature Modules & Mobile Dependency Inversion",
                    stage_name="Modular Architecture",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="mobile.sr.arch.probe.01",
                            prompt="How do you protect mobile apps against reverse engineering, API key extraction, and SSL man-in-the-middle inspection?",
                            target_probe="Mobile application hardening and certificate pinning",
                            ideal_focus="Implement SSL Certificate Pinning, code obfuscation (ProGuard/R8), runtime integrity checks (SafetyNet/Play Integrity), and avoid hardcoding static API secrets.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 8. BEHAVIORAL & STAR INTERVIEW QUESTION BANK (All Roles)
# ---------------------------------------------------------------------------
BEHAVIORAL_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Team Collaboration & Learning",
            competency_title="Feedback & Growth Mindset",
            description="Receiving code review feedback, asking for help, and learning from mistakes.",
            core_questions=[
                QuestionTemplate(
                    id="behav.jr.collab.core.01",
                    question_text="Tell me about a time when you received constructive feedback on your code during a pull request that you initially disagreed with. How did you handle the situation?",
                    ideal_answer="Structured STAR response: Candidate listened openly, asked clarifying questions to understand the reviewer's reasoning, tested the alternative, and adopted team standards constructively.",
                    primary_concept="Receiving Constructive Feedback",
                    stage_name="Team Collaboration",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="behav.jr.collab.probe.01",
                            prompt="Looking back, what key engineering lesson did you take away from that experience?",
                            target_probe="Reflection and behavioral growth",
                            ideal_focus="Focus on ego-free engineering and prioritizing team consistency over personal preference.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Managing Deadlines & Blockers",
            competency_title="Proactive Communication & Problem Solving",
            description="Identifying blockers early and communicating timeline adjustments.",
            core_questions=[
                QuestionTemplate(
                    id="behav.jr.block.core.01",
                    question_text="Describe a situation where you were stuck on a difficult technical bug and were at risk of missing a project deadline. What steps did you take?",
                    ideal_answer="Structured STAR response: Candidate attempted structured debugging, documented findings, reached out to a teammate or lead with clear context, and proactively communicated timeline updates.",
                    primary_concept="Overcoming Technical Blockers",
                    stage_name="Managing Blockers",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="behav.jr.block.probe.01",
                            prompt="How long do you typically struggle with an issue before escalating or asking a peer for assistance?",
                            target_probe="Timeboxing and team communication",
                            ideal_focus="Timeboxing effort (30-60 mins) before asking with concrete findings and hypotheses.",
                        )
                    ],
                )
            ],
        ),
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Technical Disagreements & Consensus",
            competency_title="Constructive Technical Debate",
            description="Resolving architectural disagreements and driving alignment.",
            core_questions=[
                QuestionTemplate(
                    id="behav.mid.conflict.core.01",
                    question_text="Walk me through a situation where you and a colleague had a strong disagreement on a technical design decision. How did you navigate the conversation and reach alignment?",
                    ideal_answer="Structured STAR response: Separated personal opinion from technical metrics, created quick proof-of-concept benchmarks, aligned on user/business requirements, and committed to the agreed decision.",
                    primary_concept="Technical Conflict Resolution",
                    stage_name="Technical Disagreements",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="behav.mid.conflict.probe.01",
                            prompt="If the final team consensus went against your preferred approach, how did you commit to supporting the chosen path?",
                            target_probe="Disagree and commit mindset",
                            ideal_focus="Committing fully to execution without passive resistance or undermining the decision.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Project Ownership & Accountability",
            competency_title="End-to-End Delivery & Scope Trade-offs",
            description="Owning features from conception to production delivery under tight constraints.",
            core_questions=[
                QuestionTemplate(
                    id="behav.mid.owner.core.01",
                    question_text="Describe a project where requirements shifted midway through development or were ambiguous. How did you maintain velocity and deliver the feature successfully?",
                    ideal_answer="Structured STAR response: Clarified core business priorities with product managers, negotiated MVP scope, established incremental milestones, and delivered on time.",
                    primary_concept="Navigating Ambiguous Requirements",
                    stage_name="Project Ownership",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="behav.mid.owner.probe.01",
                            prompt="What technical concessions or tech debt did you intentionally take on, and how did you track its remediation?",
                            target_probe="Pragmatic tech debt management",
                            ideal_focus="Creating backlog tech-debt tickets with clear impact justification for post-launch sprint.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Cross-Functional Technical Leadership",
            competency_title="Strategic Alignment & Mentorship",
            description="Leading complex engineering initiatives across engineering, product, and business stakeholders.",
            core_questions=[
                QuestionTemplate(
                    id="behav.sr.lead.core.01",
                    question_text="Can you describe a high-stakes technical decision you spearheaded that impacted multiple engineering teams? How did you build consensus and guide execution?",
                    ideal_answer="Structured STAR response: Authored an RFC/design document, hosted technical reviews, addressed security/scalability concerns, defined migration phases, and mentored junior engineers throughout.",
                    primary_concept="Technical Leadership & RFC Alignment",
                    stage_name="Technical Leadership",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="behav.sr.lead.probe.01",
                            prompt="How did you measure the business and engineering impact of that initiative after rollout?",
                            target_probe="Quantifiable outcome measurement",
                            ideal_focus="Tracking latency reductions, developer velocity metrics, infrastructure cost savings, or error rate drops.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Production Incident & Crisis Leadership",
            competency_title="Major Incident Response & Blameless Post-Mortem",
            description="Leading incident response under pressure and institutionalizing preventative systems.",
            core_questions=[
                QuestionTemplate(
                    id="behav.sr.incident.core.01",
                    question_text="Tell me about the most severe production outage or data integrity incident you experienced. How did you lead the mitigation and drive the blameless post-mortem?",
                    ideal_answer="Structured STAR response: Calmly coordinated emergency response, prioritized customer containment, identified root cause via telemetry, published transparent post-mortem with automated safeguards.",
                    primary_concept="Incident Leadership & Blameless Culture",
                    stage_name="Production Incidents",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="behav.sr.incident.probe.01",
                            prompt="What permanent systemic change was implemented in your deployment or testing pipeline to ensure that class of bug never reoccurred?",
                            target_probe="Systemic preventative engineering",
                            ideal_focus="Automated integration tests, canary release gates, circuit breakers, or automated rollback alerts.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# 9. SYSTEM DESIGN QUESTION BANK (All Roles / System Design Focus)
# ---------------------------------------------------------------------------
SYSTEM_DESIGN_BANK: Dict[str, List[CompetencyStage]] = {
    "junior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: System Basics & Scaling Fundamentals",
            competency_title="Vertical vs Horizontal Scaling & Load Balancing",
            description="Core concepts of distributed web architecture and stateless servers.",
            core_questions=[
                QuestionTemplate(
                    id="sys.jr.scale.core.01",
                    question_text="How does a Load Balancer distribute incoming traffic across multiple application servers, and why is stateless architecture critical for horizontal scaling?",
                    ideal_answer="Load balancers use algorithms like Round Robin or Least Connections to route requests. Stateless servers allow any server to handle any request because session state is stored in external caches/DBs.",
                    primary_concept="Load Balancing & Stateless Servers",
                    stage_name="Scaling Fundamentals",
                    difficulty="foundational",
                    follow_ups=[
                        FollowUpTemplate(
                            id="sys.jr.scale.probe.01",
                            prompt="What happens if one application server crashes behind a health-checked load balancer?",
                            target_probe="Health checking and traffic redirection",
                            ideal_focus="Health checks detect failure and automatically remove the server from the routing pool.",
                        )
                    ],
                )
            ],
        )
    ],
    "mid": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: URL Shortener & Rate Limiting System Design",
            competency_title="Key Generation & High-Read Caching",
            description="Designing high-throughput low-latency URL shortening services (e.g. TinyURL).",
            core_questions=[
                QuestionTemplate(
                    id="sys.mid.url.core.01",
                    question_text="How would you design a URL shortening service like TinyURL that handles 10,000 reads/sec with sub-20ms latency and 1,000 writes/sec?",
                    ideal_answer="Use Base62 encoding on unique sequential 64-bit IDs (or pre-generated keys in ZooKeeper/Redis). Store mapping in NoSQL/SQL with primary key on short_hash. Front with distributed Redis cache (80/20 read rule) and rate limiter.",
                    primary_concept="High-Read System Design & Key Generation",
                    stage_name="System Architecture",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="sys.mid.url.probe.01",
                            prompt="How do you handle custom alias collisions and expired link cleanups at scale?",
                            target_probe="Hash collisions and TTL cleanup strategies",
                            ideal_focus="DB unique constraints for aliases and lazy deletion or background TTL sweeps.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Scalable Notification System",
            competency_title="Message Queues & Fan-out Architectures",
            description="Designing multi-channel notification systems (Push, Email, SMS) with rate limits and priority.",
            core_questions=[
                QuestionTemplate(
                    id="sys.mid.notify.core.01",
                    question_text="How would you design a scalable notification service that delivers millions of push notifications and emails while respecting user rate limits and channel priorities?",
                    ideal_answer="API receives notification requests -> writes to RabbitMQ/Kafka priority queues -> dedicated consumer workers call third-party providers with rate-limiting tokens (Token Bucket). Store delivery logs in DB.",
                    primary_concept="Asynchronous Message Queues & Rate Limiting",
                    stage_name="Notification Systems",
                    difficulty="intermediate",
                    follow_ups=[
                        FollowUpTemplate(
                            id="sys.mid.notify.probe.01",
                            prompt="How do you prevent a slow email provider outage from stalling high-priority SMS notifications?",
                            target_probe="Queue isolation by channel",
                            ideal_focus="Separate queues and dedicated worker pools per channel so one slow third-party provider doesn't block others.",
                        )
                    ],
                )
            ],
        ),
    ],
    "senior": [
        CompetencyStage(
            stage_index=0,
            stage_name="Stage 1: Distributed Rate Limiter & Edge Gateway",
            competency_title="Sliding Window Counters & Distributed Redis Locking",
            description="Designing global rate limiting for millions of API requests across multiple data centers.",
            core_questions=[
                QuestionTemplate(
                    id="sys.sr.ratelimit.core.01",
                    question_text="How would you design a globally distributed API Rate Limiter handling 500,000 requests/sec across multi-region edge gateways using the Sliding Window Counter algorithm?",
                    ideal_answer="Implement sliding window logs/counters in Redis using Lua scripts for atomic execution. Distribute rate limit state locally at edge nodes with periodic synchronization to reduce cross-region latency, falling back to local token buckets during network partitions.",
                    primary_concept="Distributed Rate Limiting & Atomic Sliding Window",
                    stage_name="Distributed Systems",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="sys.sr.ratelimit.probe.01",
                            prompt="How do you handle race conditions when two edge nodes increment the same client's request count concurrently?",
                            target_probe="Concurrency in distributed counters",
                            ideal_focus="Redis atomic Lua scripts or CRDT counters to guarantee consistency without distributed locking stalls.",
                        )
                    ],
                )
            ],
        ),
        CompetencyStage(
            stage_index=1,
            stage_name="Stage 2: Real-time Collaborative Document / Event Feed",
            competency_title="WebSockets, CRDTs & Distributed Presence",
            description="Designing real-time collaborative editing (Google Docs) or high-throughput live feed.",
            core_questions=[
                QuestionTemplate(
                    id="sys.sr.collab.core.01",
                    question_text="Design the architecture for a real-time collaborative editor like Google Docs with millions of concurrent documents. How do you resolve simultaneous editing conflicts and scale WebSocket connections?",
                    ideal_answer="Maintain bidirectional WebSockets on horizontally scaled gateway servers using Redis Pub/Sub for cross-server presence. Resolve text conflicts using Conflict-Free Replicated Data Types (CRDTs like Yjs) or Operational Transformation (OT) on document coordinator nodes.",
                    primary_concept="Real-time WebSocket Scaling & Conflict Resolution (CRDTs)",
                    stage_name="Real-Time Systems",
                    difficulty="advanced",
                    follow_ups=[
                        FollowUpTemplate(
                            id="sys.sr.collab.probe.01",
                            prompt="What happens when a disconnected client comes back online after 10 minutes of offline edits?",
                            target_probe="Offline state merge and vector clocks",
                            ideal_focus="CRDT state vectors merge operations deterministically without needing a centralized lock.",
                        )
                    ],
                )
            ],
        ),
    ],
}


# ---------------------------------------------------------------------------
# NORMALIZATION HELPERS
# ---------------------------------------------------------------------------
def normalize_role_key(role: str) -> str:
    """Normalize role string into a canonical role identifier matching ROLE_PRESETS."""
    if not role:
        return "backend-engineer"
    r = role.strip().lower()
    if "front" in r or "react" in r or ("web" in r and "backend" not in r and "full" not in r):
        return "frontend-engineer"
    if "full" in r or "fullstack" in r:
        return "fullstack-engineer"
    if "devops" in r or "cloud" in r or "sre" in r or "infra" in r:
        return "devops-cloud-engineer"
    if "data" in r and "science" not in r and "ml" not in r:
        return "data-engineer"
    if "ml" in r or "machine" in r or "ai" in r or "data science" in r:
        return "ml-engineer"
    if "mobile" in r or "flutter" in r or "android" in r or "ios" in r:
        return "mobile-engineer"
    return "backend-engineer"


def normalize_seniority_key(seniority: str) -> str:
    """Normalize seniority string into junior, mid, or senior."""
    if not seniority:
        return "mid"
    s = seniority.strip().lower()
    if "jr" in s or "junior" in s or "entry" in s:
        return "junior"
    if "sr" in s or "senior" in s or "lead" in s or "staff" in s or "principal" in s:
        return "senior"
    return "mid"


def normalize_focus_key(focus: str) -> str:
    """Normalize focus area into Technical Core, System Design, or Behavioral."""
    if not focus:
        return "Technical Core"
    f = focus.strip().lower()
    if "system" in f or "design" in f or "arch" in f:
        return "System Design"
    if "behav" in f or "star" in f or "hr" in f or "soft" in f:
        return "Behavioral"
    return "Technical Core"


# ---------------------------------------------------------------------------
# PUBLIC QUERY INTERFACES
# ---------------------------------------------------------------------------
def get_competency_stages(
    role: str,
    seniority: str = "mid",
    focus: str = "Technical Core",
) -> List[CompetencyStage]:
    """Retrieve the structured competency stages for a given role, seniority, and focus."""
    norm_focus = normalize_focus_key(focus)
    norm_sen = normalize_seniority_key(seniority)
    norm_role = normalize_role_key(role)

    # 1. Behavioral Focus takes precedence
    if norm_focus == "Behavioral":
        return BEHAVIORAL_BANK.get(norm_sen) or BEHAVIORAL_BANK["mid"]

    # 2. System Design Focus
    if norm_focus == "System Design":
        return SYSTEM_DESIGN_BANK.get(norm_sen) or SYSTEM_DESIGN_BANK["mid"]

    # 3. Technical Core Focus by Role
    if norm_role == "frontend-engineer":
        return FRONTEND_BANK.get(norm_sen) or FRONTEND_BANK["mid"]
    if norm_role == "fullstack-engineer":
        return FULLSTACK_BANK.get(norm_sen) or FULLSTACK_BANK["mid"]
    if norm_role == "devops-cloud-engineer":
        return DEVOPS_BANK.get(norm_sen) or DEVOPS_BANK["mid"]
    if norm_role == "data-engineer":
        return DATA_BANK.get(norm_sen) or DATA_BANK["mid"]
    if norm_role == "ml-engineer":
        return ML_BANK.get(norm_sen) or ML_BANK["mid"]
    if norm_role == "mobile-engineer":
        return MOBILE_BANK.get(norm_sen) or MOBILE_BANK["mid"]

    # Default to Backend Engineer Bank
    return BACKEND_BANK.get(norm_sen) or BACKEND_BANK["mid"]


def get_fallback_question(
    role: str,
    seniority: str = "mid",
    focus: str = "Technical Core",
    stage_index: int = 0,
    excluded_question_ids: Optional[Set[str]] = None,
) -> QuestionTemplate:
    """Select a deterministic, domain-appropriate fallback question without repeating excluded IDs."""
    stages = get_competency_stages(role=role, seniority=seniority, focus=focus)
    excluded = excluded_question_ids or set()

    # Try matching stage index first
    target_stage = stages[min(stage_index, len(stages) - 1)] if stages else None
    if target_stage:
        for q in target_stage.core_questions:
            if q.id not in excluded:
                return q

    # Fallback to any unused question across all stages for this role
    for stage in stages:
        for q in stage.core_questions:
            if q.id not in excluded:
                return q

    # If all in current role are excluded, return first question of the stage
    if target_stage and target_stage.core_questions:
        return target_stage.core_questions[0]

    # Universal ultimate fallback
    return QuestionTemplate(
        id="univ.fallback.core.01",
        question_text=f"Could you walk me through the architecture of a production system you contributed to recently as a {seniority} {role}?",
        ideal_answer="Structured explanation of system requirements, architectural trade-offs, database choices, caching, and failure modes.",
        primary_concept="System Architecture & Engineering Trade-offs",
        stage_name="Universal Core Overview",
        difficulty=seniority,
    )


def get_fallback_followup(
    role: str,
    seniority: str = "mid",
    focus: str = "Technical Core",
    parent_concept: Optional[str] = None,
) -> FollowUpTemplate:
    """Retrieve an appropriate follow-up probing template."""
    stages = get_competency_stages(role=role, seniority=seniority, focus=focus)
    for stage in stages:
        for q in stage.core_questions:
            if parent_concept and parent_concept.lower() in q.primary_concept.lower():
                if q.follow_ups:
                    return q.follow_ups[0]
            if q.follow_ups:
                return q.follow_ups[0]

    # Universal fallback probe
    return UNIVERSAL_FOLLOWUPS[0]


def get_all_question_ids() -> Set[str]:
    """Return all unique question IDs across all banks to guarantee global uniqueness."""
    ids: Set[str] = set()
    all_banks = [
        BACKEND_BANK,
        FRONTEND_BANK,
        FULLSTACK_BANK,
        DEVOPS_BANK,
        DATA_BANK,
        ML_BANK,
        MOBILE_BANK,
        BEHAVIORAL_BANK,
        SYSTEM_DESIGN_BANK,
    ]
    for bank in all_banks:
        for sen_level, stages in bank.items():
            for stage in stages:
                for q in stage.core_questions:
                    ids.add(q.id)
                    for f in q.follow_ups:
                        ids.add(f.id)
    for uf in UNIVERSAL_FOLLOWUPS:
        ids.add(uf.id)
    return ids
