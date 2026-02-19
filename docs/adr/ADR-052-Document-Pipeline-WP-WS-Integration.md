# ADR-052 -- Document Pipeline Integration for Work Packages and Work Statements

**Status:** Draft (accept on merge)
**Date:** 2026-02-18
**Decision Type:** Architectural / Pipeline

**Related ADRs:**
- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-049 -- No Black Boxes: Explicit DCW Composition
- ADR-048 -- Intake POW and Workflow Routing
- ADR-045 -- System Ontology: Primitives, Composites, and Configuration Taxonomy

**Related Policies:**
- POL-WS-001 -- Standard Work Statements

---

## 1. Context

The current Combine planning pipeline terminates in Epic artifacts:

```
Concierge ? Project Discovery ? Technical Architecture ? IPP ? IPF ? Epics
```

With Work Statements (WS) established as the atomic execution unit (ADR-050) and Work Packages (WP) established as a runtime primitive (ADR-051), the pipeline must shift to produce executable structure:

```
Concierge ? Project Discovery ? Technical Architecture ? IPP ? IPF ? Work Packages ? Work Statements
```

This requires:

- Schema and prompt changes in IPP/IPF
- New artifact types (WP, WS)
- Production Floor UI updates to reflect WP/WS hierarchy and runtime state

---

## 2. Decision

### 2.1 IPP Output Changes

`epic_candidates[]` is replaced with `work_package_candidates[]`.

Each WP candidate MUST include:

| Field | Purpose |
|-------|---------|
| `title` | Name of the Work Package |
| `rationale` | Why this bundle of work exists as a coherent unit |
| `scope_in` | What is included in this Work Package |
| `scope_out` | What is explicitly excluded |
| `dependencies[]` | References to other WP candidates that must complete first |
| `definition_of_done[]` | Mechanically evaluable criteria at the WP level |

IPP prompt and schema are updated accordingly. The candidate ID pattern changes from `EC-` (Epic Candidate) to `WPC-` (Work Package Candidate).

### 2.2 IPF Reconciliation Changes

IPF reconciles WP candidates into committed Work Packages using the existing reconciliation pattern:

- `kept` -- candidate accepted as-is
- `split` -- candidate decomposed into multiple WPs
- `merged` -- multiple candidates combined into one WP
- `dropped` -- candidate removed with justification

Bidirectional traceability to upstream artifacts is preserved. The `candidate_reconciliation[]` and `source_candidate_ids[]` mechanisms remain structurally unchanged. Only the candidate type changes from Epic to Work Package.

### 2.3 Governance Pinning at WP Instantiation

When a Work Package is instantiated from IPF output, it pins the current versions of governing artifacts:

| Pinned Artifact | Purpose |
|-----------------|---------|
| Technical Architecture | Architectural constraints and decisions |
| Applicable ADRs | Governance rules in effect |
| Applicable Policies | Process constraints in effect |

These pinned versions become the inherited constraint bundle for all Work Statements executed under that WP. Governance changes after instantiation apply to future WPs, not in-flight ones (per ADR-051 Section 7).

### 2.4 Work Statement Authoring and Onboarding

Work Statements are introduced as a first-class artifact type associated with a WP's runtime work queue.

**Initial phase:** WS are authored externally (human + LLM conversation) and registered into the WP queue. This is the current operating model and it works.

**Future phase:** A DCW may generate WS from a WP's scope and Definition of Done. This is explicitly **out of scope** for this ADR. The authoring mechanism does not affect the runtime model -- WS instances in the queue behave identically regardless of how they were authored.

### 2.5 Production Floor UI Updates

The Production Floor replaces Epic nodes with Work Package nodes.

**WP node displays:**

| Element | Content |
|---------|---------|
| State badge | PLANNED / READY / IN_PROGRESS / AWAITING_GATE / DONE |
| Progress roll-up | e.g., "3/5 WS complete" |
| Dependency indicators | Which upstream WPs this depends on |
| Verification health | Mode A/B ratio for child WS |

**WS child nodes display:**

| Element | Content |
|---------|---------|
| Execution status | Pending / In Progress / Complete / Failed |
| Verification mode | A or B indicator |
| Tier 0 status | Pass / Fail / Not Run |

WS nodes are children of WP nodes, replacing the current Epic ? (no children) structure with WP ? WS hierarchy.

---

## 3. Migration Path

### 3.1 Schema Changes

| Schema | Change |
|--------|--------|
| IPP (Primary Implementation Plan) | `epic_candidates[]` ? `work_package_candidates[]` with new field set |
| IPF (Implementation Plan Final) | `candidate_reconciliation[]` operates on WP candidates; `source_candidate_ids[]` use `WPC-` prefix |
| Work Package (new) | Runtime schema with state, queue, governance pins, Definition of Done |
| Work Statement (new) | Artifact schema with verification mode, Tier 1 criteria, scope, postconditions |

### 3.2 Prompt Changes

| Prompt | Change |
|--------|--------|
| IPP task prompt | Rewritten to produce WP candidates with scope, rationale, dependencies, Definition of Done |
| IPF task prompt | Updated reconciliation rules for WP candidates instead of epic candidates |

### 3.3 Production Floor Changes

| Component | Change |
|-----------|--------|
| Production floor transformer | Epic nodes ? WP nodes with state and progress |
| DocumentNode | WP rendering with state badge, progress bar, WS children |
| FullDocumentViewer | WP and WS document viewing support |

---

## 4. Consequences

### Positive

- **Pipeline produces executable structure** -- WPs and WSs are directly actionable
- **Traceability extends further** -- from Concierge through to individual verified code changes
- **Progress tracking is meaningful** -- WP state and WS completion ratios replace opaque epic status
- **Verification health is visible** -- Mode A/B ratios surface factory maturity per Work Package
- **Foundation for self-hosting** -- The Combine can track its own development through WP/WS

### Tradeoffs

- **Schema migration** -- existing IPP/IPF documents and prompts must be updated
- **UI rework** -- Production Floor epic rendering replaced with WP/WS hierarchy
- **Two new artifact types** -- WP and WS add to the system ontology
- **Epic-based historical artifacts remain** -- not migrated, treated as historical record

---

## 5. Non-Goals

This ADR does NOT:

- Define WS authoring DCW (future work, explicitly deferred)
- Define WP/WS database schema details (implementation work)
- Migrate historical epic-based IP documents
- Change upstream pipeline (Concierge, PD, TA are unaffected)
- Define TA-to-ADR candidate generation (future work -- TA may emit ADR candidates; ADRs remain the decision ledger and are promoted independently)
- Define MCP connector integration (separate concern)

---

## 6. Acceptance Criteria

ADR-052 is considered satisfied when:

1. IPP schema and prompt produce `work_package_candidates[]` instead of `epic_candidates[]`
2. IPF schema and prompt reconcile WP candidates with bidirectional traceability
3. Work Package exists as a runtime artifact with state tracking
4. Work Statement exists as a first-class artifact associated with a WP queue
5. Production Floor renders WP nodes with state, progress, and WS children
6. At least one project has been planned through the full updated pipeline (PD ? TA ? IPP ? IPF ? WP ? WS)
7. Governance pinning is recorded on WP instantiation

---

_End of ADR-052_

