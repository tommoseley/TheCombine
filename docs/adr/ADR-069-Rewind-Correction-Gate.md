# ADR-069 — Rewind as Correction Gate: Operator Binding Corrections at Rewind Time

**Status:** Draft
**Date:** 2026-04-02
**Owners:** Tom / Combine Architecture
**Coupled With:** ADR-063 (Pipeline Rewind), ADR-064 (Durable Authority Context)

---

## 1. Context

When an operator reviews a generated document and discovers a flaw — a missing constraint, an incorrect assumption, or a boundary the system never asked about — the natural action is to rewind.

Today, rewind captures a free-text **reason** and marks downstream artifacts stale. But the operator's correction — the *binding information that should govern the regenerated path* — has no structured home. The reason field is narrative, not authoritative. It doesn't flow into regeneration. The operator must re-state the correction when the system re-asks PGC questions, or hope the system infers it.

ADR-064 established durable authority context: PGC answers persist across rewinds as project-level governed inputs. But PGC only captures what the system *knew to ask*. When the system asked the wrong questions — or failed to ask the right ones — the operator discovers the gap only at review time. That correction needs an entry point.

The right insertion point is rewind itself.

---

## 2. Problem Statement

There is no structured mechanism for an operator to inject binding corrections at the moment they identify a flaw.

**Current gap:**

1. Operator reviews a TA and discovers: "iOS app must not call Anthropic directly — all AI integration must be server-side."
2. Operator rewinds to TA stage, enters a reason: "Architecture incorrectly assumes direct Anthropic calls from iOS."
3. System rewinds. Reason is recorded in the lineage event — but as narrative, not as a binding input.
4. Regeneration starts. The LLM receives the same inputs as before. PGC may or may not ask the right question this time.
5. The correction is lost or diluted.

**What's needed:**

- A structured way to capture operator corrections at rewind time
- Those corrections must become **authority records** — consumed by regeneration, visible in audit, governing downstream stages
- The UX must be natural: one evolving correction per document/stage, not a growing stack of disconnected rewind reasons

---

## 3. Decision

### 3.1 The rewind reason IS the correction brief

There is no separate "correction" field. The rewind reason serves as both the audit narrative and the binding authority for regeneration. One field, dual-written:

1. **Lineage event** — immutable audit record (per ADR-063)
2. **Authority record** — living, supersedable, consumed by regeneration (per ADR-064)

The operator writes what's wrong and what must change in a single text area. This is always persisted as an `operator_correction` authority record with `authority_type = "operator_correction"`.

**Why one field, not two:** The GPT design conversation identified that separating "reason" (audit-only) from "correction" (authority) creates redundant re-entry. The operator who writes "Architecture must be server-side" as their reason should not have to re-state it in a separate correction field. The reason *is* the correction.

### 3.2 One evolving correction brief per stage, not a stack

The correction brief is cumulative and editable, not append-only from the operator's perspective.

- **Rewind 1** at stage TA: operator enters correction text in the reason field.
- **Rewind 2** at stage TA: the reason field is **pre-populated** with the previous correction text. The operator edits, appends, or rewrites it.
- The system always carries forward **one current correction** per (project, stage).

Internally, each rewind creates a new authority record that supersedes the previous one (same `(project_id, authority_type, key)` supersession from ADR-064). The full history is preserved in superseded records for audit; the UI shows only the current version.

### 3.3 Corrections are authority records

Operator corrections are stored in the existing `authority_records` table:

| Field | Value |
|-------|-------|
| `authority_type` | `"operator_correction"` |
| `stage` | Pipeline stage the correction originates from (e.g., `"TA"`) |
| `key` | `"correction:{stage}"` (e.g., `"correction:TA"`) |
| `value` | `{"text": "...", "applies_to_stages": ["TA", "IP"], "rewind_event_id": "<uuid>"}` |
| `source_execution_id` | UUID of the rewind lineage event (MVP surrogate — no execution exists at rewind time) |
| `lineage_path_id` | Same lineage event ID (MVP surrogate, consistent with ADR-064 pattern) |
| `actor` | `"operator"` |

