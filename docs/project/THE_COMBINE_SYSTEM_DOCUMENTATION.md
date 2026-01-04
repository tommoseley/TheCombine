# The Combine — System Architecture & Database Documentation

**Document Type:** Internal Technical Documentation  
**Status:** Canonical  
**Version:** 1.0  
**Date:** December 2025  

---

## 1. System Overview

The Combine is a document production system. It generates structured project artifacts—discovery documents, architecture specifications, epic backlogs, and story backlogs—using AI orchestration.

The system is **document-centric**, not worker-centric. Document types are the stable abstraction. The workers, prompts, and AI models that produce them are implementation details.

### 1.1 Governing Principle

**Documents are the product; workers are anonymous labor.**

The system does not "run the Architect." It "builds a Project Discovery document." This inversion—from role execution to document production—is the foundational architectural decision.

### 1.2 Key Characteristics

| Characteristic | Description |
|----------------|-------------|
| Document-centric | Documents are first-class entities; roles are metadata |
| Workflow-driven | Document dependencies form an implicit workflow |
| Deterministic | Documents are the source of truth, not agent memory |
| AI-orchestrated | LLMs generate documents; humans review and accept |
| No human editing | System-generated documents are immutable outputs |

---

## 2. System Architecture

### 2.1 Major Subsystems

The Combine consists of four major subsystems:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web UI Layer                             │
│  (FastAPI + Jinja2 + HTMX)                                      │
├─────────────────────────────────────────────────────────────────┤
│                      Document Routes                            │
│  (Request routing, HTMX/browser detection, template selection)  │
├─────────────────────────────────────────────────────────────────┤
│                     Domain Services                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Document   │  │   Document   │  │    Document Status    │  │
│  │   Builder   │  │   Service    │  │       Service         │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    Handler Registry                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Registry   │  │   Handlers   │  │   LLM Response        │  │
│  │   Loader    │  │   (per type) │  │     Parser            │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    Persistence Layer                            │
│  (PostgreSQL + SQLAlchemy Async)                                │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Subsystem Responsibilities

#### 2.2.1 Web UI Layer

**Responsibility:** Present documents and handle user interactions.

- Renders document content using Jinja2 templates
- Handles HTMX partial requests vs full page loads
- Provides sidebar navigation with document status
- Manages project tree expansion/collapse

**Boundaries:**
- Does NOT contain business logic
- Does NOT call LLM directly
- Delegates document operations to Domain Services

#### 2.2.2 Document Routes

**Responsibility:** Route requests to appropriate templates and services.

- Detects HTMX requests (`HX-Request` header) vs browser requests
- Returns partials for HTMX, full pages for browser refresh
- Fetches document type metadata from database
- Coordinates between UI layer and domain services

**Key Routes:**
- `GET /ui/projects/{project_id}/documents/{doc_type_id}` — View document
- `POST /ui/projects/{project_id}/documents/{doc_type_id}/build` — Build document (SSE stream)

#### 2.2.3 Domain Services

**Document Builder**
- The single class that builds any document type
- Registry-driven: document type determines behavior
- Handles dependency checking, input gathering, LLM invocation
- Supports synchronous and streaming builds
- Delegates parsing/validation to handlers

**Document Service**
- CRUD operations for documents
- Version management (`is_latest` flag)
- Document relation tracking (`derived_from`)
- Space-scoped queries

**Document Status Service**
- Derives readiness status (ready, stale, blocked, waiting)
- Derives acceptance state (accepted, needs_acceptance, rejected)
- Computes actionable subtitles for UI
- All status is computed, never stored

#### 2.2.4 Handler Registry

**Registry Loader**
- Reads document type configuration from database
- Caches configuration for performance
- Maps `doc_type_id` to handler instances

**Handlers (per document type)**
- Parse LLM responses
- Validate against schema
- Transform/enrich data
- Render HTML representations
- Render summary representations

**LLM Response Parser**
- Extracts structured data from raw LLM output
- Handles markdown fences, preambles, malformed JSON
- Multiple parsing strategies (direct JSON, fence extraction, repair)

### 2.3 Runtime Roles

