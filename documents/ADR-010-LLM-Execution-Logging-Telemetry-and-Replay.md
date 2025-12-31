````markdown
# ADR-010 — LLM Execution Logging, Telemetry, and Replay

## Status  
**Accepted**

## Context  
The Combine orchestrates multi-step, agentic workflows driven by Large Language Models (LLMs). These workflows must be **investigable, debuggable, auditable, and analyzable** without conflating high-volume execution telemetry with human-governance audit logs.

We need to understand:
- what inputs were provided to an LLM
- which model, prompt, tools, and parameters were used
- what outputs and errors occurred (possibly multiple)
- how long each phase took and what it cost
- how to reproduce and compare runs for regression and analysis

LLM logging must scale in volume, support flexible retention, and enable **replay of inputs** without promising deterministic outputs.

---

## Decision Summary  

1. LLM execution logging SHALL be implemented as a **separate subsystem** from project audit logging.
2. Each LLM invocation SHALL be recorded as a first-class `llm_run`.
3. All inputs, outputs, errors, and tool interactions SHALL be logged by reference, not inlined.
4. The system SHALL support **deterministic reconstruction of inputs** for replay and comparison.
5. Errors SHALL be modeled as **many-per-run**, not a single failure field.
6. Progress and phase-level events MAY be logged to support UI feedback and postmortems.

---

## Core Principles

- **Investigability over brevity**: failures must be explainable after the fact.
- **Immutability**: execution logs are append-only.
- **Separation of concerns**: governance audit ≠ execution telemetry.
- **Replayable inputs, stochastic outputs**: inputs can be reproduced; outputs may differ.

---

## LLM Run Model

### `llm_run`

One row per LLM invocation.

```sql
id                    UUID PRIMARY KEY
correlation_id        UUID NOT NULL
project_id            UUID NULL REFERENCES projects(id)
artifact_type         TEXT NULL
role                  TEXT NOT NULL              -- PM_MENTOR, QA_MENTOR, etc.
model_provider         TEXT NOT NULL
model_name             TEXT NOT NULL
prompt_id              TEXT NOT NULL              -- stable registry identifier
prompt_version         TEXT NOT NULL              -- human-readable version
effective_prompt_hash  TEXT NOT NULL              -- hash of resolved prompt text
schema_version         TEXT NULL
status                 TEXT NOT NULL              -- SUCCESS, FAILED, PARTIAL, CANCELLED
started_at             TIMESTAMPTZ NOT NULL
ended_at               TIMESTAMPTZ NULL
input_tokens           INT NULL
output_tokens          INT NULL
total_tokens           INT NULL
cost_usd               NUMERIC NULL
primary_error_code     TEXT NULL
primary_error_message  TEXT NULL
error_count            INT NOT NULL DEFAULT 0
metadata               JSONB NULL
````

**Indexes**

* `(correlation_id)`
* `(project_id, started_at DESC)`
* `(role, started_at DESC)` (optional)

---

## Content Storage & References

Raw prompt, context, tool output, and LLM response content SHALL NOT be embedded directly in `llm_run`.

Instead, all large content is stored via **opaque references**.

### `content_ref`

* Treated as an opaque URI
* Examples:

  * `db://llm_content/<uuid>`
  * `s3://bucket/path/object`
  * `file:///var/combine/llm_content/...`

**ADR stance:**
Storage backend is **implementation-configured and pluggable**. MVP MAY use database-backed content storage; future deployments MAY use object storage (S3-compatible or filesystem-backed).

---

## Input & Output References

### `llm_run_input_ref`

```sql
id               UUID PRIMARY KEY
llm_run_id       UUID NOT NULL REFERENCES llm_run(id)
kind             TEXT NOT NULL     -- system_prompt, role_prompt, user_prompt, context_doc, schema, tools
content_ref      TEXT NOT NULL
content_hash     TEXT NOT NULL
content_redacted BOOLEAN NOT NULL DEFAULT FALSE
created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
```

### `llm_run_output_ref`