**Note on `source_execution_id`:** ADR-064 defines this field as "which execution produced this." Operator corrections are created outside any workflow execution — they originate from the rewind action itself. As an MVP surrogate, we store the lineage event ID in both `source_execution_id` and `lineage_path_id`, matching the surrogate pattern ADR-064 already uses for `lineage_path_id`. The canonical rewind event linkage is in `value.rewind_event_id`, which is the authoritative provenance field for corrections. When a proper execution-independent provenance model is introduced, `source_execution_id` can be migrated.

Supersession follows ADR-064 rules: same `(project_id, "operator_correction", key)` → old record superseded, new record becomes current.

### 3.4 Regeneration consumes corrections

Corrections are consumed at two levels: the **project-scoped bundle** and the **stage-aware query**.

**Project-scoped bundle** (`get_authority_bundle(project_id)`): The existing authority bundle API remains project-scoped. It gains an `operator_corrections` key containing **all** current corrections for the project — unfiltered, sorted by pipeline order of origin stage then `created_at`. This is the global inventory; it does not imply applicability to any specific stage.

```python
# Project-scoped bundle — all corrections, no stage filtering
{
    "pgc_answers": {...},          # existing
    "pgc_questions": [...],        # existing
    "operator_corrections": [      # NEW — all current corrections, project-wide
        {
            "origin_stage": "TA",
            "text": "Cloud AI integration must be server-side...",
            "authority_record_id": "...",
        },
        {
            "origin_stage": "IP",
            "text": "All WPs must include deployment validation step...",
            "authority_record_id": "...",
        },
    ],
    "authority_record_ids": [...], # includes correction record IDs
    "authority_source": "durable_store",
}
```

**Stage-aware query** (`get_corrections_for_stage(project_id, stage)`): When the task node assembles a prompt for a specific stage, it calls this method to get the **applicable** corrections. This is the filtering step.

**Resolution rule:** For a stage being generated (e.g., IP), the applicable corrections are:
1. All current `operator_correction` records where `stage` matches the generated stage (e.g., `key = "correction:IP"`)
2. Plus all current `operator_correction` records where the generated stage appears in `value.applies_to_stages` (e.g., a TA correction that declares `applies_to_stages: ["TA", "IP"]`)

The result is a deterministic ordered list: sorted by pipeline order of originating stage, then by `created_at` within the same stage. Each correction carries its originating stage for provenance.

### 3.5 Prompt injection of corrections

Corrections are injected into the task prompt context as a governed section, similar to how `{{mockup_context}}` works (ADR-068):

- If applicable corrections exist for the stage being generated, they are assembled into an `{{operator_corrections}}` template variable
- Corrections are rendered as a numbered list with provenance, in the deterministic order from section 3.4
- The task prompt includes a conditional section:

```
{{#operator_corrections}}
## Operator Corrections (Binding)

The following corrections were provided by the operator during pipeline review.
These are BINDING constraints — they override any prior assumptions.
Each correction is numbered and tagged with its originating stage.

{{operator_corrections}}
{{/operator_corrections}}
```

Example rendered output when IP generation has two applicable corrections:

```
## Operator Corrections (Binding)

The following corrections were provided by the operator during pipeline review.
These are BINDING constraints — they override any prior assumptions.
Each correction is numbered and tagged with its originating stage.

1. [From TA rewind] Cloud AI integration must be server-side. iOS client must not call Anthropic directly or hold API credentials.
2. [From IP rewind] All Work Packages must include a deployment validation step before marking complete.
```

- If no corrections exist, the section is absent (not empty)

### 3.6 Every rewind creates an authority record

The reason field is required, and every rewind dual-writes it to the authority store. There is no "rewind without correction" — even a simple "try again" creates an authority record. This is acceptable because:

- Supersession ensures only the latest correction per (project, stage) is current
- Simple re-rolls produce lightweight records ("Regenerate with same inputs") that don't add noise to prompt injection — the correction text is what it is
- The audit trail is complete: every rewind reason is traceable as an authority record

### 3.7 Correction scope: stage-targeted with optional broadening

Each correction is keyed to the stage being rewound to. The `applies_to_stages` field allows the operator to declare that a correction should govern additional downstream stages.

