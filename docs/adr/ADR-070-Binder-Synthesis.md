# ADR-070: Binder Synthesis — Composition Quality Before Execution

| | |
|---|---|
| **Status** | Draft |
| **Date** | 2026-04-07 |
| **Decision Owner** | Tom Moseley |
| **Trigger** | MSA-001 binder review: structurally valid binder with compositional defects (overlapping WSs, uncovered TA components, platform realism issues) that no existing evaluator detects |
| **Related** | ADR-040 (Stateless Execution), ADR-049 (No Black Boxes), ADR-064 (Durable Authority), ADR-069 (Correction Gate), Architectural Review 2026-04-03 |

---

## Context

The Combine's pipeline produces a Work Binder — a collection of documents (CI, PD, IP, TA, WPs, WSs) that have each passed structural validation, QA gates, and schema enforcement. Existing evaluators check for contradiction (ADR-061), duplicate objectives (ADR-062), and TA ownership (WS-EVAL-003/005A).

MSA-001 demonstrated that a binder can pass all of these checks and still contain compositional defects that make it non-executable:

- Two WSs with 62% scope overlap across different WPs (WS-138/WS-145)
- A TA component (Media Reference Manager) with no WP execution coverage
- A TA component (Configuration Manager) mixing unrelated concerns
- A platform assumption (Siri for offline voice) that is likely wrong for the use case
- Inconsistency between IP-level decisions and WS-level implementation choices

These are not structural errors (schema catches those) and not single-document contradictions (the contradiction evaluator catches those). They are cross-document composition problems that only become visible when the entire binder is reviewed as a whole.

Currently, only the Chorus (operator + AI collaborators reviewing the binder) catches these. This ADR introduces a bounded pipeline step to surface them systematically.

---

## Decision

Add a **Synthesis** step as a post-binder composition stage that runs once after all project documents are stabilized and the binder is assembled. Synthesis is a binder-level operation, not a per-document workflow pass. It is not part of PGC, Generation, QA, or Stabilize for individual artifacts, and does not execute within earlier document creation stages.

Synthesis analyzes the complete binder and produces a structured delta (proposed actions + questions), not a rewrite.

### Position in Pipeline

```
Document workflows complete (PGC → Gen → QA → Stabilize per doc)
                          ↓
                   Binder assembled
                          ↓
              SYNTHESIS (once, project-level)
                          ↓
                   Operator review
                          ↓
                      Execution
```

### Cardinality

One invocation per binder version. If material corrections produce a new binder version (via rewind + regeneration), synthesis may be re-run on the new version. There is never "synthesis per document" or "synthesis per WP" within the pipeline.

### Core Principles

1. **Delta, not replacement.** Synthesis proposes changes to the binder. It does not rewrite documents or re-plan the project.

2. **Two output lanes.** Mechanical findings produce executable actions. Judgment findings produce questions for the operator. These lanes never mix.

3. **Restricted action set.** Synthesis may only propose actions from a fixed set. No free-form "improvements."

4. **Every action has a post-condition.** If an action can't be mechanically verified, it is not an action — it is a question.

5. **Operator decides.** Synthesis proposes. The operator accepts, rejects, or modifies. No auto-execution.

6. **Workflow-admin simple.** One workflow step, one entry point, one output shape. No per-project configuration, no branching paths, no configurable action types beyond the fixed set.

---

## Synthesis Workflow

### Structure

Two independent LLM instances analyze the same binder, producing findings independently. A mechanical comparison step classifies agreement. The operator reviews the result.

```
Binder (full)
     │
     ├──→ Instance A: Analyze → Findings A
     │
     ├──→ Instance B: Analyze → Findings B
     │
     └──→ MECHANICAL: Compare
              │
              ├─ Agreement (both flagged) → high confidence
              ├─ Disagreement (one flagged) → lower confidence
              └─ Neither flagged → no synthesis finding emitted
              │
         MECHANICAL: Classify each finding
              │
              ├─ Mechanical → propose action (DSL)
              └─ Judgment → emit question (operator-routed)
              │
         Output: Synthesis Delta
              │
         OPERATOR: Accept / Reject / Modify
```

### Scoped Memory (ADR-040 Exception)

Within the synthesis step, LLM calls share structured state — specifically, the findings from prior calls. This is consistent with ADR-040's intent: continuity from structured state, not transcripts. The shared state is:

- The binder content (input)
- Structured findings (output of analysis calls)

Not shared:
- Raw conversation transcripts
- Prior assistant responses
- Accumulated message history

Memory is discarded when the synthesis step completes.

### Dual Instance

Two independent Anthropic instances analyze the binder. Independence means:

- Separate API calls, no shared context between instances
- Each receives the full binder and the same analysis prompt
- Findings are compared mechanically after both complete

Agreement/disagreement is a confidence signal, not a vote. The operator sees both and decides.

Comparison uses canonical finding normalization (matching on artifact IDs and finding type) before agreement scoring. Two instances may describe the same problem at different granularity — normalization prevents undercounting agreement.

---

## Restricted Action Set

Synthesis may propose **only** these action types:

| Action | What It Does | Example Post-Condition |
|--------|-------------|----------------------|
| `MERGE_WS` | Combine overlapping WSs into one | `count(ws_id in targets) == 0 AND exists(merged_ws_id)` |
| `SPLIT_WS` | Decompose a WS mixing concerns | `count(ws from split) == N AND original ws removed` |
| `DEFER_COMPONENT` | Mark TA component as explicitly deferred (not removed) | `component.mvp_scope == "deferred" AND component exists in TA` |
| `REMOVE_WS` | Remove a WS with no execution value | `ws_id not in binder` |
| `NORMALIZE_BOUNDARY` | Adjust scope_in, scope_out, allowed_paths, or dependency references to eliminate overlap. May not modify objective, procedure, or definition_of_done. | `overlap_score(ws_a, ws_b) < threshold` |

