# ProjectBacklogCompilationPOW Design v1.3

| | |
|---|---|
| **Status** | Draft |
| **Created** | 2026-02-16 |
| **Updated** | 2026-02-16 |
| **Supersedes** | Conversational v1.0, v1.1; v1.2 monolithic pipeline phases |
| **Foundation** | BACKLOG-COMPILATION-PIPELINE-Implementation-Plan.md (WS-BCP-001--004 delivered) |

---

> **v1.3 Supersession Note**
>
> v1.2 described Phases 2/3 as steps in a monolithic pipeline that ran end-to-end.
> v1.3 replaces that model with **discrete UI-triggered fan-out POWs**. Each expansion
> (Epic→Features, Feature→Stories) is a separate POW run triggered from the UI.
> The operator sees intermediate results, reviews them, then decides when to expand further.
>
> Coverage audit moved from pipeline Phase 2.5 into the **IPF DCW** (pre-acceptance).
> Plan compilation changed from automatic to **operator-triggered with smart nudges**.

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
6. **Planning richness, execution leanness.** IPF artifacts may contain redundancy for human readability. BacklogItem execution artifacts must not.

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

## Execution Model: Progressive Expansion

Unlike v1.2's monolithic pipeline, v1.3 uses **discrete, operator-initiated expansion steps**:

```
Initial Compile (POW)
  → Epic backlog_items (validated, ordered)

"Generate Features" button (per epic)
  → EpicFeatureFanoutPOW
  → Feature backlog_items under that epic (validated)

"Generate Stories" button (per epic or per feature)
  → FeatureStoryFanoutPOW
  → Story backlog_items under features (validated)

"Compile Plan" button (global)
  → Mechanical validation + ordering + hashing
  → ExecutionPlan artifact
```

Each step is a separate POW run. The operator sees intermediate results, reviews, and decides when to proceed. This aligns with how The Combine works: POWs are triggered, they produce documents, documents get reviewed.

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
| `mode` | Yes | `epics_only` or `full_backlog` |

### Outputs

| Output | Notes |
|--------|-------|
| `backlog_registry_ref` | Index of all instances created |
| `execution_plan_ref` | Derived; keyed by `backlog_hash` |
| `plan_explanation_ref` | Optional DCW |

### Modes

| Mode | Behavior |
|------|----------|
| `epics_only` | Generate EPIC backlog_items only. Validate. Stop. Lightweight initial compile. |
| `full_backlog` | Generate EPICs + FEATUREs + STORYs in one run (existing v1.2 behavior, retained for backward compatibility) |

`epics_only` is recommended for progressive expansion. The operator inspects epic boundaries before committing to feature decomposition.

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

**NO wave computation here.** Ordering is Compile Plan only.

If `mode == epics_only`, the pipeline stops here after validation.

---

## Discrete Fan-Out: Feature Generation

**POW:** `EpicFeatureFanoutPOW`

**Trigger:** UI button "Generate Features" on an Epic node

**Scope:** Single epic per invocation

### Inputs

- Epic `backlog_item` (execution form: id, level, title, summary, details)
- IPF epic context (planning form: full scope, risks, architecture_notes)
- Intent summary
- Architecture summary
- **Sibling Epic Boundary Summary:** `{epic_id, title, 1-line scope}` for all other epics

### Sibling Context Purpose

The boundary summary helps the LLM avoid generating features that belong in sibling epics. It is context for coherence, not a deduplication mechanism.

Prompt instruction: *"Do not generate features that belong in sibling epics. If uncertain about placement, set `boundary_uncertain: true` in FeatureDetails."*

### Produces

- `backlog_item` instances: `level=FEATURE`, `parent_id=epic_id`
- Each item includes `details.boundary_uncertain` flag when placement is ambiguous

### Allowed Dependencies (v1)

- Feature → feature within same epic (recommended)
- Feature → feature in other epic **only if** parent epic `depends_on` that epic (otherwise emit warning)

### Post-step Mechanical Validation

- Schema validate (base + `FeatureDetails`)
- Hierarchy validate (FEATURE `parent_id` must reference an EPIC)
- Dependency validate + cycle detect

### Re-run Semantics

Clicking "Generate Features" when features already exist triggers **Regenerate Features** using SetReconciler:

- Matching IDs → `kept` (update details allowed, preserve lineage)
- New IDs → `added`
- Missing IDs → `dropped`
- No fuzzy matching