Example: operator rewinds to TA and enters a deployment constraint. They mark it as applying to `["TA", "IP"]` — both the architecture and the implementation plan should respect it.

The authority bundle query filters by the stage being generated AND by any corrections whose `applies_to_stages` includes that stage.

### 3.8 Corrections visible in binder audit

The binder evaluation sections (ADR-058, ADR-061) are extended to display which corrections were in effect **at generation time** — not the current correction state.

**Mechanism:** When a document is generated with active corrections, the task node stamps `correction_authority_record_ids` in the document's metadata (same pattern as `mockup_artifact_ids` from ADR-068). The binder resolves those IDs from the authority store — including superseded records — to show the exact corrections that governed the generation.

The binder displays per document:
- The correction text and origin stage that were active at generation time
- A status indicator: `"current"` if the correction is still active, `"superseded"` if it has been updated since generation (signaling the document may need regeneration)

**Why generation-time, not current-state:** After multiple rewinds and supersessions, the current correction set may differ from what governed a specific document. Showing current corrections would misrepresent the audit trail. The stamped authority record IDs are the authoritative link.

This closes the audit loop: correction → authority → generation (stamped IDs) → evaluation (resolved from IDs) → visible.

---

## 4. Consequences

### Positive

- **Operator corrections have a natural insertion point** — no new UI concept, just an extension of rewind
- **Corrections are authoritative** — they flow into regeneration as governed inputs, not lost narrative
- **Single evolving correction** — operators see one coherent brief, not a stack of disconnected reasons
- **Audit trail preserved** — supersession chain shows how corrections evolved
- **Reuses existing infrastructure** — authority records, authority bundle, prompt template injection
- **Corrections suppress re-asking** — PGC authority-first question generation (ADR-064) sees the correction and can suppress questions already answered by the operator's correction

### Negative

- **Prompt length growth** — corrections add to prompt context; must be monitored for token budget impact
- **Operator discipline required** — corrections that are too vague ("make it better") provide no value; UX should guide toward specificity
- **Stage-targeting complexity** — `applies_to_stages` adds a routing decision; V1 can default to "this stage only" and broaden later

### Neutral

- **No schema change** — `authority_records` table already supports arbitrary `authority_type` and JSONB `value`
- **No new ORM model** — existing `AuthorityRecord` model and `AuthorityService` are reused
- **Migration: none** — no DDL changes, only new authority_type values

---

## 5. Existing Infrastructure Reused

| Component | Current State | Extension for ADR-069 |
|-----------|---------------|----------------------|
| `authority_records` table | Stores `pgc_answer` records | Add `operator_correction` type (no schema change) |
| `AuthorityService.record_authority()` | Type-scoped supersession | Same logic, new type |
| `AuthorityService.get_authority_bundle()` | Returns `pgc_answers` dict | Add `operator_corrections` — all current corrections, project-scoped (no stage filtering) |
| `AuthorityService` (new method) | n/a | Add `get_corrections_for_stage(project_id, stage)` — stage-aware filtered list for prompt assembly and binder |
| `RewindRequestBody` | `reason` (required) | Reason is now the correction brief — dual-written. Add `applies_to_stages` (optional) |
| `RewindControl.jsx` | Single reason input | Reason textarea (pre-populated from authority store), inline stage checkboxes |
| `lineage_events` table | Records rewind events | No change (correction is in authority_records, linked by execution_id) |
| Prompt template injection | `{{mockup_context}}` pattern (ADR-068) | Add `{{operator_corrections}}` pattern |

---

## 6. UX Specification

### Rewind Dialog (Single-Field)

One textarea serves as both the audit reason and the binding correction:

```
┌─────────────────────────────────────────────┐
│  Rewind to Technical Architecture?          │
│                                             │
│  All documents from this stage onward will  │
│  be marked stale. Describe what's wrong     │
│  and what must change — this becomes a      │
│  binding constraint for regeneration.       │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Architecture incorrectly assumes    │    │
│  │ direct Anthropic calls from iOS.    │    │
│  │ Cloud AI integration must be        │    │
│  │ server-side. iOS client must not    │    │
│  │ hold API credentials.               │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  Applies to: [TA] [IP] [ ] [WP] [ ] [WS]  │
│                                             │
│  [Confirm Rewind]  [Cancel]                 │
└─────────────────────────────────────────────┘
```

