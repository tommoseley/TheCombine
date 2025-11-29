# Workbench AI — Complete Product Definition Export

**Generated:** 2024-11-29  
**Format:** Markdown  
**Contents:** Canonical Epic, Canonical Architecture, Canonical Backlog

---

## Table of Contents

1. [Canonical Epic](#canonical-epic)
2. [Canonical Architecture](#canonical-architecture)
3. [Canonical Backlog](#canonical-backlog)

---

# Canonical Epic

## Vision Statement

Workbench AI is a conversational AI-powered workspace that transforms product ideas into comprehensive, implementation-ready definitions through an orchestrated multi-agent workflow. Users describe their idea in natural language, answer clarifying questions, and receive a validated Epic, technical Architecture, and actionable Backlog—all generated through structured AI collaboration with human approval gates at each stage.

The platform serves solo founders, product managers, and small teams who need to rapidly validate and define product concepts without hiring a full product team. By combining PM discovery, architectural planning, and backlog generation into a single conversational experience, Workbench AI compresses weeks of definition work into hours while maintaining professional quality and traceability.

## Problem Statement / Opportunity

**Current Pain Points:**

Product definition is slow, expensive, and requires specialized expertise. Solo founders and small teams face a painful choice: either spend weeks learning product management best practices and writing specs themselves, or hire expensive consultants ($150-300/hour) to translate ideas into actionable plans. Existing tools (Jira, Linear, Notion) provide storage and organization but offer no intelligence—they're blank canvases that assume you already know what to build.

The result is that most early-stage ideas never get properly defined. Founders jump straight to coding without clarity on scope, architecture, or priorities, leading to expensive rewrites, scope creep, and abandoned projects. Even experienced PMs struggle with the repetitive mechanics of writing user stories, acceptance criteria, and traceability matrices.

**Market Opportunity:**

The product management software market is $2.3B and growing at 14% annually, but current tools are purely organizational—none offer AI-powered product definition. With 4.3M software developers worldwide and 50K+ new startups launched annually, there's a massive underserved market of builders who need product definition help but can't afford dedicated PMs.

Recent advances in LLMs (Claude Opus 4, GPT-4) enable conversational product discovery at quality levels approaching human experts. By orchestrating multiple specialized AI agents (PM, Architect, BA) with human approval gates, we can deliver professional-grade product definitions at 1/100th the cost of consultants while maintaining quality and enabling rapid iteration.

**Why This, Why Now:**

1. LLM capabilities have crossed the threshold for complex reasoning and structured output generation
2. No-code/low-code movement has created demand for faster ideation-to-implementation cycles
3. Remote work has normalized asynchronous, tool-based product collaboration
4. Developers increasingly work independently (freelance, solopreneurs) without access to PM resources

## Business Goals & Success Metrics

**Primary Goals:**

1. **Enable rapid product definition:** Reduce idea-to-backlog time from weeks to hours (target: <2 hours for complete workflow)
2. **Deliver professional quality:** Generate Epics, Architectures, and Backlogs that match or exceed junior PM output quality
3. **Achieve sustainable unit economics:** Maintain LLM costs below 20% of revenue per user ($5.80/month cost at $29/month price point)

**Success Metrics:**

- **Engagement:** 60% of users who start a workflow complete it to Backlog approval (primary conversion metric)
- **Quality:** 80% of users approve generated Epics on first attempt (indicates AI quality meets expectations)
- **Retention:** 40% monthly active user retention (users return to define multiple ideas)
- **Time-to-Value:** Median time from workspace creation to Backlog approval <90 minutes
- **Economics:** Gross margin >60% (revenue minus LLM API costs)

**Business Model:**

- **Pricing:** $29/month subscription (unlimited workspaces and generations within fair use limits)
- **Target Market:** Solo founders, indie hackers, freelance developers, early-stage startup teams (1-3 people)
- **GTM Strategy:** Product-led growth via developer communities (Indie Hackers, Reddit, Twitter), content marketing (case studies showing idea → production timelines)

## In Scope (Phase 1: Months 1-3)

**Core Workflow:**
- Workspace creation for product ideas (name + description)
- PM Discovery: Multi-agent question generation, user answers, Canonical Epic generation with human approval
- Architecture Generation: Multi-agent architecture proposals, Architect Mentor consolidation, Canonical Architecture with human approval
- Backlog Generation: Multi-agent user story generation, BA Mentor consolidation, Canonical Backlog with human approval
- Export: Markdown and JSON (Jira-compatible) downloads of complete product definition

**Agent Orchestration:**
- State machine for PM → Architect → BA pipeline with approval gates
- Parallel agent execution (3 agents per stage: PM1, PM2, PM3 → PM Mentor consolidation)
- Real-time streaming feedback via Server-Sent Events (SSE)
- Manual stage re-run (regenerate Epic, Architecture, or Backlog independently)
- Ad-hoc Q&A within Architecture stage (ask clarifying questions)

**Data & Persistence:**
- Canonical document storage (validated JSON schemas for Epic, Architecture, Backlog)
- Schema validation via Pydantic (CanonicalEpicV1, CanonicalArchitectureV1, CanonicalBacklogV1)
- Soft versioning (draft/approved/superseded status for document history)
- Agent logging (all LLM calls logged with prompts, responses, tokens, duration, errors)

**Authentication & Security:**
- Magic link authentication (email-only, no third-party OAuth)
- Session-based auth with secure HttpOnly cookies
- Row-level security (users can only access their own workspaces)
- Rate limiting (60 requests/minute per user)

**User Experience:**
- Server-side rendered UI (Jinja2 + HTMX, no React SPA)
- Inline editing of Epic/Architecture/Backlog sections (manual overrides)
- Workspace list (active/archived filtering)
- Archive and soft delete for workspaces

**Repository Introspection (Read-Only):**
- List repo files endpoint (GET /repo/files with allow-listed roots)
- Fetch file content endpoint (GET /repo/file for text files only)
- Strict read-only access (no write operations, no .git/.env access)

## Out of Scope (Deferred to Phase 2+)

**Phase 1 Explicitly Excludes:**
- ❌ Drift detection (warning when manual edits conflict with generated artifacts)
- ❌ Version history with rollback UI (viewing/restoring superseded documents)
- ❌ Idea library with search (finding and referencing past workspaces)
- ❌ PDF export (only Markdown and JSON in Phase 1)
- ❌ PostgreSQL (SQLite sufficient for MVP, migration path ready)
- ❌ Third-party authentication (Auth0/Clerk deferred to Phase 2)
- ❌ Multi-user collaboration (read-only sharing deferred to Phase 3)
- ❌ API access for developers (API keys and programmatic access in Phase 3)
- ❌ User-selectable LLM models (claude-sonnet-4-20250514 hardcoded in Phase 1)
- ❌ Real-time collaboration features (single-user workflows only)
- ❌ Mobile native apps (web-responsive only)
- ❌ Bi-directional sync with Jira/Linear (one-way export only)
- ❌ Custom agent prompts or user-editable system prompts
- ❌ Template system for different product types (e.g., SaaS, marketplace, mobile app)
- ❌ Analytics dashboard (usage metrics, cost tracking)
- ❌ Repository write operations (code generation, git commits)

## High-Level Requirements

**Functional Requirements:**

1. **Workspace Management:**
   - Users can create workspaces (idea name + description)
   - Users can view list of all workspaces (sorted by last updated)
   - Users can archive workspaces (hide from default view)
   - Users can soft delete workspaces (remove from all views, retain for audit)

2. **PM Discovery Workflow:**
   - System generates 8-12 clarifying questions via 3 PM agents + PM Mentor
   - User answers all questions (validated: min 10 chars per answer)
   - System generates Canonical Epic via 3 PM agents + PM Mentor
   - User approves or regenerates Epic
   - User can inline-edit Epic sections before approval

3. **Architecture Generation:**
   - System generates architecture proposals via 3 Architect agents + Architect Mentor
   - Architecture enforces Python/FastAPI/SQLite/HTMX stack (per supplemental guidance)
   - System validates against CanonicalArchitectureV1 schema
   - User approves or regenerates Architecture
   - User can ask ad-hoc questions during review

4. **Backlog Generation:**
   - System generates 20-40 INVEST-compliant user stories via 3 BA agents + BA Mentor
   - Stories grouped by Epic phase (Phase 1, 2, 3)
   - System validates against CanonicalBacklogV1 schema
   - User approves or regenerates Backlog

5. **Export:**
   - Markdown export: Epic + Architecture + Backlog in single .md file
   - JSON export: Jira-compatible structure with traceability fields
   - Immediate synchronous download (no background jobs)

6. **Real-Time Feedback:**
   - SSE streaming for all agent stages (PM, Architecture, BA)
   - Progress messages: "PM Agent 1 working... PM Agent 2 complete..."
   - Stream closes when stage completes

7. **Error Handling:**
   - Automatic retry with exponential backoff for LLM API failures
   - Schema validation with Mentor rewrite loop (max 3 attempts)
   - User-friendly error messages with retry buttons

8. **Repository Introspection:**
   - List files in allow-listed directories (app, tests, templates)
   - Fetch content of text files (UTF-8 only, max 16KB)
   - Strictly read-only (no write operations)

**Non-Functional Requirements:**

1. **Performance:**
   - Epic generation: <90 seconds end-to-end (acceptance criterion)
   - Ad-hoc Q&A: <15 seconds
   - Export generation: <5 seconds
   - Schema validation: <5ms per document

2. **Scalability:**
   - Target: 750 active users (Phase 1)
   - Workload: 3-4 ideas per user per month = 2,500 workflows/month
   - SQLite capacity: ~10 concurrent writes (sufficient for MVP)
   - Single FastAPI instance handles target load via async I/O

3. **Cost Structure:**
   - LLM API: $1,875-3,750/month (Anthropic Claude)
   - Infrastructure: $15-40/month (managed container platform + SQLite)
   - Total: <$4,000/month
   - Revenue: $21,750/month ($29/month × 750 users)
   - Gross Margin: 45-75%

4. **Reliability:**
   - LLM API retry logic: 2-3 attempts with exponential backoff
   - Schema validation: Pre-save validation prevents corrupt data
   - Soft deletes: No data loss, all versions retained as 'superseded'
   - Daily automated backups: SQLite file backups

5. **Security:**
   - Magic link authentication with secure session tokens
   - HttpOnly cookies (prevent XSS)
   - Row-level security (user_id filtering on all queries)
   - Rate limiting (60 requests/minute per user)
   - Secrets management via environment variables

## Risks & Constraints

**Technical Risks:**

1. **LLM API Instability (Medium likelihood, High impact):**
   - Risk: Anthropic Claude API downtime or rate limiting blocks workflows
   - Mitigation: Retry logic (2 attempts), user notification with retry button, agent_logs captures errors
   - Contingency: Phase 2 cached responses for common patterns

2. **Schema Validation Failures (Medium likelihood, Medium impact):**
   - Risk: Architect Mentor produces invalid CanonicalArchitectureV1, blocks pipeline
   - Mitigation: Mentor rewrite loop (max 3 attempts), detailed ValidationError feedback
   - Contingency: Manual override for admin to fix and approve

3. **SQLite Concurrent Write Limits (Low likelihood, Medium impact):**
   - Risk: SQLite supports ~10 concurrent writes; exceeding causes SQLITE_BUSY errors
   - Mitigation: Acceptable for MVP (<100 concurrent users), PostgreSQL migration ready
   - Contingency: Monitor error rates, trigger migration at >1% failure rate

**Business Risks:**

1. **Cost Overrun - LLM Usage (Medium likelihood, High impact):**
   - Risk: Users generate excessive workflows, driving LLM costs above revenue
   - Mitigation: Per-user workflow limits (10 concurrent), token usage monitoring, budget alerts
   - Contingency: Usage-based pricing tiers ($49/month unlimited, $19/month 5 workflows)

2. **Quality Perception (Medium likelihood, High impact):**
   - Risk: AI-generated artifacts perceived as generic or low-quality vs. human PMs
   - Mitigation: Quality metrics (80% first-attempt approval target), user feedback loops, prompt refinement
   - Contingency: Hybrid model with human PM review service ($99/month tier)

**Constraints:**

1. **Technology Stack:**
   - Must use Python/FastAPI backend (per Architect supplemental guidance)
   - Must use canonical document storage with Pydantic validation
   - Must avoid TypeScript/NestJS, React SPA, microservices, job queues (per guidance)

2. **Budget:**
   - Infrastructure budget: <$50/month for MVP
   - LLM API budget: <$4,000/month at scale
   - No funding for external dependencies (Auth0, cloud storage, etc.) until Phase 2

3. **Timeline:**
   - Phase 1 MVP must ship in 3 months (hard constraint for market validation)
   - Single developer or small team (2-3 engineers)

4. **Operational:**
   - No 24/7 support for MVP (best-effort email support)
   - No SLA guarantees (free tier or early adopter pricing)
   - Single-region deployment (US)

## Product Roadmap

**Phase 1: Core Platform / MVP (Months 1-3)**
- **Goal:** Ship functional product definition workflow with human-in-the-loop approval gates
- **Scope:** 22 stories, 117 story points
- **Deliverables:**
  - Magic link authentication
  - Workspace CRUD with archive/delete
  - PM Discovery (questions + Epic generation)
  - Architecture generation (Python/FastAPI stack enforced)
  - Backlog generation (INVEST stories)
  - Markdown + JSON export
  - Real-time SSE streaming
  - Repository introspection (read-only)
- **Success Criteria:**
  - 100 beta users onboarded
  - 60% workflow completion rate (workspace → approved backlog)
  - <90s Epic generation latency (P95)
  - 80% first-attempt Epic approval rate

**Phase 2: Workflow Intelligence (Months 4-6)**
- **Goal:** Add intelligence features that detect drift and enable version control
- **Scope:** 7 stories, 52 story points
- **Deliverables:**
  - Drift detection (warn when edits conflict with downstream artifacts)
  - Version history with rollback UI
  - Idea library with full-text search
  - PDF export generation
  - PostgreSQL migration (when >100 concurrent users)
  - Repository content search (read-only)
  - Third-party authentication (Auth0/Clerk migration)
- **Success Criteria:**
  - 750 active users
  - 40% monthly retention
  - <2% drift-related confusion (support tickets)

**Phase 3: Growth & Expansion (Months 7-9)**
- **Goal:** Enable team collaboration and developer integrations
- **Scope:** 3 stories, 29 story points
- **Deliverables:**
  - Read-only workspace sharing
  - API key authentication for programmatic access
  - User-selectable LLM models (Opus/Sonnet/Haiku per agent role)
- **Success Criteria:**
  - 2,000 active users
  - 20% of users share workspaces with teammates
  - 10% of users use API for automation

**Future Phases (Months 10+):**
- Real-time collaboration (multiple users editing same workspace)
- Bi-directional Jira/Linear sync
- Custom agent prompts and templates
- Analytics dashboard
- Repository write operations (code generation, git commits)
- Mobile native apps

---

# Canonical Architecture

## Summary

The canonical architecture is a Python-based MVP optimized for rapid delivery (3 months) with FastAPI backend, minimal HTMX UI, and canonical document storage as the authoritative source of truth. The architecture enforces schema validation at every stage via Pydantic models, ensuring all artifacts conform to standardized structures before persistence.

The system uses FastAPI for async API endpoints, Jinja2 for server-side HTML rendering, HTMX for dynamic interactions without JavaScript framework overhead, and SQLite for zero-configuration data persistence with a clear migration path to PostgreSQL. All AI agent outputs are validated against Pydantic schemas before storage in the canonical_documents table, which serves as the single source of truth for all downstream operations.

Key architectural decisions prioritize operational simplicity: single Docker container deployment, synchronous orchestration via Python asyncio for concurrent agent execution, local filesystem for ephemeral exports, and managed authentication via third-party providers. The architecture avoids SPA frameworks, microservices, and job queues in favor of Python-native solutions that enable faster iteration and lower operational complexity.

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│              User Browser                            │
│  Jinja2 HTML + HTMX + EventSource (SSE)              │
└────────────────────┬─────────────────────────────────┘
                     │ HTTPS
                     │
┌────────────────────▼─────────────────────────────────┐
│            FastAPI Application                       │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │         API Layer (FastAPI)                  │   │
│  │  - REST endpoints (/workspaces, /approve)    │   │
│  │  - SSE streaming (/stream)                   │   │
│  │  - Pydantic validation                       │   │
│  └────────────────┬─────────────────────────────┘   │
│                   │                                  │
│  ┌────────────────▼─────────────────────────────┐   │
│  │      Orchestration Core (Python)             │   │
│  │  - State machine (PM → Arch → BA)            │   │
│  │  - Agent dispatcher (asyncio.gather)         │   │
│  │  - Approval gate manager                     │   │
│  └────────────────┬─────────────────────────────┘   │
│                   │                                  │
│  ┌────────────────▼─────────────────────────────┐   │
│  │       Agent Service (Anthropic SDK)          │   │
│  │  - anthropic.AsyncAnthropic                  │   │
│  │  - Prompt management                         │   │
│  │  - Streaming responses                       │   │
│  └────────────────┬─────────────────────────────┘   │
│                   │                                  │
│  ┌────────────────▼─────────────────────────────┐   │
│  │    Schema Validation (Pydantic)              │   │
│  │  - CanonicalArchitectureV1 model             │   │
│  │  - Block type enforcement                    │   │
│  │  - ID uniqueness validation                  │   │
│  └────────────────┬─────────────────────────────┘   │
│                   │                                  │
│  ┌────────────────▼─────────────────────────────┐   │
│  │  Canonical Document Store (SQLite/SQLAlchemy)│   │
│  │  - workspaces                                │   │
│  │  - canonical_documents (JSON)                │   │
│  │  - pipeline_state (JSON)                     │   │
│  │  - agent_logs                                │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Anthropic API (HTTPS) ─────────────────────────────→│
└──────────────────────────────────────────────────────┘
           Single Docker Container
       (Deployed on managed platform)
```

## System Components

### Presentation Layer

**Technology:** Jinja2 Templates + HTMX + Tailwind CSS (CDN) + EventSource API

**Responsibilities:**
- Server-side HTML rendering via Jinja2 templates
- Dynamic interactions via HTMX (hx-get, hx-post, hx-swap)
- Real-time agent streaming via EventSource (SSE)
- Styling via Tailwind CSS (CDN, no build step)
- Form submissions and approval gate UI
- Export download links

**Rationale:** Server-side rendering eliminates build pipeline complexity (no package managers, bundlers, or transpilers). HTMX provides SPA-like interactions with minimal JavaScript payload. EventSource API handles SSE streaming natively in all modern browsers. Tailwind CSS via CDN avoids compilation step. This approach delivers interactive UI functionality with significantly reduced frontend complexity compared to SPA frameworks.

### API Layer

**Technology:** FastAPI + Pydantic + Uvicorn

**Responsibilities:**
- RESTful endpoints: POST /workspaces, GET /workspaces/{id}, POST /workspaces/{id}/submit
- Approval endpoints: POST /workspaces/{id}/approve?stage=epic|architecture|backlog
- SSE streaming endpoint: GET /workspaces/{id}/stream (yields agent outputs via StreamingResponse with text/event-stream content type and proper event framing)
- Request/response validation via Pydantic models
- JWT authentication via dependency injection
- Rate limiting per user
- CORS middleware for future API clients
- Automatic OpenAPI documentation

**Rationale:** FastAPI provides async support for concurrent LLM calls, automatic Pydantic validation, and built-in OpenAPI docs. Dependency injection simplifies auth and database session management. Uvicorn ASGI server handles SSE streaming efficiently. SSE implemented via FastAPI StreamingResponse with text/event-stream content type and proper event framing (data: prefix, double newline delimiters). Python's async/await syntax simplifies concurrent operations compared to callback-based approaches.

### Orchestration Core

**Technology:** Python + asyncio

**Responsibilities:**
- Finite state machine for pipeline stages (pm_questions → epic_approval → architecture_start → architecture_approval → ba_start → backlog_approval)
- Agent dispatcher: spawns 3 agents in parallel via asyncio.gather
- Approval gate manager: pauses pipeline until user approves or rejects
- Re-run coordinator: fetches Epic/Architecture from canonical_documents and replays stage
- Error handler: implements retry with exponential backoff
- Context management: stores user inputs in pipeline_state.context (JSON)

**Rationale:** Python's asyncio enables concurrent agent execution without threading complexity. Finite state machine prevents invalid transitions (e.g., cannot approve Architecture before Epic). Orchestration Core implemented as pure Python module (no FastAPI dependencies). FastAPI routes act as thin adapters that call orchestrator functions. This separation enables unit testing without web stack and future extraction to worker processes if async job queues are needed in later phases.

### Agent Service

**Technology:** anthropic Python SDK (AsyncAnthropic)

**Responsibilities:**
- Async API calls to Anthropic Claude API via anthropic.AsyncAnthropic
- Model configuration: claude-sonnet-4-20250514 (hardcoded for MVP)
- Prompt management: loads from file-based prompt library
- Streaming response handler: yields tokens to SSE endpoint
- Retry logic: multiple attempts with exponential backoff on API failures
- Token usage logging: captures tokens_used for cost tracking in agent_logs table
- Response parsing: validates agent output against expected schemas

**Rationale:** Official Anthropic SDK provides async support and streaming API. File-based prompts enable version control and updates without code changes. Token logging enables cost monitoring (critical for subscription pricing model). Retry logic handles transient API failures without user intervention. Streaming responses provide real-time feedback to users during long-running operations.

### Schema Validation Layer

**Technology:** Pydantic + Custom Validators

**Responsibilities:**
- CanonicalArchitectureV1 Pydantic model enforces: fixed section keys, block type validation, no extra keys (extra='forbid')
- Block-level validation: paragraph, heading, code, list_item, component, entity, decision, risk, table, key_value
- Custom validators: block ID uniqueness per section, table row length matches headers, risk likelihood/impact enums
- Pre-save validation: all canonical documents validated before INSERT into database
- Mentor rewrite loop: if validation fails, Architect Mentor rewrites until valid
- Schema versioning: schema_version field enables future migrations

**Rationale:** Pydantic provides runtime schema enforcement that mirrors JSON Schema specification. Custom validators catch complex constraints (ID uniqueness, table consistency). Pre-save validation prevents corrupt data from entering canonical store. Schema versioning enables backward compatibility when schemas evolve in later phases. Validation errors provide detailed feedback for debugging and mentor rewriting.

### Canonical Document Store

**Technology:** SQLite (MVP) / PostgreSQL (Phase 2+) + SQLAlchemy ORM

**Responsibilities:**
- Durable storage for workspaces, canonical documents, pipeline state, agent logs
- JSON column for canonical_documents.content (validated schemas)
- Status tracking: draft / approved / superseded (enables soft versioning)
- SQLAlchemy ORM provides database-agnostic queries (SQLite → PostgreSQL migration requires only connection string change)
- Indexes on workspace_id, doc_type, status for fast queries
- Foreign key constraints enforce referential integrity

**Rationale:** SQLite provides zero-configuration persistence for MVP (suitable for hundreds of concurrent users). JSON column support stores validated canonical documents. SQLAlchemy ORM abstracts database differences, enabling seamless PostgreSQL migration when scale requires it (no application code changes). Soft versioning (status field) prepares for version history feature without schema changes. Foreign key constraints prevent orphaned records.

### Export Service

**Technology:** Jinja2 Templates + Python JSON Serialization

**Responsibilities:**
- Markdown export: reads canonical_documents.content → applies Jinja2 template → generates .md file
- JSON export: serializes canonical document with Jira-compatible metadata (Epic → Feature → Story traceability)
- Derives from canonical store: never regenerates content from scratch
- Local filesystem storage with time-limited retention
- Download endpoints: GET /workspaces/{id}/export?format=markdown|json

**Rationale:** Template-based generation ensures consistent formatting. Deriving from canonical store (not regenerating) guarantees exports match approved artifacts. Local filesystem avoids cloud storage costs and complexity for MVP. Jinja2 templates enable customization without code changes. Time-limited retention acceptable because exports are ephemeral (users download immediately). Future migration to cloud storage requires only storage backend abstraction.

## Data Model

The data model uses SQLAlchemy ORM with SQLite for MVP and PostgreSQL-ready schema design. The canonical_documents table is the authoritative store for all validated artifacts (Epics, Architectures, Backlogs), with JSON columns storing schema-compliant documents.

### Canonical Schema Registry

The system defines multiple canonical document schemas, all stored in the canonical_documents table with schema validation via corresponding Pydantic models:

- **CanonicalArchitectureV1 (doc_type='architecture'):** Defined in this document, enforces fixed section structure with typed blocks
- **CanonicalEpicV1 (doc_type='epic'):** Defined by PM Mentor output, structure TBD in PM phase
- **CanonicalBacklogV1 (doc_type='backlog'):** Defined by BA Mentor output, structure TBD in BA phase
- **PMQuestionsV1 (doc_type='pm_questions'):** Consolidated clarifying questions from PM Mentor

All schemas follow the pattern: {type, version, sections} with section-specific block structures. Each schema has a corresponding Pydantic model for validation. The schema_version field enables backward compatibility when schemas evolve.

### workspaces

**Fields:**
- id: TEXT PRIMARY KEY (UUID as string)
- user_id: TEXT NOT NULL
- name: TEXT NOT NULL
- description: TEXT
- status: TEXT NOT NULL DEFAULT 'active' (active | archived | deleted)
- created_at: TEXT NOT NULL (ISO 8601)
- updated_at: TEXT NOT NULL (ISO 8601)

**Relationships:**
- One-to-many with canonical_documents
- One-to-one with pipeline_state
- One-to-many with agent_logs

**Indexes:**
- user_id (for user workspace queries)

### canonical_documents

**Fields:**
- id: TEXT PRIMARY KEY (UUID as string)
- workspace_id: TEXT NOT NULL REFERENCES workspaces(id)
- doc_type: TEXT NOT NULL (epic | architecture | backlog | pm_questions)
- status: TEXT NOT NULL (draft | approved | superseded)
- schema_version: INTEGER NOT NULL (e.g., 1 for CanonicalArchitectureV1)
- content: JSON NOT NULL (validated canonical document)
- created_at: TEXT NOT NULL (ISO 8601)
- updated_at: TEXT NOT NULL (ISO 8601)

**Relationships:**
- Belongs to workspace

**Indexes:**
- workspace_id (for workspace document queries)
- doc_type + status (for current document queries)
- created_at (for version history)

### pipeline_state

**Fields:**
- id: TEXT PRIMARY KEY (UUID as string)
- workspace_id: TEXT NOT NULL UNIQUE REFERENCES workspaces(id)
- stage: TEXT NOT NULL (pm_questions | awaiting_user_answers | epic_approval | architecture_start | etc.)
- approved: INTEGER NOT NULL DEFAULT 0 (boolean: 0 or 1)
- context: JSON (user inputs, intermediate state for re-runs)
- created_at: TEXT NOT NULL (ISO 8601)
- updated_at: TEXT NOT NULL (ISO 8601)

**Relationships:**
- Belongs to workspace (one-to-one)

### agent_logs

**Fields:**
- id: TEXT PRIMARY KEY (UUID as string)
- workspace_id: TEXT NOT NULL REFERENCES workspaces(id)
- role: TEXT NOT NULL (pm | architect | ba | pm_mentor | architect_mentor | ba_mentor)
- stage: TEXT NOT NULL (pipeline stage when invoked)
- prompt: TEXT (system prompt + user input)
- response: TEXT (agent output)
- tokens_used: INTEGER (for cost tracking)
- duration_ms: INTEGER (for performance monitoring)
- error: TEXT (captures failures)
- created_at: TEXT NOT NULL (ISO 8601)

**Relationships:**
- Belongs to workspace

**Indexes:**
- workspace_id + created_at (for chronological log queries)
- role + stage (for agent performance analysis)

The canonical_documents table is the single source of truth. All downstream operations (BA story generation, exports) read from this table. Schema validation via Pydantic occurs before INSERT. Status field enables soft versioning: approved documents are current, superseded documents are historical, draft documents are pending approval.

SQLite to PostgreSQL migration path: SQLAlchemy ORM enables database-agnostic queries. To migrate, update connection string and run schema migration. PostgreSQL JSONB columns replace SQLite JSON columns, enabling GIN indexes for faster JSON queries. No application code changes required.

## Key Architectural Decisions

### Python + FastAPI Backend

**Decision:** Use Python with FastAPI framework for backend API

**Alternatives:**
- Node.js + Express or NestJS
- Go + Gin or Fiber

**Rationale:**
- FastAPI provides async/await support for concurrent LLM calls via asyncio.gather
- Native Pydantic integration enables automatic request/response validation and matches schema validation requirements
- Anthropic Python SDK is official and provides async streaming support
- Python ecosystem simplifies schema validation (Pydantic mirrors JSON Schema patterns)
- Automatic OpenAPI documentation generation reduces API documentation overhead
- Simpler async syntax for concurrent operations compared to callback-based approaches

**Tradeoff:** Python's GIL limits CPU-bound parallelism, but not relevant for I/O-bound LLM API calls. FastAPI's async I/O handles concurrency effectively for MVP scale. Performance sufficient for target load of hundreds of concurrent users.

### Server-Side Rendering with HTMX

**Decision:** Use server-side rendering (Jinja2) with HTMX for dynamic interactions

**Alternatives:**
- React + Vite SPA
- Vue.js or Svelte SPA

**Rationale:**
- Eliminates build pipeline complexity (no package managers, bundlers, transpilers)
- HTMX provides SPA-like interactions with minimal JavaScript payload
- Server controls all state, eliminating client-side state management libraries
- Faster initial page loads (no large JavaScript bundle download)
- Simplified debugging (HTML returned from server, not client-rendered)
- Lower operational complexity (no separate frontend/backend deployments)

**Tradeoff:** Less responsive than full SPA (some full-page reloads), but acceptable for linear workflow (submit idea → approve stages → export). Users tolerate minor UX trade-off for faster MVP delivery and simpler architecture.

### SQLite for MVP with PostgreSQL Migration Path

**Decision:** Use SQLite for MVP with clear PostgreSQL migration path

**Alternatives:**
- PostgreSQL from day 1
- MongoDB or other document databases

**Rationale:**
- SQLite provides zero-configuration persistence (file-based, no separate database server)
- JSON column support stores validated canonical documents
- Sufficient for MVP scale (hundreds of concurrent users with read-heavy workload)
- SQLAlchemy ORM abstracts database differences (migration requires only connection string change)
- Eliminates managed database costs for MVP
- Faster local development (no database server setup)

**Tradeoff:** SQLite has concurrent write limitations and lacks advanced JSON indexing (PostgreSQL GIN indexes). Migration to PostgreSQL required when exceeding hundreds of concurrent users or needing complex JSON queries. Migration path is straightforward via SQLAlchemy abstraction.

### Canonical Document Store as Single Source of Truth

**Decision:** Store all validated artifacts in canonical_documents table; all downstream operations read from this table

**Alternatives:**
- Regenerate artifacts from agent outputs on-demand
- Store raw agent outputs and validate on read

**Rationale:**
- Schema validation (Pydantic) occurs before INSERT, preventing corrupt data from entering system
- Downstream phases (BA, Export) operate ONLY on validated canonical documents, ensuring consistency
- Traceability: all approved artifacts versioned via status field (draft/approved/superseded)
- Human + machine readable: JSON structure enables both API consumption and template-based rendering
- Audit trail: agent_logs table preserves raw agent outputs for debugging and analysis

**Tradeoff:** Requires strict schema enforcement and validation logic. Mentor agents must rewrite proposals until they pass schema validation. This adds processing time but ensures data quality and consistency across all phases.

### Pydantic Schema Enforcement for All Canonical Documents

**Decision:** Use Pydantic models to enforce all canonical document schemas (CanonicalArchitectureV1, CanonicalEpic, CanonicalBacklog)

**Alternatives:**
- JSON Schema validation via external library
- Manual validation logic

**Rationale:**
- Pydantic provides runtime schema enforcement that mirrors JSON Schema specification
- extra='forbid' configuration prevents unknown keys at all levels (root, sections, blocks, data objects)
- Custom validators handle complex constraints (block ID uniqueness, table row consistency, enum validation)
- Type hints provide IDE autocomplete and enable static type checking during development
- Native FastAPI integration enables automatic API request/response validation and documentation

**Tradeoff:** Pydantic validation adds processing overhead, but negligible compared to LLM API latency. Schema evolution requires Pydantic model updates, but schema_version field enables backward compatibility and gradual migrations.

### Synchronous Orchestration via Asyncio

**Decision:** Use Python asyncio.gather for concurrent agent execution; no separate job queue system

**Alternatives:**
- Background job queue (Celery, RQ) with message broker
- Threading or multiprocessing

**Rationale:**
- asyncio.gather spawns 3 agents in parallel with straightforward code
- Non-blocking I/O for LLM API calls (most time spent waiting for network responses)
- Acceptable latency for synchronous execution (per Epic acceptance criteria)
- Eliminates operational complexity (no message broker, worker processes, or job monitoring)
- Simpler error handling (exceptions raised in same execution context)

**Tradeoff:** User must wait for pipeline completion (no background jobs). API endpoint blocks until agents finish. Acceptable for MVP given latency targets and conversational UI expectations. Can migrate to job queue in later phases if requirements change.

### Local Filesystem for Export Storage

**Decision:** Store exports in local filesystem with time-limited retention; no cloud storage

**Alternatives:**
- Cloud object storage (AWS S3, GCS, Azure Blob) from day 1

**Rationale:**
- Exports are ephemeral (users download immediately, no long-term storage requirement)
- Derived from canonical documents (not regenerated), ensures consistency
- Zero cost compared to cloud storage fees
- Simpler deployment (no cloud credentials or SDK integration)
- Time-limited retention sufficient for MVP usage patterns

**Tradeoff:** Local filesystem not horizontally scalable (exports tied to specific container instance). Migration to cloud storage required when deploying multiple instances in later phases. Migration straightforward via storage backend abstraction pattern.

## Non-Functional Requirements

### Performance

- Architecture generation: Target completion within Epic acceptance criteria (parallel agent execution via asyncio.gather)
- Ad-hoc Q&A response: Target completion within Epic acceptance criteria (single agent call)
- Export generation: Fast template rendering from canonical JSON
- Schema validation: Minimal overhead via Pydantic validation
- Database queries: Optimized via indexes on workspace_id, doc_type, status

### Scalability (MVP)

- Target: 750 active users per Epic requirements
- Workload: 3-4 ideas per user per month per Epic requirements
- LLM API calls: Volume determined by workflow design (multiple agents per stage)
- SQLite capacity: Suitable for hundreds of concurrent users with read-heavy workload
- Single FastAPI instance handles target load via async I/O (non-blocking)
- PostgreSQL migration trigger: Exceeding hundreds of concurrent users or complex JSON query requirements

### Cost Structure (MVP)

- **LLM API (Anthropic):** Primary cost driver based on workflow token usage
- **Infrastructure:** Managed container platform with SQLite (minimal cost)
- **Export Storage:** Local filesystem (zero additional cost)
- **Total:** Dominated by LLM API usage per workflow
- **Revenue Target:** Per Epic business goals
- **Gross Margin:** Per Epic financial targets

Unit Economics: Infrastructure costs minimized via SQLite and single container deployment. Cost structure enables healthy margins per Epic financial model. LLM API costs scale linearly with usage, requiring monitoring and alerting.

### Security

- Authentication: JWT via third-party authentication provider, verified via FastAPI dependency injection
- Authorization: Row-level security via SQLAlchemy filters (all queries scoped to user_id)
- SQL Injection: Prevented via SQLAlchemy parameterized queries (no raw SQL execution)
- Rate Limiting: Per-user request rate limiting to prevent abuse
- Secret Management: Environment variables for sensitive configuration (no secrets in code)
- HTTPS: Enforced via managed platform (automatic TLS certificate management)

### Monitoring & Observability

- Logging: agent_logs table captures all LLM interactions (prompt, response, tokens, duration, errors)
- Log Format: Structured logging for parsing and analysis
- Retention: Time-based retention policy in agent_logs table
- Metrics (Phase 2): Metrics endpoint for time-to-architecture, agent failure rates, cost per workflow
- Error Tracking: Error capture and reporting integration
- Health Check: Health endpoint for platform monitoring

## Deployment Architecture

```
┌────────────────────────────────────────────┐
│           User Browser                     │
│   (HTML + HTMX + EventSource)              │
└─────────────────┬──────────────────────────┘
                  │ HTTPS (TLS)
                  │
┌─────────────────▼──────────────────────────┐
│       Managed Container Platform           │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │   Docker Container                   │ │
│  │                                      │ │
│  │  ┌────────────────────────────────┐ │ │
│  │  │  FastAPI Application           │ │ │
│  │  │  - API endpoints               │ │ │
│  │  │  - SSE streaming               │ │ │
│  │  │  - Template rendering          │ │ │
│  │  └────────────────────────────────┘ │ │
│  │                                      │ │
│  │  ┌────────────────────────────────┐ │ │
│  │  │  SQLite Database               │ │ │
│  │  │  (Persistent Volume)           │ │ │
│  │  └────────────────────────────────┘ │ │
│  │                                      │ │
│  │  /prompts (system prompts)          │ │
│  │  /templates (Jinja2 HTML)           │ │
│  │  /exports (local filesystem)        │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  Anthropic API (HTTPS) ────────────────────→
└────────────────────────────────────────────┘
```

### Hosting Platforms

- **Container:** Single Docker image containing FastAPI application, prompts, and templates
- **Platform:** Managed container platform with Docker support and persistent volumes
- **Database:** SQLite file on persistent volume
- **TLS/HTTPS:** Automatic via platform (managed certificate provisioning)
- **Domain:** Custom domain support

### Environments

- **Development:** Local environment with hot-reloading for rapid iteration
- **Staging:** Platform preview environment (auto-created on pull requests, isolated database)
- **Production:** Platform production environment (main branch auto-deploy)

### CI/CD Pipeline

- Git push to main branch triggers deployment
- Platform builds Docker image automatically
- Image deployed to container runtime (zero downtime via health checks)
- Database migrations: Schema migration tool runs on container startup

## Technology Stack Summary

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Frontend | Jinja2 + HTMX + Tailwind CSS | Server-side rendering, minimal JS, no build step |
| API | FastAPI + Pydantic | Async, automatic validation, OpenAPI docs |
| ORM | SQLAlchemy | Database-agnostic (SQLite → PostgreSQL) |
| Database | SQLite (MVP) / PostgreSQL (Phase 2+) | Zero-config → production-ready |
| LLM | anthropic Python SDK | Official SDK, async support, streaming |
| Validation | Pydantic | Schema enforcement, canonical document validation |
| Streaming | Server-Sent Events | Unidirectional, HTTP-based, EventSource API |
| Authentication | Third-party provider | Managed auth, JWT tokens |
| Rate Limiting | Per-user rate limiting | Prevent abuse and control costs |
| Deployment | Docker + Managed Platform | Single container, automated deployment |
| Export Storage | Local Filesystem | Zero cost, time-limited retention |

## Roadmap Implications

### Phase 1: Core Platform / MVP (Months 1-3)

Architecture fully supports Phase 1 requirements with Python/FastAPI stack:

- Orchestration engine: Python asyncio finite state machine for PM → Architect → BA pipeline
- Approval gates: FastAPI endpoints pause pipeline at Epic, Architecture, Backlog stages
- Basic artifact editing: HTMX forms submit updates to canonical_documents table
- Manual stage re-run: API reads Epic from canonical_documents and replays Architect agents
- Export service: Template rendering from canonical JSON, direct JSON serialization
- Ad-hoc Q&A: SSE endpoint streams single agent response to user queries

### Phase 2: Workflow Intelligence (Months 4-6)

Architecture prepares for Phase 2 features with minimal changes:

- Drift Detection: Compare canonical_documents versions (status='approved' vs. 'superseded'), flag conflicts in UI
- Version History: Query canonical_documents WHERE status='superseded' ORDER BY created_at DESC for rollback UI
- Idea Library: Add full-text search on workspaces.name + description via database full-text search capabilities
- PDF Export: Add PDF generation library, render template to PDF format
- PostgreSQL Migration: Update connection string, run schema migration tool

### Phase 3: Growth & Expansion (Months 7-9)

Architecture supports Phase 3 scaling with moderate refactoring:

- Multi-User (Read-Only): Add workspace_shares table with permission field, query filters for shared access
- API Access: Add api_keys table, API key authentication, expose REST endpoints for programmatic access
- User-Selectable Models: Add model_config JSON field to workspaces, Agent Service reads configuration
- Horizontal Scaling: Deploy multiple FastAPI containers behind load balancer, shared PostgreSQL database
- Cloud Storage Migration: Replace local filesystem with cloud object storage, environment variable toggles backend

## Risks & Mitigations

### LLM API Instability

**Risk:** LLM API Instability  
**Likelihood:** Medium  
**Impact:** High  
**Description:** Anthropic Claude API may experience downtime, rate limiting, or inconsistent output quality, blocking user workflows.

**Mitigation:**
- Retry logic with exponential backoff for transient failures
- User notification on final failure with retry option
- agent_logs table captures all errors for debugging (prompt, response, error field)
- Phase 2: Add response caching for common questions to reduce API dependency

### Cost Overrun (LLM Usage)

**Risk:** Cost Overrun (LLM Usage)  
**Likelihood:** Medium  
**Impact:** High  
**Description:** Users generate excessive workflows, driving LLM costs above revenue targets.

**Mitigation:**
- Per-user workflow limits enforced in pipeline_state queries
- Token usage monitoring via agent_logs.tokens_used field enables cost dashboards
- Alert when monthly cost exceeds budget threshold
- Future: Usage-based pricing tiers or workflow limits per subscription level

### Schema Validation Failures

**Risk:** Schema Validation Failures  
**Likelihood:** Medium  
**Impact:** Medium  
**Description:** Mentor agents produce outputs that fail canonical schema validation, blocking pipeline progression.

**Mitigation:**
- Mentor rewrite loop: If Pydantic validation fails, Mentor receives error details and regenerates
- Maximum rewrite attempts before escalating to user with error message
- Detailed validation errors logged to agent_logs.error for debugging
- Phase 2: Refine Mentor prompts based on validation failure patterns

### SQLite Concurrent Write Limits

**Risk:** SQLite Concurrent Write Limits  
**Likelihood:** Low  
**Impact:** Medium  
**Description:** SQLite has concurrent write limitations that may cause errors under heavy concurrent load.

**Mitigation:**
- Acceptable for MVP scale with read-heavy workload pattern
- Database connection pooling and write-ahead logging improve concurrency
- Monitor database errors in logs, trigger PostgreSQL migration if error rate exceeds threshold
- PostgreSQL migration ready via SQLAlchemy abstraction

### Slow Architecture Generation

**Risk:** Slow Architecture Generation  
**Likelihood:** Low  
**Impact:** Medium  
**Description:** Pipeline exceeds target latency due to LLM response times or network issues.

**Mitigation:**
- Parallel agent execution: asyncio.gather spawns 3 agents concurrently
- Optimize prompts to reduce token count (fewer input tokens = faster response)
- Monitor agent_logs.duration_ms to identify performance bottlenecks
- Phase 3: If persistent issues, migrate to async job queue for background processing

### Data Loss (User Edits)

**Risk:** Data Loss (User Edits)  
**Likelihood:** Low  
**Impact:** High  
**Description:** User loses work due to database corruption, accidental deletion, or application bugs.

**Mitigation:**
- Soft deletes: status='superseded' prevents hard deletion of canonical_documents
- Automated database backups via platform or scheduled jobs
- Transaction isolation: Database sessions with COMMIT on success, ROLLBACK on error
- Phase 2: Version history UI enables rollback to any approved checkpoint

## Explicitly Out of Scope (Deferred)

Per Epic requirements, the following features are NOT included in MVP:

- ❌ Client-side SPA frameworks (React, Vue, Svelte)
- ❌ Microservices architecture
- ❌ Background job queues (Celery, RQ, Redis-based systems)
- ❌ Drift detection and resync UI (Phase 2)
- ❌ Version history with rollback UI (Phase 2)
- ❌ Idea library with search and indexing (Phase 2)
- ❌ PDF export generation (Phase 2)
- ❌ Multi-user real-time collaboration (Phase 3)
- ❌ Bi-directional Jira/Linear sync (Phase 3)
- ❌ User-editable agent prompts or custom agents (Phase 3+)
- ❌ Mobile native apps (web-responsive UI only)

---

# Canonical Backlog

## Summary

The Canonical Backlog contains 22 INVEST-compliant user stories for Phase 1 MVP (Months 1-3), organized by Epic themes: Authentication, Workspace Management, PM Discovery, Epic Generation, Architecture Generation, Backlog Generation, Export, Real-Time Streaming, Error Handling, and Repo View. All stories trace to the Canonical Epic phases and Canonical Architecture components.

Total Phase 1 effort: 117 story points across 22 stories. Stories follow INVEST principles (Independent, Negotiable, Valuable, Estimable, Small, Testable) and include clear acceptance criteria, dependencies, and technical implementation notes aligned with the Python/FastAPI architecture.

Phase 2 and Phase 3 stories are included at high-level for roadmap visibility, with detailed breakdown deferred until Phase 1 completion per Epic guidance.

## Phase 1: Core Platform / MVP (Months 1-3)

Phase 1 delivers the core orchestrated workflow: user authentication, workspace creation, PM discovery (questions and Epic generation), Architecture generation, Backlog generation, export functionality, and read-only repository introspection. All features support single-user workflows with real-time streaming feedback.

### Theme: Authentication & User Management

#### AUTH-101: Magic link authentication (email only)

**User Story:** As a user, I want to access my workspaces via a magic link sent to my email so that I can use the platform securely without third-party auth providers.

**Acceptance Criteria:**
- Landing page form accepts email address (required, valid format).
- On submit, system generates a random 128-bit token and stores it in a new `sessions` table with fields: id (UUID), email, token_hash, expires_at (default 7 days), created_at.
- Magic link emailed via SMTP (stdlib smtplib) or simple HTTP POST to a configurable mail provider URL (env var, no SDK).
- Magic link contains a one-time token endpoint: GET /magic-login?token=...; on success, backend sets secure HttpOnly cookie with opaque session ID and redirects to workspace list.
- All protected routes use a FastAPI dependency that validates the session cookie against the `sessions` table; invalid/expired sessions return 401 and redirect to login page.
- Logout endpoint deletes the session record and clears the cookie.
- If email sending fails, user sees a friendly error with 'Retry' option; failures logged to agent/system logs.

**Story Points:** 5  
**Phase:** Phase 1  
**Epic Feature:** Authentication & Security  
**Dependencies:** None  
**Technical Notes:** Pure internal session table, no OAuth or external auth SDKs. Use stdlib smtplib or a minimal HTTP call to a configurable mail gateway. Keep implementation behind an EmailService interface for later Phase 2 swap to third-party providers.

### Theme: Workspace Management

#### WRK-100: Create new workspace for product idea

**User Story:** As a user, I want to create a new workspace by entering an idea name and description so that I can start the discovery workflow.

**Acceptance Criteria:**
- Form accepts idea name (required, max 200 chars) and description (optional, max 2000 chars)
- POST /workspaces creates workspace record in database with unique UUID
- Workspace initialized with status='active' and pipeline_state.stage='pm_questions'
- User redirected to workspace detail page showing initial status
- Validation errors displayed inline (empty name, length exceeded)
- Database errors show user-friendly retry option

**Story Points:** 3  
**Phase:** Phase 1  
**Epic Feature:** Workspace Management  
**Dependencies:** AUTH-101  
**Technical Notes:** FastAPI POST endpoint, SQLAlchemy workspace and pipeline_state models, HTMX form submission with server-side validation

#### WRK-101: View list of all my workspaces

**User Story:** As a user, I want to see a list of all my workspaces (active and archived) so that I can navigate to them.

**Acceptance Criteria:**
- GET /workspaces returns all workspaces where user_id matches authenticated user
- List displays: name, description preview (first 100 chars), status, current pipeline stage, updated_at timestamp
- Workspaces sorted by updated_at DESC (most recent first)
- Click workspace name opens workspace detail view
- Empty state shows message: 'No workspaces yet. Create your first idea!'
- Pagination if user has more than 50 workspaces

**Story Points:** 2  
**Phase:** Phase 1  
**Epic Feature:** Workspace Management  
**Dependencies:** WRK-100  
**Technical Notes:** Jinja2 template for workspace list, SQLAlchemy query with user_id filter and order_by, HTMX for pagination

#### WRK-102: Archive workspace

**User Story:** As a user, I want to archive completed or abandoned workspaces so that my workspace list stays organized.

**Acceptance Criteria:**
- Archive button visible on workspace detail page
- Confirmation prompt: 'Archive this workspace? You can restore it later.'
- PATCH /workspaces/{id} updates workspace.status='archived'
- Archived workspaces hidden from default workspace list view
- 'Show Archived' toggle reveals archived workspaces in list
- Archived workspaces cannot advance pipeline (approval buttons disabled)

**Story Points:** 2  
**Phase:** Phase 1  
**Epic Feature:** Workspace Management  
**Dependencies:** WRK-101  
**Technical Notes:** HTMX button with hx-patch, SQLAlchemy update, confirmation modal, list view filter on status field

#### WRK-103: Delete workspace (soft delete)

**User Story:** As a user, I want to permanently delete workspaces so that I can remove unwanted ideas from my account.

**Acceptance Criteria:**
- Delete button visible only for archived workspaces
- Confirmation prompt: 'Permanently delete this workspace? This cannot be undone.'
- DELETE /workspaces/{id} updates workspace.status='deleted' (soft delete)
- Deleted workspaces excluded from all user-facing queries
- Deleted workspaces retained in database for audit purposes (no hard delete)
- Cascade: Related canonical_documents, pipeline_state, agent_logs retained but inaccessible via UI

**Story Points:** 2  
**Phase:** Phase 1  
**Epic Feature:** Workspace Management  
**Dependencies:** WRK-102  
**Technical Notes:** Soft delete via status='deleted', SQLAlchemy query filters exclude deleted workspaces, confirmation modal

### Theme: PM Discovery Workflow

#### PM-100: Generate PM clarifying questions

**User Story:** As a user, I want to receive clarifying questions about my product idea so that the system understands my vision and can generate a tailored Epic.

**Acceptance Criteria:**
- After workspace creation, Orchestrator Core spawns 3 PM agents in parallel via asyncio.gather
- Each PM agent receives idea name and description, generates 3-6 clarifying questions
- PM Mentor consolidates agent outputs into 8-12 unique, non-duplicate questions
- Questions validated against PMQuestionsV1 Pydantic schema before storage
- Questions stored in canonical_documents table (doc_type='pm_questions', status='approved')
- Questions displayed in workspace view with 'Answer Questions' form
- SSE stream shows real-time agent progress: 'PM Agent 1 working... PM Agent 2 complete...'
- Pipeline state updated to 'awaiting_user_answers'

**Story Points:** 8  
**Phase:** Phase 1  
**Epic Feature:** PM Discovery Workflow  
**Dependencies:** WRK-100  
**Technical Notes:** Orchestrator Core module (pure Python), Agent Service with anthropic.AsyncAnthronic, PMQuestionsV1 Pydantic schema validation, asyncio.gather for parallel execution, SSE streaming via FastAPI StreamingResponse

#### PM-101: Answer PM clarifying questions

**User Story:** As a user, I want to provide answers to the clarifying questions so that the system can generate a personalized Epic based on my inputs.

**Acceptance Criteria:**
- Form displays all PM questions with text areas for answers
- Validation: each answer must be at least 10 characters, all questions required
- POST /workspaces/{id}/answer saves answers to pipeline_state.context as JSON
- Pipeline state updated to 'epic_generation'
- User sees 'Generating Epic...' status message with SSE progress stream
- Validation errors displayed inline with specific field highlighting

**Story Points:** 3  
**Phase:** Phase 1  
**Epic Feature:** PM Discovery Workflow  
**Dependencies:** PM-100  
**Technical Notes:** HTMX form with hx-post, Pydantic validation for answer length, pipeline_state.context JSON field update, SSE connection initiated

### Theme: Epic Generation & Approval

#### EPIC-100: Generate Canonical Epic

**User Story:** As a user, I want the system to generate a structured Canonical Epic based on my answers so that I have a comprehensive product definition document.

**Acceptance Criteria:**
- Orchestrator spawns 3 PM agents in parallel with idea description and user answers
- Each PM agent generates independent Epic proposal (vision, problem, goals, in scope, out of scope, requirements, roadmap)
- PM Mentor consolidates 3 proposals into single CanonicalEpicV1 document
- Epic validated against CanonicalEpicV1 Pydantic schema (fixed sections, typed blocks, no extra keys)
- Epic stored in canonical_documents table (doc_type='epic', status='draft')
- Epic displayed in workspace view with expandable/collapsible sections
- Sections rendered: Vision Statement, Problem/Opportunity, Business Goals, In Scope, Out of Scope, Requirements, Risks, Roadmap
- Pipeline state updated to 'epic_approval'

**Story Points:** 13  
**Phase:** Phase 1  
**Epic Feature:** PM Discovery Workflow  
**Dependencies:** PM-101  
**Technical Notes:** Agent Service parallel execution, CanonicalEpicV1 Pydantic schema, PM Mentor consolidation logic, canonical_documents INSERT with JSON content, Jinja2 template for Epic rendering

#### EPIC-101: Approve or regenerate Epic

**User Story:** As a user, I want to approve the Epic or request regeneration so that I can proceed with confidence in the product definition.

**Acceptance Criteria:**
- 'Approve Epic' button updates canonical_documents.status='approved' and advances pipeline to 'architecture_start'
- 'Regenerate Epic' button re-runs PM agents with same user answers, old Epic status set to 'superseded'
- User can inline-edit Epic section content (text edits saved to canonical_documents.content JSON)
- Manual edits display warning: 'Manual edits may not persist if Epic is regenerated'
- Approval triggers Architecture generation workflow automatically
- Regeneration shows SSE progress: 'Regenerating Epic... PM Agent 1 working...'

**Story Points:** 5  
**Phase:** Phase 1  
**Epic Feature:** PM Discovery Workflow  
**Dependencies:** EPIC-100  
**Technical Notes:** POST /workspaces/{id}/approve?stage=epic endpoint, HTMX inline editing for Epic blocks, status='superseded' for old versions, Orchestrator re-run logic

### Theme: Architecture Generation & Approval

#### ARCH-100: Generate Canonical Architecture

**User Story:** As a user, I want the system to generate a technical architecture proposal so that I understand how the product will be built.

**Acceptance Criteria:**
- After Epic approval, Orchestrator spawns 3 Architect agents in parallel with Canonical Epic
- Each Architect agent generates architecture proposal (summary, components, data model, tech stack, key decisions)
- Supplemental Python MVP guidance enforced: Python/FastAPI required, no TypeScript/NestJS, no React SPA, canonical document store enforced
- Architect Mentor consolidates into CanonicalArchitectureV1 document (validated against Pydantic schema)
- Architecture stored in canonical_documents (doc_type='architecture', status='draft')
- Architecture displayed with sections: Summary, System Diagram (ASCII), Components, Data Model, Key Decisions, Tech Stack, Deployment
- Pipeline state updated to 'architecture_approval'
- SSE stream shows: 'Architect 1 working... Architect Mentor consolidating...'

**Story Points:** 13  
**Phase:** Phase 1  
**Epic Feature:** Architecture Generation  
**Dependencies:** EPIC-101  
**Technical Notes:** Architect agents with supplemental Python MVP guidance, CanonicalArchitectureV1 Pydantic validation, Architect Mentor enforces standards (rejects TypeScript/microservices/job queues), canonical_documents INSERT

#### ARCH-101: Approve or regenerate Architecture

**User Story:** As a user, I want to approve the Architecture or request changes so that I can proceed to backlog generation with confidence in the technical approach.

**Acceptance Criteria:**
- 'Approve Architecture' button updates status='approved', advances pipeline to 'ba_start'
- 'Regenerate Architecture' re-runs Architect agents with same Epic, old Architecture status='superseded'
- Ad-hoc Q&A feature: User can type question ('Why SQLite over PostgreSQL?') via text input
- Ad-hoc question triggers single agent call with Epic + Architecture context
- Ad-hoc response streamed via SSE and displayed inline below question
- Approval triggers BA (Backlog) generation workflow automatically

**Story Points:** 5  
**Phase:** Phase 1  
**Epic Feature:** Architecture Generation  
**Dependencies:** ARCH-100  
**Technical Notes:** POST /workspaces/{id}/approve?stage=architecture, ad-hoc Q&A SSE endpoint with single agent call, HTMX for question submission and response display

### Theme: Backlog Generation & Approval

#### BACKLOG-100: Generate Canonical Backlog with INVEST user stories

**User Story:** As a user, I want the system to generate INVEST-compliant user stories so that I have an actionable development backlog.

**Acceptance Criteria:**
- After Architecture approval, Orchestrator spawns 3 BA agents with Epic + Architecture
- Each BA agent generates 20-40 user stories following INVEST principles (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- BA Mentor consolidates into CanonicalBacklogV1 (validated against Pydantic schema)
- Backlog stored in canonical_documents (doc_type='backlog', status='draft')
- Each story includes: ID, Title, User Story, Acceptance Criteria (list), Story Points, Phase, Epic Feature, Dependencies (list), Technical Notes
- Stories grouped by Epic phase (Phase 1, Phase 2, Phase 3)
- Traceability: Each story links to Epic feature and phase via structured fields
- Pipeline state updated to 'backlog_approval'
- SSE stream shows: 'BA Agent 1 generating stories... BA Mentor consolidating...'

**Story Points:** 13  
**Phase:** Phase 1  
**Epic Feature:** Backlog Generation  
**Dependencies:** ARCH-101  
**Technical Notes:** BA agents enforce INVEST principles, CanonicalBacklogV1 Pydantic schema with story blocks, BA Mentor deduplication and consolidation, canonical_documents INSERT

#### BACKLOG-101: Review and approve backlog

**User Story:** As a user, I want to review the backlog and approve it so that I can finalize my product definition and proceed to implementation or export.

**Acceptance Criteria:**
- Backlog displayed in table view with columns: Story ID, Title, Story Points, Phase, Status
- Filter dropdown or tabs: All Stories / Phase 1 / Phase 2 / Phase 3
- Click story row expands details: User Story, Acceptance Criteria (bulleted list), Dependencies, Technical Notes
- 'Approve Backlog' button updates status='approved', marks workspace as complete
- 'Regenerate Backlog' re-runs BA agents with same Epic + Architecture
- Approval enables export functionality (Markdown and JSON downloads)
- Story count and total story points displayed at top of table

**Story Points:** 5  
**Phase:** Phase 1  
**Epic Feature:** Backlog Generation  
**Dependencies:** BACKLOG-100  
**Technical Notes:** HTMX table with expandable rows, filtering via query params, POST /workspaces/{id}/approve?stage=backlog, Jinja2 template for backlog view

### Theme: Export Functionality

#### EXPORT-100: Export workspace as Markdown

**User Story:** As a user, I want to download my workspace as a Markdown file so that I can share the complete product definition with my team or store it externally.

**Acceptance Criteria:**
- Export button visible after backlog approval
- GET /workspaces/{id}/export?format=markdown generates .md file
- Markdown structure: Epic sections (Vision, Problem, Goals, etc.) → Architecture sections (Summary, Components, Decisions) → Backlog (stories grouped by phase)
- Template-based generation using Jinja2 templates that read from canonical_documents table
- Filename format: {workspace_name}_{YYYY-MM-DD}.md
- Immediate synchronous download (no background job or queue)
- Export includes traceability: Story IDs, Epic feature references, phase labels

**Story Points:** 5  
**Phase:** Phase 1  
**Epic Feature:** Export Functionality  
**Dependencies:** BACKLOG-101  
**Technical Notes:** Export Service module, Jinja2 templates for Markdown formatting, canonical_documents query for epic/architecture/backlog, FastAPI Response with Content-Disposition header

#### EXPORT-101: Export workspace as JSON (Jira-compatible)

**User Story:** As a user, I want to export my workspace as JSON so that I can import it into Jira or Linear without manual field mapping.

**Acceptance Criteria:**
- GET /workspaces/{id}/export?format=json generates .json file
- JSON structure: {workspace: {...}, epic: {...}, architecture: {...}, backlog: {stories: [...]}}
- Each story object includes: id, title, description (user story), acceptance_criteria (array), story_points, phase, epic_feature, dependencies (array), technical_notes
- Traceability fields: epic_id, feature_id, phase_id for each story
- Jira-compatible schema: Can be imported via Jira REST API or CSV import without manual mapping
- Direct JSON serialization from canonical_documents.content (no template)
- Filename format: {workspace_name}_{YYYY-MM-DD}.json

**Story Points:** 3  
**Phase:** Phase 1  
**Epic Feature:** Export Functionality  
**Dependencies:** BACKLOG-101  
**Technical Notes:** Python JSON serialization via json.dumps, canonical_documents query, Jira-compatible schema mapping, FastAPI JSONResponse

### Theme: Real-Time Streaming (SSE)

#### SSE-100: Stream agent progress via Server-Sent Events

**User Story:** As a user, I want to see real-time updates while agents are working so that I know the system is actively processing my request.

**Acceptance Criteria:**
- GET /workspaces/{id}/stream returns SSE with Content-Type: text/event-stream
- Event types: {type: 'status', message: '...'}, {type: 'agent_start', agent: 'pm_1'}, {type: 'agent_output', agent: 'pm_1', content: '...'}, {type: 'agent_complete', agent: 'pm_1'}, {type: 'mentor_start'}, {type: 'mentor_complete'}
- EventSource client in frontend receives and displays status messages in workspace view
- Progress messages: 'PM Agent 1 working... PM Agent 2 complete... PM Mentor consolidating... Epic generation complete!'
- SSE stream automatically closes when Mentor finishes consolidation (stage completion)
- Auto-reconnect on disconnect (EventSource built-in retry with 3-second timeout)
- Proper SSE framing: data: prefix for each event, double newline (\n\n) delimiter between events

**Story Points:** 8  
**Phase:** Phase 1  
**Epic Feature:** Real-Time Streaming  
**Dependencies:** PM-100, EPIC-100, ARCH-100, BACKLOG-100  
**Technical Notes:** FastAPI StreamingResponse with text/event-stream, asyncio.Queue for agent output messages, proper SSE framing (data: prefix, \n\n delimiter), EventSource API in frontend JavaScript

### Theme: Error Handling & Resilience

#### ERROR-100: Retry failed LLM API calls

**User Story:** As a system, I want to automatically retry failed LLM API calls so that transient network or API errors don't block user workflows.

**Acceptance Criteria:**
- Agent Service implements retry logic with exponential backoff for failed anthropic API calls
- Retry sequence: First attempt → wait 0.5s → second attempt → wait 2s → third attempt (if configured)
- On each failure: Error logged to agent_logs table with error message and stack trace
- On final failure after all retries: User notified with message 'Agent failed to respond. [Retry] [Contact Support]'
- Retry button re-runs specific failed agent (not entire stage)
- Errors tracked: API timeout, rate limiting (429), invalid response format, network errors
- Success after retry: No user notification, workflow continues normally

**Story Points:** 5  
**Phase:** Phase 1  
**Epic Feature:** Error Handling & Resilience  
**Dependencies:** PM-100, EPIC-100, ARCH-100, BACKLOG-100  
**Technical Notes:** Retry logic in Agent Service with exponential backoff via asyncio.sleep, agent_logs.error field for error messages, HTMX retry button UI

#### ERROR-101: Validate canonical documents before saving

**User Story:** As a system, I want to validate all canonical documents against Pydantic schemas before saving so that data integrity is maintained and downstream processes can rely on consistent structure.

**Acceptance Criteria:**
- Schema Validation Layer validates canonical_documents.content against appropriate Pydantic schema (PMQuestionsV1, CanonicalEpicV1, CanonicalArchitectureV1, CanonicalBacklogV1) before INSERT
- On validation error: Mentor agent receives detailed Pydantic error message and regenerates output (max 3 attempts)
- Validation rules enforced: fixed section keys, allowed block types only, no extra keys (extra='forbid'), block ID uniqueness per section, table row consistency
- If all Mentor rewrite attempts fail: Error logged to agent_logs.error with full Pydantic ValidationError details
- User notification on final failure: 'Generation failed due to validation error. Please try again or contact support.'
- Successful validation: Document saved to canonical_documents with status='draft' or 'approved'

**Story Points:** 5  
**Phase:** Phase 1  
**Epic Feature:** Error Handling & Resilience  
**Dependencies:** EPIC-100, ARCH-100, BACKLOG-100  
**Technical Notes:** Pydantic ValidationError handling, Mentor rewrite loop in Orchestrator, agent_logs.error logging, user error notification UI

### Theme: Re-run & Manual Overrides

#### RERUN-100: Re-run any pipeline stage

**User Story:** As a user, I want to re-run PM/Architecture/Backlog stages so that I can regenerate artifacts if I'm unsatisfied with the initial output.

**Acceptance Criteria:**
- 'Re-run' button available for each completed stage (PM Questions, Epic, Architecture, Backlog)
- Re-run fetches original context from canonical_documents (Epic for Architecture re-run, Epic + Architecture for Backlog re-run)
- Orchestrator spawns agents with original inputs (user answers, Epic, Architecture)
- Old canonical document status updated to 'superseded' (soft version)
- New output validated and saved with status='draft'
- SSE stream shows regeneration progress: 'Regenerating Architecture... Architect 1 working...'
- User can re-run unlimited times (no artificial limit)
- Re-run preserves all superseded versions for future Phase 2 version history feature

**Story Points:** 8  
**Phase:** Phase 1  
**Epic Feature:** Re-run & Manual Overrides  
**Dependencies:** EPIC-101, ARCH-101, BACKLOG-101  
**Technical Notes:** Orchestrator re-run logic with context retrieval, canonical_documents status='superseded' updates, new document INSERT with status='draft', SSE progress streaming

### Theme: Repo View (Read-Only)

#### REPO-100: List repo files (read-only)

**User Story:** As the AI Dev Orchestrator, I want a read-only API to list files in the repo so that I can discover existing modules, routes, models, and templates before changing anything.

**Acceptance Criteria:**
- GET /repo/files endpoint accepts query params: root (required, e.g. 'app'), glob (optional, e.g. '**/*.py'), max_files (optional, default 200)
- Endpoint enforces allow-list of roots: 'app', 'tests', 'templates', 'static', 'pyproject.toml', 'README.md'; rejects access to .env, secrets, .git, or any path outside allow-list
- Returns JSON with fields: {root: string, files: array of relative paths}
- Returns at most max_files entries; if exceeded, returns truncated: true flag
- Implemented in FastAPI under dedicated router (e.g. app/routers/repo_view.py), mounted on main app
- Endpoint is strictly read-only: no file writes, deletes, or git operations allowed
- Binary files (.pyc, .sqlite, .db) excluded from listings

**Story Points:** 3  
**Phase:** Phase 1  
**Epic Feature:** Repo View  
**Dependencies:** ARCH-100  
**Technical Notes:** Use pathlib for file traversal with glob support; apply strict allow-listing on roots and ignore binary files. This service is for LLM/Orchestrator introspection only and must not expose .env, secrets, or the .git directory.

#### REPO-101: Get repo file content (read-only)

**User Story:** As the AI Dev Orchestrator, I want to fetch the contents of a specific file so that I can inspect existing implementations (routes, models, templates) and follow the established patterns.

**Acceptance Criteria:**
- GET /repo/file endpoint accepts path query parameter (relative to an allowed root from REPO-100 allow-list)
- Endpoint enforces allow-listed directories and blocks access to .env, secrets, .git, and any non-text file extensions (.pyc, .sqlite, .db, .png, .jpg, etc.)
- Supports optional max_bytes query param (default 16384 bytes / 16 KB); truncates responses above limit and adds truncated: true flag
- Returns JSON: {path: string, content: string, truncated: boolean}
- Only serves UTF-8 text files; non-text or binary files return 400 error with message: 'File is not a text file'
- Implemented in same repo_view router as REPO-100
- Strictly read-only: no write operations permitted

**Story Points:** 3  
**Phase:** Phase 1  
**Epic Feature:** Repo View  
**Dependencies:** REPO-100  
**Technical Notes:** This endpoint is read-only and intended for AI/Orchestrator consumption. Combine with REPO-100 so agents can list then fetch files, instead of guessing project structure. Use pathlib.read_text() with error handling for encoding issues.

**Phase 1 Total:** 22 stories, 117 story points. Estimated completion: 3 months with 2-3 full-stack engineers (39 story points per month average).

## Phase 2: Workflow Intelligence (Months 4-6)

Phase 2 adds workflow intelligence features: drift detection when users manually edit canonical documents, version history with rollback UI, idea library with search, PDF export, PostgreSQL migration, repo content search, and migration to third-party authentication providers.

### Phase 2 Stories (High-Level)

- **AUTH-200:** Migrate to third-party authentication (Auth0/Clerk) - 13 points
- **DRIFT-100:** Detect drift when user edits canonical documents - 8 points
- **VERSION-100:** Version history with rollback UI - 8 points
- **LIBRARY-100:** Idea library with full-text search - 5 points
- **PDF-100:** PDF export generation - 5 points
- **MIGRATE-100:** SQLite to PostgreSQL migration - 8 points
- **REPO-200:** Search repo by content (read-only) - 5 points

**Phase 2 Total:** 7 stories, 52 story points. Estimated completion: 2-3 months.

## Phase 3: Growth & Expansion (Months 7-9)

Phase 3 adds growth features: read-only workspace sharing, API access for developers, user-selectable LLM models, horizontal scaling, and cloud storage migration.

### Phase 3 Stories (High-Level)

- **SHARE-100:** Read-only workspace sharing - 13 points
- **API-100:** API key authentication for programmatic access - 8 points
- **MODEL-100:** User-selectable LLM models - 8 points

**Phase 3 Total:** 3 stories, 29 story points. Estimated completion: 2-3 months.

## Backlog Summary

| Phase | Stories | Story Points | Duration |
|-------|---------|--------------|----------|
| Phase 1: Core Platform / MVP | 22 | 117 | 3 months |
| Phase 2: Workflow Intelligence | 7 | 52 | 2-3 months |
| Phase 3: Growth & Expansion | 3 | 29 | 2-3 months |
| **Total** | **32** | **198** | **7-9 months** |

Estimated team velocity: 39 story points per month (assumes 2-3 full-stack engineers with Python/FastAPI expertise). Phase 1 MVP deliverable in 3 months, full roadmap in 7-9 months.

All stories trace to Canonical Epic features and phases. All Phase 1 stories align with Canonical Architecture (Python/FastAPI, HTMX, SQLite, canonical document store). Technical notes reference specific architecture components (Orchestrator Core, Agent Service, Schema Validation Layer, Export Service, Repo View).

---

**End of Export**