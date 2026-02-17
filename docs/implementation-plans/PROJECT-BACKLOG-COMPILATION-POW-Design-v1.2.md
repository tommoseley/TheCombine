# ProjectBacklogCompilationPOW Design v1.2

| | |
|---|---|
| **Status** | Draft |
| **Created** | 2026-02-16 |
| **Supersedes** | Conversational v1.0, v1.1 |
| **Foundation** | BACKLOG-COMPILATION-PIPELINE-Implementation-Plan.md (WS-BCP-001--004 delivered) |

---

## Intent

Take an `intent_packet` (+ PGC answers) and produce:

- Epic set (instances)
- Feature set (instances, nested under epics)
- Story set (instances, nested under features)
- ExecutionPlan(s) + explanation
- Everything lineage-linked and mechanically validated

---

## Guiding Rules

1. **PGC once at POW level; inherited downward.**
2. **LLMs generate candidates; mechanical validators/compilers decide.**
3. **Waves computed once (single source of truth) after all edges exist.**
4. **Construct-then-refine:** initial materialization is `constructed`; refinement is explicit DCW per Epic/Feature (stories/tasks on-demand).
5. **Parent hierarchy is not dependency.** `parent_id` never implies `depends_on`.

---

## Schema Strategy

**Doc Type:** `backlog_item` (multi-instance)

**Base fields** (compiler-owned):

```
id, level, parent_id, depends_on[], priority_score
```

**Details** (level-specific, schema-validated):

```
details: oneOf { EpicDetails, FeatureDetails, StoryDetails, TaskDetails }
```

**Compiler and hashing operate ONLY on base fields.**

### Hash Boundary Invariant

`backlog_hash` is computed exclusively from base fields: `(id, level, parent_id, sorted(depends_on), priority_score)`. The `details` block is explicitly excluded.

**Consequence:** Editing a backlog item's description, acceptance criteria, or any level-specific detail does NOT invalidate the execution plan. Only structural changes (new dependencies, priority changes, hierarchy changes) produce a new plan.

**Consequence:** Refinement DCWs that update only `details` preserve plan stability. The operator should understand that prose edits are "free" with respect to plan identity.

This invariant MUST be documented in the `backlog_item` schema and enforced by the `BacklogPlanCompiler` implementation.

---

## Top-Level POW

**POW:** `ProjectBacklogCompilationPOW`

### Inputs

| Input | Required | Notes |
|-------|----------|-------|
| `intent_id` | Yes | |
| `pgc_merge_ref` | Yes | Or answers artifact |
| `architecture_ref` | Policy-gated | See Phase 0 |
| `method_profile` | Yes | e.g., `software_product`, `non_software_plan` |

### Outputs

| Output | Notes |
|--------|-------|
| `backlog_registry_ref` | Index of all instances created |
| `execution_plan_ref` | Derived; keyed by `backlog_hash` |
| `plan_explanation_ref` | Optional DCW |
| `phase_status_ref` | Partial-completion ledger |
| `coverage_audit_ref` | Post-Phase-2 |

### Concurrency Controls

| Parameter | Scope |
|-----------|-------|
| `max_parallel_phase2_epics` | Per execution |
| `max_parallel_phase3_features` | Per execution |

### Partial Completion Policy (v1)

Phases continue when independent branches fail.

Phase outputs include:

```
completed[], failed[], skipped[]
```

Rules:
- If failure rate exceeds threshold (e.g., >25% branches), **halt phase** to prevent runaway cost.
- Epics/Features with failures are marked `INCOMPLETE` (UI-visible) until retried.
- Retry targets the specific failed branch, not the entire phase.

---

## Phase 0 -- Preconditions (Policy Gating)

**Gate:** `ArchitectureRequiredGate`

### Rule

If `method_profile == software_product`:
- **Require** `architecture_ref`
- Allow override flag `--skip-architecture`
- When overridden:
  - Stamp warning **once on the POW execution** (not on every child artifact)
  - Child artifacts inherit the warning through `parent_execution_id` lineage
  - UI surfaces the warning from the POW level; child views reference inherited flags
  - Auto-enable Coverage Audit
  - Optionally reduce generation caps

---

## Phase 1 -- Generate Epics (single DCW)

**DCW:** `EpicSetGeneratorDCW`

### Inputs

- Intent summary + constraints + PGC answers
- Architecture summary (if present; else warning injected)

### Produces

- `backlog_item` instances: `level=EPIC`, `parent_id=null`
- `epic_set_ref`: list of epic IDs + titles + short scopes

### Constraints

- Hard cap on epic count (configurable, e.g., 4-12)
- Dependencies allowed only across epics (rare)

### Post-step Mechanical Validation

- Schema validate (base + `EpicDetails`)
- Hierarchy validate (EPIC rules: `parent_id` must be null)
- Dependency validate (`depends_on` references exist within epic set)
- Dependency cycle detection (`depends_on` only)

