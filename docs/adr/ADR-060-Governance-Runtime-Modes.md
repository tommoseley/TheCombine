# ADR-060 — Governance Runtime Modes

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-03-19 |
| **Origin** | External critique of APAM-005 binder |

---

## 1. Problem

Binders assume execution inside a fully provisioned Combine runtime. When exported or evaluated standalone:

- Governance references non-existent scripts and paths (e.g., `ops/scripts/tier0.sh`)
- Enforcement becomes impossible outside the Combine environment
- Credibility is reduced with external evaluators who cannot verify referenced infrastructure

---

## 2. Decision

Introduce explicit governance runtime modes:

```yaml
governance_runtime:
  mode: combine_native | portable
```

### `combine_native`

- Full operational governance
- References to scripts, directories, enforcement tooling allowed
- Environment must satisfy all governance requirements
- Verification commands are executable

### `portable`

- Governance rendered as declarative constraints
- No references to non-existent infrastructure
- Enforcement expressed as:
  - Requirements ("WS execution MUST follow tests-before-implementation ordering")
  - Invariants ("All work statements MUST reference governing policies")
  - Expectations ("Verification criteria MUST be objectively checkable")
- Policies included as reference text, not operational instructions

---

## 3. Consequences

**Positive:**

- Binders become exportable and credible outside the Combine
- External critique becomes valid and actionable
- Governance adapts to execution context without losing intent

**Negative:**

- Requires dual rendering logic in binder renderer
- Introduces mode-based complexity in governance section generation

---

## 4. Follow-On Work

- WP-CMB-001 — Governance Runtime Modes implementation

---

*End of ADR-060*
