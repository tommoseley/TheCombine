# ADR-062 — Duplicate Work Detection

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-03-19 |
| **Origin** | External critique of APAM-005 binder (duplicate Alpaca auth, CSV logging) |

---

## 1. Problem

The system does not detect duplicate implementation intent across Work Statements:

- Multiple WS implement Alpaca API authentication independently (WS-002 and WS-013)
- Multiple WS implement CSV logging independently (WS-011 and WS-017)
- This violates the reuse-first principle (POL-CODE-001 Section 2)

The existing WP boundary overlap evaluator catches component-name and scope-phrase overlap between WPs, but does not detect functional duplication at the WS level.

---

## 2. Decision

Introduce duplicate WS objective detection:

- Analyze WS `scope_in` and `objective` fields across the entire binder
- Identify semantically overlapping objectives using mechanical heuristics
- Flag duplicates as advisory findings in the binder evaluation section

### Detection Approach

- Extract key action phrases from WS objectives (e.g., "implement Alpaca API authentication")
- Normalize and compare across all WS pairs
- Flag pairs where objective similarity exceeds threshold
- Report which WS should depend on or reuse the other

### Severity

- Advisory only (initial phase)
- Future: configurable enforcement per project

---

## 3. Scope

**Included:**

- WS-to-WS objective similarity detection
- WS scope_in overlap detection across WP boundaries
- Duplicate finding reporting in binder evaluation section

**Deferred:**

- Capability ownership model
- Reuse enforcement (blocking duplicate creation)
- Shared component promotion workflow
- Full capability graph

---

## 4. Consequences

**Positive:**

- Surfaces duplication early in planning phase
- Low complexity compared to full capability graph
- Improves design hygiene and reduces implementation waste
- Reinforces reuse-first principle mechanically

**Negative:**

- Heuristic-based detection (not perfect — false positives possible)
- No enforcement initially (advisory only)
- Cannot distinguish intentional duplication from accidental

---

## 5. Follow-On Work

- WP-CMB-003 — Duplicate WS Objective Detection implementation
- Future: Capability Graph & Reuse Enforcement (if heuristic detection proves insufficient)

---

*End of ADR-062*
