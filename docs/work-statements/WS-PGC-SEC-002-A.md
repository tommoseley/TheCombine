# WS-PGC-SEC-002-A: Secret Detector Calibration Spike

## Status: Complete

## Governing References

- GOV-SEC-T0-002 -- Tier-0 Secrets Handling and Ingress Control Policy
- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- combine-config/governance/secrets/
- tests/
- ops/scripts/

---

## Objective

Determine empirically validated entropy and length thresholds for the canonical secret detector. Thresholds must catch known credential formats while avoiding false positives on natural language PGC answers. Results are committed as a versioned calibration artifact.

---

## Preconditions

- GOV-SEC-T0-002 accepted

---

## Scope

### In Scope

- Build prose corpus (historical PGC answers, synthetic prose, infrastructure descriptions, structured JSON)
- Build secret corpus (AWS keys, PEM blocks, OAuth tokens, random keys, short API keys, Base64, JWTs)
- Sweep threshold combinations (length x entropy)
- Measure TPR and FPR per combination
- Document tradeoff curve
- Produce versioned calibration artifact

### Out of Scope

- Detector implementation (that is WS-PGC-SEC-002)
- HTTP middleware
- Orchestrator integration
- Separate ingress vs orchestrator thresholds (use one threshold unless empirically justified)

---

## 1. Corpus Requirements

### 1.1 Prose Corpus (Non-Secret)

- Historical PGC answers (sanitized)
- Synthetic prose approximating real user responses
- Infrastructure descriptions without secrets
- Structured JSON without credentials

Minimum corpus size: 5,000+ samples

### 1.2 Secret Corpus

Must include:

- AWS access keys (AKIA prefix)
- PEM blocks (RSA, EC)
- OAuth tokens
- Randomly generated 128-512 bit keys
- Short API keys (20-40 chars)
- Base64-encoded secrets
- JWTs

Must include both long secrets and short secrets.

---

## 2. Methodology

For each candidate threshold combination:

- Length threshold: 20, 24, 28, 32
- Entropy threshold: 3.5, 4.0, 4.2, 4.5, 5.0

Measure:

- True Positive Rate (TPR) -- percentage of secrets correctly detected
- False Positive Rate (FPR) -- percentage of prose incorrectly flagged

Document:

- Missed secret classes per threshold
- False positive patterns per threshold
- Tradeoff curve (TPR vs FPR)

---

## 3. Output Artifact

Produce calibration artifact:

```json
{
  "detector_version": "v1",
  "length_threshold": 28,
  "entropy_threshold": 4.2,
  "expected_tpr": 0.997,
  "expected_fpr": 0.002,
  "calibration_corpus_hash": "<sha256>",
  "date": "YYYY-MM-DD"
}
```

Committed to:

`combine-config/governance/secrets/detector_calibration.v1.json`

---

## 4. Design Constraint

Do not tune ingress and orchestrator thresholds separately unless divergence is justified empirically.

If separate thresholds are used:

- Document why
- Both thresholds must be versioned
- Both must be tested independently

Otherwise, use one threshold.

---

## 5. Known Limitations

Entropy detection is weaker against:

- Human-chosen passwords (e.g., "Summer2024!")
- Poorly generated keys
- Secrets embedded inside sentences

These limitations are accepted. They are mitigated by:

- Format accelerators (PEM, known patterns)
- Stabilization gate (second scan opportunity)
- Dual boundary architecture (ingress + orchestrator)

Security via layered defense, not a magic threshold.

---

## Tier 1 Verification Criteria

1. **Prose corpus meets minimum size**: Corpus contains >= 5,000 non-secret samples
2. **Secret corpus covers all required types**: AWS, PEM, OAuth, random, short, Base64, JWT all represented
3. **Threshold sweep complete**: All length x entropy combinations tested
4. **TPR meets target**: Selected threshold achieves >= 99% TPR on secret corpus
5. **FPR meets target**: Selected threshold achieves <= 1% FPR on prose corpus
6. **Short API keys caught**: Selected threshold detects 20-40 char API keys
7. **Calibration artifact valid**: Output JSON matches schema with all required fields
8. **Corpus hash recorded**: Calibration artifact contains SHA-256 of the corpus used

---

## Procedure

### Phase 1: Build Corpora

1. Collect and sanitize historical PGC answers (or generate synthetic equivalents)
2. Generate prose samples covering infrastructure descriptions, JSON payloads, natural conversation
3. Generate secret samples across all required types and lengths
4. Verify corpus sizes meet minimums

### Phase 2: Sweep

1. Implement threshold sweep script (can be standalone, does not need to integrate with Combine runtime)
2. Run all length x entropy combinations against both corpora
3. Record TPR, FPR, missed classes, false positive patterns per combination

### Phase 3: Select and Document

1. Select threshold combination that meets TPR >= 99% and FPR <= 1%
2. If no single threshold meets both targets, document the tradeoff and recommend the best option
3. Produce calibration artifact JSON
4. Commit to `combine-config/governance/secrets/detector_calibration.v1.json`

### Phase 4: Verify

1. All Tier 1 criteria pass
2. Calibration artifact on disk and valid

---

## Prohibited Actions

- Do not hardcode thresholds without empirical justification
- Do not skip short API key testing (these are the hardest to catch)
- Do not use the secret corpus for anything other than calibration (do not persist real secrets)
- Do not implement the detector itself (that is WS-PGC-SEC-002)

---

## Verification Checklist

- [x] Prose corpus >= 5,000 samples (5,500)
- [x] Secret corpus covers all required types (26 types, 675 samples)
- [x] All threshold combinations tested (35 combinations: 5 length x 7 entropy)
- [x] TPR >= 99% on selected threshold (100% at length=20, entropy=3.0)
- [x] FPR <= 1% on selected threshold (0.00%)
- [x] Short API keys detected (100% detection rate, 20-40 char keys)
- [x] Tradeoff curve documented (calibration_sweep_results.json)
- [x] Calibration artifact committed with corpus hash
- [x] Calibration artifact matches required schema

---

_End of WS-PGC-SEC-002-A_
