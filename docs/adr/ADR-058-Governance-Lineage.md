# ADR-058: Governance Lineage

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-03-18 |
| **Decision Owner** | Product Owner |
| **Applies To** | All document types in the production pipeline |
| **Related Artifacts** | POL-ADR-EXEC-001, POL-WS-001, ADR-052, ADR-045 |

---

## 1. Context

The Combine's production pipeline creates documents in sequence: IPF -> PD -> TA -> IP -> WP -> WS. Each document may carry governance metadata (`governance_pins`) that downstream artifacts inherit and augment.

During the WS prompt improvement experiment (Iteration 0b/1b, 2026-03-18), we observed that:

- The WP generator produced artifacts with `policy_refs: []` and `adr_refs: []`
- The WS generator inherited these empty pins and produced Work Statements with no governance grounding
- A v1.1.0 WS prompt supplement compensated by inferring governance rules, reducing defects from 7 to 0
- However, this created **derived governance** (inferred by downstream prompt) rather than **inherited governance** (propagated from upstream artifact)

Derived governance is a valid safety net. It is not a valid primary mechanism.

---

## 2. Decision

**Governance lineage may originate at different artifact boundaries. Where upstream artifacts do not carry governance pins, the first governed artifact in the chain must establish the governance floor, and downstream artifacts must inherit and/or augment it according to artifact-type policy.**

### Rules

1. **Each artifact type has a governance floor** — a minimum set of policy references that MUST be present on every produced instance of that type.

2. **Governance floors are artifact-type-specific** — WPs require `POL-ADR-EXEC-001` (authorization chain). WSs require `POL-WS-001` (execution discipline). Applying the wrong floor to the wrong type is a defect.

3. **Enforcement is two-layered:**
   - **Layer 1 (Prompt):** The generation prompt instructs the LLM to populate governance pins correctly. This is the primary mechanism.
   - **Layer 2 (Mechanical):** `ensure_governance_floor()` runs deterministically after handler output, before persistence. If the LLM omitted the floor policy, this layer injects it. This is the safety net.

4. **Downstream artifacts inherit upstream governance** — When a WS is created from a WP, it inherits the WP's `governance_pins` via `inherit_governance_pins()`, then the WS floor is applied on top.

5. **Governance origin matters** — Inherited governance (from upstream) is preferred over inferred governance (from downstream prompt). Both are valid, but a system that relies primarily on inference is fragile.

---

## 3. Governance Floor Registry

| Artifact Type | Floor Policy | Rationale |
|---------------|-------------|-----------|
| `work_package` | `POL-ADR-EXEC-001` | Every WP exists because of the ADR execution authorization chain |
| `work_statement` | `POL-WS-001` | Every WS is governed by WS execution discipline |

Additional artifact types may be added as they become governed.

---

## 4. Implementation

- **Floor function:** `ensure_governance_floor(data, artifact_type)` in `app/domain/services/work_statement_registration.py`
- **Post-processing wrapper:** `apply_post_processing(data, doc_type_id)` in `app/domain/services/document_builder_pure.py`
- **Wiring:** Called in `DocumentBuilder.build()`, `DocumentBuilder.build_stream()`, and `DocumentBuilder._create_child_documents()` — three call sites, zero bypass paths
- **Tests:** `tests/tier1/test_governance_floor.py` (pure function), `tests/tier1/services/test_document_builder_post_processing.py` (wiring)

---

## 5. Consequences

- Every WP and WS persisted to the database is guaranteed to have at least its floor policy in `governance_pins.policy_refs`
- LLM prompt improvements are additive — they produce better artifacts, but the floor catches omissions
- Future evaluator checks can distinguish `governance_origin: inherited_from_input` vs `inferred_by_prompt` to track upstream completeness over time
- The governance floor registry (`_GOVERNANCE_FLOORS`) is the single source of truth for minimum policy requirements per artifact type

---

## 6. Validation Evidence

| Metric | Baseline (v1.0.0) | After (v1.1.0 + floor) |
|--------|-------------------|------------------------|
| WS governance_pins failures | 4/4 (100%) | 0/4 (0%) |
| WS required_sections failures | 4/4 (100%) | 0/4 (0%) |
| WS tests_before_implementation failures | 3/4 (75%) | 0/4 (0%) |
| Total defects | 7 | 0 |

Measured via replay harness against APAM-002 WS generation run `80333cde-9cf5-4b13-baa6-128b88122ef9`.
