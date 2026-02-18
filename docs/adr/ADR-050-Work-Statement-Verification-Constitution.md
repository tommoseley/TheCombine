# ADR-050 -- Work Statement Verification Constitution

**Status:** Accepted
**Date:** 2026-02-18
**Accepted:** 2026-02-18
**Decision Type:** Governance / Policy

**Related ADRs:**
- ADR-047 -- Mechanical Operations
- ADR-049 -- No Black Boxes: Explicit DCW Composition

**Related Policies:**
- POL-WS-001 -- Standard Work Statements

---

## 1. Context

The Combine is transitioning from document generation to governed execution. Work Statements (POL-WS-001) are the atomic unit of execution -- explicit, step-ordered, mechanically followable procedures.

LLM-based execution introduces **capability drift**: an agent may confidently produce implementations that appear correct but subtly violate intent. Unlike human developers who stall when confused, LLMs simulate competence. A plausible-looking implementation that does not satisfy intent is worse than a visible failure.

To operate as a production system rather than an assisted development tool, the Combine requires:

- **Deterministic verification** -- postconditions that are mechanically checkable
- **Independent encoding of intent** -- tests derived from criteria, not from implementation
- **Mechanical enforcement of constraints** -- Tier 0 baseline that catches collateral damage
- **Measurable automation maturity** -- distinguishing factory operation from assisted development

Without mechanical verification, the factory produces papier-mache: output that looks correct and passes casual inspection but collapses under load.

---

## 2. Decision

The Combine adopts the **Work Statement Verification Constitution**:

1. **Mode A** is the default: every Work Statement requires mechanical verification
2. **Mode B** is a narrow, tracked exception for inherently subjective transitions
3. **Verification is tiered**: Tier 0 (mandatory baseline) + Tier 1 (WS-specific postconditions)
4. **Tests encode intent, not implementation**: the Test-First Rule
5. **Mode B usage is instrumented**: B-rate is a factory health indicator

This policy applies globally to all Combine-managed projects. Verification is not project-optional.

---

## 3. Mode A -- Mechanical Verification (Default)

All Work Statements MUST:

1. Include explicit **Tier 1 verification criteria** that are machine-testable
2. Require tests derived from those criteria to be **written before implementation**
3. Require **Tier 0 baseline checks** to pass after implementation
4. **Refuse execution** if failing tests cannot be written from stated criteria

A Work Statement that cannot produce failing tests from its verification criteria is **invalid**.

The inability to write a failing test is itself the test of mechanical verifiability.

---

## 4. Mode B -- Human Gate (Narrow Exception)

Mode B is permitted **only** when:

- The transition is **inherently subjective** (copy tone, UX feel, visual judgment); OR
- Mechanical verification infrastructure **does not yet exist** (temporary bootstrap)

Mode B requires:

| Field | Purpose |
|-------|---------|
| `verification_mode = B` | Explicit marking -- never silent |
| `justification` | Why mechanical verification is not possible |
| `mechanization_plan` | How this becomes Mode A in the future |

Mode B additionally triggers:

- Automatic creation of a **Verification Debt** artifact
- Explicit **human acceptance gate** before promotion
- Inclusion in **B metrics** tracking

**Mode B is technical debt, not a parallel execution lane.**

Mode B is intended to be slightly uncomfortable. It should never feel routine.

---

## 5. Tiered Verification Model

### 5.1 Tier 0 -- Mandatory Baseline (All Work Statements)

For the Combine's Python/FastAPI + React SPA stack:

| Check | Tool | Condition |
|-------|------|-----------|
| Backend tests pass | `pytest` | No new failures, no regressions |
| No new lint violations | `ruff` / configured linter | Clean or no worse than baseline |
| No new type errors | `mypy` / configured checker | Clean or no worse than baseline |
| SPA builds successfully | `npm run build` | If frontend files touched |
| No forbidden file modifications | Scope validation | Only declared files changed |

Tier 0 is enforced mechanically for every Work Statement. Tier 0 must be runnable as a single command.

### 5.2 Tier 1 -- Work Statement Specific

Each Work Statement must define explicit postconditions derived from its intent. Examples:

- Endpoint returns expected status code and response schema
- Database migration applies cleanly and rolls back cleanly
- Service function returns expected output for defined inputs
- Component renders expected structure
- Security rule enforced for specified conditions

Tier 1 criteria must be **encoded as executable tests** that fail before implementation and pass after.

Tier 1 tests must not encode implementation details -- they encode intent.

