# WS-EVAL-001: Cross-Layer Evaluator Component Extraction Calibration

## Status: Draft

## Parent Work Package: WP-EVAL-001

## Governing References

- ADR-061 -- Cross-Layer Contradiction Detection

## Verification Mode: A

## Allowed Paths

- app/domain/services/cross_layer_evaluator.py
- tests/tier1/test_cross_layer_evaluator.py

---

## Objective

Fix the CLDR-003 component extraction regex to stop producing false positives from procedure text. The current regex `\w+(?:\s+\w+)?\s+(?:engine|service|module|...)` matches articles ("a validation service"), procedure verbs ("create scoring module"), and generic phrases ("in the service layer") as component references. This generates noise (38 false findings for APAM-005) that degrades trust in the entire validation layer.

---

## Preconditions

- cross_layer_evaluator.py exists at app/domain/services/cross_layer_evaluator.py
- 17 tests exist at tests/tier1/test_cross_layer_evaluator.py
- APAM-005 binder produced 38 CLDR-003 findings, most of which are false positives

---

## Scope

### In Scope

- Fix `_extract_component_references()` to distinguish declared component names from procedure verbs
- Add a stopword prefix filter: strip leading articles (a, an, the) and procedure verbs (create, implement, add, build, configure, set up, establish, write, use, integrate, design) before matching
- Normalize extracted references to remove stopword prefixes
- Add test cases for false-positive patterns from APAM-005 (e.g., "create scoring module", "a validation service", "in the service layer", "for API client", "all API client", "importing each module", "names configuration module")
- Verify existing true-positive tests still pass

### Out of Scope

- CLDR-001 (schema field mismatches) changes
- CLDR-002 (persistence contradictions) changes
- Adding new evaluator rules
- Ontology evaluator changes

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **Stopword prefix stripped**: "create scoring module" does NOT produce a component reference (the verb "create" is stripped, "scoring module" is checked against TA)
2. **Article prefix stripped**: "a validation service" does NOT produce `a_validation_service` (the article "a" is stripped)
3. **Preposition prefix stripped**: "in the service layer" does NOT produce `in_the_service`
4. **True positives preserved**: "Email Notification Service" still produces `email_notification_service` when it's a genuine undeclared component
5. **APAM-005 noise reduction**: the specific false patterns from APAM-005 ("importing_each_module", "create_configuration_module", "names_configuration_module", "management_utility_module", "all_decision_engine", "for_api_client") are NOT extracted as component references
6. **Existing tests pass**: all 17 existing tests remain green

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests for criteria 1-5 using the false-positive patterns from APAM-005. Verify they fail (i.e., current extractor incorrectly produces these as component references).

### Phase 2: Implement

1. In `_extract_component_references()`, add a stopword prefix filter:
   - Define `PROCEDURE_VERBS`: create, implement, add, build, configure, set, establish, write, use, integrate, design, install, import, importing, names, all, for, from, with, in, the, a, an, and, each, of
   - After regex match, split the captured group into words
   - Strip leading words that appear in PROCEDURE_VERBS
   - If the remaining text still ends with a component suffix (engine, service, module, etc.) AND has at least one non-stopword before the suffix, keep it
   - Otherwise discard the match

2. Alternatively, tighten the regex to require the word before the suffix to NOT be a stopword:
   - Replace `\w+(?:\s+\w+)?` with a pattern that excludes known stopwords in the leading position

3. Extend the existing blacklist (currently only "error_handler", "file_manager", "log") with additional generic patterns if needed

### Phase 3: Verify

1. All new tests pass (false positives eliminated)
2. All 17 existing tests still pass
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify CLDR-001 or CLDR-002 rules
- Do not change how TA components are extracted from TA documents
- Do not modify the evaluator invocation in projects.py
- Do not remove the CLDR-003 rule entirely

---

## Verification Checklist

- [ ] All new tests fail before implementation
- [ ] Stopword prefix filter implemented
- [ ] APAM-005 false positive patterns eliminated
- [ ] True positive detection preserved
- [ ] All 17 existing tests pass
- [ ] All new tests pass
- [ ] Tier 0 returns zero

---

_End of WS-EVAL-001_
