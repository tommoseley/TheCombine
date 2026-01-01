# ADR-010 Implementation Plan: LLM Execution Logging, Telemetry, and Replay

## Blocking Questions

**None.** All critical architectural questions have been answered through code review:

- ✅ LLM calls are centralized in `DocumentBuilder.build_stream()`
- ✅ Streaming uses `anthropic.messages.stream()` with SSE events
- ✅ `RolePromptService` provides `ComposedPrompt` with version info
- ✅ No tool calls currently in use (deferred to post-MVP)
- ✅ FastAPI + PostgreSQL + SQLAlchemy stack confirmed
- ✅ Request correlation can be added via middleware

---

## Executive Summary

- **Implement four core tables** (`llm_run`, `llm_run_input_ref`, `llm_run_output_ref`, `llm_run_error`) plus `llm_content` for DB-backed storage; defer `llm_run_tool_call` to post-MVP
- **Centralized logging service** (`LLMExecutionLogger`) encapsulates all logging operations, preventing scattered instrumentation and enforcing invariants
- **Streaming-aware instrumentation** creates `llm_run` before streaming starts, accumulates content during stream, logs outputs after completion
- **Correlation ID middleware** injects `correlation_id` into request state, propagates through DocumentBuilder to logging layer
- **DB-backed content storage** via `llm_content` table with `db://llm_content/{uuid}` URIs; deduplication via SHA-256 hash; pluggable for future object storage
- **Replay API endpoint** (`POST /api/admin/llm-runs/{id}/replay`) reconstructs inputs, executes new run, returns comparison metadata
- **Zero business logic changes** - logging wraps existing DocumentBuilder flow via try/catch, graceful degradation if logging fails
- **Single Alembic migration** creates all tables atomically; no backfill required (logs accumulate forward from deployment)

---

## Current-State Assumptions

### What We Inferred From Repository

1. **Architecture**: FastAPI backend with PostgreSQL database, SQLAlchemy async ORM
2. **LLM Invocation**: Centralized in `DocumentBuilder.build_stream()` using `anthropic.messages.stream()`
3. **Streaming Pattern**: Server-Sent Events (SSE) to client, content accumulated in memory during stream
4. **Prompt System**: `RolePromptService` provides `ComposedPrompt` dataclass with:
   - `task_id` (UUID) - stable identifier
   - `version` (string) - human-readable version (e.g., "1.2.3")
   - `role_name` (string) - pm, architect, ba, developer, qa
   - `task_name` (string) - preliminary, final, epic_creation, etc.
   - `identity_prompt` + `task_prompt` - composed into final prompt
5. **Request Context**: FastAPI Request object available in routes, can hold correlation_id in `request.state`
6. **Project Audit**: Implemented per ADR-009 with `project_audit` table
7. **No Tool Calls**: Current implementation does not use LLM tool calling (confirmed by product owner)
8. **Database Migration**: Alembic is standard for FastAPI/SQLAlchemy projects (assumption)
9. **Error Handling**: Try/except patterns with SSE error events to client
10. **Document Flow**: `document_routes.py` → `DocumentBuilder` → `DocumentService.create_or_update_document()`

### Explicit Uncertainties / Open Questions