### Lineage

Each epic instance: `origin=construct`, `created_by_run_id=...`, `parent_execution_id=<POW run>`

### Note

**NO wave computation here.** Ordering is Phase 5 only.

---

## Phase 2 -- Generate Features per Epic (fan-out, parallel)

**POW:** `EpicFeatureFanoutPOW`

For each Epic E (rate-limited by `max_parallel_phase2_epics`):

**DCW:** `FeatureSetGeneratorDCW`

### Inputs

- `epic_id`
- Inherited: intent + PGC + architecture summary
- Global registry summary: IDs/titles for all epics + already-generated features across all epics (to avoid duplication)

### Known Property: Registry Asymmetry

When epics run in parallel, early-finishing epics' features are visible to later-finishing epics, but not vice versa. The registry is asymmetric based on completion order. This is acceptable -- the Coverage Audit (Phase 2.5) catches gaps and overlaps afterward. Do not attempt to "fix" this with a two-pass approach.

### Produces

- `backlog_item` instances: `level=FEATURE`, `parent_id=epic_id`
- `feature_set_ref` for Epic E

### Allowed Dependencies (v1)

- Feature -> feature within same epic (recommended)
- Feature -> feature in other epic **only if** parent epic `depends_on` that epic (otherwise emit warning)

### Post-step Mechanical Validation

- Schema validate (base + `FeatureDetails`)
- Hierarchy validate (FEATURE `parent_id` must reference an EPIC)
- Dependency validate + cycle detect (within feature set scope; cross-refs allowed if exist)

### Re-run Semantics (Set Reconciliation)

If re-running Feature generation for Epic E:
1. Produce candidate feature set
2. Run SetReconciler (see Shared Primitives) against existing features under Epic E
3. Emit reconciliation report + lineage

---

## Phase 2.5 -- Coverage Audit (lightweight, global)

**Step:** `FeatureCoverageAudit`

### Purpose

Catch gaps between parallel branches (auth, logging, data boundaries, etc.) without full harmonization.

### Inputs

- Intent + constraints + architecture (if present)
- Epic list + feature titles (and optional 1-liners); NOT full bodies

### Outputs

`coverage_audit_ref`:

```
suspected_gaps[]
suspected_overlaps[]
platform_concerns_missing[]    (if software_product)
recommendations[]              (non-binding)
```

### Implementation (v1)

Mechanical checklist + optional single LLM referee call (configurable).

### Operator Checkpoint

After the Coverage Audit completes, the pipeline **pauses** before Phase 3.

UI displays: "Coverage audit complete. N recommendations. **Continue** / **Review**"

The operator can:
- **Continue** -- proceed to Phase 3 immediately
- **Review** -- inspect gaps/overlaps, optionally add features or re-run Phase 2 for specific epics, then continue

A `--headless` override flag auto-continues (for CI/batch runs).

---

## Phase 3 -- Generate Stories per Feature (fan-out, parallel)

**POW:** `FeatureStoryFanoutPOW`

For each Feature F (rate-limited by `max_parallel_phase3_features`):

**DCW:** `StorySetGeneratorDCW`

### Inputs

- `feature_id`
- Inherited: intent + PGC + architecture summary
- Parent chain summaries (epic + feature)
- Sibling story titles (if re-run) to reduce churn
- **`coverage_audit_summary`** -- injected from Phase 2.5 output (non-binding awareness context; the LLM can use or ignore)

### Produces

- `backlog_item` instances: `level=STORY`, `parent_id=feature_id`
- `story_set_ref` for Feature F

### Allowed Dependencies (v1 recommended)

- Story -> story within same feature only
- Cross-feature story deps: **disallowed**; if model suggests, emit `needs_cross_feature_dep[]` warnings for future work

### Post-step Mechanical Validation