| Role | Responsibility |
|------|----------------|
| **Handler** | Process a specific document type (parse, validate, transform, render) |
| **Builder** | Orchestrate document production (gather inputs, call LLM, invoke handler) |
| **Registry** | Map document type IDs to configurations and handlers |

### 2.4 Document Flow

```
User clicks "Generate {Document Type}"
           │
           ▼
┌─────────────────────────────────┐
│   Document Routes (build)       │
│   POST /documents/{type}/build  │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│      Document Builder           │
│  1. Load config from registry   │
│  2. Check dependencies          │
│  3. Gather input documents      │
│  4. Load prompts from DB        │
│  5. Build user message          │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│      Anthropic API              │
│   (Streaming response)          │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│      Handler.process()          │
│  1. Parse raw text              │
│  2. Validate schema             │
│  3. Transform/enrich            │
│  4. Extract title               │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│      Document Service           │
│  1. Create document record      │
│  2. Set is_latest = true        │
│  3. Create derived_from edges   │
│  4. Compute revision hash       │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│      Handler.render()           │
│   (For immediate display)       │
└─────────────────────────────────┘
           │
           ▼
      UI Updated via SSE
```

---

## 3. Document Model

### 3.1 Canonical Document Types

The system currently supports four document types:

| doc_type_id | Name | Purpose | Scope |
|-------------|------|---------|-------|
| `project_discovery` | Project Discovery | Initial architectural exploration; surfaces unknowns, blocking questions, early decision points, MVP guardrails | project |
| `epic_backlog` | Epic Backlog | PM-level decomposition into epics with high-level stories; defines work streams | project |
| `technical_architecture` | Technical Architecture | Comprehensive architecture specification; components, interfaces, data models, workflows | project |
| `story_backlog` | Story Backlog | BA-level decomposition into implementation-ready stories; detailed acceptance criteria | project |

### 3.2 Document Type Configuration

Each document type is defined in the `document_types` table with:

| Field | Purpose |
|-------|---------|
| `doc_type_id` | Stable identifier (the public contract) |
| `name` | Human-readable display name |
| `description` | Explains what this document represents |
| `icon` | Lucide icon name for UI |
| `builder_role` | Which role produces this (architect, pm, ba) |
| `builder_task` | Which task within that role |
| `handler_id` | Maps to code handler class |
| `required_inputs` | Document types that must exist before building |
| `optional_inputs` | Document types that enhance output if present |
| `acceptance_required` | Whether human sign-off is needed |
| `accepted_by_role` | Which role must accept |
| `scope` | Where document appears (project, epic, story) |
| `display_order` | UI ordering |

### 3.3 Document Dependencies

Documents form an implicit workflow through their dependencies:

```
project_discovery
       │
       ├───────────────┬──────────────────┐
       ▼               ▼                  ▼
  epic_backlog    technical_architecture  │
       │               │                  │
       └───────────────┴──────────────────┘
                       │
                       ▼
                 story_backlog
                 (requires both)
```

**Current Dependency Configuration:**

| Document Type | Required Inputs | Optional Inputs |
|---------------|-----------------|-----------------|
| `project_discovery` | (none) | (none) |
| `epic_backlog` | `project_discovery` | (none) |
| `technical_architecture` | `project_discovery` | `epic_backlog` |
| `story_backlog` | `epic_backlog`, `technical_architecture` | (none) |

### 3.4 Creation Triggers

Documents are created through explicit user action:

1. **User navigates to document** that does not exist
2. **UI displays "Not Created" state** with document description
3. **User clicks "Generate {Document Type}"** button
4. **System checks dependencies** — if missing, build is blocked
5. **System gathers input documents** from required/optional inputs
6. **System invokes LLM** with role prompts and input context
7. **System parses and validates** response
8. **System persists document** with provenance

There is no automatic document generation. All builds are user-initiated.

### 3.5 Readiness Semantics

Document readiness is derived, never stored. The `DocumentStatusService` computes:

| Status | Meaning | Derivation Logic |
|--------|---------|------------------|
| `ready` | Exists, valid, safe to use | Document exists AND `is_stale = false` |
| `stale` | Exists but inputs changed | Document exists AND `is_stale = true` |
| `blocked` | Cannot be built | Required inputs missing |
| `waiting` | Can be built, not yet built | Prerequisites met, document does not exist |

