# Improvement Validation Record: IVR-WP-PROMPT-001

## Identification

| Field | Value |
|-------|-------|
| Record ID | IVR-WP-PROMPT-001 |
| Date | 2026-03-17 |
| Station | Work Package Generation (PM / document_generator) |
| Artifact changed | `prompt:task:work_package` |
| Version | 1.0.0 → 1.1.0 |
| Method | Replay A/B experiment via WS-PI-0B harness |
| Predecessor | IVR-WS-PROMPT-001 (validated same pattern at WS layer) |

## Constraint Addressed

Work Package generation produced outputs with empty governance_pins.policy_refs and
empty adr_refs. Root cause: the v1.0.0 task prompt used permissive language ("may be
empty array") and instructed "Do not modify the governance_pins from what the IPF
committed" — but the IPF carries no governance_pins at all. The WP generator must
**establish** governance traceability, not merely copy it.

This is an upstream defect that propagates to all downstream Work Statements. The
WS v1.1.0 prompt (IVR-WS-PROMPT-001) compensates with a safety net, but the correct
fix is establishing governance at the WP layer where it originates.

## Governance Floor Analysis

Before crafting the fix, we identified the correct governance floor per artifact type:

| Policy | Governs | Applies to WP? |
|--------|---------|-----------------|
| POL-ADR-EXEC-001 | ADR execution authorization chain | **Yes — primary** |
| POL-QA-001 | Testing & verification | Yes — all governed work |
| POL-ARCH-001 | Architectural integrity | Yes — when WP involves architecture |
| POL-WS-001 | Work Statement execution | **No — WS-specific** |
| POL-CODE-001 | Code construction | Marginal |

**Correct WP floor: POL-ADR-EXEC-001** (not POL-WS-001, which is WS-specific).

## Experiment Design

- **Control**: Original LLM run `b3225599-5f1f-407f-b302-b4f2790932b9` (APAM-002 project, WP generation node)
- **Treatment**: Replay of same run with governance floor supplement appended to prompt
- **Single variable changed**: Prompt content (appended governance rules)
- **Held constant**: Model (sonnet), temperature (0.3), max_tokens (16384), all input context

## Results

### Baseline (v1.0.0 prompt)

```json
"governance_pins": {
  "ta_version_id": "TA-v1.0-baseline",
  "adr_refs": [],
  "policy_refs": []
}
"contradiction_notes": NOT PRESENT
```

### V2 (governance floor supplement)

```json
"governance_pins": {
  "ta_version_id": "TA-2026-03-08-001",
  "adr_refs": ["ADR-009", "ADR-010"],
  "policy_refs": ["POL-ADR-EXEC-001", "POL-QA-001"]
}
"contradiction_notes": ["IPF entry lacked governance_pins - established per governance supplement requirements"]
```

### Delta

| Field | Baseline | V2 | Status |
|-------|----------|-----|--------|
| policy_refs | `[]` | `["POL-ADR-EXEC-001", "POL-QA-001"]` | Fixed |
| adr_refs | `[]` | `["ADR-009", "ADR-010"]` | Fixed |
| ta_version_id | Present | Present (refined) | Maintained |
| contradiction_notes | Absent | Present (gap disclosed) | Fixed |

## Replay Run References

| Run | ID | Purpose |
|-----|----|---------|
| Original (baseline) | `b3225599-5f1f-407f-b302-b4f2790932b9` | WP generation |
| V2 replay | `6fabc9f0-1196-455c-91b6-f66e58f0155d` | Governance floor supplement |

## Changes Made to v1.1.0 Prompt

Key changes from v1.0.0:

1. **Governance pin establishment section** — new section explaining that WP must ESTABLISH
   governance_pins (not just copy from IPF, which has none)
2. **Policy floor** — changed policy_refs from "may be empty" to "required, non-empty" with
   POL-ADR-EXEC-001 as the minimum floor (correct for WP artifact type)
3. **ADR derivation** — changed adr_refs from "SHOULD" to "MUST reference" with guidance to
   derive from TA context
4. **Removed contradictory instruction** — removed "Do not modify the governance_pins from
   what the IPF committed" (IPF has none to commit)
5. **Contradiction disclosure** — added contradiction_notes as required output field
6. **Failure conditions** — added empty policy_refs as automatic reject
7. **Self-check list** — expanded from 8 to 11 items covering new requirements

## Known Caveats

1. **Single-run sample**: Validated on one WP generation run (APAM-002). Broader validation
   across multiple projects recommended before certifying.
2. **Token metadata discrepancy**: Same discrepancy pattern as IVR-WS-PROMPT-001.
3. **No WP-specific evaluator yet**: The ws_defect_evaluator is WS-specific. A parallel
   wp_defect_evaluator would enable automated baseline measurement for WPs. Manual
   inspection was used for this IVR.
4. **Mechanical enforcement pending**: This IVR validates the prompt fix only. A mechanical
   `ensure_governance_floor()` function is planned as the next step to provide deterministic
   guarantees independent of model compliance.

## Disposition

**Validated.** The prompt change correctly establishes governance traceability at the WP layer
where it originates. Promoted to `prompt:task:work_package:1.1.0` pending certification and
manifest update.

## Governance Chain After Fix

```
IPF (no governance_pins — gap disclosed in WP contradiction_notes)
  ↓ WP v1.1.0 prompt ESTABLISHES governance floor
WP (governance_pins: { ta_version_id: ✓, policy_refs: [POL-ADR-EXEC-001, ...], adr_refs: [ADR-009, ...] })
  ↓ inherit_governance_pins() copies faithfully
WS (governance_pins: inherited + WS v1.1.0 enforces POL-WS-001 addition)
```

Both layers now active: WP establishes, WS enforces and augments.
