# ADR-066 — TA Consumes IP as Authoritative Decomposition Context

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-03-28 |
| **Origin** | APAM-003 investigation — TA/IP divergence and WP ownership overlap |
| **Contributors** | Tom, Claude, ChatGPT |

---

## 1. Context

The Combine currently models:

- `PD → IP`
- `PD → TA`

Where:

- **IP** (Implementation Plan) defines work decomposition into Work Package Candidates (WPCs)
- **TA** (Technical Architecture) defines system components and responsibilities

These are generated independently from PD.

### Observed Failure

This independence creates structural misalignment:

- TA components do not reflect IP-defined boundaries
- WPs (derived from IP) and WSs (derived against TA) overlap or duplicate responsibilities
- Ownership conflicts emerge (e.g., safety, sizing, logging, config)
- Cross-layer evaluators detect symptoms, but not root cause

From APAM-003:

- IP v6 produced clean WPC decomposition (6 candidates)
- TA produced valid components (10 components)
- But the two were not aligned by construction
- DB WPCs were from IP v1 (never re-imported after 5 IP regenerations)

### Root Issue

TA and IP are parallel planners with no shared contract.

---

## 2. Decision

**TA MUST consume IP as authoritative decomposition context.**

The pipeline is redefined as:

```
PD → IP → TA → WP → WS
```

TA now receives:

- Project Discovery (PD)
- Accepted Implementation Plan (IP)

---

## 3. Architectural Principle

**IP defines responsibility boundaries. TA must be compatible with those boundaries.**

- TA is no longer a free-form planner
- It is a refinement layer constrained by IP

---

## 4. Rules

### 4.1 Input Contract

TA workflow `requires_inputs` MUST include `implementation_plan`.

TA prompt assembly MUST include the IP artifact with WPC list (IDs, titles, scope_in/scope_out, dependencies).

TA must not be generated from PD alone.

### 4.2 Compatibility Requirement

TA output MUST be compatible with IP decomposition:

TA **must not:**
- Merge unrelated WPC responsibilities into a single opaque component
- Split a WPC across components in a way that obscures ownership
- Introduce cross-cutting ownership that violates IP boundaries
- Silently redefine or ignore IP boundaries

TA **may:**
- Refine internal structure within a WPC boundary
- Define shared infrastructure components (e.g., logging, config) consistent with IP scope
- Define components that support multiple WPCs if responsibilities remain separable

### 4.3 Conflict Handling

If TA cannot cleanly align with IP:

- TA MUST surface the issue via `open_questions`
- TA MUST NOT silently adjust boundaries

### 4.4 Ownership Traceability

TA components SHOULD expose `owns[]` aligned to IP responsibilities where possible.

Future enhancement: explicit `supports_wpc_ids[]` mapping.

---

## 5. Non-Goals

This ADR does **not** require:

- 1:1 mapping between WPCs and TA components
- TA to mirror IP structure exactly
- Elimination of shared components

This ADR enforces **compatibility**, not rigidity.

---

## 6. Consequences

**Positive:**
- Eliminates structural cause of WP/WS duplication
- Aligns decomposition (IP) with implementation structure (TA)
- Improves determinism of downstream generation
- Reduces reliance on evaluators to detect misalignment after the fact

**Negative:**
- TA becomes more constrained
- Prompt complexity increases slightly
- Existing TA artifacts may need regeneration

---

## 7. Alternatives Considered

| Alternative | Decision |
|-------------|----------|
| Keep TA independent | Rejected — proven to produce structural misalignment |
| Merge IP and TA into single stage | Rejected — loses separation of concerns |
| Post-hoc alignment via evaluators only | Rejected — reactive, not preventative |

---

## 8. Implementation

- Update TA workflow: `requires_inputs = ['project_discovery', 'implementation_plan']`
- Create TA task prompt v1.4.0 with IP boundary rules
- Update `active_releases.json` to reference new versions
- Verify prompt assembly passes correct IP document

### Recommended Follow-ons

- Certification rule: TA-IP-COMPAT-001
- Lineage fields: TA → source IP version
- Update CLDR to leverage TA/IP alignment

---

## 9. Relationships

| ADR | Relationship |
|-----|-------------|
| ADR-049 | No black boxes — TA composition must be explicit |
| ADR-058 | Two-layer enforcement — evaluator + prompt |
| ADR-063 | Pipeline rewind — IP rewind now cascades to WPCs |

---

## 10. Summary

TA is no longer a parallel planner. It is a constrained architectural refinement of IP.

This restores a single authoritative decomposition path through the Combine pipeline and eliminates a major source of ownership drift.