### 3.6 Acceptance Semantics

Acceptance is optional per document type. When `acceptance_required = true`:

| State | Meaning | Derivation Logic |
|-------|---------|------------------|
| `accepted` | Explicitly approved | `accepted_at IS NOT NULL` AND `rejected_at IS NULL` |
| `needs_acceptance` | Awaiting review | `accepted_at IS NULL` AND `rejected_at IS NULL` |
| `rejected` | Changes requested | `rejected_at IS NOT NULL` |

Acceptance gates downstream use:
- A document with `acceptance_required = true` cannot be used as input for other documents until accepted
- Stale + accepted documents display a warning but remain usable

### 3.7 "Not Found → Create" Flow

When a user navigates to a document that does not exist:

1. **Route handler** queries for document in database
2. **Document not found** — route returns "not found" template
3. **Template displays:**
   - Document type name and icon
   - Document type description (from `document_types.description`)
   - "Generate {Document Type}" button
4. **User clicks generate** — triggers POST to `/build` endpoint
5. **Build endpoint** returns SSE stream with progress updates
6. **On completion** — UI refreshes to show created document

The "not found" state is a normal UI state, not an error.

---

## 4. Database / Persistence Model

### 4.1 Entity-Relationship Overview

```
┌─────────────┐      ┌──────────────────┐
│   Project   │      │  DocumentType    │
│             │      │    (Registry)    │
└──────┬──────┘      └────────┬─────────┘
       │                      │
       │ space_id             │ doc_type_id
       │                      │
       ▼                      ▼
┌─────────────────────────────────────────┐
│               Document                   │
│  (space_type, space_id, doc_type_id)    │
└──────────────────┬──────────────────────┘
                   │
                   │ from_document_id / to_document_id
                   ▼
          ┌─────────────────┐
          │ DocumentRelation│
          └─────────────────┘

┌─────────────┐      ┌──────────────────┐
│    Role     │◄─────│    RoleTask      │
│ (identity)  │      │ (task prompts)   │
└─────────────┘      └──────────────────┘
```

### 4.2 Core Tables

#### 4.2.1 projects

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `project_id` | VARCHAR(8) | Short identifier (e.g., "HMP", "DEMO") |
| `name` | VARCHAR(200) | Display name |
| `description` | TEXT | Project description (used as LLM context) |
| `status` | VARCHAR(50) | active, archived |
| `icon` | VARCHAR(50) | Lucide icon name |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last modification |

#### 4.2.2 document_types

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `doc_type_id` | VARCHAR(100) | Stable identifier (UNIQUE) |
| `name` | VARCHAR(255) | Display name |
| `description` | TEXT | What this document represents |
| `category` | VARCHAR(100) | architecture, planning, development |
| `icon` | VARCHAR(50) | Lucide icon name |
| `schema_definition` | JSONB | JSON Schema for validation |
| `schema_version` | VARCHAR(20) | Schema version |
| `builder_role` | VARCHAR(50) | architect, pm, ba |
| `builder_task` | VARCHAR(100) | Task name within role |
| `handler_id` | VARCHAR(100) | Maps to code handler |
| `required_inputs` | JSONB | Array of doc_type_ids |
| `optional_inputs` | JSONB | Array of doc_type_ids |
| `gating_rules` | JSONB | Additional conditions |
| `acceptance_required` | BOOLEAN | Requires human sign-off |
| `accepted_by_role` | VARCHAR(64) | Role that accepts |
| `scope` | VARCHAR(50) | project, epic, story |
| `display_order` | INTEGER | UI ordering |
| `is_active` | BOOLEAN | Enabled/disabled |

