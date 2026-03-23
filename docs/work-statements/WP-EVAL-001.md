# WP-EVAL-001 — Evaluator Calibration + TA Component Registry + PGC Authority Capture

**Status:** Draft
**Date:** 2026-03-23
**Governing ADR:** ADR-061 (Cross-Layer Contradiction Detection), ADR-064 (Durable Authority Context)
**Priority:** HIGH — evaluator trust is prerequisite for governance automation

## Objective

Fix the judge, strengthen the spec, tighten the intake. Three bounded improvements that make the binder validation pipeline trustworthy:

1. **CLDR-003 component extraction** produces false positives by matching procedure verbs and articles as component references. Fix the extractor so findings are trustworthy.
2. **TA schema** lacks component ownership paths. WSs reference components but there's no machine-readable mapping of component → code paths. Add it.
3. **PGC questions** for domain projects don't pin concrete decision parameters (thresholds, scoring weights). These should be captured as durable authority, not left as "configurable."

## Scope

### In Scope
- Cross-layer evaluator component extraction calibration (CLDR-003)
- TA output schema enrichment with optional `owns` field per component
- TA prompt adjustment to instruct LLM to populate ownership paths
- PGC context improvement for domain-parameter capture

### Out of Scope
- New evaluator rules beyond CLDR-003 calibration
- CLDR-001 or CLDR-002 changes
- Ontology leakage evaluator changes (separate concern)
- WP overlap evaluator changes
- Full prompt version bumps (minimal contract tuning only for TA)

## Work Statements

| WS ID | Title | Order | Dependencies |
|-------|-------|-------|--------------|
| WS-EVAL-001 | Cross-Layer Evaluator Component Extraction Calibration | a0 | None |
| WS-EVAL-002 | TA Component Registry Schema Enrichment | a1 | None |
| WS-EVAL-003 | PGC Decision-Parameter Authority Capture | a2 | None |

**Parallelism:** All three are independent. They touch different files and can execute in parallel.

## Verification Criteria
- CLDR-003 findings for APAM-005 drop from 38 to a reasonable count (< 5 true positives)
- TA schema accepts optional `owns` field per component
- Re-running the binder evaluator produces only actionable findings
- All existing evaluator tests still pass
- Tier 0 passes

## Allowed Paths
- app/domain/services/cross_layer_evaluator.py
- combine-config/document_types/technical_architecture/
- combine-config/prompts/tasks/technical_architecture/
- tests/tier1/test_cross_layer_evaluator.py
- tests/tier1/

## Governance Decision

PGC context files and TA prompts are governed prompt fragments (ADR-045). WS-EVAL-002 and WS-EVAL-003 change what the LLM produces — these are behavioral enrichments, not cosmetic edits. Both require version bumps, re-certification, and manifest updates per seed governance rules.

## Prohibited Actions
- Do not modify CLDR-001 or CLDR-002 rules
- Do not modify ontology evaluator or WP overlap evaluator

---

_End of WP-EVAL-001_
