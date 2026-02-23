# WS-PGC-SEC-002: Dual Gate Secret Ingress Control

## Status: Draft

## Governing References

- GOV-SEC-T0-002 -- Tier-0 Secrets Handling and Ingress Control Policy
- ADR-010 -- LLM Execution Logging
- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- combine-config/governance/
- app/api/
- app/domain/
- app/core/
- tests/

---

## Objective

Implement deterministic, dual-gate secret ingress protection using a single canonical detector module. Secrets must be caught at HTTP ingress (before persistence) and at the orchestrator Tier-0 boundary (before stabilization, rendering, and replay). Both gates invoke the same versioned detector.

---

## Preconditions

- GOV-SEC-T0-002 accepted
- WS-PGC-SEC-002-A complete (detector calibration spike -- thresholds determined empirically)
- PGC workflow nodes exist and execute through orchestrator

---

## Deliverables

1. Canonical detector module (`detector.v1`)
2. HTTP ingress middleware invoking detector
3. Orchestrator Tier-0 governance primitive invoking detector
4. PGC prompt injection mechanism (PromptAssembler)
5. Redacted logging mechanism
6. Audit metadata fields
7. Regression test suite

---

## 1. Canonical Detector

Required capabilities:

- Entropy-based detection (threshold from calibration artifact)
- Length threshold (from calibration artifact)
- Character distribution scoring
- Structured format recognition (PEM, known patterns)
- Version stamp (detector_version)

Deterministic output:

```json
{
  "verdict": "CLEAN | SECRET_DETECTED",
  "entropy_score": 4.21,
  "classification": "HIGH_ENTROPY | PEM_BLOCK | PATTERN_MATCH"
}
```

Thresholds loaded from:

`combine-config/governance/secrets/detector_calibration.v1.json`

---

## 2. HTTP Middleware

Behavior:

- Run canonical detector on raw request body
- Execute before any logging persistence
- If `verdict == SECRET_DETECTED`:
  - Abort request
  - Return HTTP 422
  - Log redacted event only: `[REDACTED_SECRET_DETECTED]`
  - Do not persist payload

Permitted log metadata:

- Request ID
- Detector version
- Entropy score
- Detection classification

---

## 3. Orchestrator Governance Primitive

Trigger points:

- PGC answer intake
- Pre-stabilization
- Pre-render (detail_html, pdf)
- Replay ingestion

If `verdict == SECRET_DETECTED`:

- Emit HARD_STOP
- Rollback transaction
- Redact logging
- Emit structured governance event
- Allow resumable correction

---

## 4. Audit Fields

Workflow metadata must record on every scan:

```json
{
  "secret_scan": {
    "detector_version": "v1",
    "verdict": "CLEAN",
    "entropy_score": 3.42
  }
}
```

If detected:

```json
{
  "secret_scan": {
    "detector_version": "v1",
    "verdict": "SECRET_DETECTED",
    "classification": "HIGH_ENTROPY"
  }
}
```

No secret value retained.

---

## 5. Injection Mechanism

PromptAssembler must:

- Detect `node.kind == "pgc"`
- Prepend Tier-0 clause from `combine-config/governance/tier0/pgc_secrets_clause.v1.txt`
- For QA nodes, prepend from `combine-config/governance/tier0/pgc_secrets_clause_qa.v1.txt`
- Record `injected_clauses` in resolved prompt metadata
- Record `resolved_prompt_hash` (SHA-256)

Injection is mandatory and non-removable.

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **HTTP ingress rejects high entropy payload**: POST with known secret format returns HTTP 422
2. **HTTP ingress does not persist rejected payload**: No DB record created for rejected request
3. **Orchestrator blocks secret in PGC answer**: Secret pasted as PGC answer triggers HARD_STOP
4. **Orchestrator blocks pre-stabilization**: Artifact containing secret blocked before commit
5. **Orchestrator blocks replay payload**: Replay with secret in content triggers HARD_STOP
6. **PGC question asking for API key triggers HARD_STOP**: LLM output requesting "please provide your API key" is caught
7. **Redacted logging verified**: Log entry contains metadata but no secret value
8. **HTML rendering blocked on secret**: detail_html render with secret in content is blocked
9. **PDF rendering blocked on secret**: pdf render with secret in content is blocked
10. **Detector version recorded in metadata**: Audit fields include detector_version on every scan
11. **Injection applied to PGC nodes**: Resolved prompt for PGC node contains Tier-0 clause
12. **Injection not applied to non-PGC nodes**: Resolved prompt for non-PGC node does not contain clause
13. **Injection cannot be disabled via Workbench**: Workbench prompt edit does not remove injected clause

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-13. Verify all fail.

### Phase 2: Implement

1. Build canonical detector module at `combine-config/governance/secrets/detector.v1`
2. Load thresholds from `detector_calibration.v1.json`
3. Build HTTP ingress middleware invoking detector
4. Build orchestrator Tier-0 governance primitive invoking detector
5. Implement PromptAssembler injection for PGC nodes
6. Implement redacted logging (detection metadata only, no secret values)
7. Add audit metadata fields to workflow execution records
8. Author Tier-0 clause files in `combine-config/governance/tier0/`

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not create separate detector implementations for ingress and orchestrator
- Do not hardcode entropy thresholds (must come from calibration artifact)
- Do not persist secret values under any circumstance including error logging
- Do not allow Workbench to modify or remove Tier-0 injected clauses
- Do not modify ADR-010 logging infrastructure (redact at the boundary, not in the logger)

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] Canonical detector built and versioned
- [ ] HTTP middleware rejects secrets before persistence
- [ ] Orchestrator HARD_STOP on secret detection
- [ ] PGC injection mechanism operational
- [ ] Redacted logging -- no secret values in any log
- [ ] Audit metadata recorded on every scan
- [ ] Clause files authored in combine-config
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-PGC-SEC-002_