#### 4.2.3 documents

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `space_type` | VARCHAR(50) | project, organization, team |
| `space_id` | UUID | FK to owning entity |
| `doc_type_id` | VARCHAR(100) | FK to document_types |
| `version` | INTEGER | Version number |
| `revision_hash` | VARCHAR(64) | SHA-256 of content |
| `is_latest` | BOOLEAN | True for current version |
| `title` | VARCHAR(500) | Document title |
| `summary` | TEXT | Short description |
| `content` | JSONB | The actual document data |
| `status` | VARCHAR(50) | draft, active, stale, archived |
| `is_stale` | BOOLEAN | Inputs have changed |
| `created_by` | VARCHAR(200) | User or system ID |
| `created_by_type` | VARCHAR(50) | user, builder, import |
| `builder_metadata` | JSONB | model, tokens, prompt_id |
| `accepted_at` | TIMESTAMP | When accepted |
| `accepted_by` | VARCHAR(200) | Who accepted |
| `rejected_at` | TIMESTAMP | When rejected |
| `rejected_by` | VARCHAR(200) | Who rejected |
| `rejection_reason` | TEXT | Why rejected |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last modification |

#### 4.2.4 document_relations

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `from_document_id` | UUID | Source document |
| `to_document_id` | UUID | Target document |
| `relation_type` | VARCHAR(50) | requires, derived_from |
| `pinned_version` | INTEGER | Optional version pin |
| `pinned_revision` | VARCHAR(64) | Optional hash pin |
| `notes` | TEXT | Human notes |
| `relation_metadata` | JSONB | Additional data |
| `created_at` | TIMESTAMP | Creation time |

#### 4.2.5 roles

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(50) | architect, pm, ba, developer, qa |
| `identity_prompt` | TEXT | "Who you are" system prompt portion |
| `description` | TEXT | Role description |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last modification |

#### 4.2.6 role_tasks

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `role_id` | UUID | FK to roles |
| `task_name` | VARCHAR(100) | Task identifier |
| `task_prompt` | TEXT | "What you are doing" prompt portion |
| `expected_schema` | JSONB | Expected output schema |
| `progress_steps` | JSONB | UI progress indicators |
| `is_active` | BOOLEAN | Enabled/disabled |
| `version` | VARCHAR(16) | Prompt version |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last modification |

### 4.3 What Is Stored

| Data | Storage Location |
|------|------------------|
| Document content | `documents.content` (JSONB) |
| Document metadata | `documents.*` columns |
| Document provenance | `documents.builder_metadata`, `document_relations` |
| Document versions | Multiple rows with `is_latest` flag |
| Document relationships | `document_relations` table |
| Document type registry | `document_types` table |
| Role prompts | `roles` + `role_tasks` tables |
| Project metadata | `projects` table |

### 4.4 What Is NOT Stored

| Data | Reason |
|------|--------|
| Document readiness status | Derived from `documents.is_stale` and `document_types.required_inputs` |
| Document acceptance state | Derived from `accepted_at` and `rejected_at` columns |
| UI subtitles | Derived by `DocumentStatusService` |
| LLM conversation history | Documents replace conversational memory |
| Agent state | Workers are stateless |
| Workflow state | Implicit in document existence and dependencies |

### 4.5 Determinism Preservation

The system maintains determinism through:

1. **Documents as source of truth** — No agent memory, no conversation history
2. **Revision hashes** — `documents.revision_hash` provides immutability verification
3. **Provenance tracking** — `builder_metadata` records model, tokens, prompt version
4. **Input references** — `document_relations.derived_from` tracks which documents were inputs
5. **Version lineage** — `is_latest` flag enables version history without mutation

### 4.6 Documents Replace Agent Memory

Traditional AI systems maintain conversation context. The Combine does not.

When building a new document:
1. The system queries the database for required input documents
2. Input documents are serialized and included in the LLM prompt
3. The LLM has no memory of previous interactions
4. All context comes from documents

This ensures:
- Reproducibility (same inputs → same prompt)
- Auditability (provenance is explicit)
- No context drift (documents are immutable)
- Scalability (no session state)

---

## 5. Handler Architecture

### 5.1 Handler Responsibilities

Each handler implements:

| Method | Purpose |
|--------|---------|
| `process(raw_text, schema)` | Parse, validate, transform raw LLM output |
| `render(data)` | Produce full HTML view |
| `render_summary(data)` | Produce compact representation |
| `transform(data)` | Enrich with computed fields |