1. **Alembic Migration Location**: Where do migration files live? (`alembic/versions/` assumed)
2. **Cost Calculation**: Should we compute `cost_usd` from token counts + pricing table, or leave NULL in MVP? (Assume: NULL in MVP, add post-MVP)
3. **Redaction Policy**: Who/what triggers `content_redacted=true`? (Assume: manual admin action only in MVP)
4. **Content Cleanup**: Retention policy for `llm_content` table? (Assume: no automatic deletion in MVP, operational concern)
5. **Replay Permissions**: Admin-only or project-role-based? (Assume: admin-only via `/api/admin/` prefix)
6. **Migration Rollback**: Do we need down migrations? (Assume: yes, for development safety)
7. **Logging Failure Impact**: If logging fails, should LLM execution continue? (Assume: yes, graceful degradation with stderr logging)
8. **Existing Correlation Infra**: Is there any correlation tracking already? (Assume: no, we're adding it fresh)

---

## MVP Scope (What Will Be Implemented Now)

### Core Tables
- `llm_content` (DB-backed content storage)
- `llm_run` (main execution record)
- `llm_run_input_ref` (prompt, context, schema references)
- `llm_run_output_ref` (response references)
- `llm_run_error` (detailed error tracking)

### Infrastructure
- `LLMExecutionLogger` service class (centralized logging API)
- Correlation ID middleware (FastAPI HTTP middleware)
- DocumentBuilder instrumentation (streaming-aware)
- Content storage/resolution functions

### Integration
- Instrument `DocumentBuilder.build_stream()` with logging
- Pass `correlation_id` from route → builder → logger
- Capture inputs before streaming, outputs after completion
- Link to `project_audit` via metadata when documents saved

### Replay
- API endpoint: `POST /api/admin/llm-runs/{id}/replay`
- Input reconstruction from `llm_run_input_ref`
- New run creation with `is_replay=true` metadata
- Basic comparison output (token deltas, output diff)

### Testing
- Unit tests for `LLMExecutionLogger` methods
- Integration tests for instrumented document builds
- Replay scenario tests
- Error logging tests

---

## Out of Scope / Post-MVP Enhancements

**Explicitly Deferred (Per ADR-010):**

1. **`llm_run_event` table** - Phase-level progress tracking (e.g., "READING", "GENERATING", "VALIDATING")
2. **`llm_run_tool_call` table** - Currently no tool usage; table defined in schema but unused until tools are added
3. **Detailed retry telemetry** - Basic retry count in `metadata` acceptable, detailed per-retry logging deferred
4. **Object storage backends** - S3/MinIO/filesystem for `content_ref`; MVP is DB-only with `db://` URIs
5. **Replay UI** - Admin web interface for triggering replays and viewing diffs
6. **Automated diff tooling** - Text diff algorithms, semantic comparison, regression detection
7. **Cost dashboards** - Analytics UI showing cost trends, model comparisons, optimization opportunities
8. **Prompt regression testing framework** - Automated replay suite for prompt version validation
9. **Content redaction automation** - PII detection, automated flagging (manual redaction only in MVP)
10. **Advanced retention policies** - Automated cleanup of old `llm_content` records based on age/access

**Rationale for Deferral:**
- Tool calls: Not currently used, would add complexity without value
- Progress events: Nice-to-have UI feature, not critical for investigability
- Object storage: DB storage sufficient for MVP volume, pluggable architecture enables future migration
- Dashboards/UI: Data is logged, visualization is separate concern

---

## Data Model & Migrations

### Migration Ordering

**Single Migration File**: `alembic/versions/2024XXXX_add_llm_execution_logging.py`

Creates tables in dependency order:
1. `llm_content` (no dependencies)
2. `llm_run` (references `projects` table)
3. `llm_run_input_ref` (references `llm_run`)
4. `llm_run_output_ref` (references `llm_run`)
5. `llm_run_error` (references `llm_run`)
6. `llm_run_tool_call` (references `llm_run`) - **created but unused in MVP**

### Exact Table Definitions (DDL-Level Detail)

```sql
-- ============================================================================
-- Content storage table (DB-backed blob store)
-- ============================================================================
CREATE TABLE llm_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hex digest
    content_text TEXT NOT NULL,         -- Actual content
    content_size INT NOT NULL,          -- Bytes (UTF-8 encoded)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT now()  -- For cache eviction metrics
);

CREATE INDEX idx_llm_content_hash ON llm_content(content_hash);
CREATE INDEX idx_llm_content_accessed ON llm_content(accessed_at);

COMMENT ON TABLE llm_content IS 'Content storage for LLM inputs/outputs (ADR-010)';
COMMENT ON COLUMN llm_content.content_hash IS 'SHA-256 hash for deduplication';
COMMENT ON COLUMN llm_content.accessed_at IS 'Updated on each access for cache metrics';


-- ============================================================================
-- Main execution record (one per LLM invocation)
-- ============================================================================
CREATE TABLE llm_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id UUID NOT NULL,
    project_id UUID NULL REFERENCES projects(id) ON DELETE SET NULL,
    artifact_type TEXT NULL,              -- discovery, epic, architecture, story, qa
    role TEXT NOT NULL,                   -- PM_MENTOR, BA_MENTOR, ARCHITECT_MENTOR, DEVELOPER_MENTOR, QA_MENTOR
    model_provider TEXT NOT NULL,         -- anthropic, openai
    model_name TEXT NOT NULL,             -- claude-sonnet-4-20250514
    prompt_id TEXT NOT NULL,              -- Stable identifier (e.g., "pm/preliminary")
    prompt_version TEXT NOT NULL,         -- Human-readable version (e.g., "1.2.3")
    effective_prompt_hash TEXT NOT NULL,  -- SHA-256 of final resolved prompt
    schema_version TEXT NULL,             -- Output schema version if applicable
    status TEXT NOT NULL,                 -- IN_PROGRESS, SUCCESS, FAILED, PARTIAL, CANCELLED
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NULL,
    input_tokens INT NULL,
    output_tokens INT NULL,
    total_tokens INT NULL,
    cost_usd NUMERIC(10, 6) NULL,        -- Computed cost (nullable in MVP)
    primary_error_code TEXT NULL,
    primary_error_message TEXT NULL,
    error_count INT NOT NULL DEFAULT 0,
    metadata JSONB NULL,                  -- retry_count, is_replay, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_run_correlation ON llm_run(correlation_id);
CREATE INDEX idx_llm_run_project_time ON llm_run(project_id, started_at DESC) WHERE project_id IS NOT NULL;
CREATE INDEX idx_llm_run_role_time ON llm_run(role, started_at DESC);
CREATE INDEX idx_llm_run_status ON llm_run(status);
CREATE INDEX idx_llm_run_started ON llm_run(started_at DESC);

COMMENT ON TABLE llm_run IS 'LLM execution records (ADR-010)';
COMMENT ON COLUMN llm_run.correlation_id IS 'Request trace ID (propagated from HTTP layer)';
COMMENT ON COLUMN llm_run.prompt_id IS 'Stable prompt identifier from registry';
COMMENT ON COLUMN llm_run.effective_prompt_hash IS 'Hash of actual prompt sent to LLM';
COMMENT ON COLUMN llm_run.status IS 'IN_PROGRESS during streaming, SUCCESS/FAILED after completion';


-- ============================================================================
-- Input references (prompt, context, schema)
-- ============================================================================
CREATE TABLE llm_run_input_ref (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llm_run_id UUID NOT NULL REFERENCES llm_run(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,                   -- system_prompt, role_prompt, user_prompt, context_doc, schema, tools
    content_ref TEXT NOT NULL,            -- db://llm_content/{uuid}
    content_hash TEXT NOT NULL,           -- SHA-256 for verification
    content_redacted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_input_ref_run ON llm_run_input_ref(llm_run_id);
CREATE INDEX idx_llm_input_ref_kind ON llm_run_input_ref(llm_run_id, kind);

COMMENT ON TABLE llm_run_input_ref IS 'LLM input references by content_ref (ADR-010)';
COMMENT ON COLUMN llm_run_input_ref.kind IS 'Input type: role_prompt, user_prompt, context_doc, schema';
COMMENT ON COLUMN llm_run_input_ref.content_redacted IS 'Manual redaction flag (PII/sensitive data)';


-- ============================================================================
-- Output references (raw text, JSON, reports)
-- ============================================================================
CREATE TABLE llm_run_output_ref (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llm_run_id UUID NOT NULL REFERENCES llm_run(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,                   -- raw_text, json, tool_calls, qa_report
    content_ref TEXT NOT NULL,            -- db://llm_content/{uuid}
    content_hash TEXT NOT NULL,
    parse_status TEXT NULL,               -- PARSED, FAILED
    validation_status TEXT NULL,          -- PASSED, FAILED
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_output_ref_run ON llm_run_output_ref(llm_run_id);
CREATE INDEX idx_llm_output_ref_kind ON llm_run_output_ref(llm_run_id, kind);

COMMENT ON TABLE llm_run_output_ref IS 'LLM output references by content_ref (ADR-010)';
COMMENT ON COLUMN llm_run_output_ref.parse_status IS 'Whether output parsed successfully';
COMMENT ON COLUMN llm_run_output_ref.validation_status IS 'Whether output passed validation';


-- ============================================================================
-- Error tracking (many-per-run)
-- ============================================================================
CREATE TABLE llm_run_error (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llm_run_id UUID NOT NULL REFERENCES llm_run(id) ON DELETE CASCADE,
    sequence INT NOT NULL,                -- Monotonic per run (1, 2, 3...)
    stage TEXT NOT NULL,                  -- PROMPT_BUILD, MODEL_CALL, TOOL_CALL, PARSE, VALIDATE, QA_GATE, PERSIST
    severity TEXT NOT NULL,               -- INFO, WARN, ERROR, FATAL
    error_code TEXT NULL,                 -- Canonical error codes (e.g., AnthropicAPIError)
    message TEXT NOT NULL,
    details JSONB NULL,                   -- Stack traces, validation errors, provider IDs
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(llm_run_id, sequence)
);

CREATE INDEX idx_llm_error_run ON llm_run_error(llm_run_id);
CREATE INDEX idx_llm_error_stage ON llm_run_error(stage);
CREATE INDEX idx_llm_error_severity ON llm_run_error(severity);

COMMENT ON TABLE llm_run_error IS 'LLM execution errors (many-per-run model, ADR-010)';
COMMENT ON COLUMN llm_run_error.sequence IS 'Monotonic sequence within run';
COMMENT ON COLUMN llm_run_error.stage IS 'Execution stage where error occurred';


-- ============================================================================
-- Tool call tracking (DEFERRED - created but unused in MVP)
-- ============================================================================
CREATE TABLE llm_run_tool_call (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llm_run_id UUID NOT NULL REFERENCES llm_run(id) ON DELETE CASCADE,
    sequence INT NOT NULL,                -- Order in LLM response
    tool_name TEXT NOT NULL,              -- web_search, read_document, etc.
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NULL,
    status TEXT NOT NULL,                 -- PENDING, SUCCESS, FAILED
    input_ref TEXT NOT NULL,              -- db://llm_content/{uuid}
    output_ref TEXT NULL,                 -- db://llm_content/{uuid}
    error_ref TEXT NULL,                  -- db://llm_content/{uuid}
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(llm_run_id, sequence)
);

CREATE INDEX idx_llm_tool_call_run ON llm_run_tool_call(llm_run_id);
CREATE INDEX idx_llm_tool_call_name ON llm_run_tool_call(tool_name);
CREATE INDEX idx_llm_tool_call_status ON llm_run_tool_call(status);

COMMENT ON TABLE llm_run_tool_call IS 'Tool call tracking (ADR-010) - UNUSED IN MVP, reserved for future';
```

### Foreign Keys & Constraints

**Cascading Deletes:**
- When `llm_run` deleted → all children cascade (`input_ref`, `output_ref`, `error`, `tool_call`)
- Rationale: Execution logs are atomic units; partial runs are meaningless

**SET NULL on Project Deletion:**
- `llm_run.project_id` → `SET NULL` if project deleted
- Rationale: Preserve execution telemetry even if project removed (audit trail)

**Unique Constraints:**
- `llm_content.content_hash` → Enforces deduplication at DB level
- `llm_run_error(llm_run_id, sequence)` → Ensures monotonic error sequence
- `llm_run_tool_call(llm_run_id, sequence)` → Preserves tool call order

**NOT NULL Enforcement:**
- `correlation_id` → Mandatory for tracing (cannot be NULL)
- `started_at` → Always set when run created (never NULL)
- `status` → Always has value (defaults to IN_PROGRESS)

### Migration Down (Rollback)

```sql
-- Rollback order (reverse of creation)
DROP TABLE IF EXISTS llm_run_tool_call CASCADE;
DROP TABLE IF EXISTS llm_run_error CASCADE;
DROP TABLE IF EXISTS llm_run_output_ref CASCADE;
DROP TABLE IF EXISTS llm_run_input_ref CASCADE;
DROP TABLE IF EXISTS llm_run CASCADE;
DROP TABLE IF EXISTS llm_content CASCADE;
```

---

## Content Storage Strategy (MVP)

### Content Reference Generation

**Format**: `db://llm_content/{uuid}`

**Algorithm**:
```python
def store_content(content: str) -> str:
    """
    Store content and return opaque reference.
    
    Deduplicates via SHA-256 hash.
    Returns existing ref if content hash matches.
    """
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    # Check for existing content
    existing = db.query("SELECT id FROM llm_content WHERE content_hash = %s", content_hash)
    if existing:
        # Touch accessed_at for cache metrics
        db.execute("UPDATE llm_content SET accessed_at = now() WHERE id = %s", existing.id)
        return f"db://llm_content/{existing.id}"
    
    # Create new record
    new_id = db.execute("""
        INSERT INTO llm_content (content_hash, content_text, content_size)
        VALUES (%s, %s, %s)
        RETURNING id
    """, content_hash, content, len(content.encode('utf-8')))
    
    return f"db://llm_content/{new_id}"
```

### Content Resolution

**Algorithm**:
```python
def resolve_content(content_ref: str) -> str:
    """
    Resolve content_ref to actual text.
    
    Raises ValueError if ref invalid or content not found.
    """
    if not content_ref.startswith("db://llm_content/"):
        raise ValueError(f"Invalid content_ref: {content_ref}")
    
    content_id = UUID(content_ref.split("/")[-1])
    
    result = db.query("SELECT content_text FROM llm_content WHERE id = %s", content_id)
    if not result:
        raise ValueError(f"Content not found: {content_ref}")
    
    # Touch accessed_at
    db.execute("UPDATE llm_content SET accessed_at = now() WHERE id = %s", content_id)
    
    return result.content_text
```

### Deduplication Benefits

**Example Scenario:**
- Same system prompt used across 1000 runs
- Without dedup: 1000 × 50KB = 50MB storage
- With dedup: 1 × 50KB = 50KB storage (999× savings)

**Hash Collision Risk:**
- SHA-256 collision probability: ~0 (cryptographically infeasible)
- Even if collision occurred, content would be semantically identical

### Redaction Handling

**MVP Approach**: Manual admin action only

```python
def redact_input(input_ref_id: UUID, reason: str):
    """
    Mark input as redacted.
    
    Content remains in llm_content (immutable), but ref is flagged.
    """
    db.execute("""
        UPDATE llm_run_input_ref
        SET content_redacted = true,
            metadata = jsonb_set(COALESCE(metadata, '{}'), '{redaction_reason}', %s)
        WHERE id = %s
    """, reason, input_ref_id)
```

**Resolution with Redaction Check**:
```python
def resolve_content_safe(ref: LLMRunInputRef) -> str:
    """Resolve content, respecting redaction flag."""
    if ref.content_redacted:
        return "[REDACTED]"
    return resolve_content(ref.content_ref)
```

**Post-MVP Enhancement**: Automated PII detection (spaCy, Presidio) sets redaction flag

### Pluggable Architecture

**Current (MVP)**:
```python
content_ref = "db://llm_content/{uuid}"
```

**Future (S3)**:
```python
content_ref = "s3://combine-llm-logs/runs/{correlation_id}/{run_id}/input_1.txt"
```

**Future (Filesystem)**:
```python
content_ref = "file:///var/combine/llm_content/{correlation_id}/{run_id}/output.json"
```

**Resolution abstraction**:
```python
def resolve_content(content_ref: str) -> str:
    if content_ref.startswith("db://"):
        return _resolve_db(content_ref)
    elif content_ref.startswith("s3://"):
        return _resolve_s3(content_ref)
    elif content_ref.startswith("file://"):
        return _resolve_file(content_ref)
    else:
        raise ValueError(f"Unsupported content_ref scheme: {content_ref}")
```

---

## Backend Integration Plan

### Correlation ID Propagation

**Step 1: FastAPI Middleware**

Create `app/middleware/correlation.py`:
```python
"""Correlation ID middleware for distributed tracing."""
import logging
from uuid import uuid4
from fastapi import Request

logger = logging.getLogger(__name__)

async def correlation_middleware(request: Request, call_next):
    """
    Inject correlation_id into request state.
    
    Checks for X-Correlation-ID header, generates if missing.
    Propagates to response header for client tracking.
    """
    corr_id = request.headers.get("X-Correlation-ID")
    if not corr_id:
        corr_id = str(uuid4())
        logger.debug(f"Generated correlation_id: {corr_id}")
    
    # Store in request.state for access in routes/services
    request.state.correlation_id = corr_id
    
    # Execute request
    response = await call_next(request)
    
    # Echo correlation_id to client
    response.headers["X-Correlation-ID"] = corr_id
    
    return response
```

**Step 2: Register Middleware**

In `app/main.py`:
```python
from app.middleware.correlation import correlation_middleware

app = FastAPI(...)

# Register correlation middleware
app.middleware("http")(correlation_middleware)
```

**Step 3: Access in Routes**

In `app/api/routers/document_routes.py`:
```python
@router.post("/projects/{project_id}/documents/{doc_type_id}/build")
async def build_document(
    request: Request,  # Already present
    project_id: str,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Extract correlation_id from request state
    correlation_id = UUID(request.state.correlation_id)
    
    # Pass to DocumentBuilder
    builder = DocumentBuilder(
        db=db,
        prompt_service=prompt_adapter,
        document_service=document_service,
        correlation_id=correlation_id  # ← NEW
    )
    
    return StreamingResponse(builder.build_stream(...), ...)
```

### LLMExecutionLogger Service

**Location**: `app/domain/services/llm_execution_logger.py`

**Core Methods**:
```python
class LLMExecutionLogger:
    """Centralized LLM execution logging service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def start_run(...) -> UUID:
        """Create llm_run at start of execution."""
        # INSERT INTO llm_run ... RETURNING id
        
    async def add_input(run_id, kind, content):
        """Store input reference."""
        # content_ref = await _store_content(content)
        # INSERT INTO llm_run_input_ref ...
        
    async def add_output(run_id, kind, content):
        """Store output reference."""
        # content_ref = await _store_content(content)
        # INSERT INTO llm_run_output_ref ...
        
    async def log_error(run_id, stage, severity, message, details):
        """Append error to run."""
        # Get next sequence number
        # INSERT INTO llm_run_error ...
        # UPDATE llm_run SET error_count++, primary_error_*
        
    async def complete_run(run_id, status, usage, cost_usd):
        """Finalize run with metrics."""
        # UPDATE llm_run SET status, ended_at, tokens, cost_usd
        
    async def _store_content(content: str) -> str:
        """Store content, return db:// reference."""
        # SHA-256 hash
        # Check for existing via content_hash
        # Insert if new, touch accessed_at if exists
        # Return db://llm_content/{uuid}
```

**Invariants Enforced**:
- `correlation_id` never NULL (validated in `start_run()`)
- Content refs always stored before creating input/output refs
- Error sequence is monotonic (SELECT MAX(sequence) + 1)
- Primary error is latest ERROR or FATAL (updated on each error)

### DocumentBuilder Instrumentation

**Location**: `app/domain/services/document_builder.py`

**Changes Required**:

1. **Add correlation_id to __init__**:
```python
def __init__(
    self,
    db: AsyncSession,
    prompt_service,
    document_service,
    correlation_id: UUID  # ← ADD
):
    self.db = db
    self.prompt_service = prompt_service
    self.document_service = document_service
    self.correlation_id = correlation_id  # ← ADD
```

2. **Wrap build_stream() with logging**:
```python
async def build_stream(self, doc_type_id, space_type, space_id, inputs, options):
    """Build document with LLM streaming, instrumented with execution logging."""
    
    logger_svc = LLMExecutionLogger(self.db)
    run_id = None
    
    try:
        # === EXISTING: Get role/task ===
        role_name, task_name = self.prompt_service.map_doc_type(doc_type_id)
        
        # === EXISTING: Build prompt ===
        prompt_text, task_id = await self.prompt_service.build_prompt(
            role_name=role_name,
            task_name=task_name,
            epic_context=inputs.get("user_query"),
            artifacts=inputs.get("artifacts"),
        )
        
        # === NEW: Get prompt metadata ===
        composed_prompt = await self.prompt_service.prompt_service.get_prompt_by_id(task_id)
        
        # === NEW: Start LLM run ===
        run_id = await logger_svc.start_run(
            correlation_id=self.correlation_id,
            project_id=space_id if space_type == 'project' else None,
            artifact_type=doc_type_id,
            role=f"{role_name.upper()}_MENTOR",
            model_provider="anthropic",
            model_name=options.get("model", "claude-sonnet-4-20250514"),
            prompt_id=f"{role_name}/{task_name}",
            prompt_version=composed_prompt.version,
            effective_prompt=prompt_text,
        )
        
        # === NEW: Log inputs ===
        await logger_svc.add_input(run_id, "role_prompt", prompt_text)
        if inputs.get("user_query"):
            await logger_svc.add_input(run_id, "user_prompt", inputs["user_query"])
        if inputs.get("project_description"):
            await logger_svc.add_input(run_id, "context_doc", inputs["project_description"])
        
        # === EXISTING: Prepare messages ===
        messages = [{"role": "user", "content": prompt_text}]
        
        # === EXISTING: Stream from Anthropic ===
        accumulated_text = []
        usage_data = None
        
        async with anthropic.messages.stream(
            model=options.get("model", "claude-sonnet-4-20250514"),
            max_tokens=options.get("max_tokens", 16384),
            temperature=options.get("temperature", 0.5),
            messages=messages,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    accumulated_text.append(event.delta.text)
                    yield self._format_sse("content_delta", {"text": event.delta.text})
                elif event.type == "message_stop":
                    usage_data = event.message.usage
        
        # === EXISTING: Save document ===
        full_text = "".join(accumulated_text)
        document = await self.document_service.create_or_update_document(
            space_type=space_type,
            space_id=space_id,
            doc_type_id=doc_type_id,
            content=full_text,
        )
        
        # === NEW: Log output ===
        await logger_svc.add_output(run_id, "raw_text", full_text)
        
        # === NEW: Complete run ===
        await logger_svc.complete_run(
            run_id,
            status="SUCCESS",
            usage={
                "input_tokens": usage_data.input_tokens,
                "output_tokens": usage_data.output_tokens,
                "total_tokens": usage_data.input_tokens + usage_data.output_tokens,
            }
        )
        
        # === EXISTING: Yield completion ===
        yield self._format_sse("completion", {"document_id": str(document.id)})
        
    except Exception as e:
        # === NEW: Log error ===
        if run_id:
            await logger_svc.log_error(
                run_id,
                stage="MODEL_CALL",
                severity="ERROR",
                error_code=type(e).__name__,
                message=str(e),
                details={"traceback": traceback.format_exc()}
            )
            await logger_svc.complete_run(run_id, "FAILED", {})
        
        # === EXISTING: Yield error event ===
        yield self._format_sse("error", {"message": f"Error: {str(e)}"})
        raise
```

### Error Capture Strategy

**Stages**:
- `PROMPT_BUILD` - Error resolving prompt from registry
- `MODEL_CALL` - Anthropic API error (rate limit, auth, network)
- `PARSE` - Response parsing failure (malformed JSON)
- `VALIDATE` - Schema validation failure
- `PERSIST` - Database write error (saving document)

**Severity Levels**:
- `INFO` - Non-blocking informational (e.g., "Prompt is stale")
- `WARN` - Recoverable issue (e.g., "Retrying after rate limit")
- `ERROR` - Operation failed but run continues (e.g., "Validation failed")
- `FATAL` - Unrecoverable failure (e.g., "API key invalid")

**Example Error Logging**:
```python
try:
    document = await document_service.create_or_update_document(...)
except Exception as e:
    await logger_svc.log_error(
        run_id,
        stage="PERSIST",
        severity="ERROR",
        error_code="DocumentSaveError",
        message=str(e),
        details={"document_type": doc_type_id, "traceback": traceback.format_exc()}
    )
    raise
```

### Linking to Project Audit

**When Governance Event Occurs** (document saved):

In `DocumentBuilder.build_stream()` after document created:
```python
# Document saved successfully
document = await self.document_service.create_or_update_document(...)

# Link to project audit
if space_type == 'project':
    await project_audit.log_event(
        project_id=space_id,
        event_type=f"{doc_type_id.upper()}_GENERATED",
        user_id=None,  # System-generated
        metadata={
            "correlation_id": str(self.correlation_id),
            "llm_run_id": str(run_id),
            "document_id": str(document.id),
            "artifact_type": doc_type_id,
        }
    )
```

**Query Pattern** (find LLM run from audit):
```sql
SELECT lr.*
FROM project_audit pa
JOIN llm_run lr ON lr.id = (pa.metadata->>'llm_run_id')::uuid
WHERE pa.id = :audit_id;
```

---

## Tool Call Logging Plan

### Current State: No Tool Calls

**User Confirmation**: "I don't believe so" (no tool calls in current implementation)

**MVP Decision**: 
- ✅ Create `llm_run_tool_call` table (schema defined)
- ❌ Do NOT implement logging (no tool calls to log)
- ✅ Document as "reserved for future use"

### Future Implementation (When Tools Added)

**Detection Strategy** (when DocumentBuilder uses tools):
```python
async with anthropic.messages.stream(..., tools=[...]) as stream:
    async for event in stream:
        if event.type == "tool_use":
            # Log tool call intent
            await logger_svc.log_tool_call(
                run_id=run_id,
                sequence=event.index,
                tool_name=event.name,
                input_data=json.dumps(event.input),
                status="PENDING"
            )
```

**Execution Tracking**:
```python
# After tool executes
await logger_svc.update_tool_call(
    tool_call_id=tool_call_id,
    status="SUCCESS",
    output_data=json.dumps(result),
    ended_at=datetime.now(timezone.utc)
)
```

**MVP Status**: **Deferred** (table exists, unused)

---

## Replay Enablement Plan

### Input Reconstruction

**Function**: `reconstruct_inputs(run_id: UUID) -> Dict[str, str]`

**Algorithm**:
```python
async def reconstruct_inputs(db: AsyncSession, run_id: UUID) -> Dict[str, str]:
    """
    Rebuild exact inputs from llm_run_input_ref.
    
    Returns dict keyed by input kind:
    {
        "role_prompt": "...",
        "user_prompt": "...",
        "context_doc": "..."
    }
    
    Raises ValueError if any input is redacted.
    """
    inputs = {}
    
    result = await db.execute(
        text("""
            SELECT kind, content_ref, content_redacted
            FROM llm_run_input_ref
            WHERE llm_run_id = :run_id
            ORDER BY created_at
        """),
        {"run_id": run_id}
    )
    
    for row in result:
        if row.content_redacted:
            raise ValueError(f"Cannot replay: input '{row.kind}' is redacted")
        
        # Resolve content
        content = await resolve_content(db, row.content_ref)
        inputs[row.kind] = content
    
    return inputs
```

### Replay Execution

**API Endpoint**: `POST /api/admin/llm-runs/{run_id}/replay`

**Implementation**:
```python
@router.post("/api/admin/llm-runs/{run_id}/replay")
async def replay_llm_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)  # Admin only
):
    """
    Replay an LLM run with identical inputs.
    
    Creates new llm_run with is_replay=true metadata.
    Returns comparison of original vs replay.
    """
    # Load original run
    result = await db.execute(
        text("SELECT * FROM llm_run WHERE id = :run_id"),
        {"run_id": run_id}
    )
    original = result.fetchone()
    if not original:
        raise HTTPException(404, "Run not found")
    
    # Reconstruct inputs
    try:
        inputs = await reconstruct_inputs(db, run_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    # Create execution context
    correlation_id = uuid4()  # New correlation for replay
    
    # Execute LLM call (simplified - actual impl would use DocumentBuilder)
    response = await anthropic_client.messages.create(
        model=original.model_name,
        messages=[
            {"role": "user", "content": inputs["role_prompt"]}
        ],
        max_tokens=16384,
    )
    
    # New run is automatically logged (if using instrumented builder)
    # OR manually create run with is_replay=true
    
    # Query new run
    new_run_result = await db.execute(
        text("SELECT id FROM llm_run WHERE correlation_id = :corr_id"),
        {"corr_id": correlation_id}
    )
    new_run_id = new_run_result.scalar_one()
    
    # Mark as replay
    await db.execute(
        text("""
            UPDATE llm_run
            SET metadata = jsonb_set(
                COALESCE(metadata, '{}'),
                '{is_replay}', 'true'::jsonb
            ),
            metadata = jsonb_set(
                metadata,
                '{original_run_id}', to_jsonb(:original_id::text)
            )
            WHERE id = :new_run_id
        """),
        {"original_id": str(run_id), "new_run_id": new_run_id}
    )
    
    # Generate comparison
    comparison = await compare_runs(db, run_id, new_run_id)
    
    return {
        "status": "success",
        "original_run_id": str(run_id),
        "replay_run_id": str(new_run_id),
        "comparison": comparison
    }
```

### Comparison Output

**Function**: `compare_runs(original_id, replay_id) -> Dict`

**Output Structure**:
```json
{
  "original_run_id": "uuid",
  "replay_run_id": "uuid",
  "metadata": {
    "original_started_at": "2024-01-15T10:30:00Z",
    "replay_started_at": "2024-01-20T14:45:00Z",
    "time_delta_days": 5
  },
  "token_delta": {
    "input_tokens": 0,      // Should be identical if prompt unchanged
    "output_tokens": -50,   // Replay generated fewer tokens
    "total_tokens": -50
  },
  "cost_delta_usd": -0.002,
  "outputs": {
    "original_hash": "sha256:abc123...",
    "replay_hash": "sha256:def456...",
    "identical": false,
    "length_delta": -200    // Replay was 200 chars shorter
  },
  "notes": [
    "Output content differs (expected - LLM is stochastic)",
    "Token counts identical (prompt unchanged)"
  ]
}
```

**What is NOT Compared**:
- Exact text diff (post-MVP: use difflib or semantic comparison)
- Quality assessment (post-MVP: automated scoring)
- Tool call differences (deferred with tool calls)

**Replay Semantics**:
- Inputs are reconstructed deterministically ✅
- Model/prompt/parameters are identical ✅
- Outputs may differ (stochastic LLM) ✅
- Comparison provides data for manual analysis ✅

---

## Server-Side Contracts & Invariants

### MUST Always Be True

1. **Every LLM invocation creates exactly one `llm_run`**
   - Even if call fails before LLM responds
   - Status remains IN_PROGRESS if process crashes
   
2. **`correlation_id` is never NULL**
   - Enforced at DB level (NOT NULL constraint)
   - Validated in `LLMExecutionLogger.start_run()`
   - Middleware ensures it exists in request.state
   
3. **`llm_run.started_at` is set before LLM call**
   - Captures queue time, not just LLM execution time
   - Always populated (NOT NULL constraint)
   
4. **Content refs are immutable**
   - Never UPDATE `llm_content.content_text` after creation
   - Only UPDATE `accessed_at` for cache metrics
   
5. **Errors are append-only**
   - `llm_run_error.sequence` is monotonic (1, 2, 3...)
   - Never DELETE errors (audit trail)
   
6. **Primary error is latest FATAL or ERROR**
   - Derived from `llm_run_error` on each error insert
   - `llm_run.primary_error_*` summarizes for quick access
   
7. **Tool call sequence matches LLM response order**
   - (Unused in MVP, but enforced when implemented)
   - Sequence field preserves execution flow
   
8. **Input reconstruction is deterministic**
   - Same `run_id` → same inputs every time
   - Hash verification ensures content integrity

### MUST Never Happen

1. **Logging failure blocks LLM execution**
   - All logging wrapped in try/except
   - Errors logged to stderr, LLM call proceeds
   - Graceful degradation principle
   
2. **Content redaction deletes content**
   - Flag `content_redacted=true`, preserve audit trail
   - Content remains in `llm_content` (immutable)
   
3. **Replay mutates original run**
   - Always creates new `llm_run` with new correlation_id
   - Original run unchanged (append-only)
   
4. **`llm_run` without inputs**
   - At minimum, `role_prompt` must exist
   - Enforced in `DocumentBuilder.build_stream()`
   
5. **Tool call without parent `llm_run`**
   - FK constraint enforces at DB level
   - (Unused in MVP)
   
6. **Correlation ID reuse across projects**
   - UUIDs prevent collisions
   - Each request gets unique correlation_id
   
7. **Cost calculated from stale pricing**
   - MVP: `cost_usd` is NULL (no pricing table yet)
   - Post-MVP: compute from token counts + pricing table
   
8. **Sensitive content in `llm_run.metadata`**
   - No API keys, passwords, user PII
   - Only operational metadata (retry_count, is_replay)

### Validation Checks

**Pre-save validation** (in `LLMExecutionLogger`):
```python
def validate_llm_run(run: dict):
    """Validate llm_run before DB insert."""
    assert run["correlation_id"] is not None, "correlation_id required"
    assert run["started_at"] is not None, "started_at required"
    assert run["error_count"] >= 0, "error_count cannot be negative"
    
    if run["status"] == "SUCCESS":
        assert run["ended_at"] is not None, "successful run must have end time"
        assert run["input_tokens"] is not None, "successful run must have tokens"
```

---

## Test Plan

### Unit Tests

**File**: `tests/services/test_llm_execution_logger.py`

**Content Storage**:
- `test_store_content_creates_new_record()` - First storage creates new `llm_content`
- `test_store_content_deduplicates_identical()` - Same content returns existing ref
- `test_resolve_content_returns_text()` - Valid ref resolves to content
- `test_resolve_content_raises_on_invalid_ref()` - Invalid ref raises ValueError
- `test_redact_content_sets_flag()` - Redaction flag set, content preserved

**LLM Run Lifecycle**:
- `test_start_run_creates_record()` - `start_run()` inserts with IN_PROGRESS
- `test_start_run_validates_correlation_id()` - Raises if correlation_id NULL
- `test_add_input_stores_reference()` - Input ref created with content_ref
- `test_add_output_stores_reference()` - Output ref created after streaming
- `test_log_error_increments_count()` - Error count increments, primary error set
- `test_log_error_enforces_sequence()` - Sequence is monotonic (1, 2, 3)
- `test_complete_run_sets_end_time()` - `ended_at` populated, status updated
- `test_complete_run_with_tokens()` - Token counts and cost stored

**Error Handling**:
- `test_logging_failure_does_not_raise()` - DB error in logging doesn't propagate
- `test_invalid_stage_logged()` - Unknown stage values logged (no validation)

### Integration Tests

**File**: `tests/integration/test_llm_logging.py`

**End-to-End Logging**:
- `test_document_build_creates_complete_log()`
  - Trigger document build via API
  - Mock Anthropic response
  - Verify `llm_run`, `input_ref`, `output_ref` created
  - Check correlation_id propagated from request header
  
**Error Scenarios**:
- `test_llm_api_error_logs_error()`
  - Force Anthropic API error (mock)
  - Verify `llm_run_error` created with stage=MODEL_CALL
  - Verify run status=FAILED, primary_error_* set
  
**Streaming Integration**:
- `test_streaming_accumulates_content()`
  - Mock streaming events (content_block_delta)
  - Verify full text logged in output_ref after completion
  - Verify token counts from usage data

**Project Audit Linkage**:
- `test_document_save_links_to_audit()`
  - Build document (project_discovery)
  - Verify `project_audit` has `llm_run_id` in metadata
  - Query via metadata->>'llm_run_id' succeeds

### Replay Tests

**File**: `tests/integration/test_llm_replay.py`

**Input Reconstruction**:
- `test_reconstruct_inputs_returns_all_kinds()`
  - Create run with role_prompt, user_prompt, context_doc
  - Reconstruct inputs
  - Verify all three kinds returned
  
- `test_reconstruct_inputs_fails_on_redacted()`
  - Redact one input
  - Attempt reconstruction
  - Verify ValueError raised with message

**Replay Execution**:
- `test_replay_creates_new_run()`
  - Replay original run
  - Verify new `llm_run` created (different ID)
  
- `test_replay_uses_same_model_and_prompt()`
  - Replay run
  - Verify new run has same model_name, prompt_id, prompt_version
  
- `test_replay_has_different_correlation_id()`
  - Replay run
  - Verify new correlation_id != original

**Comparison**:
- `test_compare_runs_shows_token_delta()`
  - Compare original and replay
  - Verify token_delta calculated correctly
  
- `test_compare_runs_flags_identical_outputs()`
  - Replay with mocked identical output
  - Verify `identical=true` in comparison

### Failure & Retry Scenarios

**Logging Resilience**:
- `test_llm_succeeds_even_if_logging_fails()`
  - Mock DB unavailable during logging
  - Verify LLM call completes (document created)
  - Verify error logged to stderr (check logs)
  
**Partial Runs**:
- `test_incomplete_run_marked_as_partial()`
  - Simulate stream interrupted mid-flight
  - Verify `status=PARTIAL`, `ended_at=NULL`
  
**Correlation Propagation**:
- `test_correlation_id_propagates_from_header()`
  - Send request with X-Correlation-ID header
  - Verify same ID appears in llm_run
  - Verify ID echoed in response header

### Performance Tests (Optional)

**Content Deduplication**:
- `test_dedup_performance_1000_identical_prompts()`
  - Store same prompt 1000 times
  - Verify only 1 `llm_content` record created
  - Measure time (should be <1s)

**Concurrent Logging**:
- `test_concurrent_runs_do_not_conflict()`
  - Start 10 document builds concurrently
  - Verify all 10 `llm_run` records created
  - Verify no sequence conflicts in errors

---

## Rollout Plan

### Phase 1: Development Environment

**Week 1 - Schema & Infrastructure**

1. **Create Alembic migration** (`alembic/versions/2024XXXX_add_llm_execution_logging.py`)
   - Define all six tables
   - Include comments and indexes
   - Test up/down migrations
   
2. **Run migration in dev DB**
   ```bash
   alembic upgrade head
   # Verify tables created: \dt llm_*
   ```
   
3. **Implement `LLMExecutionLogger` service**
   - Create `app/domain/services/llm_execution_logger.py`
   - Implement all methods (start, add_input, add_output, log_error, complete)
   - No integration yet (pure service layer)
   
4. **Write unit tests**
   - Test content storage/resolution
   - Test run lifecycle
   - Test error logging
   - Target: 90% coverage on logger service
   
5. **Verify**: All unit tests pass, tables exist, service functional

**Week 2 - Integration**

1. **Add correlation middleware**
   - Create `app/middleware/correlation.py`
   - Register in `main.py`
   - Test: Send request, check `request.state.correlation_id` exists
   
2. **Modify DocumentBuilder**
   - Add `correlation_id` parameter to `__init__`
   - Instrument `build_stream()` with logging
   - Import `LLMExecutionLogger`
   
3. **Modify document_routes**
   - Extract `correlation_id` from request.state
   - Pass to DocumentBuilder constructor
   
4. **Write integration tests**
   - Test full document build flow
   - Mock Anthropic responses
   - Verify logging happens
   
5. **Verify**: Integration tests pass, manual test in dev creates logs

**Week 3 - Replay Implementation**

1. **Implement replay endpoint**
   - Create `app/api/routers/admin.py` (if not exists)
   - Add `POST /api/admin/llm-runs/{run_id}/replay`
   - Implement input reconstruction
   - Implement comparison logic
   
2. **Write replay tests**
   - Test reconstruction
   - Test execution
   - Test comparison output
   
3. **Manual testing**
   - Build a document
   - Find `llm_run.id` in DB
   - Call replay endpoint via curl/Postman
   - Verify new run created, comparison returned
   
4. **Verify**: Replay functional, tests pass

### Phase 2: Testing Environment

**Week 4 - Deploy to Test**

1. **Run migration in test DB**
   ```bash
   # On test server
   alembic upgrade head
   ```
   
2. **Deploy updated backend** to test environment
   - Build Docker image (if containerized)
   - Deploy via CI/CD pipeline
   - Restart services
   
3. **Execute regression test suite**
   - Run all existing tests
   - Ensure no business logic broken
   - Verify documents still build successfully
   
4. **Manual testing checklist**:
   - [ ] Trigger PM workflow → document created
   - [ ] Check `llm_run` table has record
   - [ ] Query `llm_run_input_ref` → 2-3 inputs logged
   - [ ] Query `llm_run_output_ref` → 1 output logged
   - [ ] Check correlation_id in response header
   - [ ] Replay a run via API → new run created
   
5. **Performance check**:
   - Measure document build latency (before/after)
   - Acceptable: <+50ms overhead
   - If >100ms: investigate slow queries
   
6. **Verify**: All workflows functional, logs accumulate, no performance degradation

### Phase 3: Production Deployment

**Week 5 - Production Rollout**

1. **Feature flag** (optional safety measure):
   ```python
   # config.py
   ENABLE_LLM_LOGGING = os.getenv("ENABLE_LLM_LOGGING", "true").lower() == "true"
   
   # In DocumentBuilder
   if ENABLE_LLM_LOGGING:
       logger_svc = LLMExecutionLogger(self.db)
       run_id = await logger_svc.start_run(...)
   ```
   
2. **Run migration in prod DB** (during maintenance window):
   ```bash
   # Review SQL first
   alembic upgrade --sql > migration.sql
   # Inspect migration.sql
   
   # Apply migration
   alembic upgrade head
   ```
   
3. **Deploy backend** (zero downtime, backward compatible):
   - New code runs migration
   - Old code ignores new tables (no breaking changes)
   - Rolling deployment if using K8s
   
4. **Monitor immediately after deployment**:
   - DB disk usage (watch `llm_content` table size)
   - API latency (p50, p95, p99)
   - Error rates in `llm_run_error`
   - Correlation_id presence in logs
   
5. **Alert thresholds**:
   - >5% of runs fail logging → investigate immediately
   - Content table >10GB in first week → review retention
   - p95 latency >+100ms → optimize queries
   
6. **Verify**: Production logging working, no customer impact

### Phase 4: Post-Deployment Verification

**Week 6 - Validation**

1. **Sample run inspection**:
   ```sql
   -- Get recent runs
   SELECT id, correlation_id, status, artifact_type, 
          input_tokens, output_tokens, started_at, ended_at
   FROM llm_run
   ORDER BY started_at DESC
   LIMIT 10;
   
   -- Check inputs logged
   SELECT kind, content_hash
   FROM llm_run_input_ref
   WHERE llm_run_id = '<sample_run_id>';
   
   -- Check outputs logged
   SELECT kind, content_hash, parse_status
   FROM llm_run_output_ref
   WHERE llm_run_id = '<sample_run_id>';
   ```
   
2. **Replay validation**:
   - Execute replay on production run (admin account)
   - Verify new run created
   - Compare outputs manually
   
3. **Content deduplication check**:
   ```sql
   -- Count unique hashes vs total rows
   SELECT 
     COUNT(*) as total_content,
     COUNT(DISTINCT content_hash) as unique_content,
     (COUNT(*) - COUNT(DISTINCT content_hash)) as duplicates_saved
   FROM llm_content;
   ```
   
4. **Performance validation**:
   - Compare p95 latency before/after (CloudWatch, Datadog, etc.)
   - Acceptable: <10% increase
   - If >10%: add indexes or optimize logging
   
5. **Error logging validation**:
   - Trigger intentional error (invalid API key in test)
   - Verify error appears in `llm_run_error`
   - Verify run status=FAILED

### Backfill Considerations

**None required.** 

- Logging starts forward from deployment
- Historical runs are not logged (acceptable per ADR-010)
- Execution logs are telemetry, not governance (no compliance requirement for historical data)

### Rollback Strategy

**If rollback needed**:

1. **Stop writing logs** (fastest):
   ```bash
   # Set env var
   export ENABLE_LLM_LOGGING=false
   # Restart services
   ```
   
2. **Revert code** (if feature flag not used):
   ```bash
   git revert <commit_hash>
   # Deploy previous version
   ```
   
3. **Drop tables** (optional, destructive):
   ```sql
   DROP TABLE IF EXISTS llm_run_tool_call CASCADE;
   DROP TABLE IF EXISTS llm_run_error CASCADE;
   DROP TABLE IF EXISTS llm_run_output_ref CASCADE;
   DROP TABLE IF EXISTS llm_run_input_ref CASCADE;
   DROP TABLE IF EXISTS llm_run CASCADE;
   DROP TABLE IF EXISTS llm_content CASCADE;
   ```
   Or:
   ```bash
   alembic downgrade -1
   ```
   
4. **Remove instrumentation** (or leave as no-op):
   - Logging code gracefully degrades if tables missing
   - Errors logged to stderr, LLM execution continues

**Data loss**: Acceptable (telemetry, not governance)

**Recovery time**: <10 minutes (feature flag or code revert)

---

## Risks & Mitigations

### Risk 1: Logging Overhead Impacts User Experience

**Impact**: Document builds take 10-50ms longer, users perceive slowness

**Probability**: Medium

**Mitigation**:
- Use async DB operations (non-blocking)
- Batch insert inputs when possible (single transaction)
- Monitor p95 latency with alerts
- Feature flag to disable logging if severe
- Optimize queries (indexes on correlation_id, run_id)

**Acceptance Criteria**: p95 latency increase <10%

### Risk 2: Content Table Growth Exceeds Disk

**Impact**: Database runs out of space, writes fail, service disruption

**Probability**: Medium (depends on usage volume)

**Mitigation**:
- Monitor `llm_content` table size daily
- Alert at 80% disk usage
- Implement retention policy (delete content >90 days old)
- Post-MVP: Migrate to object storage (S3/MinIO)
- Estimate: 1000 builds/day × 50KB/build = 50MB/day = 18GB/year (manageable)

**Acceptance Criteria**: Disk usage tracked, alerts configured

### Risk 3: Logging Bug Breaks LLM Execution

**Impact**: Critical workflows fail, users cannot generate documents

**Probability**: Low (with defensive coding)

**Mitigation**:
- **Wrap all logging in try/except** (never propagate exceptions)
- Log logging errors to stderr/Sentry
- Feature flag for emergency disable
- Comprehensive integration tests (>80% coverage)
- Code review focuses on error paths

**Acceptance Criteria**: Zero production incidents where logging blocks LLM

### Risk 4: Correlation ID Collisions

**Impact**: Runs incorrectly correlated, investigation confused

**Probability**: Very Low

**Mitigation**:
- Use UUID v4 (collision probability ~2^-122)
- Validate correlation_id is valid UUID in middleware
- Index on correlation_id for fast lookups
- Monitor for duplicate correlation_ids (should never happen)

**Acceptance Criteria**: Zero correlation_id collisions in production

### Risk 5: Prompt Hash Mismatch

**Impact**: `effective_prompt_hash` doesn't match actual prompt sent, replay inconsistent

**Probability**: Medium (prompt resolution is complex)

**Mitigation**:
- Hash after final resolution (post variable substitution)
- Unit test hash generation with known inputs
- Replay exposes mismatches (outputs won't make sense if prompt different)
- Add test: "hash of reconstructed input matches effective_prompt_hash"

**Acceptance Criteria**: Replay regression tests pass

### Risk 6: Replay with Side Effects

**Impact**: Replay triggers actions that modify external state (future risk with tools)

**Probability**: Low (no tools in MVP)

**Mitigation**:
- **Document clearly**: Replay executes LLM call, may have side effects
- Post-MVP: Add `--dry-run` flag to simulate without execution
- Require admin approval for prod replays
- When tools added: Log tool calls but don't re-execute by default

**Acceptance Criteria**: Replay documentation clear, admin-only access

### Risk 7: Migration Failure in Production

**Impact**: Deployment blocked, potential downtime

**Probability**: Low (tables are additive)

**Mitigation**:
- Test migration in dev, test, staging environments first
- Use `alembic upgrade --sql` to review SQL before applying
- Schedule migration during maintenance window
- Have rollback script ready (`alembic downgrade -1`)
- Migration is additive (no ALTER existing tables)

**Acceptance Criteria**: Migration succeeds in <2 minutes, zero downtime

### Risk 8: Sensitive Data Logged

**Impact**: PII/credentials in prompts logged without redaction

**Probability**: Medium (depends on user inputs)

**Mitigation**:
- Manual redaction flag in MVP (admin action)
- Post-MVP: Automated PII detection (Presidio, spaCy)
- Never log API keys or passwords (enforce in code)
- Access control: Only admins can query `llm_content` directly
- Audit trail: Log who accesses content

**Acceptance Criteria**: Zero API keys/passwords in `llm_content`

---

## Definition of Done

### Schema & Infrastructure

- [ ] Alembic migration created and reviewed
- [ ] Migration tested in dev environment (up and down)
- [ ] All six tables exist with correct indexes and FK constraints
- [ ] Comments added to tables and critical columns
- [ ] `LLMExecutionLogger` service class implemented
- [ ] Content storage/resolution functions working
- [ ] Unit tests for logger service pass (>90% coverage)

### Integration

- [ ] Correlation ID middleware implemented and registered
- [ ] Correlation ID propagates from request → DocumentBuilder → logger
- [ ] DocumentBuilder modified (correlation_id param, instrumentation)
- [ ] document_routes modified (extract correlation_id, pass to builder)
- [ ] All existing LLM call sites instrumented (currently just DocumentBuilder)
- [ ] Input/output references stored correctly
- [ ] Errors logged with correct stage/severity
- [ ] Project audit links to `llm_run_id` on governance events
- [ ] Integration tests pass (full workflow coverage)

### Replay

- [ ] API endpoint `/api/admin/llm-runs/{run_id}/replay` implemented
- [ ] Input reconstruction returns all input kinds
- [ ] Replay creates new `llm_run` with `is_replay=true` metadata
- [ ] Comparison utility shows token/cost deltas and output metadata
- [ ] Replay tests pass (reconstruction, execution, comparison)
- [ ] Admin-only access enforced (authentication check)

### Documentation

- [ ] ADR-010 updated with "Implemented" status, reference to this plan
- [ ] API docs updated (replay endpoint documented in OpenAPI)
- [ ] Developer guide written: "How to instrument new LLM calls"
- [ ] Operational runbook written: "How to query LLM logs for debugging"
- [ ] README updated with logging feature description

### Testing

- [ ] All unit tests pass (logger service)
- [ ] All integration tests pass (full workflows)
- [ ] Replay tests pass (reconstruction, comparison)
- [ ] Manual testing completed in dev environment
- [ ] Manual testing completed in test environment
- [ ] Regression suite passes (no business logic broken)
- [ ] Performance tests pass (latency within acceptable range)

### Production Readiness

- [ ] Migration applied to test DB successfully
- [ ] Backend deployed to test environment
- [ ] Test environment validated (logs accumulate, replays work)
- [ ] Migration applied to production DB
- [ ] Backend deployed to production
- [ ] Monitoring dashboards configured (DB size, error rates, latency)
- [ ] Alert thresholds set (disk usage >80%, error rate >5%)
- [ ] Feature flag tested (can disable if needed)
- [ ] Rollback procedure documented and tested in test environment

### Post-Deployment Verification

- [ ] At least 10 successful document builds logged in production
- [ ] Sample `llm_run` record inspected (all fields populated correctly)
- [ ] Correlation IDs appear in response headers
- [ ] Replay executed successfully on production run
- [ ] No performance degradation observed (p95 latency <+10%)
- [ ] Content deduplication working (hash collisions observed in logs)
- [ ] Error logging captures actual failures (not just test cases)
- [ ] Project audit linkage verified (metadata->>'llm_run_id' queries work)
- [ ] Admin access to replay endpoint enforced
- [ ] No sensitive data (API keys, passwords) found in `llm_content` sample

---

**End of Implementation Plan**