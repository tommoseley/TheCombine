# ADR-061 — Cross-Layer Contradiction Detection

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-03-19 |
| **Origin** | External critique of APAM-005 binder (CSV vs SQLite drift) |

---

## 1. Problem

Decisions made at higher layers (PD, TA) are not enforced downstream:

- PD selected CSV persistence
- TA introduced SQLite as primary store
- WS layer implemented both inconsistently

There is no mechanism to detect contradictions across artifact layers. This produces confusion during execution — an implementer encounters contradictory instructions with no clear authority.

---

## 2. Decision

Introduce a lightweight cross-layer contradiction detection evaluator:

- Extract key decisions from TA (the authoritative architecture layer)
- Scan WS content for implementations that contradict TA decisions
- Flag contradictions as findings in the binder evaluation section

### Detection Targets (Initial)

| Category | Example |
|----------|---------|
| Technology mismatch | WS implements CSV persistence when TA specifies SQLite |
| Schema mismatch | WS scope-in references fields not in TA data model |
| Component mismatch | WS creates a component not declared in TA |
| Dependency mismatch | WS ordering contradicts IP dependency declarations |

### Severity

- **Phase 1**: Advisory (findings reported, not blocking)
- **Phase 2** (future): Configurable — advisory or HARD_STOP per project

---

## 3. Scope

**Included:**

- TA → WS contradiction detection
- Technology/persistence mismatch detection
- Schema vs implementation mismatch detection
- WP ordering vs IP dependency chain validation

**Deferred:**

- Full decision registry with override tracking
- Binding enforcement with explicit override declarations
- PD → TA reconciliation (TA is treated as authoritative)

---

## 4. Consequences

**Positive:**

- Immediate detection of decision drift (e.g., CSV vs SQLite)
- Low implementation complexity (evaluator pattern, no new infrastructure)
- High practical value — catches the exact class of defect found in APAM-005

**Negative:**

- Partial solution (does not reconcile, only detects)
- May produce false positives when WS legitimately extends beyond TA
- Requires TA to be sufficiently detailed to serve as authority

---

## 5. Follow-On Work

- WP-CMB-002 — Cross-Layer Contradiction Evaluator implementation
- Future: Full Cross-Layer Decision Registry (CLDR) if detection proves insufficient

---

*End of ADR-061*