---

## 6. Test-First Rule (Intent-First Enforcement)

For every Tier 1 criterion:

1. A **failing test** must be written before implementation begins
2. The test must derive from the **Work Statement's stated criteria**, not from the implementation
3. If a test **passes prior to implementation**, one of three things is true:
   - The Work Statement is unnecessary (the postcondition is already met)
   - The test is invalid (it does not actually verify the criterion)
   - The criterion is not mechanically verifiable (the WS must be rejected or moved to Mode B)

Tests encode intent. Implementation satisfies tests. Never the reverse.

This is the sibling of AI.md's Bug-First Testing Rule:
- **Bug-First**: prove the defect exists before you fix it
- **Intent-First**: prove the intent is unmet before you implement it

Both prevent the same failure mode: changing code without independent verification of what "correct" means.

---

## 7. B Metrics (Factory Health Indicators)

The Combine shall track:

| Metric | Definition | Signal |
|--------|------------|--------|
| **B-rate** | B count / total WS | Overall automation maturity |
| **B-streak length** | Consecutive Mode B transitions | Lost automation momentum |
| **B-to-A conversion rate** | Mode B items that became Mode A | Debt repayment velocity |
| **Verification debt half-life** | Time for half of Mode B items to gain mechanical verification | Factory improvement trajectory |

**Thresholds (guidelines, not hard policy):**

| B-rate | Interpretation |
|--------|---------------|
| < 10% | Factory operation |
| 10-30% | Maturing system -- acceptable during bootstrap |
| 30-50% | Assisted development -- requires improvement plan |
| > 50% | Not a factory -- systemic issue |

High B-rate sustained over time indicates the system is performing assisted development, not industrial production.

---

## 8. Execution Protocol

When a Work Statement is executed (whether by human, AI agent, or Claude Code via MCP):

1. **Read** the Work Statement's Tier 1 verification criteria
2. **Write failing tests** that assert each criterion (Phase 1: Intent encoding)
3. **Verify all Tier 1 tests fail** -- if any pass, investigate before proceeding
4. **Implement** the Work Statement's procedure (Phase 2: Implementation)
5. **Verify all Tier 1 tests pass** -- implementation satisfies intent
6. **Run Tier 0 sweep** -- no collateral damage (Phase 3: Baseline)
7. **Produce demo package** -- evidence of completion (test output, files changed, commands run)

This protocol is compatible with POL-WS-001's existing execution rules. It adds verification discipline to the existing step-by-step execution model.

---

## 9. Governance Mutation

Changes to governing artifacts (ADRs, policies, schemas) are state transitions.

Governance mutation must follow the same verification discipline as any other Work Statement. This prevents:

- Silent weakening of verification rules
- Retroactive scope changes
- Untracked policy drift

A governance change that cannot be verified mechanically requires Mode B with explicit justification.

---

## 10. Consequences

### Positive

- **Work Statements become executable contracts** -- not just procedures, but verifiable transitions
- **Capability drift is mechanically caught** -- tests fail when implementation diverges from intent
- **Automation maturity is measurable** -- B-rate provides an honest assessment
- **Self-hosting becomes possible** -- Claude Code can execute WS with mechanical verification
- **Confirmation bias is prevented** -- tests encode intent before implementation exists

### Tradeoffs

- **Work Statement authoring is harder** -- criteria must be specific enough to test
- **Mode A is a high bar** -- some legitimate work requires Mode B
- **Tier 0 harness must be maintained** -- a broken baseline invalidates all verification
- **Slower initial velocity** -- writing failing tests before implementation adds upfront time

These tradeoffs are intentional. Speed without verification is not production -- it is hope.

---

## 11. Non-Goals

This ADR does NOT:

- Define the Work Statement document type schema (that is implementation work)
- Define specific Tier 0 tooling choices (ruff vs flake8, etc.)
- Create a UI for B metrics (logging is sufficient initially)
- Change POL-WS-001's execution rules (it extends them with verification)
- Require Mode A for all historical Work Statements (applies going forward)

---

## 12. Acceptance Criteria

ADR-050 is considered satisfied when:

1. Tier 0 enforcement is runnable as a single command against the Combine codebase
2. At least one Work Statement has been executed under Mode A with Intent-First testing
3. Mode B tracking exists (even if only logging -- dashboards are not required initially)
4. POL-WS-001 references ADR-050 as the governing verification policy
5. The Test-First Rule is documented in AI.md as a mandatory execution constraint

---

_End of ADR-050_
