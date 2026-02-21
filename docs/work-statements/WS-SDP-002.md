# WS-SDP-002: Align UI and Execution Affordances to ADR-053

## Status: Accepted

## Governing References

- ADR-053 -- Planning Before Architecture in Software Product Development
- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- spa/src/
- tests/

---

## Purpose

Reflect new canonical order (Discovery -> IPP -> IPF -> TA -> WPs) in UI and execution flow.

---

## Scope

### In Scope

- SPA document flow hints
- Button ordering / sequencing if needed
- Minor UX copy updates
- Ensure UI surfaces IPF completion before TA
- Ensure "Start Production" affordance does not imply TA precedes IPF
- Update any instructional text referencing previous order

### Out of Scope

- TA gating enforcement
- Staleness propagation logic
- Conflict detection automation

---

## Tier 1 Verification Criteria

1. **User flow matches canonical order**: UI presents documents in Discovery -> IPP -> IPF -> TA sequence
2. **No UI suggests TA precedes IPF**: No button labels, flow hints, or instructional text implies TA before IPF
3. **No broken links or missing transitions**: Navigation between document stages works

---

## Procedure

### Phase 1: Audit

Review SPA components for references to previous ordering (TA before IPF, Epic-era flow hints).

### Phase 2: Implement

Update any components, labels, or flow hints to reflect ADR-053 canonical order.

### Phase 3: Verify

1. All Tier 1 criteria met
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not implement TA gating logic
- Do not add staleness propagation
- Do not modify workflow definitions (that is WS-SDP-001)
- Do not modify handlers or prompts

---

## Verification Checklist

- [ ] UI presents documents in canonical order
- [ ] No UI element suggests TA precedes IPF
- [ ] No broken navigation
- [ ] Tier 0 returns zero

---

## Expected Blast Radius

Low. UX copy and ordering only.

---

_End of WS-SDP-002_