### 5.2 Registered Handlers

| handler_id | Handler Class | Document Type |
|------------|---------------|---------------|
| `project_discovery` | `ProjectDiscoveryHandler` | Project Discovery |
| `epic_backlog` | `EpicBacklogHandler` | Epic Backlog |
| `technical_architecture` | `ArchitectureSpecHandler` | Technical Architecture |
| `story_backlog` | `StoryBacklogHandler` | Story Backlog |

### 5.3 Handler Registration

Handlers are registered in `app/domain/handlers/registry.py`:

```python
HANDLERS: Dict[str, BaseDocumentHandler] = {
    "project_discovery": ProjectDiscoveryHandler(),
    "epic_backlog": EpicBacklogHandler(),
    "technical_architecture": ArchitectureSpecHandler(),
    "story_backlog": StoryBacklogHandler(),
}
```

Adding a new document type requires:
1. Create handler class
2. Register in `HANDLERS` dict
3. Insert row in `document_types` table
4. Insert row in `role_tasks` table (for prompts)

---

## 6. Prompt Architecture

### 6.1 Two-Part Prompts

Each document build uses two prompts combined:

1. **Identity Prompt** (from `roles.identity_prompt`)
   - "Who you are"
   - Shared across all tasks for a role
   - Example: "You are a senior software architect..."

2. **Task Prompt** (from `role_tasks.task_prompt`)
   - "What you are doing"
   - Specific to each document type
   - Example: "Generate a Project Discovery document..."

### 6.2 Prompt Resolution

```
document_types.builder_role  →  roles.name  →  roles.identity_prompt
document_types.builder_task  →  role_tasks.task_name  →  role_tasks.task_prompt
```

### 6.3 Prompt Versioning

- `role_tasks.version` tracks prompt versions
- Multiple versions can exist (only `is_active = true` is used)
- Version changes do not require code deployment

---

## 7. Status Derivation Rules

### 7.1 Readiness Derivation

```python
def derive_readiness(doc_type, document, existing_types):
    # Check dependencies first
    required = doc_type.required_inputs or []
    missing = [dep for dep in required if dep not in existing_types]
    
    if missing:
        return BLOCKED, missing
    
    if document is None:
        return WAITING, []
    
    if document.is_stale:
        return STALE, []
    
    return READY, []
```

### 7.2 Acceptance Derivation

```python
def derive_acceptance(doc_type, document):
    if not doc_type.acceptance_required:
        return None  # Not applicable
    
    if document is None:
        return None  # Can't accept nothing
    
    if document.rejected_at is not None:
        return REJECTED
    
    if document.accepted_at is None:
        return NEEDS_ACCEPTANCE
    
    return ACCEPTED
```

### 7.3 Subtitle Derivation

| Condition | Subtitle |
|-----------|----------|
| Blocked | "Missing: {dep1}, {dep2}" |
| Stale + Accepted | "Inputs changed — review recommended" |
| Needs Acceptance | "Needs acceptance ({role})" |
| Rejected | "Changes requested" |
| Waiting + Acceptance Required | "Will need acceptance ({role})" |

---

## 8. Ambiguities and Notes

### 8.1 Observed Ambiguities

1. **Staleness propagation**: The mechanism for marking documents stale when their inputs change is not fully visible in the examined code. The `is_stale` column exists but the trigger/update logic was not observed.

2. **Acceptance workflow UI**: The acceptance/rejection buttons and workflow are referenced in documentation but the implementation details were not examined.

3. **Epic scope documents**: The schema supports `scope = 'epic'` for per-epic documents, but current implementation focuses on project-scope documents.

### 8.2 Naming Conventions

- `doc_type_id` and `handler_id` should match (convention, not enforced)
- `task_name` in `role_tasks` matches `builder_task` in `document_types`
- `role.name` matches `builder_role` in `document_types`

### 8.3 Single-Tenant Assumption

The current implementation assumes single-tenant deployment:
- No user authentication visible in document routes
- `space_type = 'project'` is the primary scope
- No organization/team hierarchy observed in use

---

*This document describes The Combine as it exists. It does not propose changes or improvements.*