**UI shows reconciliation summary before applying drops.** Operator confirms or cancels.

### Staleness

The pipeline_run record stores `source_hash` = epic's structural hash at generation time.

Staleness rule: `current_epic.structural_hash != run_record.source_hash` → feature set = **STALE**

---

## Discrete Fan-Out: Story Generation

**POW:** `FeatureStoryFanoutPOW`

**Trigger:** UI button "Generate Stories" (per epic fans out over all features; per feature generates for one)

**Scope:** One or more features under a single epic

### Inputs

- Feature `backlog_item`(s)
- Parent epic summary
- Intent summary
- Architecture summary
- Sibling story titles (if re-run) to reduce churn

### Produces

- `backlog_item` instances: `level=STORY`, `parent_id=feature_id`

### Story Dependency Scope Policy

| Scope | Allowed | Notes |
|-------|---------|-------|
| Within same feature | Yes | Normal case |
| Cross-feature, within same epic | Yes | e.g., auth story depends on user-model story in sibling feature |
| Cross-epic | No (v1) | If detected, emit `needs_cross_epic_dep_warning[]` (non-binding) |

This gives the LLM enough room to express real dependencies (auth/model/setup patterns) without opening the global graph.

### Post-step Mechanical Validation

- Schema validate (base + `StoryDetails`)
- Hierarchy validate (STORY `parent_id` must reference a FEATURE)
- Dependency validate + cycle detect (within epic scope)
- Cross-epic dependency warning emission (non-binding)

### Re-run Semantics

Same reconciliation as Feature fan-out, scoped to stories under the target feature(s). UI shows reconciliation summary before applying drops.

### Staleness

`source_hash` = feature's structural hash at generation time. Same rule as feature staleness.

---

## Tasks (on-demand)

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

## Compile Plan (operator-triggered, mechanical)

**Mechanical Service:** `BacklogPlanCompiler`

### Trigger

**Do not auto-compile after every fan-out run.** Instead:

- After a fan-out completes, UI shows: *"Backlog changed. Compile plan?"* with one-click action
- Global "Compile Plan" button at project level always available
- `--auto-compile` flag for headless/CI mode

Auto-compiling after every small change creates unnecessary plan churn in the audit trail.

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

## Explain Plan (optional, read-only DCW)

**DCW:** `ExecutionPlanExplanationDCW`

### Inputs

- Execution plan + backlog titles + key dependency highlights

### Output

- Explanation artifact

**Strictly read-only over mechanical outputs. NEVER modifies plan or backlog items.**

---

## Coverage Audit (IPF DCW, pre-acceptance)

> **Moved from v1.2 Phase 2.5 into the IPF DCW.**
>
> Epic quality is a planning problem, not a compilation problem. The audit belongs
> inside the IPF DCW, before acceptance, before compilation starts.

**Pass within IPF DCW:** `EpicCoverageAuditPass`

### Inputs

- Intent + constraints + architecture (if present)
- Generated epics (scope, out_of_scope, risks, dependencies)

### Outputs

```
status: "SUFFICIENT" | "GAPS_DETECTED"
coverage_gaps[]           -- missing capabilities, severity
overlaps[]                -- epic pairs with ambiguous boundaries
cross_cutting_concerns_missing[]
architectural_misalignment[]
refinement_recommendations[]  -- ADD_EPIC, MERGE_EPICS, SPLIT_EPIC, CLARIFY_BOUNDARY
```

### Implementation

Second LLM pass within the IPF DCW (Strategy B: generate → audit). Separates generation from evaluation.

### Integration

Audit results inform the IPF acceptance decision. The IPF already requires `acceptance_required: true` with stakeholder/technical_lead signoff. Audit findings surface during that review.

---

## Shared Primitives

### SetReconciler (for re-runs)

**Mechanical + (optional) LLM referee:** `SetReconciler`

Used when regenerating Feature sets or Story sets against an existing set.

### Inputs

- Existing set under a parent (Epic → Features or Feature → Stories)
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

### UI Confirmation

**Default: show reconciliation summary before applying drops.** Operator confirms or cancels.

This prevents accidental data loss when regeneration produces a different ID set. The operator sees exactly what will be added/dropped and can cancel if the changes look wrong.

### v1 Policy

- Prefer `keep` when ID matches (update details, preserve lineage)
- Never silently overwrite without reporting
- No `replaced` category -- items either match by ID (`kept`) or don't (separate `added`/`dropped`)

---

## Staleness Mechanism

