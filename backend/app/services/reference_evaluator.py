"""Reference Answers, Expected Concepts, and Evaluation Rubrics Engine.

Provides authoritative, evidence-based reference benchmarks, structured expected concepts
with importance tiers (CORE vs SUPPORTING), and intent-calibrated evaluation rubrics for mock interview turns.
Guarantees zero candidate-answer contamination and strict prompt-injection resistance.
"""

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.evaluation import (
    ArchitectureEdge,
    ArchitectureNode,
    ConceptImportance,
    EvaluationRubric,
    EvidenceCategory,
    ExpectedConcept,
    QuestionReferencePayload,
    SystemDesignReferenceArchitecture,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CURATED DETERMINISTIC EXPECTED CONCEPTS & RUBRICS FOR QUESTION ARTIFACTS
# ---------------------------------------------------------------------------

CURATED_QUESTION_CONCEPTS: Dict[str, List[Tuple[str, ConceptImportance, str]]] = {
    # Relational Database Fundamentals
    "primary key": [
        ("Primary Key Row Uniqueness", ConceptImportance.CORE, "Uniquely identifies each row in a database table."),
        ("Entity Integrity & Uniqueness Constraint", ConceptImportance.CORE, "Enforces database-level entity integrity and prevents duplicate keys."),
        ("Not-Null Constraint Enforcement", ConceptImportance.SUPPORTING, "Columns composing a primary key cannot hold NULL values."),
        ("Foreign Key Reference Target & Indexing", ConceptImportance.SUPPORTING, "Serves as the target for relational foreign keys and default indexing."),
    ],
    # HTTP & REST API Fundamentals
    "http semantics & idempotency": [
        ("Idempotency semantics of PUT", ConceptImportance.CORE, "PUT completely replaces resource representation idempotently."),
        ("Partial update semantics of PATCH", ConceptImportance.CORE, "PATCH modifies specific fields without full resource replacement."),
        ("Payload schema validation", ConceptImportance.SUPPORTING, "Handling optional/missing fields safely with schema validators."),
    ],
    "http get": [
        ("Idempotent & Safe Retrieval", ConceptImportance.CORE, "GET method retrieves resource representation without modifying server state."),
        ("Query Parameter Filtering", ConceptImportance.SUPPORTING, "Passes search and filter parameters via URL query strings."),
    ],
    "hash table complexity": [
        ("Hash table lookup average time complexity is O(1) constant time", ConceptImportance.CORE, "Average time complexity for key lookup in a hash table is O(1) constant time."),
    ],
    "hash table lookup": [
        ("Hash table lookup average time complexity is O(1) constant time", ConceptImportance.CORE, "Average time complexity for key lookup in a hash table is O(1) constant time."),
    ],
    "database transactions & acid": [
        ("ACID Properties (Atomicity, Consistency, Isolation, Durability)", ConceptImportance.CORE, "Guarantees transactional integrity across multiple operations."),
        ("Transaction rollback mechanisms", ConceptImportance.CORE, "Automatic rollback to clean up uncommitted writes upon failure."),
        ("Isolation levels and concurrency anomalies", ConceptImportance.SUPPORTING, "Dirty reads, non-repeatable reads, and phantom read prevention."),
    ],
    "exception handling": [
        ("Runtime Error Interception", ConceptImportance.CORE, "Catches runtime exceptions using try-except or try-catch blocks to prevent crashes."),
        ("Graceful Error Recovery & Logging", ConceptImportance.SUPPORTING, "Logs diagnostic error details and returns safe fallback responses."),
    ],
    "centralized exception handling": [
        ("Global exception middleware", ConceptImportance.CORE, "Intercepting unhandled exceptions uniformly before sending response."),
        ("Information leakage prevention", ConceptImportance.CORE, "Masking raw stack traces, internal paths, and DB schemas from public clients."),
        ("Standard HTTP error response schemas", ConceptImportance.SUPPORTING, "Returning predictable JSON error objects with clear status codes."),
    ],
    "database indexing & query performance": [
        ("B-Tree index structure and lookups", ConceptImportance.CORE, "Logarithmic search time O(log N) on indexed columns."),
        ("Write overhead of indexes", ConceptImportance.CORE, "Every insert/update/delete requires updating index trees."),
        ("Composite index column order (Prefix Rule)", ConceptImportance.SUPPORTING, "Leftmost prefix matching for compound indexes."),
    ],
    "relational schema normalization": [
        ("Eliminating data redundancy", ConceptImportance.CORE, "Decomposing tables to store each fact in exactly one place."),
        ("Preventing update, insert, and delete anomalies", ConceptImportance.CORE, "Avoiding inconsistent states during row updates."),
        ("Normal forms (1NF, 2NF, 3NF)", ConceptImportance.SUPPORTING, "Atomic values, full functional dependency, and transitive dependency removal."),
    ],
    "database normalization": [
        ("Eliminating data redundancy", ConceptImportance.CORE, "Decomposing tables to store each fact in exactly one place."),
        ("Preventing update, insert, and delete anomalies", ConceptImportance.CORE, "Avoiding inconsistent states during row updates."),
        ("Normal forms (1NF, 2NF, 3NF)", ConceptImportance.SUPPORTING, "Atomic values, full functional dependency, and transitive dependency removal."),
    ],
    "asynchronous programming & concurrency": [
        ("Event loop and non-blocking I/O", ConceptImportance.CORE, "Single-threaded event loop delegating I/O without blocking threads."),
        ("Async/await cooperative multitasking", ConceptImportance.CORE, "Yielding control during network/disk wait times."),
        ("CPU-bound vs I/O-bound trade-offs", ConceptImportance.SUPPORTING, "Async is optimal for I/O; CPU-bound tasks require process pools."),
    ],
    "caching strategies & cache invalidation": [
        ("Sub-millisecond in-memory lookups (Redis/Memcached)", ConceptImportance.CORE, "Serving hot reads directly from RAM."),
        ("Cache invalidation patterns (Cache-Aside, Write-Through)", ConceptImportance.CORE, "Strategies for synchronizing cache with persistent store."),
        ("Cache stampede and TTL eviction", ConceptImportance.SUPPORTING, "Preventing thundering herd on cache miss using locks/probabilistic TTL."),
    ],
}


# ---------------------------------------------------------------------------
# DETERMINISTIC SYSTEM DESIGN REFERENCE ARCHITECTURE BLUEPRINT CATALOG
# ---------------------------------------------------------------------------

SYSTEM_DESIGN_BLUEPRINT_CATALOG: Dict[str, SystemDesignReferenceArchitecture] = {
    "sys.sr.ratelimit.core.01": SystemDesignReferenceArchitecture(
        scenario_id="sys.sr.ratelimit.core.01",
        title="Globally Distributed API Rate Limiter (Sliding Window Counter)",
        description="High-throughput edge rate limiter using atomic Redis sliding window counters, localized token buckets, and asynchronous telemetry.",
        nodes=[
            ArchitectureNode(id="client", label="API Clients / Mobile App", type="client", purpose="Sends high-concurrency API requests with API keys or bearer tokens.", is_core=True),
            ArchitectureNode(id="edge_gateway", label="Regional Edge API Gateway", type="gateway", purpose="Intercepts requests, evaluates client rate quotas, and enforces 429 Too Many Requests.", is_core=True),
            ArchitectureNode(id="redis_cluster", label="Distributed Redis Cluster (Lua Scripts)", type="cache", purpose="Atomic sliding window counter increments and TTL key expiration via Lua scripts.", is_core=True),
            ArchitectureNode(id="local_cache", label="Local In-Memory Token Bucket", type="cache", purpose="Low-latency fallback cache for high-frequency requests during Redis connection spikes.", is_core=True),
            ArchitectureNode(id="app_services", label="Core Application Microservices", type="service", purpose="Downstream business logic services protected from traffic surges and DDoS.", is_core=True),
            ArchitectureNode(id="telemetry", label="Rate Limit Telemetry & Audit Store", type="database", purpose="Logs blocked request spikes, client quota breaches, and system metrics asynchronously.", is_core=False),
        ],
        edges=[
            ArchitectureEdge(source="client", target="edge_gateway", label="HTTPS API Requests", protocol="https", mode="sync"),
            ArchitectureEdge(source="edge_gateway", target="redis_cluster", label="Atomic Sliding Window Eval", protocol="redis", mode="sync"),
            ArchitectureEdge(source="edge_gateway", target="local_cache", label="Local Fallback & Batch Quota", protocol="memory", mode="sync"),
            ArchitectureEdge(source="edge_gateway", target="app_services", label="Allowed Requests Forwarding", protocol="grpc", mode="sync"),
            ArchitectureEdge(source="edge_gateway", target="telemetry", label="Async Quota Breach Events", protocol="kafka", mode="async"),
        ],
        key_tradeoffs=[
            "Sliding Window Counter vs Token Bucket: Sliding window prevents boundary burst anomalies at the cost of slightly higher memory overhead per active client key.",
            "Centralized Redis vs Edge Local Counting: Centralized Redis guarantees strict global accuracy across all regions; local edge counting trades exactness for sub-millisecond latency.",
            "Fail-Open vs Fail-Closed: Production API gateways typically fail-open during total Redis outages to preserve availability for legitimate traffic.",
        ],
        failure_considerations=[
            "Redis Cluster Partition / Outage: Edge gateway falls back to local in-memory token bucket quotas with relaxed thresholds to avoid blocking all traffic.",
            "Thundering Herd on Expired Keys: Atomic Lua script execution ensures get-and-increment operations execute in a single roundtrip without race conditions.",
            "Client Clock Skew: Timestamps must be generated from server/Redis cluster clock rather than client headers.",
        ],
        scaling_considerations=[
            "Partition Redis keys by client_id or tenant_id with consistent hashing to balance load across Redis cluster shards.",
            "Asynchronous batch synchronization between edge points of presence (PoPs) and central cache for multi-region coordination.",
        ],
    ),
    "sys.sr.collab.core.01": SystemDesignReferenceArchitecture(
        scenario_id="sys.sr.collab.core.01",
        title="Real-time Collaborative Document Engine (CRDTs + WebSockets)",
        description="Low-latency collaborative document architecture using bidirectional WebSockets, Redis Pub/Sub presence fan-out, and conflict-free replicated data types.",
        nodes=[
            ArchitectureNode(id="client_a", label="Collaborator Clients (Web/Mobile)", type="client", purpose="Renders document model, captures local keystroke operations, and applies remote CRDT state vectors.", is_core=True),
            ArchitectureNode(id="ws_gateway", label="WebSocket Gateway Cluster", type="gateway", purpose="Terminates persistent full-duplex WebSocket connections and authenticates document sessions.", is_core=True),
            ArchitectureNode(id="redis_pubsub", label="Redis Pub/Sub & Presence Broker", type="cache", purpose="Distributes real-time cursor positions, user awareness, and broadcast operational changes across gateway servers.", is_core=True),
            ArchitectureNode(id="crdt_coordinator", label="Document Coordinator & CRDT Engine", type="service", purpose="Validates document operations, resolves state vector convergence, and manages periodic compaction.", is_core=True),
            ArchitectureNode(id="snapshot_db", label="Document Snapshot & Revision Store", type="database", purpose="Persists periodic immutable document snapshots and append-only edit logs in PostgreSQL / S3.", is_core=True),
            ArchitectureNode(id="analytics_stream", label="Document Event Analytics", type="queue", purpose="Streams document audit history and collaboration telemetry to data lake.", is_core=False),
        ],
        edges=[
            ArchitectureEdge(source="client_a", target="ws_gateway", label="Bidirectional Delta Streams", protocol="ws", mode="sync"),
            ArchitectureEdge(source="ws_gateway", target="redis_pubsub", label="Broadcast Presence & Ops", protocol="redis", mode="async"),
            ArchitectureEdge(source="ws_gateway", target="crdt_coordinator", label="Forward Mutation Deltas", protocol="grpc", mode="sync"),
            ArchitectureEdge(source="crdt_coordinator", target="snapshot_db", label="Periodic Snapshot & Write Log", protocol="sql", mode="async"),
            ArchitectureEdge(source="crdt_coordinator", target="analytics_stream", label="Audit Event Streaming", protocol="kafka", mode="async"),
        ],
        key_tradeoffs=[
            "CRDT (Conflict-Free Replicated Data Types) vs OT (Operational Transformation): CRDTs support peer-to-peer and offline-first merging without central server transformation locks, but consume more metadata memory.",
            "WebSocket Sticky Sessions vs Shared Presence Bus: Stateful WebSocket connections require a distributed Pub/Sub layer (Redis/NATS) so collaborators connected to different gateway servers see instant updates.",
            "Continuous Persistence vs Periodic Snapshot Compaction: Writing every keystroke to disk causes I/O exhaustion; periodically persisting compressed state snapshots with write-ahead logs optimizes throughput.",
        ],
        failure_considerations=[
            "Offline Reconnection & State Catch-up: Client sends local state vector upon reconnection; coordinator returns only missing deltas rather than the entire document.",
            "WebSocket Server Termination: Clients implement exponential backoff reconnection and immediately re-subscribe to document channel.",
            "Document Memory Bloat: CRDT tombstone garbage collection and milestone snapshot compaction prevent unbounded memory growth.",
        ],
        scaling_considerations=[
            "Shard document rooms across coordinator nodes using consistent hashing on document_id.",
            "Decouple high-frequency transient cursor movements from persistent textual state updates.",
        ],
    ),
    "be.sr.event.core.01": SystemDesignReferenceArchitecture(
        scenario_id="be.sr.event.core.01",
        title="Transactional Outbox Pattern & Reliable Event Streaming",
        description="Guaranteed at-least-once distributed event publishing eliminating dual-write inconsistencies between relational databases and Kafka brokers.",
        nodes=[
            ArchitectureNode(id="api_client", label="API Client / Frontend", type="client", purpose="Submits business transactions (e.g. order checkout, user registration).", is_core=True),
            ArchitectureNode(id="order_service", label="Domain Application Service", type="service", purpose="Executes business logic and commits entity state alongside event messages in a single DB transaction.", is_core=True),
            ArchitectureNode(id="primary_db", label="Relational Database (Entity + Outbox Table)", type="database", purpose="Stores domain entities (e.g. orders) and pending event records in atomic outbox table.", is_core=True),
            ArchitectureNode(id="cdc_poller", label="Outbox Relay / Debezium CDC Engine", type="service", purpose="Captures new outbox rows via transaction log tailing (WAL / CDC) or indexed polling.", is_core=True),
            ArchitectureNode(id="kafka_broker", label="Kafka Message Broker", type="queue", purpose="Partitioned, durable event stream delivering domain events to downstream consumers.", is_core=True),
            ArchitectureNode(id="downstream_consumer", label="Idempotent Downstream Consumer", type="service", purpose="Consumes domain events, performs deduplication with processed message keys, and updates downstream state.", is_core=True),
        ],
        edges=[
            ArchitectureEdge(source="api_client", target="order_service", label="Create Order Request", protocol="https", mode="sync"),
            ArchitectureEdge(source="order_service", target="primary_db", label="Atomic Multi-Table Commit (Order + Outbox)", protocol="sql", mode="sync"),
            ArchitectureEdge(source="cdc_poller", target="primary_db", label="Read Outbox via WAL / Polling", protocol="sql", mode="sync"),
            ArchitectureEdge(source="cdc_poller", target="kafka_broker", label="Publish Event with At-Least-Once Guarantee", protocol="kafka", mode="async"),
            ArchitectureEdge(source="kafka_broker", target="downstream_consumer", label="Partitioned Event Consumption", protocol="kafka", mode="async"),
        ],
        key_tradeoffs=[
            "Transactional Outbox vs Direct Dual Write: Direct dual writes suffer from split-brain when Kafka or DB fails after the first write; Outbox guarantees database-level atomicity.",
            "CDC (Change Data Capture / Debezium) vs Polling Publisher: CDC reads database transaction logs (WAL) without query overhead or lock contention; polling is simpler but adds database query load.",
            "At-Least-Once Delivery vs Exactly-Once: Outbox guarantees at-least-once delivery; consumers must be idempotent to handle network duplicate deliveries safely.",
        ],
        failure_considerations=[
            "Kafka Broker Temporary Outage: Outbox rows remain safely stored in the database outbox table until Kafka recovers, preventing data loss.",
            "Duplicate Event Delivery: Downstream consumers store processed event_id in a unique database deduplication table within the consumer transaction.",
            "Outbox Table Growth: Automated background cleanup worker deletes processed outbox rows older than retention TTL to keep index size small.",
        ],
        scaling_considerations=[
            "Partition Kafka topics by entity_id (e.g. order_id) to guarantee strict in-order processing per entity across consumer threads.",
            "Use log-based CDC (Debezium/Postgres WAL) to eliminate polling query load on primary database tables.",
        ],
    ),
    "be.sr.data.core.01": SystemDesignReferenceArchitecture(
        scenario_id="be.sr.data.core.01",
        title="Distributed Database Sharding & Replication Topology",
        description="Horizontal data partitioning architecture with consistent hashing routers, primary-replica replication, and read-after-write consistency.",
        nodes=[
            ArchitectureNode(id="api_layer", label="Application API Layer", type="service", purpose="Handles client requests and delegates data operations with partition keys.", is_core=True),
            ArchitectureNode(id="shard_router", label="Shard Routing & Proxy Layer (e.g. Vitess)", type="gateway", purpose="Evaluates shard key with consistent hashing and routes queries to target shard primary or replicas.", is_core=True),
            ArchitectureNode(id="shard_1_primary", label="Shard 1 Primary (Writes)", type="database", purpose="Handles ACID writes and primary lookups for partition range 0-33%.", is_core=True),
            ArchitectureNode(id="shard_1_replica", label="Shard 1 Read Replicas", type="database", purpose="Asynchronously replicated nodes serving high-volume read queries for Shard 1.", is_core=True),
            ArchitectureNode(id="shard_2_primary", label="Shard 2 Primary (Writes)", type="database", purpose="Handles ACID writes and primary lookups for partition range 34-67%.", is_core=True),
            ArchitectureNode(id="shard_3_primary", label="Shard 3 Primary (Writes)", type="database", purpose="Handles ACID writes and primary lookups for partition range 68-100%.", is_core=True),
        ],
        edges=[
            ArchitectureEdge(source="api_layer", target="shard_router", label="SQL Query + Shard Key (user_id)", protocol="sql", mode="sync"),
            ArchitectureEdge(source="shard_router", target="shard_1_primary", label="Route Write / Master Read", protocol="sql", mode="sync"),
            ArchitectureEdge(source="shard_router", target="shard_1_replica", label="Route Scaled Read Queries", protocol="sql", mode="sync"),
            ArchitectureEdge(source="shard_1_primary", target="shard_1_replica", label="Async Binary Replication Stream", protocol="sql", mode="async"),
            ArchitectureEdge(source="shard_router", target="shard_2_primary", label="Route Partition Writes", protocol="sql", mode="sync"),
            ArchitectureEdge(source="shard_router", target="shard_3_primary", label="Route Partition Writes", protocol="sql", mode="sync"),
        ],
        key_tradeoffs=[
            "Range-Based Sharding vs Hash-Based Sharding: Hash-based sharding with consistent hashing avoids write hotspots by distributing uniformly; range-based simplifies range queries but creates hot partitions.",
            "Cross-Shard Joins vs Denormalization: Cross-shard joins require expensive 2-phase query coordination across network boundaries; denormalizing data co-locates related data on the same shard.",
            "Strong Consistency vs Replication Lag: Routing reads to replicas reduces master load but introduces replication lag; use session consistency tokens to route read-after-write to primary.",
        ],
        failure_considerations=[
            "Primary Shard Node Hardware Failure: Automated failover orchestrator (e.g. Orchestrator/Patroni) promotes in-sync replica to primary with zero data loss.",
            "Replication Lag Spikes: Shard proxy monitors replica lag and temporarily removes degraded replicas from read routing pool.",
            "Hotspot on Popular Entity (Celebrity Problem): Salt high-traffic shard keys with random suffix to spread heavy write volume across multiple sub-shards.",
        ],
        scaling_considerations=[
            "Use consistent hashing with virtual nodes (vnodes) to add new physical database shards with minimal data migration.",
            "Maintain global lookup secondary index tables in distributed key-value stores for queries without primary shard keys.",
        ],
    ),
    "be.sr.ha.core.01": SystemDesignReferenceArchitecture(
        scenario_id="be.sr.ha.core.01",
        title="Active-Active Multi-Region High Availability & Quorum Architecture",
        description="Global multi-region topology with latency-based GeoDNS, distributed consensus quorum, conflict resolution, and adaptive load shedding.",
        nodes=[
            ArchitectureNode(id="global_users", label="Global Client Base", type="client", purpose="Issues requests globally across Americas, EMEA, and APAC regions.", is_core=True),
            ArchitectureNode(id="geodns_routing", label="Anycast & GeoDNS Routing Layer (Route53/Cloudflare)", type="gateway", purpose="Routes traffic to closest healthy regional cluster based on latency and health checks.", is_core=True),
            ArchitectureNode(id="region_a_cluster", label="Region A Cluster (US-East)", type="service", purpose="Active application services and ingress gateway in primary region.", is_core=True),
            ArchitectureNode(id="region_b_cluster", label="Region B Cluster (EU-West)", type="service", purpose="Active application services and ingress gateway in secondary region.", is_core=True),
            ArchitectureNode(id="distributed_db", label="Multi-Region Distributed Database (CockroachDB / Spanner)", type="database", purpose="Distributed Raft/Paxos consensus storage providing serializable multi-region consistency.", is_core=True),
            ArchitectureNode(id="load_shedder", label="Adaptive Load Shedding & Health Monitor", type="service", purpose="Monitors CPU/p99 latency saturation and sheds low-priority traffic during regional failover spikes.", is_core=True),
        ],
        edges=[
            ArchitectureEdge(source="global_users", target="geodns_routing", label="Global HTTPS Requests", protocol="https", mode="sync"),
            ArchitectureEdge(source="geodns_routing", target="region_a_cluster", label="Geo-Routed Traffic (US Clients)", protocol="https", mode="sync"),
            ArchitectureEdge(source="geodns_routing", target="region_b_cluster", label="Geo-Routed Traffic (EU Clients)", protocol="https", mode="sync"),
            ArchitectureEdge(source="region_a_cluster", target="distributed_db", label="Quorum Reads / Writes", protocol="sql", mode="sync"),
            ArchitectureEdge(source="region_b_cluster", target="distributed_db", label="Quorum Reads / Writes", protocol="sql", mode="sync"),
            ArchitectureEdge(source="load_shedder", target="region_a_cluster", label="Telemetry & Throttling Feedback", protocol="grpc", mode="sync"),
        ],
        key_tradeoffs=[
            "Active-Active vs Active-Passive: Active-Active maximizes resource utilization and achieves near-zero RTO, but requires handling cross-region consistency and conflict resolution.",
            "Synchronous Quorum vs Asynchronous Replication: Synchronous consensus (Raft/Paxos) prevents data loss (RPO=0) at the cost of cross-region network latency (100ms+ roundtrips); async replication reduces latency but risks data loss during regional outages.",
            "Rate Limiting vs Load Shedding: Rate limiting drops traffic based on caller identity quotas; load shedding drops non-essential requests based on internal CPU/queue depth to protect core infrastructure.",
        ],
        failure_considerations=[
            "Total Cloud Region Outage: GeoDNS health checks detect consecutive probe failures and automatically divert traffic to surviving region.",
            "Regional Network Partition (Split-Brain): Raft consensus requires strict majority quorum (e.g. 2 out of 3 regions) before committing writes, preventing diverging state.",
            "Cascading Failure Surge: When Region A fails, Region B receives 2x traffic; adaptive load shedding rejects background/batch requests to keep checkout services responsive.",
        ],
        scaling_considerations=[
            "Locate quorum tie-breaker witness nodes in a third lightweight cloud region to avoid split-brain ties.",
            "Use read-local data pinning (interleaved tables) for region-specific user data to achieve single-digit millisecond read latencies.",
        ],
    ),
    "sys.mid.url.core.01": SystemDesignReferenceArchitecture(
        scenario_id="sys.mid.url.core.01",
        title="High-Throughput Distributed URL Shortener (Base62 + Redis Caching)",
        description="Low-latency URL shortening system with distributed Base62 key generation, multi-tier cache-aside layer, and persistent key-value storage.",
        nodes=[
            ArchitectureNode(id="web_clients", label="Web & Mobile Clients", type="client", purpose="Requests short URL creation (POST) and link redirections (GET /xyz).", is_core=True),
            ArchitectureNode(id="api_gateway", label="API Gateway & Load Balancer", type="gateway", purpose="Terminates HTTPS, applies IP rate limiting, and routes read/write endpoints.", is_core=True),
            ArchitectureNode(id="url_service", label="URL Application Service", type="service", purpose="Orchestrates Base62 encoding, custom alias validation, and cache-aside read/write logic.", is_core=True),
            ArchitectureNode(id="id_generator", label="Unique ID Generator (Snowflake / ZooKeeper)", type="service", purpose="Generates monotonically increasing 64-bit unique IDs for Base62 encoding without collision.", is_core=True),
            ArchitectureNode(id="redis_cache", label="Distributed Redis Cache (LRU Eviction)", type="cache", purpose="Caches hot short-to-long URL mappings in memory for sub-5ms 301/302 redirect responses.", is_core=True),
            ArchitectureNode(id="persistent_db", label="Persistent URL Store (PostgreSQL / DynamoDB)", type="database", purpose="Durable primary store containing full short_url, original_url, created_at, and user_id mapping.", is_core=True),
            ArchitectureNode(id="analytics_queue", label="Click Analytics Stream (Kafka)", type="queue", purpose="Asynchronously logs redirect click events, geolocation, and referrers without adding redirect latency.", is_core=False),
        ],
        edges=[
            ArchitectureEdge(source="web_clients", target="api_gateway", label="POST /shorten & GET /{short_code}", protocol="https", mode="sync"),
            ArchitectureEdge(source="api_gateway", target="url_service", label="Route Request", protocol="http", mode="sync"),
            ArchitectureEdge(source="url_service", target="id_generator", label="Fetch Next Unique ID", protocol="grpc", mode="sync"),
            ArchitectureEdge(source="url_service", target="redis_cache", label="Check Cache / Populate on Miss", protocol="redis", mode="sync"),
            ArchitectureEdge(source="url_service", target="persistent_db", label="Persist Record / Lookup Miss", protocol="sql", mode="sync"),
            ArchitectureEdge(source="url_service", target="analytics_queue", label="Emit Redirect Click Event", protocol="kafka", mode="async"),
        ],
        key_tradeoffs=[
            "Base62 Encoding vs MD5/SHA256 Hashing: Base62 encoding sequential IDs produces fixed 6-7 character strings with zero hash collisions; MD5/SHA256 requires truncation and collision retry loops.",
            "HTTP 301 (Permanent) vs HTTP 302 (Found): 301 redirects are cached in browser saving backend requests, but prevent tracking click analytics; 302 forces requests to hit server for accurate metrics.",
            "Cache-Aside vs Read-Through: Cache-aside allows fine-grained TTL management and graceful database fallback on cache miss.",
        ],
        failure_considerations=[
            "Cache Stampede on Viral Link: Use distributed locks or probabilistic early cache refresh (XFetch) to prevent thousands of simultaneous DB queries when a viral link's cache key expires.",
            "ID Generator Node Failure: Use distributed Snowflake ID generators with distinct worker machine IDs so any available node can generate collision-free IDs independently.",
            "Database Scale Bottleneck: Partition persistent storage by short_hash prefix or use horizontally scalable NoSQL (DynamoDB/Cassandra) with hash key on short_code.",
        ],
        scaling_considerations=[
            "80-20 Rule (Pareto Principle): Caching the top 20% most popular short links in Redis serves 80% of all read traffic from memory.",
            "Asynchronously offload click tracking to Kafka to ensure redirect response times stay under 15ms.",
        ],
    ),
    "sys.mid.notify.core.01": SystemDesignReferenceArchitecture(
        scenario_id="sys.mid.notify.core.01",
        title="Scalable Multi-Channel Notification Engine (Priority Queues + Rate Limits)",
        description="High-throughput multi-channel notification architecture with channel-isolated priority queues, provider circuit breakers, and user preference rate limiting.",
        nodes=[
            ArchitectureNode(id="internal_services", label="Triggering Services (Order, Auth, Marketing)", type="service", purpose="Submits notification requests (e.g. OTP SMS, Order confirmation email, Push notification).", is_core=True),
            ArchitectureNode(id="notify_api", label="Notification Ingress API & Validator", type="gateway", purpose="Validates notification payloads, deduplicates idempotent request tokens, and evaluates user opt-outs.", is_core=True),
            ArchitectureNode(id="user_prefs_db", label="User Preferences & Rate Limit Cache", type="cache", purpose="Checks user frequency caps (e.g. max 3 marketing emails/day) and communication preferences.", is_core=True),
            ArchitectureNode(id="priority_queues", label="Channel & Priority Message Queues (Kafka / RabbitMQ)", type="queue", purpose="Isolated queues partitioned by channel (SMS, Email, Push) and priority (Critical vs Marketing).", is_core=True),
            ArchitectureNode(id="sms_workers", label="SMS Dispatch Workers & Token Bucket", type="service", purpose="Consumes SMS queue, applies Twilio provider rate limits, and dispatches SMS messages.", is_core=True),
            ArchitectureNode(id="email_workers", label="Email Dispatch Workers & Pool", type="service", purpose="Consumes Email queue, renders HTML templates, and calls SendGrid/SES.", is_core=True),
            ArchitectureNode(id="push_workers", label="Push Notification Workers (APNs/FCM)", type="service", purpose="Consumes Push queue, packages platform payloads, and communicates with Apple APNs / Google FCM.", is_core=True),
            ArchitectureNode(id="external_providers", label="Third-Party Gateways (Twilio, SES, APNs)", type="external", purpose="External carrier and cloud gateway providers delivering final messages to end users.", is_core=True),
        ],
        edges=[
            ArchitectureEdge(source="internal_services", target="notify_api", label="POST /notify (Event Payload)", protocol="https", mode="sync"),
            ArchitectureEdge(source="notify_api", target="user_prefs_db", label="Check Opt-In & Frequency Caps", protocol="redis", mode="sync"),
            ArchitectureEdge(source="notify_api", target="priority_queues", label="Enqueue to Target Channel Topic", protocol="kafka", mode="async"),
            ArchitectureEdge(source="priority_queues", target="sms_workers", label="Consume Critical SMS Messages", protocol="kafka", mode="async"),
            ArchitectureEdge(source="priority_queues", target="email_workers", label="Consume Email Queue", protocol="kafka", mode="async"),
            ArchitectureEdge(source="priority_queues", target="push_workers", label="Consume Mobile Push Queue", protocol="kafka", mode="async"),
            ArchitectureEdge(source="sms_workers", target="external_providers", label="Dispatch via Provider API", protocol="https", mode="sync"),
            ArchitectureEdge(source="email_workers", target="external_providers", label="Dispatch via Provider API", protocol="https", mode="sync"),
            ArchitectureEdge(source="push_workers", target="external_providers", label="Dispatch via Provider API", protocol="https", mode="sync"),
        ],
        key_tradeoffs=[
            "Single Unified Queue vs Channel-Isolated Queues: A single queue causes slow email providers to stall urgent OTP SMS; channel isolation guarantees critical SMS bypasses marketing email backlogs.",
            "Synchronous Provider Calls vs Asynchronous Queue Dispatch: Synchronous calls lock API threads during external provider latency; asynchronous queueing decouples client response times from delivery delays.",
            "Immediate Retry vs Dead-Letter Queue with Exponential Backoff: Naive immediate retries trigger provider rate-limit penalties; exponential backoff with jitter and DLQ protects system stability.",
        ],
        failure_considerations=[
            "Third-Party Provider Outage (e.g. Twilio Down): Circuit breakers trip, routing pending SMS to secondary backup provider (e.g. AWS SNS) or dead-letter queue.",
            "Notification Thundering Herd (Flash Sale Event): Rate-limiting token buckets at the worker layer pace outbound API calls to stay strictly within provider SLA limits.",
            "Duplicate Message Prevention: Notification API checks Redis deduplication key (hash of user_id + event_type + timestamp_window) before enqueuing.",
        ],
        scaling_considerations=[
            "Scale worker pools independently based on queue lag metrics (e.g. scale push workers up during marketing campaigns without touching SMS workers).",
            "Store static email/notification templates in memory or CDN and compile with dynamic variables on worker nodes.",
        ],
    ),
    "be.sr.arch.core.01": SystemDesignReferenceArchitecture(
        scenario_id="be.sr.arch.core.01",
        title="Distributed Saga Pattern & Microservices Event Orchestration",
        description="Eventual consistency orchestration architecture managing multi-service distributed transactions with compensating rollback workflows.",
        nodes=[
            ArchitectureNode(id="checkout_client", label="Client Checkout Application", type="client", purpose="Initiates multi-step purchase workflow across inventory, payment, and fulfillment.", is_core=True),
            ArchitectureNode(id="api_gateway", label="API Gateway", type="gateway", purpose="Authenticates client and forwards checkout request to Saga Orchestrator.", is_core=True),
            ArchitectureNode(id="saga_orchestrator", label="Saga Orchestrator Service", type="service", purpose="State machine managing step execution, transaction logs, and coordinating compensating rollback events.", is_core=True),
            ArchitectureNode(id="inventory_service", label="Inventory Microservice & DB", type="service", purpose="Reserves product stock; executes reverse compensation (release stock) upon failure.", is_core=True),
            ArchitectureNode(id="payment_service", label="Payment Microservice & DB", type="service", purpose="Charges customer payment method; executes refund compensation upon downstream failure.", is_core=True),
            ArchitectureNode(id="shipping_service", label="Shipping & Fulfillment Service", type="service", purpose="Generates shipping label and assigns courier for delivery.", is_core=True),
            ArchitectureNode(id="saga_state_db", label="Saga State Store & Event Log", type="database", purpose="Durable state store recording current step, status (started, pending, compensated), and payload.", is_core=True),
        ],
        edges=[
            ArchitectureEdge(source="checkout_client", target="api_gateway", label="POST /checkout", protocol="https", mode="sync"),
            ArchitectureEdge(source="api_gateway", target="saga_orchestrator", label="Start Checkout Saga", protocol="grpc", mode="sync"),
            ArchitectureEdge(source="saga_orchestrator", target="saga_state_db", label="Log Saga Step State", protocol="sql", mode="sync"),
            ArchitectureEdge(source="saga_orchestrator", target="inventory_service", label="1. Reserve Inventory (Compensate: Release)", protocol="grpc", mode="sync"),
            ArchitectureEdge(source="saga_orchestrator", target="payment_service", label="2. Process Payment (Compensate: Refund)", protocol="grpc", mode="sync"),
            ArchitectureEdge(source="saga_orchestrator", target="shipping_service", label="3. Create Shipment", protocol="grpc", mode="sync"),
        ],
        key_tradeoffs=[
            "Saga Orchestration vs Saga Choreography: Orchestration centralizes transaction flow in a state machine (easy to trace, test, and debug); choreography uses event broadcasting (loosely coupled but harder to monitor and debug).",
            "Saga (Eventual Consistency) vs Two-Phase Commit (2PC): 2PC holds blocking database locks across services leading to latency spikes and single points of failure; Saga executes local transactions with semantic compensations.",
            "Pivot Step Identification: Placing non-reversible operations (e.g. shipping dispatch) after guaranteed reversible steps (e.g. inventory reservation) ensures clean compensation paths.",
        ],
        failure_considerations=[
            "Step Failure in Multi-Step Workflow: If Step 3 (Shipping) fails, the orchestrator executes compensating actions in reverse order: refunds payment (Step 2), then releases inventory (Step 1).",
            "Orchestrator Crash Mid-Transaction: On restart, orchestrator polls durable saga state store and resumes pending sagas from the last committed step.",
            "Idempotency of Compensating Actions: Compensating endpoints (e.g. refund, release stock) must be strictly idempotent to safely allow automated retries.",
        ],
        scaling_considerations=[
            "Asynchronously execute independent parallel steps within a saga (e.g. reserve inventory and check fraud score concurrently) before proceeding to payment.",
            "Use lightweight distributed event streams (Kafka/RabbitMQ) for communication between orchestrator and microservices to handle high transaction volumes.",
        ],
    ),
}

# Alias mapping for probes and variants
SYSTEM_DESIGN_SCENARIO_ALIASES: Dict[str, str] = {
    "sys.sr.ratelimit.probe.01": "sys.sr.ratelimit.core.01",
    "sys.sr.collab.probe.01": "sys.sr.collab.core.01",
    "be.sr.event.probe.01": "be.sr.event.core.01",
    "be.sr.data.probe.01": "be.sr.data.core.01",
    "be.sr.ha.probe.01": "be.sr.ha.core.01",
    "sys.mid.url.probe.01": "sys.mid.url.core.01",
    "sys.mid.notify.probe.01": "sys.mid.notify.core.01",
    "be.sr.arch.probe.01": "be.sr.arch.core.01",
}


def resolve_system_design_blueprint(
    question_id: Optional[str] = None,
    question_text: Optional[str] = None,
    primary_concept: Optional[str] = None,
    intent: Optional[str] = None,
) -> Optional[SystemDesignReferenceArchitecture]:
    """Deterministically resolve a System Design Reference Architecture Blueprint if the turn matches a curated scenario.
    
    Returns None for technical core, behavioral, or unsupported scenarios (graceful degradation).
    """
    # 1. Exact or alias ID match
    if question_id:
        clean_qid = question_id.strip()
        if clean_qid in SYSTEM_DESIGN_BLUEPRINT_CATALOG:
            return SYSTEM_DESIGN_BLUEPRINT_CATALOG[clean_qid]
        if clean_qid in SYSTEM_DESIGN_SCENARIO_ALIASES:
            target_id = SYSTEM_DESIGN_SCENARIO_ALIASES[clean_qid]
            return SYSTEM_DESIGN_BLUEPRINT_CATALOG.get(target_id)

    # 2. Text / Concept semantic matching
    text_corpus = f"{question_text or ''} {primary_concept or ''}".lower()

    if any(k in text_corpus for k in ["rate limiter", "rate limiting", "sliding window counter"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]

    if any(k in text_corpus for k in ["collaborative doc", "google docs", "crdt", "operational transformation", "real-time collaborative"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.collab.core.01"]

    if any(k in text_corpus for k in ["transactional outbox", "outbox pattern", "dual-write", "dual write"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["be.sr.event.core.01"]

    if any(k in text_corpus for k in ["sharding", "database sharding", "partition key", "cross-shard"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["be.sr.data.core.01"]

    if any(k in text_corpus for k in ["active-active", "multi-region", "split-brain", "disaster recovery & multi-region"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["be.sr.ha.core.01"]

    if any(k in text_corpus for k in ["url shorten", "tinyurl", "base62"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.mid.url.core.01"]

    if any(k in text_corpus for k in ["notification service", "notification engine", "push notification", "multi-channel notification"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.mid.notify.core.01"]

    if any(k in text_corpus for k in ["saga pattern", "saga orchestrat", "compensating transaction", "distributed transaction"]):
        return SYSTEM_DESIGN_BLUEPRINT_CATALOG["be.sr.arch.core.01"]

    return None


def sanitize_untrusted_text(text: Optional[str]) -> str:
    """Sanitize untrusted candidate, resume, or JD text to prevent prompt injection and delimiter breakout."""
    if not text:
        return ""
    # Strip dangerous instruction injection keywords and control tags
    sanitized = re.sub(
        r"(ignore\s+(all\s+)?previous\s+instructions|system\s+instruction|system\s+prompt|disregard\s+instructions|override\s+evaluation|give\s+100|rate\s+100|---\s*system:)",
        "[REDACTED_INJECTION_ATTEMPT]",
        text,
        flags=re.IGNORECASE,
    )
    # Strip markdown block breakout tags
    sanitized = re.sub(r"```", "'''", sanitized)
    sanitized = re.sub(r"</?[a-zA-Z0-9_-]+>", "", sanitized)
    return sanitized.strip()


def extract_expected_concepts_from_text(
    ideal_answer: str,
    primary_concept: str,
    intent: str = "core_skill",
) -> List[ExpectedConcept]:
    """Deterministically extract structured ExpectedConcept items with CORE and SUPPORTING tiers."""
    concepts: List[ExpectedConcept] = []
    seen_names: Set[str] = set()

    safe_ideal = ideal_answer if isinstance(ideal_answer, str) else ""
    safe_primary = primary_concept if isinstance(primary_concept, str) else ""

    # 1. Check curated registry first
    norm_primary = safe_primary.strip().lower()
    if norm_primary:
        for key, curated_list in CURATED_QUESTION_CONCEPTS.items():
            if key in norm_primary or norm_primary in key:
                for name, imp, desc in curated_list:
                    seen_names.add(name.lower())
                    concepts.append(
                        ExpectedConcept(concept=name, importance=imp, description=desc)
                    )
            if concepts:
                return concepts

    # 2. Deterministically parse clauses from ideal_answer
    if safe_ideal and safe_ideal.strip():
        # Split on sentence boundaries and list markers
        clauses = re.split(r"[.;\n]|,\s*(?:while|whereas|including|such as|and|covering)\s*", safe_ideal)
        for idx, clause in enumerate(clauses):
            c_clean = clause.strip()
            # Must be a substantive phrase (2 to 14 words)
            words = c_clean.split()
            if 2 <= len(words) <= 14:
                # Clean leading prepositions/conjunctions
                c_clean = re.sub(r"^(and|while|whereas|including|such as|using|covering|to|for|with)\s+", "", c_clean, flags=re.IGNORECASE)
                c_clean = c_clean.capitalize()
                if c_clean.lower() not in seen_names and len(c_clean) >= 6:
                    seen_names.add(c_clean.lower())
                    # First 2 parsed clauses are CORE, subsequent are SUPPORTING
                    imp = ConceptImportance.CORE if len(concepts) < 2 else ConceptImportance.SUPPORTING
                    concepts.append(
                        ExpectedConcept(
                            concept=c_clean,
                            importance=imp,
                            description=f"Technical detail: {c_clean}",
                        )
                    )
            if len(concepts) >= 4:
                break

    # 3. Add Primary Concept as CORE if specific and not generic placeholder
    if safe_primary and safe_primary.strip() and safe_primary.strip() not in ("Engineering Competency", "Targeted Probing Analysis"):
        primary_clean = safe_primary.strip()
        if primary_clean.lower() not in seen_names:
            seen_names.add(primary_clean.lower())
            concepts.insert(
                0,
                ExpectedConcept(
                    concept=primary_clean,
                    importance=ConceptImportance.CORE,
                    description=f"Core conceptual understanding of {primary_clean}.",
                ),
            )
    elif not concepts and safe_primary:
        concepts.append(
            ExpectedConcept(
                concept=safe_primary.strip(),
                importance=ConceptImportance.CORE,
                description=f"Core conceptual understanding of {safe_primary.strip()}.",
            )
        )

    return concepts


def build_rubric_for_intent(
    intent: str,
    question_text: str,
    ideal_answer: str,
    primary_concept: str,
    expected_concepts: List[ExpectedConcept],
) -> EvaluationRubric:
    """Construct an intent-calibrated evaluation rubric with clear tier characteristics."""
    norm_intent = (intent or "core_skill").lower().strip()

    if norm_intent in ("resume_project", "project_deep_dive", "project_architecture"):
        return EvaluationRubric(
            question_intent="project_deep_dive",
            expected_knowledge="Architecture breakdown, component boundaries, data flow, candidate ownership, and trade-offs.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Clearly articulates component architecture, data flow, and technology choices.",
                "Demonstrates authentic ownership by explaining implementation decisions, trade-offs, and failure handling.",
                "Explains edge-case handling, performance bottlenecks, and concrete outcomes.",
            ],
            partial_indicators=[
                "Describes high-level tech stack and responsibilities but lacks architectural depth or failure mitigation details.",
                "Mentions the chosen solution without explaining the underlying trade-offs or technical challenges.",
            ],
            weak_indicators=[
                "Provides vague or generic summary with unsubstantiated claims or buzzwords without demonstrable system design understanding or clear individual contribution.",
            ],
            incorrect_indicators=[
                "Misrepresents fundamental technology behaviors or claims technically contradictory implementations.",
            ],
            irrelevant_indicators=[
                "Discusses unrelated projects or technologies not requested in the prompt.",
            ],
        )

    elif norm_intent in ("work_experience", "production_milestone"):
        return EvaluationRubric(
            question_intent="work_experience",
            expected_knowledge="Production engineering capability, incident mitigation, operational metrics, and reliability.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Structures response logically (problem context, technical root-cause, mitigation, and measurable results).",
                "Demonstrates strong production engineering instincts (observability, rollback safety, latency budgets).",
            ],
            partial_indicators=[
                "Explains the problem at a high level but omits concrete technical troubleshooting steps or operational impact.",
            ],
            weak_indicators=[
                "Generic recitation of routine job duties without deep engineering ownership or problem-solving evidence.",
            ],
            incorrect_indicators=[
                "Describes unsafe production practices or factually flawed recovery approaches.",
            ],
            irrelevant_indicators=[
                "Evades the operational challenge question and discusses unrelated topics.",
            ],
        )

    elif norm_intent in ("system_design", "scenario", "practical_scenario"):
        return EvaluationRubric(
            question_intent=norm_intent,
            expected_knowledge="Scalability trade-offs, bottleneck identification, data consistency, caching, and fault isolation.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Employs hypothesis-driven triage, observability, log/metric analysis, and systematic root-cause isolation.",
                "Analyzes horizontal vs vertical scalability, database read/write bottlenecks, and caching invalidation.",
                "Proposes resilient mitigations with clear trade-offs and zero-regression testing.",
            ],
            partial_indicators=[
                "Proposes standard fixes (e.g. 'add more servers' or 'add caching') without analyzing root causes or trade-offs.",
            ],
            weak_indicators=[
                "Guesses random components without structured diagnostic reasoning or architectural justification.",
            ],
            incorrect_indicators=[
                "Proposes architectures that introduce single points of failure, data corruption, or distributed deadlocks.",
            ],
            irrelevant_indicators=[
                "Ignores the scenario constraints and describes unrelated tools.",
            ],
        )

    elif norm_intent in ("behavioral", "leadership", "collaboration"):
        return EvaluationRubric(
            question_intent="behavioral",
            expected_knowledge="Engineering collaboration, conflict resolution, technical ownership, decision reasoning, and reflection.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Articulates clear context, specific personal ownership, decisive constructive actions, and quantifiable impact with mature reflection and growth takeaways.",
                "Demonstrates mature engineering empathy, constructive feedback incorporation, and retrospection.",
            ],
            partial_indicators=[
                "Describes team achievements without clarifying candidate's individual ownership or actions.",
            ],
            weak_indicators=[
                "Vague hypothetical answers rather than concrete lived engineering experiences.",
            ],
            incorrect_indicators=[
                "Exhibits blame-shifting, lack of accountability, or destructive team dynamics.",
            ],
            irrelevant_indicators=[
                "Answers an unrelated prompt.",
            ],
        )

    elif norm_intent in ("follow_up", "probing"):
        return EvaluationRubric(
            question_intent="follow_up",
            expected_knowledge="Specific deep-dive into the concrete mechanism, edge case, or trade-off raised in the probe.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Directly answers the targeted follow-up question with specific technical mechanisms and concrete patterns.",
                "Explains the underlying trade-off, edge case, or failure condition without dodging.",
            ],
            partial_indicators=[
                "Acknowledges the probed area but gives a surface-level response without mechanical depth.",
            ],
            weak_indicators=[
                "Repeats the initial core answer without providing any additional technical detail requested by the probe.",
            ],
            incorrect_indicators=[
                "Provides factually erroneous technical claims regarding the probed mechanism.",
            ],
            irrelevant_indicators=[
                "Pivots away from the follow-up question to an unrelated topic.",
            ],
        )

    else:
        # Default: CORE_SKILL / JD_REQUIREMENT / TECHNICAL_CORE
        return EvaluationRubric(
            question_intent="core_skill",
            expected_knowledge="Deep technical understanding of domain protocols, data structures, algorithms, and production performance patterns.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Technically accurate explanation of underlying mechanisms, internals, and execution flows.",
                "Addresses edge cases, performance implications, and practical production constraints.",
                "Concise and direct for factual questions (e.g. HTTP verbs, database types).",
            ],
            partial_indicators=[
                "Identifies main concepts and happy-path usage but omits internal mechanics or edge-case trade-offs.",
            ],
            weak_indicators=[
                "Vague dictionary definition without practical engineering depth or syntax clarity.",
            ],
            incorrect_indicators=[
                "States factually wrong definitions, incorrect algorithmic complexities, or invalid API semantics.",
            ],
            irrelevant_indicators=[
                "Explains a completely different framework, tool, or domain.",
            ],
        )


class ReferenceEvaluatorService:
    """Service governing evaluation reference payloads, expected concepts, and rubrics."""

    def resolve_reference_for_turn(
        self,
        question_text: Optional[str] = None,
        ideal_answer: Optional[str] = None,
        primary_concept: Optional[str] = None,
        question_intent: Optional[str] = None,
        question_id: Optional[str] = None,
        is_follow_up: bool = False,
        is_candidate_specific: bool = False,
        target_role: str = "Software Engineer",
        seniority_level: str = "mid",
        turn: Optional[Any] = None,
        parsed_jd_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
        focus_skills: Optional[List[str]] = None,
    ) -> QuestionReferencePayload:
        """Construct or resolve an authoritative QuestionReferencePayload.
        
        Zero Candidate Contamination: candidate_answer is NEVER accepted or used in reference generation.
        """
        # Handle case where turn object is passed as first positional argument
        if turn is None and question_text is not None and not isinstance(question_text, str) and hasattr(question_text, "question_text"):
            turn = question_text
            question_text = None

        if turn is not None:
            raw_q = getattr(turn, "question_text", "")
            if isinstance(raw_q, str) and raw_q.strip():
                question_text = question_text or raw_q

            raw_ia = getattr(turn, "ideal_answer", None)
            if isinstance(raw_ia, str) and raw_ia.strip():
                ideal_answer = ideal_answer or raw_ia

            raw_pc = getattr(turn, "primary_concept", None)
            if isinstance(raw_pc, str) and raw_pc.strip():
                primary_concept = primary_concept or raw_pc

            if getattr(turn, "question_type", None) == "follow_up":
                is_follow_up = True
            
            q_meta = getattr(turn, "question_metadata", None) or {}
            if isinstance(q_meta, dict):
                if not question_intent:
                    q_int = q_meta.get("question_intent") or q_meta.get("intent")
                    if isinstance(q_int, str) and q_int.strip():
                        question_intent = q_int
                if not primary_concept:
                    p_c = q_meta.get("primary_concept") or q_meta.get("competency")
                    if isinstance(p_c, str) and p_c.strip():
                        primary_concept = p_c
                if not ideal_answer:
                    i_a = q_meta.get("ideal_answer") or q_meta.get("reference_answer")
                    if isinstance(i_a, str) and i_a.strip():
                        ideal_answer = i_a
                if q_meta.get("is_candidate_specific"):
                    is_candidate_specific = True

            if not is_candidate_specific:
                ctx_id = getattr(turn, "context_item_id", None)
                if isinstance(ctx_id, str) and ctx_id.strip():
                    is_candidate_specific = True

        safe_q_str = question_text if isinstance(question_text, str) else ""
        clean_q = sanitize_untrusted_text(safe_q_str) or "Technical interview question."
        safe_intent_str = question_intent if isinstance(question_intent, str) else ""
        intent = "follow_up" if is_follow_up else (safe_intent_str or "core_skill")

        # Baseline reference answer
        safe_ia_str = ideal_answer if isinstance(ideal_answer, str) else ""
        ref_ans = (
            safe_ia_str.strip()
            if safe_ia_str and safe_ia_str.strip()
            else f"Senior-level benchmark response for {clean_q} covering core technical principles, architectural trade-offs, and failure handling."
        )

        safe_pc_str = primary_concept if isinstance(primary_concept, str) else ""
        prim_concept = (
            safe_pc_str.strip()
            if safe_pc_str and safe_pc_str.strip()
            else ("Targeted Probing Analysis" if is_follow_up else "Engineering Competency")
        )

        expected_concepts = extract_expected_concepts_from_text(
            ideal_answer=ref_ans,
            primary_concept=prim_concept,
            intent=intent,
        )

        rubric = build_rubric_for_intent(
            intent=intent,
            question_text=clean_q,
            ideal_answer=ref_ans,
            primary_concept=prim_concept,
            expected_concepts=expected_concepts,
        )

        source = "question_bank" if question_id else (
            "planner_archetype" if is_candidate_specific else "curated_deterministic"
        )

        # Educational Senior Reference Architecture Blueprint resolution
        arch_blueprint = resolve_system_design_blueprint(
            question_id=question_id,
            question_text=clean_q,
            primary_concept=prim_concept,
            intent=intent,
        )

        return QuestionReferencePayload(
            question_id=question_id,
            question_text=clean_q,
            question_intent=intent,
            reference_answer=ref_ans,
            primary_concept=prim_concept,
            expected_concepts=expected_concepts,
            rubric=rubric,
            architecture_blueprint=arch_blueprint,
            source=source,
            is_candidate_specific=is_candidate_specific,
        )


def get_reference_evaluator_service() -> ReferenceEvaluatorService:
    """Dependency provider for ReferenceEvaluatorService."""
    return ReferenceEvaluatorService()
