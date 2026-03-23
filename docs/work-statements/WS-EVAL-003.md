# WS-EVAL-003: PGC Decision-Parameter Authority Capture

## Status: Draft

## Parent Work Package: WP-EVAL-001

## Governing References

- ADR-064 -- Durable Authority Context

## Verification Mode: A

## Allowed Paths

- combine-config/document_types/technical_architecture/
- combine-config/document_types/project_discovery/
- tests/tier1/

---

## Objective

Improve PGC context for Project Discovery and Technical Architecture document types so that concrete decision parameters (thresholds, scoring weights, algorithm choices, configuration values) are captured as PGC answers and persisted as durable authority records. Currently, decision parameters like RSI thresholds, MACD interpretation rules, and scoring weights emerge inside WS prose as "configurable" — they should be pinned upstream as project authority.

---

## Preconditions

- WP-AUTH-001 complete (authority records persist PGC answers)
- PGC context files exist per document type in combine-config/document_types/{type}/releases/{version}/prompts/pgc_context.prompt.txt
- PGC questions are generated dynamically from context blocks

---

## Scope

### In Scope

- Enrich Project Discovery `pgc_context.prompt.txt` to instruct the LLM to ask about concrete decision parameters when the project involves algorithms, scoring logic, or configurable thresholds
- Enrich Technical Architecture `pgc_context.prompt.txt` to instruct the LLM to ask about implementation-critical parameters (indicator settings, scoring rules, threshold values) so they become TA authority
- Add guidance text: "If the project involves algorithms or decision logic, ask for the specific parameters, thresholds, and rules that govern those decisions. These become binding project authority."
- Test that PGC context contains the new guidance

### Out of Scope

- Modifying the clarification_questions_generator task prompt
- Creating new document types
- Modifying authority service code (already handles pgc_answer persistence)
- Retroactively fixing APAM-005's missing parameters

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **PD pgc_context contains decision parameter guidance**: Project Discovery pgc_context.prompt.txt contains instruction to ask about decision parameters and algorithmic thresholds
2. **TA pgc_context contains decision parameter guidance**: Technical Architecture pgc_context.prompt.txt contains instruction to ask about implementation-critical parameters
3. **Guidance references authority**: context text mentions that answers become "binding project authority" or equivalent

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests that read the pgc_context files and assert the decision-parameter guidance text is present. Verify they fail.

### Phase 2: Implement

1. In `combine-config/document_types/project_discovery/releases/1.4.0/prompts/pgc_context.prompt.txt`:
   - Add a section under "Questions Asked Here Must":
     ```
     If the project involves algorithms, scoring logic, decision rules, or configurable thresholds:
     * Ask for the specific parameters, thresholds, and rules that govern those decisions
     * Ask for concrete values, not "configurable" — these become binding project authority
     * Examples: indicator periods (RSI 14-day), scoring thresholds (buy > 0.6), position limits (30% cap)
     ```

2. In `combine-config/document_types/technical_architecture/releases/1.0.0/prompts/pgc_context.prompt.txt`:
   - Add a section:
     ```
     If the system involves decision logic or configurable parameters:
     * Ask for the exact algorithm parameters, scoring weights, and threshold values
     * These answers become binding technical authority for downstream Work Statements
     * Do not leave algorithmic parameters as "configurable" — pin them here
     ```

### Phase 3: Verify

1. All new tests pass
2. Tier 0 returns zero

---

## Governance Note

PGC context files are governed prompt fragments (ADR-045). Adding decision-parameter guidance changes what questions the LLM asks — this is behavioral. Per seed governance rules, this requires version bumps on the affected pgc_context files, re-certification, and manifest update.

- PD pgc_context: 1.4.0 → 1.5.0
- TA pgc_context: 1.0.0 → 1.1.0

## Prohibited Actions

- Do not modify the clarification_questions_generator task prompt
- Do not create new document types
- Do not modify authority service code

---

## Verification Checklist

- [ ] PD pgc_context contains decision-parameter guidance
- [ ] TA pgc_context contains decision-parameter guidance
- [ ] Guidance references binding authority
- [ ] All existing tests pass
- [ ] Tier 0 returns zero

---

_End of WS-EVAL-003_
