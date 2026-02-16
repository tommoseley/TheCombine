# Implementation Plan: Backlog Compilation Pipeline

| | |
|---|---|
| **Status** | Draft |
| **Created** | 2026-02-16 |
| **Execution State** | Not Authorized |

---

## Summary

Build the core pipeline that transforms raw human intent into a structured, dependency-validated, deterministically ordered execution plan. This is the next product milestone for The Combine.

The pipeline follows a strict separation: LLMs generate candidates and explain results. All ordering, validation, and plan derivation is mechanical.

---

## Design Principles

1. **LLMs generate. Machines order.** The backlog is LLM-produced. The execution plan is machine-derived. The explanation is LLM-produced. The ordering is never LLM-produced.
2. **One schema, one `level` field.** No separate Epic/Feature/Story types. One `BacklogItem` with a `level` discriminator.
3. **Fail hard, fail loud.** Invalid IDs, cyclic dependencies, and schema violations halt the pipeline. No silent correction.
4. **Derived artifacts are never authored.** ExecutionPlan is computed from validated backlog. It is never written by an LLM or a human.
5. **Add fields later. Never remove them.** Start minimal. `priority_score`, `depends_on`, `parent_id`. No status, sprint, effort, owner, velocity, or ceremony.

---

## Explicit Non-Goals

Do not build:

- Sprint modeling
- Capacity simulation
- Status tracking
- Backlog editing UI
- Reprioritization loops
- Velocity modeling
- Multi-user collaboration
- Autonomous story execution
- Jira integration

---

## Reuse Analysis

Per the Reuse-First Rule:

| Option | Artifact | Decision | Rationale |
|--------|----------|----------|-----------|
| Document persistence | `documents` table + `instance_id` | **Reuse** | BacklogItem is a multi-instance document type, identical pattern to epics |
| Schema validation | `combine-config/schemas/` | **Reuse** | New schemas follow existing JSON Schema conventions |
| DCW infrastructure | Existing DCW engine + plan_executor | **Reuse** | Backlog Generator is a standard DCW (prompt + schema + QA gate) |
| LLM execution | Existing `document_generator` template | **Reuse** | Same template pattern, new task prompt + output schema |
| Graph algorithms | None existing | **Create** | New domain service for cycle detection + topological sort |
| ExecutionPlan derivation | None existing | **Create** | New mechanical function, no LLM involved |

---

## Affected Components

| Component | Change |
|-----------|--------|
| `combine-config/schemas/` | `intent_packet.schema.json`, `backlog_item.schema.json` |
| `combine-config/workflows/` | `backlog_generator/` DCW definition |
| `combine-config/prompts/` | Backlog generation task prompt, explanation task prompt |
| `alembic/versions/` | Migration for `intent_packet` and `backlog_item` document types |
| `app/api/v1/routers/` | Intent intake endpoints (`POST /intents`, `GET /intents/{id}`) |
| `app/domain/` | Graph validation service (fail-fast), ordering engine, plan derivation |
| `app/domain/handlers/` | Backlog generator handler, explanation generator handler |
| `tests/tier1/` | Graph validation, ordering, cycle detection, wave grouping unit tests |

---

## Core Object Definitions

### IntentPacket (v1)

```
intent_id       UUID (auto)
raw_intent      string (required)
constraints     string | null
success_criteria string | null
context         string | null
created_at      timestamp (auto)
schema_version  string
```

Document type: `intent_packet`, cardinality: `single`.

### BacklogItem (unified)

```
id              string (required, unique within backlog)
level           EPIC | FEATURE | STORY (required)
title           string (required)
description     string (required)
priority_score  number (required)
depends_on      array[string] (required, may be empty)
parent_id       string | null
```

Document type: `backlog_item`, cardinality: `multi`, instance_key: `id`.

#### ID Format Rule

IDs use a level prefix + numeric suffix, unique within the backlog:

