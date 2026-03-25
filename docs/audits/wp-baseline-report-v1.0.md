# WP Baseline Report v1.0

**Date:** 2026-03-18
**Prompt Version:** 1.1.0 (governance-supplemented)
**Model:** claude-sonnet-4-20250514
**Evaluator:** wp_defect_evaluator v1.0
**Post-processing:** apply_post_processing (governance floor active)

---

## Dataset

5 synthetic scenarios with intentional variation:

| ID | Label | Scope | Complexity |
|----|-------|-------|-----------|
| WP-SIMPLE-001 | Simple single-feature | Auth module | Low |
| WP-MODERATE-002 | Moderate multi-WS | REST API layer | Medium |
| WP-COMPLEX-003 | Complex multi-phase | DB migration + multi-tenancy | High |
| WP-AMBIGUOUS-004 | Ambiguous requirements | "Improve UX" | Low (vague) |
| WP-CONSTRAINED-005 | Highly constrained | Secret management + SOC-2 | High (governance-heavy) |

All scenarios stored in `ops/scripts/wp_baseline_runner.py` as fixed dataset.

---

## Execution Summary

| Metric | Value |
|--------|-------|
| Total runs | 5 |
| Successful | 5 |
| Failed | 0 |
| Input tokens | 14,744 |
| Output tokens | 1,710 |
| Total tokens | 16,454 |

---

## Defect Distribution

| Check | Pass | Fail | Advisory | N/E | Fail% |
|-------|------|------|----------|-----|-------|
| governance_pins_populated | 5 | 0 | 0 | 0 | 0% |
| required_sections_present | 5 | 0 | 0 | 0 | 0% |
| policy_floor_present | 5 | 0 | 0 | 0 | 0% |
| contradiction_disclosure_present | 0 | 0 | 0 | 5 | 0% |
| ws_index_present | 0 | 0 | 5 | 0 | 0% |

**Average defects per WP: 0.0**
**Total defects: 0**

---

## Governance Quality (Detail)

The model populated `policy_refs` with contextually appropriate policies beyond the floor:

| Scenario | policy_refs |
|----------|------------|
| WP-SIMPLE-001 | POL-ADR-EXEC-001, POL-QA-001 |
| WP-MODERATE-002 | POL-ADR-EXEC-001, POL-CODE-001, POL-QA-001 |
| WP-COMPLEX-003 | POL-ADR-EXEC-001, POL-ARCH-001, POL-QA-001 |
| WP-AMBIGUOUS-004 | POL-ADR-EXEC-001 |
| WP-CONSTRAINED-005 | POL-ADR-EXEC-001, GOV-SEC-T0-002, POL-QA-001, POL-ARCH-001 |

The model correctly identified domain-specific policies (GOV-SEC-T0-002 for security, POL-ARCH-001 for architecture-heavy work, POL-CODE-001 for API construction).

---

## Non-Defect Observations

### contradiction_notes (not_evaluable)
All 5 runs produced `contradiction_notes: []` — the field exists but is empty. The model considered contradictions but found none (reasonable given synthetic inputs with no conflicting requirements). The evaluator classifies empty arrays as `not_evaluable`; this could be refined to `pass` for field-present-but-empty.

### ws_index (advisory)
All 5 runs have no `ws_index` — expected since these are generation-only runs. WS creation happens downstream in the pipeline.

---

## Comparison: Pre-v1.1.0 vs Post-v1.1.0

| Check | APAM-002 (v1.0.0) | Baseline (v1.1.0) |
|-------|-------------------|-------------------|
| governance_pins_populated | FAIL (empty) | 5/5 PASS |
| policy_floor_present | FAIL (empty) | 5/5 PASS |
| required_sections_present | PASS | 5/5 PASS |
| contradiction_disclosure_present | not_evaluable | 5/5 not_evaluable |
| ws_index_present | advisory | 5/5 advisory |

---

## Conclusion

The v1.1.0 prompt + mechanical governance floor produces **zero structural defects** across all 5 scenarios. The governance layer is working as designed:
- Layer 1 (prompt) produces contextually rich policy references
- Layer 2 (mechanical floor) guarantees POL-ADR-EXEC-001 minimum

### Top Defect Class for Next Improvement
No structural defects remain. The next improvement targets are:
1. **contradiction_disclosure refinement** — refine evaluator to distinguish "field present, empty" (pass) from "field absent" (not_evaluable)
2. **Semantic quality checks** — extend evaluator with objective clarity, scope specificity, rationale grounding (requires new check types, not structural)
3. **Cross-scenario consistency** — the ambiguous scenario (WP-AMBIGUOUS-004) produced minimal but valid output; quality improvement for vague inputs is a prompt tuning opportunity

---

## Reproducibility

```bash
cd ~/dev/TheCombine
python3 ops/scripts/wp_baseline_runner.py
```

Dataset is fixed in `ops/scripts/wp_baseline_runner.py`. Results in `docs/audits/wp-baseline-v1.0.json`.
