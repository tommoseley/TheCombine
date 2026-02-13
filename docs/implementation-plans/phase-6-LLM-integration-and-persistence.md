# Phase 6: LLM Integration & Document Persistence

## Overview

Phase 6 connects The Combine to real LLM providers and implements persistent document storage. This phase transforms the execution engine from mock-based testing to actual AI-powered document generation.

## Goals

1. **LLM Client**: Anthropic Claude API integration with retry/fallback
2. **Prompt Assembly**: Role-based prompt construction from step definitions
3. **Response Parsing**: Structured output extraction and validation
4. **Document Storage**: PostgreSQL-based document persistence
5. **Execution Logging**: Comprehensive LLM call telemetry (ADR-010)

## Timeline: 5 Days

| Day | Focus | Estimated Tests |
|-----|-------|-----------------|
| 1 | LLM client abstraction and Anthropic provider | 12 |
| 2 | Prompt assembly and role templates | 10 |
| 3 | Response parsing and validation | 10 |
| 4 | Document persistence (PostgreSQL) | 12 |
| 5 | Execution logging and telemetry | 10 |
| **Total** | | **~54** |

**Target: 565 tests (511 + 54)**

---

## Day 1: LLM Client Abstraction

### Deliverables

1. **LLM Provider Protocol** - Base interface for LLM providers
2. **Message and Response Models** - Dataclasses for LLM communication
3. **Anthropic Provider** - Claude API implementation with caching
4. **Mock Provider** - Testing without API calls

### Key Classes

- LLMProvider protocol with complete() and complete_with_retry()
- Message dataclass (role, content)
- LLMResponse dataclass (content, tokens, latency, cached)
- AnthropicProvider with httpx async client
- MockLLMProvider for testing

### Tests (12)
- Provider protocol compliance
- Anthropic request formatting
- Response parsing
- Retry on rate limit
- Mock provider for testing
- Token counting

---

## Day 2: Prompt Assembly

### Deliverables

1. **Role Templates** - System prompts for PM, BA, Developer, QA, Architect
2. **Prompt Builder** - Constructs messages from step and context
3. **Document Condenser** - Role-aware document summarization
4. **Input Assembler** - Resolves step inputs from registry

### Tests (10)
- Role template selection
- System prompt construction
- User prompt with documents
- Document condensing by role
- Input resolution
- Multi-document assembly

---

## Day 3: Response Parsing & Validation

### Deliverables

1. **Output Parser Protocol** - Interface for response parsing
2. **Markdown Parser** - Extracts markdown documents
3. **JSON Parser** - Extracts structured JSON from code blocks
4. **Clarification Parser** - Detects when LLM needs more info
5. **Quality Validator** - Validates output against document schema

### Tests (10)
- Markdown extraction
- JSON parsing from code blocks
- Schema validation
- Clarification detection
- Question extraction
- Error handling for malformed output

---

## Day 4: Document Persistence

### Deliverables

1. **Document ORM Model** - SQLAlchemy model with versioning
2. **Document Repository** - PostgreSQL CRUD operations
3. **Execution State Repository** - Persists workflow execution state
4. **Context Repository** - Persists execution context

### Database Schema

```sql
CREATE TABLE documents (
    document_id UUID PRIMARY KEY,
    document_type VARCHAR NOT NULL,
    scope_id VARCHAR NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP,
    created_by_step VARCHAR,
    execution_id UUID REFERENCES executions
);

CREATE INDEX idx_doc_scope_type ON documents(scope_id, document_type);
CREATE UNIQUE INDEX idx_doc_version ON documents(scope_id, document_type, version);
```

### Tests (12)
- Document CRUD operations
- Version management
- Scope-based queries
- Execution state persistence
- Context persistence
- Transaction handling

---

## Day 5: Execution Logging & Telemetry

### Deliverables

1. **LLM Call Log Model** - Tracks every LLM request/response
2. **Telemetry Service** - Aggregates metrics and costs
3. **Cost Calculator** - Computes costs per model
4. **Execution Metrics** - Summary statistics per execution

### Database Schema

```sql
CREATE TABLE llm_call_logs (
    call_id UUID PRIMARY KEY,
    execution_id UUID NOT NULL,
    step_id VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    latency_ms FLOAT,
    cached BOOLEAN DEFAULT FALSE,
    cost_usd NUMERIC(10,6),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_type VARCHAR,
    error_message TEXT
);
```

### Tests (10)
- LLM call logging
- Cost calculation
- Execution metrics aggregation
- Daily cost reporting
- Model usage statistics
- Cache hit tracking

---

## File Structure

```
app/
├── llm/
│   ├── __init__.py
│   ├── models.py           # Message, LLMResponse
│   ├── providers/
│   │   ├── base.py         # LLMProvider protocol
│   │   ├── anthropic.py    # Anthropic Claude
│   │   └── mock.py         # Mock for testing
│   ├── prompt_builder.py   # Prompt assembly
│   ├── output_parser.py    # Response parsing
│   └── telemetry.py        # Logging and metrics
├── persistence/
│   ├── models.py           # ORM models
│   ├── document_repo.py    # Document repository
│   └── execution_repo.py   # Execution state repo

tests/
├── llm/
│   ├── test_providers.py
│   ├── test_prompt_builder.py
│   ├── test_output_parser.py
│   └── test_telemetry.py
└── persistence/
    ├── test_document_repo.py
    └── test_execution_repo.py
```

---

## Dependencies

```
httpx>=0.27.0         # Async HTTP client
tenacity>=8.2.0       # Retry logic
```

## Success Criteria

1. LLM calls execute against Anthropic API
2. Prompts assembled correctly per role
3. Responses parsed into documents
4. Documents persisted to PostgreSQL
5. All LLM calls logged with costs
6. Mock provider enables API-free testing
7. 565+ tests passing

---

## Design Decision: LLM Response Streaming

**Decision:** Synchronous LLM calls with progress-level SSE (Option A)

**Rationale:**
- Fits "pipeline runs unattended" execution model
- Simpler response parsing and validation
- Quality gates require complete output before validation
- Progress SSE provides sufficient user feedback ("gathering inputs", "calling LLM", "parsing response")

**Current Implementation:**
- `build_stream()` yields `ProgressUpdate` events via SSE
- Anthropic `messages.create()` is synchronous
- Users see stage transitions, not token-by-token output

**Future Consideration (Option C):**
- Token streaming for interactive/human-watched steps
- Synchronous for automated pipeline steps
- Would require WebSocket per step or chunked SSE
- Defer until user feedback indicates need