### Principle

Staleness is deterministic, keyed off structural hash changes at the parent level. No vibes.

### Mechanism

Each fan-out pipeline_run record stores:

| Field | Value |
|-------|-------|
| `source_id` | The parent item ID (epic_id or feature_id) |
| `source_hash` | The parent item's structural hash at generation time |

### Detection Rule

```
current_parent.structural_hash != run_record.source_hash → child set = STALE
```

Applies transitively: if an epic's hash changes, its features are stale. If a feature's hash changes, its stories are stale.

### UI State Machine

Expansion state for each parent node, derived from existence of backlog_items + staleness:

| State | Meaning |
|-------|---------|
| `missing` | No children generated yet |
| `generating` | Fan-out POW currently running |
| `ready` | Children exist and source_hash matches |
| `stale` | Children exist but parent structural hash changed |
| `failed` | Last fan-out run failed |

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

| Surface | Content | Actions |
|---------|---------|---------|
| Floor | Intake/discovery/plan/architecture + EPIC nodes | View Document |
| Epic node | Shows F count, S count, expansion state | Generate Features, View Document |
| Epic document view | Feature list (expandable); wave + dependencies + status | Generate Stories (per epic) |
| Feature row | Story list | Generate Stories (per feature) |
| Story detail | Tasks (on-demand) | Generate Tasks |
| Project level | Global backlog state | Compile Plan |

Each list row can display wave/global index using ExecutionPlan projection.

### Post-Expansion Nudge

After any fan-out completes: *"Backlog changed. Compile plan?"* — one-click action, not auto-triggered.

---

## What Does NOT Change

These remain stable across expansion:

- BacklogItem schema (v1.0.0)
- Hash boundary rules
- Ordering algorithm (Kahn + priority)
- IntentSanityGate
- IPF acceptance logic
- Graph validator core (dependency, hierarchy, cycle detection)

---

## Explicitly Deferred

- Cross-epic story dependencies + harmonizer
- Automatic feedback loops (operator triggers re-runs manually)
- Capacity/sprint planning
- Multi-user collaboration
- Backlog editing UI
- Autonomous story execution
- Two-pass registry synchronization for parallel fan-outs

---

## WS-BCP-005 Scope

**WS-BCP-005 — Progressive Expansion Workflows**

| Deliverable | Notes |
|-------------|-------|
| `EpicFeatureFanoutPOW` | POW + DCW configuration |
| `FeatureStoryFanoutPOW` | POW + DCW configuration |
| Staleness detection | `source_hash` on pipeline_run, UI state derivation |
| Reconciliation with UI confirmation | SetReconciler + confirmation modal |
| UI buttons | Generate Features, Generate Stories, Compile Plan |
| Expansion state + counts | F count, S count, state badge on epic/feature nodes |
| Plan compile nudge banner | Post-expansion suggestion, not auto-trigger |
| This document updated | v1.2 monolithic phases superseded |

No compiler changes. No schema changes (beyond `boundary_uncertain` already added).

---

## Delta from v1.2

| # | Change | Rationale |
|---|--------|-----------|
| 1 | Phases 2/3 replaced by discrete UI-triggered fan-out POWs | Monolithic pipeline hides intermediate state; discrete POWs align with The Combine's document-review model |
| 2 | Coverage audit moved from pipeline Phase 2.5 into IPF DCW | Epic quality is a planning problem; audit belongs pre-acceptance, not mid-compilation |
| 3 | Story dependency scope expanded: within-epic cross-feature allowed (v1) | Enables realistic dependencies (auth/model/setup) without opening global graph |
| 4 | `boundary_uncertain` flag added to FeatureDetails | Generator signals ambiguous epic boundary placement for operator review |
| 5 | Staleness mechanism: `source_hash` on pipeline_run records | Deterministic staleness detection keyed off parent structural hash changes |
| 6 | Reconciliation UI confirmation before applying drops | Prevents accidental data loss on regeneration |
| 7 | Plan compilation changed to operator-triggered with nudge | Auto-compile creates plan churn; nudge banner preserves operator control |
| 8 | Sibling Epic Boundary Summary as feature generator input | Coherence context without pretending to solve deduplication mechanically |
| 9 | `epics_only` mode for initial compile | Reduces blast radius; operator inspects epic boundaries before feature expansion |
| 10 | `risk_summary` in IPF derived mechanically by handler | Deterministic aggregation from per-epic risks; LLM no longer self-aggregates |