**Five actions. No more.** If a finding doesn't map to one of these, it is a judgment question, not an action.

Each proposed action must include:

- `action_type` — one of the five above
- `targets` — artifact IDs affected
- `rationale` — one sentence, grounded in binder content
- `post_condition` — machine-checkable assertion

If the LLM cannot produce a valid post-condition, the finding is reclassified as a judgment question.

---

## Judgment Questions

Findings that require human judgment are emitted as questions, not actions:

| Lens | What It Asks | Example |
|------|-------------|---------|
| Platform realism | Is this platform assumption valid? | "WS-140 assumes SiriKit supports offline journal entry. Verify this is correct for the target iOS version." |
| MVP discipline | Is this scope appropriate for MVP? | "Media Reference Manager exists in TA but has no WP coverage. Should it be deferred or added?" |
| Authority hygiene | Is this component mixing concerns? | "Configuration Manager owns API keys, processing thresholds, and user preferences. Should these be separated?" |
| Execution readiness | Is this WS actually executable? | "WS-149 assumes a Search Engine exists but no prior WS creates one. Is a prerequisite missing?" |

Questions include:

- `finding_id`
- `lens` — one of the four above
- `severity` — `advisory` | `should_fix` | `blocking`
- `artifacts` — affected document IDs
- `question` — one sentence
- `confidence` — `high` (both instances flagged) | `moderate` (one instance flagged)

**Four lenses. No more.** This prevents the synthesis step from becoming an open-ended architecture review.

---

## Output Shape

Synthesis produces one artifact: the **Synthesis Delta**.

```json
{
  "project_id": "...",
  "binder_document_count": 23,
  "instance_a_finding_count": 7,
  "instance_b_finding_count": 5,
  "agreement_count": 4,
  "actions": [
    {
      "action_type": "MERGE_WS",
      "targets": ["WS-138", "WS-145"],
      "rationale": "62% scope overlap in storage operations across WP-025/WP-026",
      "post_condition": "count(ws_id in ['WS-138','WS-145']) == 0"
    }
  ],
  "questions": [
    {
      "finding_id": "F-002",
      "lens": "platform_realism",
      "severity": "should_fix",
      "artifacts": ["WS-140", "TA-001"],
      "question": "WS-140 assumes SiriKit supports offline journal entry creation. Verify this is correct for the target iOS version.",
      "confidence": "high"
    }
  ]
}
```

The operator reviews the delta and accepts, rejects, or modifies each item. Accepted mechanical actions are applied to the binder. Accepted questions become correction briefs (ADR-069) for the relevant stage.

---

## Workflow Admin Constraints

This step must remain manageable in the workflow admin:

- **One workflow node.** Synthesis is a single step, not a sub-graph.
- **No per-project configuration.** The action set and lens set are fixed. No project-specific rules.
- **No branching paths.** The workflow is linear: analyze → compare → classify → output.
- **No iterative loops.** Synthesis runs once. If the operator wants to re-run after corrections, they rewind and regenerate, then synthesis runs again on the new binder. It does not loop internally.
- **Fixed action count.** Five action types, four question lenses. These are governed in the ADR, not configurable at runtime.
- **Bounded cost.** Two full binder reads (one per instance) plus comparison. Total token cost is predictable from binder size.

---

## What This Does Not Do

- Does not rewrite documents
- Does not re-plan the project
- Does not auto-execute actions
- Does not replace the operator's judgment
- Does not guarantee a correct binder (stochastic analysis, not deterministic)
- Does not loop or iterate within the step
- Does not introduce per-project configuration

---

## Success Criteria

Synthesis is working correctly when:

1. Compositional defects like MSA-001's findings are surfaced before execution
2. Mechanical actions include verifiable post-conditions that can be checked after application
3. Judgment questions are clearly separated from mechanical actions
4. Operators report that synthesis findings are useful, not noisy
5. The step runs in a single pass without manual intervention beyond the final review
6. Total token cost per synthesis is bounded and predictable

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Synthesis becomes persuasive instead of trustworthy — operators over-trust confident-sounding findings | High | Strict separation of mechanical (verifiable) and judgment (questions only). No auto-execution. |
| Both instances agree on a wrong finding | Medium | Restricted action set limits blast radius. Operator reviews all proposed actions. |
| Synthesis step adds cost/time without improving binder quality | Medium | Measure: track how many synthesis findings operators accept vs reject. Kill the step if acceptance rate is consistently low. |
| Action DSL becomes too rigid for real findings | Low | Five actions cover the MSA-001 defect classes. If new classes emerge, add actions via ADR amendment, not runtime config. |

---

## Implementation Notes

- Synthesis is a post-binder workflow step, not a DCW node type. It operates at binder level, outside the per-document creation lifecycle.
- The dual-instance pattern may use a single API with two independent calls, or two separate API configurations
- Finding comparison is mechanical (canonical normalization then structural match on artifact IDs and finding type), not LLM-based
- The Synthesis Delta is a governed artifact with lineage, stored alongside the binder
- Accepted actions feed back into the pipeline as corrections (ADR-069) or direct mutations, depending on action type

---

*End of ADR-070*