```sql
id                 UUID PRIMARY KEY
llm_run_id         UUID NOT NULL REFERENCES llm_run(id)
kind               TEXT NOT NULL     -- raw_text, json, tool_calls, qa_report
content_ref        TEXT NOT NULL
content_hash       TEXT NOT NULL
parse_status       TEXT NULL         -- PARSED, FAILED
validation_status  TEXT NULL         -- PASSED, FAILED
created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

## Error Modeling

### `llm_run_error`

Multiple errors may occur per run.

```sql
id          UUID PRIMARY KEY
llm_run_id  UUID NOT NULL REFERENCES llm_run(id)
sequence    INT NOT NULL
stage       TEXT NOT NULL    -- PROMPT_BUILD, MODEL_CALL, TOOL_CALL, PARSE, VALIDATE, QA_GATE, PERSIST
severity    TEXT NOT NULL    -- INFO, WARN, ERROR, FATAL
error_code  TEXT NULL
message     TEXT NOT NULL
details     JSONB NULL
created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
```

* `llm_run` maintains a **summary view** (`primary_error_*`, `error_count`)
* Detailed investigation uses `llm_run_error`

---

## Tool Call Tracking

Tool usage SHALL be explicitly modeled.

### `llm_run_tool_call`

```sql
id          UUID PRIMARY KEY
llm_run_id  UUID NOT NULL REFERENCES llm_run(id)
sequence    INT NOT NULL
tool_name   TEXT NOT NULL
started_at  TIMESTAMPTZ NOT NULL
ended_at    TIMESTAMPTZ NULL
status      TEXT NOT NULL        -- SUCCESS, FAILED
input_ref   TEXT NOT NULL
output_ref  TEXT NULL
error_ref   TEXT NULL
```

Raw tool call payloads MAY also be stored in `llm_run_output_ref` with `kind = 'tool_calls'`.

---

## Progress & Phase Events (Optional but Supported)

To support long-running workflows and UI feedback, phase-level events MAY be logged.

### `llm_run_event`

```sql
id          UUID PRIMARY KEY
llm_run_id  UUID NOT NULL REFERENCES llm_run(id)
sequence    INT NOT NULL
event_type  TEXT NOT NULL      -- PHASE, STATUS, WARNING
phase       TEXT NULL          -- READING, GENERATING, VALIDATING, QA_REVIEW, SAVING
percent     INT NULL
message     TEXT NULL
created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Non-Goal:** token-by-token streaming persistence.

---

## Retry Behavior (Execution Context)

LLM services may perform internal retries (e.g., rate-limit backoff, transient failures).

* Retry behavior SHALL be treated as **execution context**, not as a separate error model.
* Retry information MAY be recorded in `llm_run.metadata`, including:

  * retry count
  * retry reasons
  * total latency including retries
* Per-retry detail MAY optionally be captured in `llm_run_error.details` when useful.

Retry logging is an enhancement and not required for MVP completeness.

---

## Replay Capability (Explicit Design Goal)

### Goal

The system SHALL support **deterministic reconstruction of inputs and configuration** for any LLM run.

Replay enables:

* prompt regression testing
* model comparison
* bug reproduction and analysis

### Replay Semantics

* Inputs are reconstructed from `llm_run_input_ref`
* Model, prompt version, schema, tools, and parameters are reused
* Replay produces a **new `llm_run`**
* Outputs are compared analytically (diffs, validation results, metrics)

### Explicit Non-Goals

* Replay does NOT guarantee identical outputs
* Replay does NOT automatically re-execute external side effects
* Tool calls MAY be replayed live or compared against recorded outputs (policy-driven)

---

## Relationship to Project Audit

When an LLM run results in a governance-relevant outcome (e.g., “Discovery generated and saved”):

* A `project_audit` entry SHALL be written
* Audit metadata SHOULD reference:

  * `llm_run_id`
  * `correlation_id`
  * artifact type

Project audit remains **human-scale**; LLM logs remain **execution-scale**.

---

## Retention & Access

* LLM execution logs are high-volume and retention-configurable
* Raw content access SHALL be more restricted than summary metadata
* Redaction flags MUST be respected

---

## Consequences

### Positive

* Deep investigability and replay support
* Clean separation from governance audit
* Scales with agentic complexity
* Enables cost, performance, and quality analysis

### Tradeoffs

* More schema and plumbing than naïve logging
* Requires discipline in correlation propagation

---

## Non-Goals

* Full event sourcing of orchestrator behavior
* Permanent retention of all raw content
* Deterministic LLM output reproduction

---

## Canonical Invariant

> **Every LLM decision must be explainable after the fact, even when it cannot be reproduced exactly.**

```
```
