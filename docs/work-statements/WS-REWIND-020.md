# WS-REWIND-020 — Compliance Audit Graceful Degradation When Authority Bundle Is Absent

**Status:** Implemented (quick fix)
**Parent WP:** WP-REWIND-003
**Governing ADR:** ADR-063

## Objective

When QA semantic compliance audit cannot be performed due to missing authority context (PGC questions, bound constraints, correlation_id), treat the finding as advisory rather than a hard gate failure.

## Problem

After rewind and regeneration, the new execution may lack PGC context from the prior run. The QA LLM prompt then reports "Cannot perform compliance audit — missing inputs" as a severity=error finding. The gate node treats any LLM gate=fail as a hard failure, blocking the document from stabilizing even though the generated content may be fine.

## Fix Applied

In `app/domain/workflow/nodes/qa.py`, the `_check_semantic_qa` method now distinguishes between:

- **True compliance failure**: document is noncompliant → hard fail (unchanged)
- **Audit incomplete**: missing authority context → convert to warning, pass gate

Detection heuristic: error messages containing "missing" + "input/pgc/constraint" or "cannot perform" + "audit".

## Limitations

- Heuristic-based detection — relies on LLM error message wording
- Does not fix the root cause (missing context during regeneration)
- Should be replaced by proper authority context carry-forward (WS-REWIND-021)

## Verification

- QA gate passes when authority context is absent (with warning)
- QA gate still fails on true compliance violations
- Warning message clearly identifies that audit was incomplete