- EPIC: `E001`, `E002`, ...
- FEATURE: `F001`, `F002`, ...
- STORY: `S001`, `S002`, ...

Enforced by: QA gate (format match) and graph validator (uniqueness). The LLM prompt specifies this format. IDs are stable within a single generation run — they are not globally unique across intents.

#### Hierarchy Rules (Canonical)

These rules are the **single source of truth** for parent/child relationships. Prompt writers and the graph validator must agree on these exactly.

| Level | `parent_id` | Rule |
|-------|-------------|------|
| EPIC | `null` | EPICs are top-level. `parent_id` must be null. |
| FEATURE | points to EPIC | `parent_id` must reference an item with `level: EPIC`. |
| STORY | points to FEATURE | `parent_id` must reference an item with `level: FEATURE`. |

Additional constraints:
- Parent chain must terminate (no parent cycles) — enforced by hierarchy validation (Task 4b, `ParentCycle`)
- STORY cannot parent anything
- FEATURE cannot parent EPIC
- Every FEATURE and STORY must have a non-null `parent_id`

These rules are enforced by the graph validator (`HierarchyViolation`, `InvalidLevelTransition`, `ParentCycle`). The QA gate only checks that `parent_id` is present on FEATURE/STORY levels — it does not validate the referenced level.

### ExecutionPlan (derived)

```
plan_id              UUID (auto)
backlog_hash         string (SHA-256 of sorted backlog content — identity key)
intent_id            UUID (metadata reference, not part of identity)
run_id               string (metadata reference, not part of identity)
ordered_backlog_ids  array[string]
waves                array[array[string]]
generated_at         timestamp (auto)
generator_version    string
```

Document type: `execution_plan`, cardinality: `single` **per `backlog_hash`**. Never LLM-authored.

Identity rule: Two identical backlogs must produce the same plan. `backlog_hash` is the identity key. `intent_id` and `run_id` are metadata — they record provenance but do not affect plan content. If a replay produces a different `backlog_hash`, it's a different plan. If it produces the same `backlog_hash`, the existing plan is returned (not regenerated).

#### `backlog_hash` Computation (Precise)

The hash covers only fields that affect plan ordering. Prose changes (title, description) do not invalidate plan identity.

Algorithm:
1. Sort items by `id` ASC
2. For each item, extract the **structure-only tuple**: `(id, level, priority_score, sorted(depends_on), parent_id)`
3. Normalize `priority_score` to integer before hashing — `int(priority_score)`. Fractional priorities are not supported; schema enforces integer type. This eliminates `1` vs `1.0` vs `1.00` divergence across serializers.
4. Serialize as canonical JSON (sorted keys, no whitespace)
5. SHA-256 the serialized string

**Included fields** (affect topological sort / wave grouping):
- `id` — node identity
- `level` — hierarchy rules
- `priority_score` — intra-tier ordering
- `depends_on` — edge set (sorted for determinism)
- `parent_id` — hierarchy structure

**Excluded fields** (prose, do not affect ordering):
- `title` — display only
- `description` — display only

Rationale: Editing a backlog item's description or title should not invalidate the execution plan. Only structural changes (new dependencies, priority changes, hierarchy changes) produce a new plan.

---

## Sequence

### EPIC 1 — Core Backlog Compilation Pipeline

#### Phase 1: Schema Definitions & Intent Intake

**Task 1 — IntentPacket Schema**

- Deliverable: `combine-config/schemas/intent_packet/1.0.0/schema.json`
- JSON Schema with required fields: `raw_intent`
- Optional fields: `constraints`, `success_criteria`, `context`
- Register `intent_packet` document type (cardinality: single)
- Acceptance: Schema validates, document type persists

**Task 1b — Intent Intake Service**

- `POST /intents` — persist IntentPacket as a document, return `intent_id`
- `GET /intents/{id}` — retrieve packet
- Minimal UI: textarea + submit button
- IntentPacket is persisted **before** any LLM runs — immutable input for replay/audit
- Backlog Generator DCW reads IntentPacket by `intent_id` (not embedded ad hoc)
- No intent editor, no versioning UX — to revise, create a new intent packet