On subsequent rewinds to the same stage, the textarea is **pre-populated** with the previous correction brief. The operator edits in place — one evolving field, not a stack.

---

## 7. Data Flow

```
Operator identifies flaw in TA
    │
    ▼
Clicks "Rewind to TA"
    │
    ▼
Dialog: enters reason + optional correction
    │
    ├──► Rewind executes (ADR-063): downstream docs marked stale
    │
    ├──► Correction stored as authority_record:
    │    (project_id, "operator_correction", "correction:TA", value, ...)
    │
    ├──► Any prior correction:TA superseded (ADR-064 rules)
    │
    ▼
Operator triggers regeneration from TA
    │
    ▼
Plan executor assembles inputs for TA:
    │
    ├──► Stage-aware correction query: get_corrections_for_stage(project, "TA")
    │    └── Returns: [{origin: "TA", text: "Cloud AI must be..."}]
    │       (filtered to applicable corrections, ordered by pipeline stage)
    │
    ├──► Task prompt rendered with {{operator_corrections}} numbered list
    │    (section stripped entirely if no corrections apply)
    │
    ▼
LLM generates TA with correction as binding context
    │
    ▼
QA gate validates: does output respect operator corrections?
    │
    ▼
Binder resolves meta.correction_authority_record_ids → shows generation-time corrections
```

---

## 8. Implementation Scope

**Estimated scope:** Multi-commit (3 WPs)

### WP-REWIND-CORRECT-001: Backend Authority Extension
- Extend `AuthorityService.get_authority_bundle()` to include `operator_corrections`
- Extend `RewindRequestBody` with optional `corrections` field
- Wire rewind endpoint to persist correction as authority record on rewind
- Load current correction for pre-population endpoint
- Tests: authority service, rewind with correction, supersession, bundle assembly

### WP-REWIND-CORRECT-002: Prompt Injection + Regeneration
- Add `{{operator_corrections}}` template variable to prompt assembly
- Extend task prompts (TA, IP, PD) with conditional correction section
- Version bump affected prompts and workflows
- Test: correction flows through to LLM input, absent when no corrections exist

### WP-REWIND-CORRECT-003: UI + Binder Audit
- Extend `RewindControl.jsx` with corrections textarea and stage checkboxes
- Pre-populate correction from authority store on subsequent rewinds
- Extend binder evaluation to display active corrections
- Test: UI renders, pre-populates, submits; binder shows corrections

---

## 9. Alternatives Considered

### 9.1 Standalone Authority Editor

A dedicated UI for adding/editing authority records outside of rewind.

**Rejected because:** Loose and decontextualized. Corrections should be tied to a specific correction event (the rewind), not free-floating. A standalone editor can be built later if needed, but rewind is the natural insertion point.

### 9.2 Multiple Rewind Reasons (Stack)

Each rewind appends a new reason. UI shows all of them.

**Rejected because:** Creates ambiguity about which reason is authoritative. Partial contradictions accumulate. A single evolving correction is cleaner — one coherent statement of "what must change."

### 9.3 PGC-Only (No Separate Correction Mechanism)

Rely on PGC to eventually ask the right questions after rewind.

**Rejected because:** PGC asks what the system knows to ask. When the system's model is wrong (e.g., assumes direct API calls are valid), PGC won't ask about the constraint the operator discovered. The operator needs a way to inject what PGC missed.

### 9.4 Correction as Lineage Event Metadata

Store corrections in the `lineage_events` table alongside the rewind reason.

**Rejected because:** Lineage events are immutable audit records. Corrections need supersession semantics (edit on re-rewind). Authority records already have this. Using two storage mechanisms for the same concept creates inconsistency.

---

## 10. Related ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-063 | Pipeline Rewind — the mechanism this extends |
| ADR-064 | Durable Authority Context — the storage and supersession model reused |
| ADR-068 | Mockup Attachments — established the `{{template_variable}}` injection pattern |
| ADR-049 | No Black Boxes — corrections must be visible in prompt composition, not hidden |
| ADR-040 | Stateless LLM — corrections arrive via structured context, not conversation replay |
