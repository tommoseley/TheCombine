# POL-ADR-EXEC-001: ADR Execution Authorization Process

| | |
|---|---|
| **Status** | Accepted |
| **Effective Date** | 2026-01-06 |
| **Decision Owner** | Product Owner |
| **Applies To** | All human and AI contributors executing work governed by ADRs |
| **Related Artifacts** | ADRs, POL-WS-001 |

---

## 1. Purpose

This policy defines the mandatory process for authorizing and executing work derived from an accepted Architectural Decision Record (ADR).

It exists to ensure that:

- Architectural decisions are not implemented prematurely
- Execution intent is explicit, reviewed, and authorized
- AI agents do not confuse momentum with permission
- Execution is controlled, auditable, and reversible

---

## 2. Key Principle

**Acceptance of an ADR does not authorize execution.**

Execution is permitted only after completing the authorization steps defined in this policy.

---

## 3. Architectural Status vs Execution State

ADR architectural status and execution state are distinct and independent.

### 3.1 Architectural Status (unchanged)

Architectural status reflects design law only:

- Draft
- Accepted
- Deprecated
- Superseded

### 3.2 Execution State (new)

Execution state governs whether work may proceed:

- `null` — No execution authorized
- `authorized` — Implementation planning complete; Work Statements may be prepared
- `active` — Work Statement accepted; execution permitted
- `complete` — All authorized execution finished

Execution state transitions MUST be explicit and MUST be recorded in the ADR document or a governing system of record.

---

## 4. Trigger

**Trigger:**
A human operator explicitly instructs the system to begin work on a specific ADR that is already in Accepted architectural status.

Implicit triggers (e.g., "the ADR is accepted") are invalid.

---

## 5. Execution Authorization Process

Execution of an ADR MUST follow these steps in order.

### Step 1 — Implementation Plan Draft

- An LLM prepares an Implementation Plan for the ADR.
- The plan describes:
  - Scope of work
  - Affected components
  - Sequence of changes
  - Risks and dependencies
- No system changes may occur during this step.

### Step 2 — Implementation Plan Review and Acceptance

- The human operator reviews and edits the Implementation Plan.
- Multiple review/edit cycles are permitted.
- Execution must not proceed until the plan is explicitly accepted.

### Step 3 — Authorization to Prepare Execution Artifacts

Upon Implementation Plan acceptance:

- The ADR `execution_state` is set to `authorized`
- This authorizes:
  - Preparation of one or more Work Statements
- This does not authorize execution.

### Step 4 — Work Statement Preparation

- The LLM prepares one or more Work Statements in accordance with POL-WS-001.
- Work Statements define exact execution procedures.
- No execution may occur during this step.

### Step 5 — Work Statement Review and Acceptance

- Each Work Statement is reviewed and edited by the human operator.
- Each Work Statement must be explicitly accepted before execution.
- Acceptance of one Work Statement does not imply acceptance of others.

### Step 6 — Execution

Upon acceptance of a Work Statement:

- The ADR `execution_state` is set to `active`
- The LLM may execute work only as specified in the accepted Work Statement.

Multiple Work Statements may be executed under a single ADR authorization, each requiring independent acceptance.

---

## 6. Deviation Handling

**Minor deviations** (within approved scope and intent):

- Require amendment of the affected Work Statement
- Require re-review and re-acceptance of that Work Statement

**Scope or intent changes:**

- Require stopping execution
- Require returning to Implementation Plan review (Step 2)

Unauthorized deviation is prohibited.

---

## 7. Prohibited Actions

The following actions are prohibited:

- Treating ADR acceptance as execution authorization
- Executing work without an accepted Implementation Plan
- Executing work without an accepted Work Statement
- Skipping or collapsing authorization steps
- Performing exploratory, convenience, or refactor work under execution authority

---

## 8. Enforcement

- Work performed outside this process is unauthorized
- Unauthorized work may be rejected regardless of quality
- AI agents MUST refuse execution if any required authorization is missing or ambiguous

---

## 9. Inclusion in AI Bootstrap

AI bootstrap instructions MUST include:

- Recognition of ADR architectural status vs execution state
- Obligation to request an Implementation Plan
- Obligation to request a Work Statement
- Refusal to execute without explicit acceptance signals

---

## 10. Completion

When all authorized Work Statements have been executed and verified:

- The ADR `execution_state` is set to `complete`
- No further work may occur without re-triggering this process

---

*End of Policy*