**Task 2 — BacklogItem Schema**

- Deliverable: `combine-config/schemas/backlog_item/1.0.0/schema.json`
- Fields: `id`, `level` (enum), `title`, `description`, `priority_score`, `depends_on`, `parent_id`
- No additional properties allowed
- Register `backlog_item` document type (cardinality: multi, instance_key: `id`)
- Acceptance: Schema validates, IDs unique within output

#### Phase 2: Backlog Generator DCW

**Task 3 — Backlog Generator Workflow**

- Input: IntentPacket document content (loaded by `intent_id`)
- Output: `List[BacklogItem]`
- DCW definition: `combine-config/workflows/backlog_generator/releases/1.0.0/definition.json`
- Task prompt: generates structured backlog from intent
- QA gate scope (narrow — per DQ-2):
  - Schema-valid JSON
  - IDs present + unique
  - Numeric `priority_score` values
  - `parent_id` required on FEATURE and STORY levels
  - At least 1 EPIC
- QA gate does NOT validate: dependency existence, cycles, hierarchy rules (graph layer owns those)
- Reject if: missing ID, missing `priority_score`, invalid `level`, malformed JSON
- Prompt version stored with every run (per ADR-010)
- Child document spawning: each BacklogItem becomes a `backlog_item` document with `instance_id` = item `id`

### EPIC 2 — Graph Validation Layer

#### Phase 3: Dependency Validation & Cycle Detection

The graph validator service is the **single authority** for graph correctness (per DQ-2). It produces explicit failure types in two separate buckets, never silent corrections.

**Task 4a — Dependency Validation**

- Domain service function: `validate_dependencies(items: List[BacklogItem]) -> DependencyResult`
- Failure bucket: **Dependency Errors**
  - `MissingReference` — `depends_on` ID not found in item set
  - `SelfReference` — item depends on itself
- Fail hard — error message lists all missing/invalid IDs
- No silent correction, no self-heal
- Errors returned as "blocked: fix required — dependency errors"
- Unit tests: missing refs, valid refs, empty depends_on, self-reference
- Future: dependency errors may be fixable by targeted re-prompting

**Task 4b — Hierarchy Validation**

- Domain service function: `validate_hierarchy(items: List[BacklogItem]) -> HierarchyResult`
- Failure bucket: **Hierarchy Errors**
  - `HierarchyViolation` — `parent_id` points to wrong level (see Hierarchy Rules above)
  - `InvalidLevelTransition` — e.g., STORY parents EPIC, FEATURE parents FEATURE
  - `OrphanedItem` — FEATURE/STORY with null `parent_id`
  - `ParentNotFound` — `parent_id` references non-existent item
  - `ParentCycle` — `parent_id` chain forms a cycle (A→B→A)
- Parent-cycle detection is owned here, not in Task 5 — a parent cycle is a hierarchy error
- Fail hard — error message lists all violations grouped by type
- No silent correction, no self-heal
- Errors returned as "blocked: fix required — hierarchy errors"
- Unit tests: valid tree, STORY→EPIC (invalid), FEATURE→null (orphan), missing parent, nested valid tree, parent cycle
- Future: hierarchy errors are structural — likely require full backlog regeneration

Separating dependency and hierarchy errors enables UX to show two distinct correction paths and prepares for future auto-regeneration loops with different strategies per bucket.

**Task 5 — Dependency Cycle Detection**