- Schema validate (base + `StoryDetails`)
- Hierarchy validate (STORY `parent_id` must reference a FEATURE)
- Dependency validate + cycle detect (within feature's stories)

### Re-run Semantics (Set Reconciliation)

Same reconciliation step as Phase 2, scoped to stories under Feature F.

---

## Phase 4 -- Tasks (on-demand)

**DCW:** `TaskSetGeneratorDCW` (triggered, not automatic)

### Trigger

- User opens Story detail and clicks "Generate Tasks", OR
- "Ready-to-execute mode" toggle for a story/feature

### Produces

Either:
- Embedded task list inside `StoryDetails` (simplest), OR
- `backlog_item` instances: `level=TASK`, `parent_id=story_id` (only if first-class tracking needed)

### Validation

- Schema validate (`TaskDetails`)
- Hierarchy validate (TASK `parent_id` must reference a STORY)
- Dependencies limited within story

---

## Phase 5 -- Compile Plan (global, mechanical SSoT)

**Mechanical Service:** `BacklogPlanCompiler`

### Inputs

- All `backlog_item` base fields in scope (EPIC/FEATURE/STORY [+TASK if present])
- `backlog_hash` computed from canonicalized base fields only (see Hash Boundary Invariant)

### Outputs

`execution_plan` (single per `backlog_hash`):

| Field | Notes |
|-------|-------|
| `waves` | Required; Kahn tiers on `depends_on` edges |
| `ordered_ids` | Flattened waves; `priority_score` DESC; `id` ASC tiebreak |
| `wave_index_by_id` | UI indexing map |
| `global_index_by_id` | UI indexing map |

### Notes

- `parent_id` **ignored** for topological ordering
- Compiler emits diagnostics if graph invalid (should be prevented by earlier phases)
- Same `backlog_hash` returns existing plan (no recomputation)

---

## Phase 6 -- Explain Plan (optional, read-only DCW)

**DCW:** `ExecutionPlanExplanationDCW`

### Inputs

- Execution plan + backlog titles + key dependency highlights
- Coverage audit summary (optional, from Phase 2.5)

### Output

- Explanation artifact

**Strictly read-only over mechanical outputs. NEVER modifies plan or backlog items.**

---

## Shared Primitives

### SetReconciler (for re-runs)

**Mechanical + (optional) LLM referee:** `SetReconciler`

Used when regenerating Feature sets or Story sets against an existing set.

### Inputs

- Existing set under a parent (Epic -> Features or Feature -> Stories)
- Candidate set produced by DCW

### Match Strategy (v1)

**ID match only.** If an existing item's ID matches a candidate item's ID, it's a match.

Non-matching IDs become **add** (candidate side) + **drop** (existing side). No title-similarity matching in v1.

Rationale: Title-based fuzzy matching creates false "replaced" entries when titles change during refinement. Paired add/drop is cleaner -- the operator can manually link them if appropriate.

### Outputs

`reconciliation_report`:

```
kept[]          -- ID matched, content may differ
dropped[]       -- existing item not in candidate set
added[]         -- candidate item not in existing set
```

Lineage records for each item transformation (`kept`, `dropped`, `added`).

### v1 Policy

- Prefer `keep` when ID matches (update details, preserve lineage)
- Never silently overwrite without reporting
- No `replaced` category -- items either match by ID (`kept`) or don't (separate `added`/`dropped`)

---

## Lineage Model (construct-then-refine)

Every generated item instance stores:

| Field | Purpose |
|-------|---------|
| `created_by_run_id` | The DCW run that created it |
| `parent_execution_id` | The orchestrating POW execution ID |
| `source_refs` | Intent, PGC, architecture, parent chain |
| `transformation` | `constructed` or `kept` (refinement vocabulary) |
| `inherited_flags` | Propagated from POW (e.g., `skip_architecture_warning`) |

Refinement runs update the same instance through DCW lifecycle, preserving:
- Origin and first-creation lineage
- Subsequent transformations appended

---

## DCW Lifecycle Boundaries

| Level | DCW Lifecycle | Default | Rationale |
|-------|---------------|---------|-----------|
| Epic | Enabled | Yes | Complexity boundary; refinement expected |
| Feature | Enabled | Yes | Complexity boundary; refinement expected |
| Story | Optional | Constructed + viewable | Refine only when asked |
| Task | Optional/on-demand | Generated when requested | Prevents workflow explosion |

---

## UI Mapping

| Surface | Content |
|---------|---------|
| Floor | Intake/discovery/plan/architecture + EPIC nodes (features optional later) |
| Epic document view | Feature list (expandable); each row shows wave + dependencies + status |
| Feature expansion | Story list |
| Story detail | Tasks (on-demand generation) |

Each list row can display wave/global index using ExecutionPlan projection.

---

## Explicitly Deferred

- Cross-feature story dependencies + harmonizer
- Automatic feedback loops (operator triggers re-runs manually)
- Capacity/sprint planning
- Multi-user collaboration
- Backlog editing UI
- Autonomous story execution

---

## Delta from v1.1

| # | Change | Rationale |
|---|--------|-----------|
| 1 | Explicit hash boundary invariant (`details` excluded; structural-only changes affect plan) | Prevents confusion when prose edits don't trigger replan |
| 2 | Operator checkpoint between Coverage Audit and story generation (+ `--headless` override) | Gives operator a chance to act on gaps before 100+ story DCWs fire |
| 3 | Reconciliation uses ID-only matching; non-matching IDs become add/drop (no title similarity) | Fuzzy matching creates false "replaced" entries; clean add/drop is safer |
| 4 | Coverage audit summary injected into Phase 3 context | Story generators aware of identified gaps without binding constraint |
| 5 | Skip-architecture warning stamped once at POW; child views reference inherited flags | Prevents noise at scale (warning on every artifact) |
| 6 | Registry asymmetry in Phase 2 documented as known property | Prevents future attempts to "fix" with unnecessary two-pass approach |