- Domain service function: `detect_dependency_cycles(items: List[BacklogItem]) -> Optional[CycleTrace]`
- Scope: `depends_on` edges only — parent cycles are owned by Task 4b
- Failure type: `DependencyCycleDetected` — returns human-readable cycle trace (`A -> B -> C -> A`)
- Implement DAG cycle detection (Kahn's algorithm or DFS) over `depends_on` graph
- Deterministic failure
- Unit tests: simple dependency cycle, multi-node cycle, large DAG, acyclic graph

### EPIC 3 — Deterministic Ordering Engine

#### Phase 4: Topological Sort & Plan Derivation

**Task 6 — Topological Sort**

- Domain service function: `order_backlog(items: List[BacklogItem]) -> List[str]`
- Algorithm: topological sort by `depends_on`, within same tier sort by `priority_score` DESC, tie-break by `id` ASC
- Pure function — no LLM involved
- Same input always produces same output
- Unit tests with fixed expected output

**Task 7 — ExecutionPlan Derivation**

- Mechanical function: takes validated backlog, runs ordering, produces ExecutionPlan artifact
- Wave grouping (per DQ-3):
  - Computed using Kahn-style tiers: Wave N = all nodes with in-degree 0 after removing prior wave nodes
  - Within a wave, order by `priority_score` DESC, tie-break by `id` ASC
  - Waves are required (non-optional) but non-authoritative — total order is the authority
- ExecutionPlan schema emits both:
  - `ordered_backlog_ids` — flattened total order (authoritative)
  - `waves` — tier groups (derived view, required)
- Persisted as `execution_plan` document type (cardinality: single)
- Replay with same backlog produces identical plan
- Never authored by LLM

### EPIC 4 — Human Explanation Layer

#### Phase 5: Explanation Generator

**Task 8 — Plan Explanation Generator DCW**

- Input: backlog items, dependencies, priority scores, final order, waves
- Output: 1-2 paragraph explanation of why this order makes sense
- This does NOT determine order — it only explains the mechanical output
- Explanation references dependencies, priority, and wave grouping explicitly
- Can include: "Wave 1 is safe parallel work because..."
- Stored separately from ExecutionPlan
- Optional but valuable — the LLM shines at explanation, not computation

### EPIC 5 — Integration Flow

#### Phase 6: End-to-End Pipeline

**Task 9 — Pipeline Integration**

- One command triggers full pipeline:
  1. Load IntentPacket by `intent_id`
  2. Run Backlog Generator DCW (QA gate: structural invariants only)
  3. Run graph validator: dependency validation — Task 4a (fail hard)
  4. Run graph validator: hierarchy validation — Task 4b (fail hard)
  5. Run graph validator: cycle detection — Task 5 (fail hard)
  6. Generate ExecutionPlan: topological sort + wave grouping (mechanical)
  7. Check `backlog_hash` — if existing plan matches, return it; else persist new plan
  8. Generate Explanation (optional, LLM)
- All artifacts stored as documents
- Failure at any stage halts downstream steps — "blocked: fix required"
- Logs include schema versions and generator versions
- No user-confirmation UX for waves — show waves + rationale; override = new intent packet

### EPIC 6 — Observability

#### Phase 7: Determinism & Replay

**Task 10 — Replay Metadata**

- For every run store:
  - IntentPacket hash
  - Prompt version
  - Model version
  - Backlog hash
  - Plan hash (covers both `ordered_backlog_ids` and `waves`)
- Replay run produces same plan hash
- Hash mismatches clearly reported

---

## Design Decisions (Resolved)

### DQ-1: IntentPacket Intake Method

**Decision:** IntentPacket is created by a mechanical intake endpoint (or UI flow) that persists the packet before any LLM runs, then hands its `intent_id` into the pipeline.

**Rationale:**
- Keeps intent stable for replay/audit — "what the user said" becomes immutable input
- Avoids the "LLM normalized my intent" problem
- Supports multiple intake surfaces later (UI, API, file upload) without changing downstream flows

**Work statement impact:** Adds an "Intent Intake Service" work statement:
- `POST /intents` — persist IntentPacket, return `intent_id`
- `GET /intents/{id}` — retrieve packet
- Minimal UI: textarea + submit
- Backlog Generator DCW reads IntentPacket by `intent_id` (not embedded ad hoc)

**Premature optimization to avoid:** Don't build intent editor or versioning UX. Store the original. If the user wants to revise, they create a new intent packet.

### DQ-2: Dependency Validation Timing

**Decision:** Fail-fast in graph layer. No self-heal. The DCW QA gate enforces local structural invariants only. The graph layer is the single authority for dependency existence, hierarchy rules, cycle detection, ordering, and wave grouping.

**Rationale:**
- "Self-heal" creates non-deterministic edits ("the system fixed it") and erodes trust
- One locus of truth for graph correctness prevents hidden coupling where prompts assume the QA gate will patch mistakes
- Keeps the "deterministic backlog compiler" story clean: LLM proposes, compiler accepts or rejects

**DCW QA gate stays narrow:**
- Schema-valid JSON
- IDs present + unique
- Numeric priorities
- Required `parent_id` on FEATURE/STORY levels

**Graph validator service owns (two separate buckets):**

Dependency errors (Task 4a — potentially fixable by re-prompting):
- `MissingReference` — `depends_on` ID not in item set
- `SelfReference` — item depends on itself

Hierarchy errors (Task 4b — structural, likely requires full regeneration):
- `HierarchyViolation` — `parent_id` points to wrong level
- `InvalidLevelTransition` — level nesting rules violated
- `OrphanedItem` — FEATURE/STORY with null `parent_id`
- `ParentNotFound` — `parent_id` references non-existent item
- `ParentCycle` — `parent_id` chain forms a loop

Dependency cycle errors (Task 5 — `depends_on` graph only):
- `DependencyCycleDetected` — circular `depends_on` chain

Errors are returned as "blocked: fix required" with bucket indicated. Automated regeneration loop can be added later with different strategies per bucket, but never silent repair.

### DQ-3: Wave Grouping

**Decision:** Waves are derived and non-authoritative. The authoritative artifact is the total order. Waves are a required view computed from the same inputs.

**Rationale:**
- Waves are the primary parallelism signal and planning cue — too useful to make optional
- But they must not be misinterpreted as a scheduling promise
- Keeping total order as primary prevents "wave == sprint" thinking

**Wave algorithm (deterministic):**
- After topological sort, compute waves using Kahn-style tiers
- Wave N = all nodes with in-degree 0 at that stage (after removing prior wave nodes)
- Within a wave, order by `priority_score` DESC, tie-break by `id` ASC
- "No mutual dependencies" is guaranteed by tiering; "no hidden coupling" (same system component) is out of scope

**ExecutionPlan schema includes both:**
- `ordered_backlog_ids` — flattened total order (authoritative)
- `waves` — tier groups (derived view, required)
- Explanation DCW can reference: "Wave 1 is safe parallel work because..."

**No user-confirmation UX.** Show waves + one-line rationale. If user wants to override, that's a new intent packet / new run, not an edit-in-place.

---

## Risks

| Risk | Mitigation |
|------|------------|
| LLM produces invalid dependency references | Graph validator catches post-generation; QA gate only checks structural validity |
| Backlog too large for single LLM call | Decompose: generate EPICs first, then FEATURE/STORY per EPIC |
| Over-modeling BacklogItem | Start minimal, explicit non-goals enforced |
| Ordering appears arbitrary to users | Explanation Generator (Task 8) makes ordering legible |
| Waves misread as scheduling promises | Total order is authoritative; waves are derived view only |
| Silent self-heal erodes trust | Fail-fast in graph layer; no silent correction anywhere in pipeline |

---

## What You Have After Completing This

```
Intent
  -> Structured backlog (typed, validated, multi-instance documents)
  -> Dependency-safe (no missing refs, no cycles)
  -> Deterministically ordered (topological + priority)
  -> Wave-grouped (parallelism visible)
  -> Explainable execution plan (LLM explains, never computes)
```

That is a real product milestone.
