# APAM-002 — AI Portfolio Agent MVP

> Generated: 2026-03-09T20:27:33.953129+00:00
> Renderer: render-md@1.0.0
> Documents: 31

## Table of Contents

### Project Governance
  - [GOV-SEC-T0-002 -- Tier-0 Secrets Handling and Ingress Control Policy](#gov-sec-t0-002)
  - [POL-ADR-EXEC-001: ADR Execution Authorization Process](#pol-adr-exec-001)
  - [POL-ARCH-001: Architectural Integrity Standard](#pol-arch-001)
  - [POL-CODE-001: Code Construction Standard](#pol-code-001)
  - [POL-QA-001: Testing & Verification Standard](#pol-qa-001)
  - [POL-WS-001: Standard Work Statements](#pol-ws-001)

### Pipeline Documents
- [CI-001 — Concierge Intake: AI Portfolio Agent MVP](#ci-001)
- [PD-001 — AI Portfolio Agent MVP](#pd-001)
- [IP-001 — AI Portfolio Agent MVP: Implementation Plan](#ip-001)
- [TA-001 — AI Portfolio Agent MVP: Technical Architecture](#ta-001)
- [WP-001 — Foundation and Configuration Infrastructure](#wp-001)
  - [WS-001 — Project Directory Structure Setup](#ws-001)
  - [WS-002 — Shared Configuration Infrastructure](#ws-002)
  - [WS-003 — Logging Infrastructure Implementation](#ws-003)
  - [WS-004 — Virtual Environment Setup and Activation Scripts](#ws-004)
  - [WS-005 — Error Handling Framework Foundation](#ws-005)
  - [WS-006 — Alpaca API Connectivity Validation](#ws-006)
  - [WS-007 — Market Calendar and Trading Day Utilities](#ws-007)
- [WP-002 — Monthly Decision Engine](#wp-002)
  - [WS-008 — Technical Indicator Analysis Module](#ws-008)
  - [WS-009 — Risk Parameter Enforcement Engine](#ws-009)
  - [WS-010 — Position Sizing and Allocation Calculator](#ws-010)
  - [WS-011 — SPY Baseline Performance Comparator](#ws-011)
  - [WS-012 — Trading Decision Integration and CSV Output](#ws-012)
- [WP-003 — Integration Testing and Validation](#wp-003)
  - [WS-013 — End-to-End Integration Test Suite Development](#ws-013)
  - [WS-014 — Data Source Failure and Fallback Testing](#ws-014)
  - [WS-015 — Error Handling and Notification Testing](#ws-015)
  - [WS-016 — Edge Case and Market Condition Testing](#ws-016)
  - [WS-017 — Performance Testing Under Normal Load](#ws-017)
  - [WS-018 — Configuration Validation Testing](#ws-018)
  - [WS-019 — Audit Trail Verification and Completeness Testing](#ws-019)
- [WP-004 — Windows Task Scheduler Integration and Deployment](#wp-004)
- [WP-005 — Data Retention and Cleanup Automation](#wp-005)
- [WP-006 — Market Data Collection and Technical Indicators](#wp-006)
- [WP-007 — Monthly Trade Execution Engine](#wp-007)
- [WP-008 — Notification and Monitoring Infrastructure](#wp-008)

---

# Project Governance

These standards apply to all work in this project.

---

## GOV-SEC-T0-002 -- Tier-0 Secrets Handling and Ingress Control Policy

# GOV-SEC-T0-002 -- Tier-0 Secrets Handling and Ingress Control Policy

**Status:** Active
**Scope:** All HTTP ingress, PGC workflow nodes, stabilization, rendering, and logging subsystems

---

## 1. Purpose

This policy establishes deterministic, multi-layer controls designed to prevent persistence of credential material within The Combine.

The system is designed to:

- Prevent secret solicitation
- Detect secret ingress
- Block workflow execution
- Redact prior to persistence
- Audit detection events

No claim of infallibility is made.

---

## 2. Definitions

### 2.1 Secret

A Secret is any value that:

- Grants authentication or authorization
- Enables service/API access
- Is intended for storage in a secret manager
- Contains credential material within structured formats

Examples (non-exhaustive):

- API keys
- Passwords
- OAuth tokens
- Bearer tokens
- Private keys
- Access key pairs
- Credential-bearing connection strings

Allowed metadata:

- Secret provider
- Secret identifier/path
- Secret name
- Storage mechanism

Secret metadata is permitted. Secret values are not.

---

## 3. Tier-0 Rules

### 3.1 Prohibited

The system MUST NOT:

- Request secret values
- Persist secret values
- Render secret values into HTML or PDF
- Store secret values in logs
- Store secret values in workflow artifacts

### 3.2 Permitted

PGC may request only:

- Whether a secret is required
- Which provider will manage it
- The identifier/path
- Lifecycle ownership
- Runtime resolution intent

All secret-related questions must concern management intent only.

---

## 4. Detection and Enforcement Model

### 4.1 Dual Gate Architecture (Mandatory)

Secrets screening shall occur at:

1. **HTTP Ingress Boundary**
2. **Orchestrator Tier-0 Governance Boundary**

Both gates must invoke the same canonical detector implementation.

---

## 5. Canonical Secret Detector

There shall be one authoritative detector module:

`combine-config/governance/secrets/detector.v1`

This module must be versioned and auditable.

### 5.1 Detection Hierarchy

**Primary trigger:**

- High entropy string detection (threshold >= configured value)
- Minimum length threshold
- Character distribution analysis

**Secondary accelerators:**

- Known credential patterns (AWS AKIA, PEM headers, etc.)

No vendor-enumeration reliance.

---

## 6. HTTP Ingress Gate

### 6.1 Execution

At HTTP ingress:

- Run canonical detector on raw request body
- Execute before any logging persistence

### 6.2 If Secret Detected

System must:

- Reject request (HTTP 422)
- Not create workflow instance
- Not persist request body
- Log only redacted event: `[REDACTED_SECRET_DETECTED]`

Permitted log metadata:

- Request ID
- Detector version
- Entropy score
- Detection classification

Secret value must never be written.

---

## 7. Orchestrator Tier-0 Gate

### 7.1 Execution Points

Detector must run on:

- PGC user answers
- Generated artifacts before stabilization
- Render inputs (detail_html, pdf)
- Replay or connector payloads

### 7.2 If Secret Detected

System must:

- Issue HARD_STOP
- Abort node execution
- Roll back transaction
- Prevent persistence
- Emit structured governance event
- Allow resumable correction

---

## 8. HARD_STOP Definition

HARD_STOP results in:

- Immediate termination of current workflow node
- Transaction rollback
- No stabilization
- No rendering
- No artifact persistence
- Redacted logging only
- Structured error response
- No human intervention required

---

## 9. Logging Precedence (ADR-010 Alignment)

If a conflict exists between logging requirements and secret protection:

**Tier-0 Secret Protection takes precedence.**

Secret-bearing payloads must be redacted prior to persistence.

Logging may record:

- Detection metadata
- Governance event
- Redacted placeholder

Logging may not store secret material.

---

## 10. Tier-0 Injection Requirement (PGC)

All PGC task and QA prompts must include the injected clause defined in Section 11.

Clause must be injected automatically and be non-removable.

---

## 11. Canonical Injected Clauses

Location:

- `combine-config/governance/tier0/pgc_secrets_clause.v1.txt`
- `combine-config/governance/tier0/pgc_secrets_clause_qa.v1.txt`

### 11.1 PGC Task Clause (Exact Text)

```
[[TIER0_PGC_SECRETS_CLAUSE_V1]]

Tier-0 Governance Rule: Secrets Handling

You MUST NOT request, collect, validate, echo, or persist any credential or secret value.

A secret includes (but is not limited to):
- API keys
- Passwords
- OAuth tokens
- Bearer tokens
- Private keys
- Access key pairs
- Credential-bearing connection strings

You MAY ask how secrets should be managed, including:
- Whether a secret is required
- Which provider will manage it
- The secret identifier or storage path
- Whether runtime resolution should occur

All secret-related questions must concern management intent only.

If a user provides a secret value:
- Do not repeat it
- Do not store it
- Instruct the user to use a supported secret manager
- Continue safely without persisting the value
```

### 11.2 PGC QA Clause (Exact Text)

```
[[TIER0_PGC_SECRETS_CLAUSE_V1]]

Tier-0 Governance Rule: Secrets Validation

You MUST verify that:
- No PGC question requests a secret value
- No artifact contains credential material
- No secret fragments appear in output

If secret solicitation is detected:
- Mark as HARD_STOP violation
- Explain violation clearly

If secret material appears in user input:
- Mark as invalid
- Require use of secret manager
```

---

## 12. Authority

This policy:

- Cannot be overridden by package.yaml
- Cannot be modified via Workbench triad editing
- Is governed as Tier-0 Combine infrastructure

---

_End of GOV-SEC-T0-002_


---

## POL-ADR-EXEC-001: ADR Execution Authorization Process

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

### 5.1 Scope Assessment

Before beginning execution authorization, assess expected scope:

- **Single-commit scope:** One atomic change, no phasing required
- **Multi-commit scope:** Multiple changes, phasing/sequencing required

The expected scope (single-commit or multi-commit) MUST be explicitly declared in the Work Statement or Implementation Plan.

### 5.2 Single-Commit Path

For single-commit work:

1. Work Statement Preparation (per POL-WS-001)
2. Work Statement Review and Acceptance
3. Execution

No Implementation Plan required.

### 5.3 Multi-Commit Path

For multi-commit work:

1. Implementation Plan Draft
2. Implementation Plan Review and Acceptance
3. Authorization to Prepare Execution Artifacts (`execution_state` = `authorized`)
4. Work Statement(s) Preparation
5. Work Statement Review and Acceptance
6. Execution

### 5.4 Scope Escalation

If, during execution, it becomes apparent that the remaining work cannot be completed in a single commit:

1. STOP execution
2. Draft Implementation Plan for remaining work
3. Resume multi-commit path from Step 2

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

---

## POL-ARCH-001: Architectural Integrity Standard

# POL-ARCH-001: Architectural Integrity Standard

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-03-06 |
| **Applies To** | All human and AI contributors modifying architecture, APIs, workflows, or infrastructure in The Combine |
| **Related Artifacts** | CLAUDE.md (Execution Constraints, Non-Negotiables, Execution Model), ADR-009, ADR-010, ADR-040, ADR-049 |

---

## 1. Purpose

This policy formalizes the architectural integrity rules that govern system boundaries, schema authority, workflow composition, API contracts, and traceability in The Combine. These rules ensure the system remains coherent, auditable, and mechanically verifiable.

---

## 2. Separation of Concerns

- **Documents are memory, not LLM context.** The system persists state in documents, not conversation transcripts.
- **Workers are anonymous, interchangeable components.** No execution depends on a specific worker identity.
- **LLMs handle creative/synthesis tasks; code handles mechanical tasks** (storage, validation, rendering, routing).
- **UI, domain, and infrastructure layers MUST remain distinct.** No layer may assume or embed the responsibilities of another.

*Source: CLAUDE.md "Execution Model (Concrete)", ADR-040 (Stateless LLM Execution Invariant)*

---

## 3. Stateless LLM Execution (ADR-040)

Each LLM invocation MUST receive:
- The canonical role prompt
- The task- or node-specific prompt
- The current user input (single turn only)
- Structured `context_state` (governed data derived from prior turns)

Each LLM invocation MUST NOT receive:
- Prior conversation history (even from same execution)
- Previous assistant responses
- Accumulated user messages
- Raw conversational transcripts

Continuity comes from structured state, not transcripts. `node_history` is for audit; `context_state` is for memory. Keep them separate.

*Source: CLAUDE.md "Stateless LLM Execution Invariant (ADR-040)"*

---

## 4. Schema Authority

- All document structures MUST originate from governed schemas in `seed/schemas/`.
- Prompts live in `seed/prompts/` -- they are governed inputs, not documentation.
- Prompt changes require: explicit intent, version bump, re-certification, manifest regeneration.
- Prompts are versioned, certified, hashed (`seed/manifest.json`), and logged on every LLM execution.

*Source: CLAUDE.md "Seed Governance"*

---

## 5. Workflow Integrity (ADR-049)

- Every DCW (Document Creation Workflow) MUST be explicitly composed of gates, passes, and mechanical operations.
- "Generate" is deprecated as a step abstraction -- it hides too much.
- DCWs are first-class workflows, not opaque steps inside POWs.
- Handlers own input assembly, prompt selection, LLM invocation, and output persistence.
- Handlers do NOT infer missing inputs -- they fail explicitly.
- Retry/circuit-breaker logic belongs to the engine, not the plan.

### Composition Patterns

- **Full pattern:** PGC Gate (LLM -> UI -> MECH) -> Generation (LLM) -> QA Gate (LLM + remediation)
- **QA-only pattern:** Generation (LLM) -> QA Gate (LLM + remediation)
- **Gate Profile pattern:** Multi-pass classification with internals

*Source: CLAUDE.md "No Black Boxes (ADR-049)", "Execution Model (Concrete)"*

---

## 6. API & Interface Contracts

- Routes are API contracts -- no silent route removal (deprecation protocol required).
- All API routes live under `/api/v1/`.
- Kebab-case in URL paths, snake_case in JSON fields.
- Command routes are async, idempotent, and return `task_id`.

*Source: Established API conventions, CLAUDE.md "Repository Structure"*

---

## 7. Traceability

- All state changes MUST be explicit and traceable (ADR-009).
- LLM execution MUST be logged with inputs, outputs, tokens, and timing (ADR-010).
- Every execution is replayable via `/api/admin/llm-runs/{id}/replay`.

*Source: CLAUDE.md "Execution Model (Concrete)", ADR-009, ADR-010*

---

## 8. Git & Deployment Integrity

- Session summaries are immutable logs -- never edit after writing.
- ADRs are append-only governance records.
- Docker copies only `app/`, `alembic/`, `alembic.ini` (explicit, not blanket).
- Anything in `ops/` is operator-facing and never in the runtime container.

*Source: CLAUDE.md "Non-Negotiables", "Repository Structure", "Knowledge Layers"*

---

## 9. Governance Boundary

This policy formalizes rules already enforced through CLAUDE.md, ADR-009, ADR-010, ADR-040, ADR-049, and established layer conventions. It does not introduce new rules or enforcement mechanisms. Mechanical enforcement is out of scope and deferred to future quality gate work.

---

*End of Policy*


---

## POL-CODE-001: Code Construction Standard

# POL-CODE-001: Code Construction Standard

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-03-06 |
| **Applies To** | All human and AI contributors writing or modifying code in The Combine |
| **Related Artifacts** | CLAUDE.md (Reuse-First Rule, Execution Constraints), ADR-045 (System Ontology), ADR-057 (Ontology) |

---

## 1. Purpose

This policy formalizes the code construction rules that govern how code is written, extended, and maintained in The Combine. These rules ensure consistency, reuse, testability, and terminological precision across the codebase.

---

## 2. Reuse-First Rule

Before creating anything new (file, module, schema, service, prompt):

1. **Search** the codebase and existing docs/ADRs.
2. **Prefer** extending or refactoring over creating.
3. **Create new** only when reuse is not viable.

### Constraints

- If you create something new, you MUST be able to justify why reuse was not appropriate.
- Creating something new when a suitable existing artifact exists is a defect.

*Source: CLAUDE.md "Reuse-First Rule"*

---

## 3. Complexity Management

### CRAP Score Thresholds

- Functions exceeding CRAP score > 30 are flagged as critical and require remediation.
- Remediation path: decompose into focused sub-methods (cyclomatic complexity reduction), add test coverage (coverage increase), or both.

### Structural Rules

- No god functions: business logic MUST be modular and testable.
- Mechanical/deterministic checks are preferred over LLM-based validation wherever possible.
- Make every change as simple as possible. Find root causes, not symptoms.
- No temporary fixes. No "we'll clean this up later" without a tech debt entry.
- Changes should only touch what is necessary.

*Source: WP-CRAP-001/002 practices, CLAUDE.md "Planning Discipline - Simplicity First"*

---

## 4. Ontology Compliance

Per ADR-045 and ADR-057, terminological precision is mandatory:

- **One meaning per term, system-wide.** No synonyms in code.
- **Registration before use:** Check the ontology before naming columns, fields, classes, or parameters.
- **Use registered terms:** Code identifiers MUST use registered terms, not alternatives.
- Prose documentation may use natural language; code MUST NOT.

### ADR-045 Taxonomy

| Category | Examples |
|----------|----------|
| **Primitives** | Prompt Fragment, Schema |
| **Composites** | Role, Task, DCW, POW |
| **Ontological terms** | Interaction Pass |

Core principle: Prompt Fragments shape behavior; Schemas define acceptability; Interaction Passes bind and execute both.

*Source: CLAUDE.md "ADR-045 Taxonomy Reference", ADR-057*

---

## 5. Code Style

- **Explicit dependencies:** All imports and dependencies MUST be declared.
- **Readability over cleverness:** Favor clarity and maintainability.
- **No silent failures:** Errors MUST be surfaced, not swallowed.
- **No black boxes:** If a step does something non-trivial, it must show its passes (ADR-049). "Generate" is deprecated as a step abstraction.

*Source: CLAUDE.md "Execution Constraints" (ADR-049), "Non-Negotiables"*

---

## 6. Prompt and Seed Governance

Prompts are governed inputs, not documentation:

- Prompts live in `seed/prompts/` and are versioned, certified, hashed, and logged.
- Do NOT merge role logic into task prompts.
- Do NOT edit prompts without a version bump.
- Prompt changes require: explicit intent, version bump, re-certification, manifest regeneration.

*Source: CLAUDE.md "Seed Governance", "Non-Negotiables"*

---

## 7. Governance Boundary

This policy formalizes rules already enforced through CLAUDE.md, ADR-045, ADR-049, ADR-057, and established CRAP score audit practices. It does not introduce new rules or enforcement mechanisms. Mechanical enforcement is out of scope and deferred to future quality gate work.

---

*End of Policy*


---

## POL-QA-001: Testing & Verification Standard

# POL-QA-001: Testing & Verification Standard

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-03-06 |
| **Applies To** | All human and AI contributors executing governed work in The Combine |
| **Related Artifacts** | CLAUDE.md (Bug-First Testing Rule, Testing Strategy), ADR-010, POL-WS-001 |

---

## 1. Purpose

This policy formalizes the testing and verification rules that govern all implementation work in The Combine. These rules ensure that defects are understood before modification, fixes are causally linked to observed failures, and regressions are prevented by construction.

---

## 2. Bug-First Testing Rule

When a runtime error, exception, or incorrect behavior is observed, the following sequence **MUST** be followed:

1. **Reproduce First** -- A failing automated test MUST be written that reproduces the observed behavior. The test must fail for the same reason the runtime behavior failed.
2. **Verify Failure** -- The test MUST be executed and verified to fail before any code changes are made.
3. **Fix the Code** -- Only after the failure is verified may code be modified to correct the issue.
4. **Verify Resolution** -- The test MUST pass after the fix. No fix is considered complete unless the reproducing test passes.

### Constraints

- Tests MUST NOT be written after the fix to prove correctness.
- Code MUST NOT be changed before a reproducing test exists.
- If a bug cannot be reliably reproduced in a test, the issue MUST be escalated rather than patched heuristically.
- Vibe-based fixes are explicitly disallowed.

This rule applies to all runtime defects including: exceptions, incorrect outputs, state corruption, and boundary condition failures.

*Source: CLAUDE.md "Bug-First Testing Rule (Mandatory)"*

---

## 3. Money Tests

Bug fixes MUST include a "money test" that reproduces the exact root-cause scenario:

- The money test MUST fail before the fix is applied.
- The money test MUST pass after the fix is applied.
- The money test serves as the regression guard for that specific defect.

*Source: Established session practice (WS-RING0-001, WP-CRAP-001/002)*

---

## 4. Testing Tiers

All tests operate within the following tier structure:

| Tier | Scope | Dependencies | Purpose |
|------|-------|-------------|---------|
| Tier-1 | In-memory repositories, no DB | None | Pure business logic verification (fast unit tests) |
| Tier-2 | Spy repositories | None | Call contract verification (wiring tests) |
| Tier-3 | Real PostgreSQL | Test DB infrastructure | Integration verification (**deferred**) |

### Tier Constraints

- Tier-3 tests are not currently required. Infrastructure does not yet exist.
- Do NOT suggest SQLite as a substitute for PostgreSQL testing.
- Tier-1 and Tier-2 tests MUST pass before any work is considered complete.

*Source: CLAUDE.md "Testing Strategy (Current)"*

---

## 5. Verification Before Completion

- Work is not complete until all tests pass and acceptance criteria are verified.
- Never mark a task complete without proving it works.
- The standard is "does Tier 0 pass?" -- not "does this look right?"
- Tier 0 verification (`ops/scripts/tier0.sh`) is the mandatory baseline for all work.
- When executing a Work Statement, Tier 0 MUST be invoked in WS mode with `--scope` derived from the WS's `allowed_paths[]`.

*Source: CLAUDE.md "Planning Discipline - Verification Before Done", POL-WS-001 Section 6*

---

## 6. Regression Protection

- Fixes MUST NOT reduce existing test coverage.
- Tests MUST be deterministic -- they MUST NOT depend on external services or non-deterministic inputs.
- Every autonomous bug fix MUST include the test name and root cause in its report.

*Source: CLAUDE.md "Bug-First Testing Rule", "Autonomous Bug Fixing"*

---

## 7. Governance Boundary

This policy formalizes rules already enforced through CLAUDE.md, ADR-010, and established session practices. It does not introduce new rules or enforcement mechanisms. Mechanical enforcement is out of scope and deferred to future quality gate work.

---

*End of Policy*


---

## POL-WS-001: Standard Work Statements

# POL-WS-001: Standard Work Statements

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-01-06 |
| **Applies To** | All human and AI contributors executing governed work in The Combine |
| **Related Artifacts** | ADRs, Governance Policies, Schemas, Work Statements |

---

## 1. Purpose

Standard Work Statements (WS) define how governed work is executed repeatedly, correctly, and without drift.

They translate architectural decisions (ADRs) and governance policies into explicit, mechanical execution procedures suitable for both human contributors and AI agents.

Work Statements exist to:

- Prevent interpretive or "creative" compliance
- Enable safe and repeatable delegation to AI
- Preserve architectural integrity during change
- Ensure auditability and consistent outcomes

---

## 2. When a Work Statement Is Required

A Work Statement **MUST** be used when any of the following apply:

- An ADR or policy is being applied to existing code or systems
- An ADR or policy is being applied to multiple surfaces or instances
- Execution is delegated to an AI agent
- Deviation would introduce architectural drift
- The work establishes or propagates a new architectural pattern

A Work Statement **MAY** be used for:

- Complex one-off changes
- High-risk or irreversible work
- Coordination across multiple components

A Work Statement is **NOT** required for:

- Pure analysis or exploration
- Drafting ADRs or policies
- Non-durable discussion

---

## 3. Relationship to ADRs and Policies

- **ADRs** define *what must be true*
- **Policies** define *how governance operates*
- **Work Statements** define *how work is executed*

Work Statements:

- **MUST** reference the governing ADRs, policies, and schemas
- **MUST NOT** reinterpret, extend, or override ADRs
- **MUST NOT** introduce new architectural decisions

If a governing ADR or policy is unclear, contradictory, or incomplete:

1. **STOP**
2. Escalate for clarification
3. Do not proceed until corrected

---

## 4. Required Structure of a Work Statement

Every Work Statement **MUST** include the following sections:

### Purpose
What work is being executed and why

### Governing References
ADRs, policies, schemas, and standards that control the work

### Verification Mode
`A` (all criteria verified) or `B` (declared exceptions)

### Allowed Paths
A list of file-path prefixes that define the containment boundary for this Work Statement. These prefixes are passed to Tier 0 as `--scope` arguments during WS execution (see Section 6).

Example:
```
## Allowed Paths
- ops/scripts/
- tests/infrastructure/
- combine-config/policies/
- CLAUDE.md
```

### Scope
Explicit statement of what is included and excluded

### Preconditions
Required artifacts, system state, approvals, or inputs

### Procedure
Step-by-step execution instructions

- Written to be followed mechanically
- No assumed knowledge
- No skipped or implicit steps

### Prohibited Actions
Actions that must not be taken (see Section 5)

### Verification Checklist
Objective checks to confirm correct execution

### Definition of Done
Conditions under which the work is considered complete

---

## 5. Prohibited Actions (Authoritative)

A Work Statement **MUST** explicitly list known prohibited actions relevant to the task.

In addition, **all prohibitions and constraints defined in governing ADRs, policies, schemas, and architectural rules are implicitly in force**, whether or not they are restated in the Work Statement.

Lack of explicit prohibition in a Work Statement does **not** grant permission to:

- Violate ADRs
- Violate governance policies
- Breach architectural boundaries
- Circumvent quality gates
- Introduce implicit behavior, shortcuts, or assumptions

If a contributor believes an action is permitted due to omission:

1. **STOP**
2. Escalate for clarification
3. Do not proceed on assumption

---

## 6. Execution Rules

### Do No Harm Audit (Mandatory Pre-Execution)

Before executing any Work Statement, the executor **MUST** verify that the WS's assumptions about the codebase match reality.

1. Identify assumptions the WS makes about existing code, schemas, APIs, configuration, or infrastructure
2. Check each assumption against the actual codebase state
3. If any assumption is materially wrong, **STOP** and report mismatches before touching anything
4. Do not execute a WS whose assumptions do not match the terrain

This audit prevents executing well-structured Work Statements against a codebase that has diverged from what the WS author believed existed. A correct procedure applied to a wrong assumption produces wrong output.

### General Rules

- Work Statements are executed **exactly as written**
- Steps must not be skipped, reordered, merged, optimized, or reinterpreted

If a step cannot be completed as written:

1. **STOP**
2. Escalate for revision or clarification

### Tier 0 Verification in WS Mode

When executing a Work Statement, Tier 0 **MUST** be invoked in WS mode with `--scope` prefixes derived from the Work Statement's `allowed_paths[]` field:

```bash
ops/scripts/tier0.sh --ws --scope <each allowed_paths prefix>
```

If Tier 0 is run in WS mode without `--scope`, it will **FAIL by design**. This prevents "false green" runs where scope was never validated.

### AI-Specific Rules

AI agents:

- Must treat Work Statements as authoritative instructions
- Must not infer missing steps
- Must not generalize beyond stated scope
- Must refuse execution if a required Work Statement is missing

---

## 7. Modification and Versioning

Work Statements are versioned artifacts.

Changes require:

- Explicit revision
- Documented rationale

Silent or informal edits are **prohibited**.

Superseded Work Statements must be clearly marked as such.

---

## 8. Acceptance and Closure

A Work Statement is considered complete only when:

- All procedural steps are executed
- All verification checklist items pass
- The Definition of Done is satisfied
- The outcome conforms to all governing ADRs and policies

Partial completion is **not acceptable** unless explicitly defined in the Work Statement.

---

## 9. Enforcement

Failure to use or comply with a required Work Statement constitutes:

- A governance violation
- Grounds for rejection of the work output

All contributors—human and AI—are held to the same standard.

---

## 10. Inclusion in AI Bootstrap

This policy is a **mandatory reference** in all AI bootstrap prompts.

AI agents must be instructed to:

- Request a Work Statement when required
- Refuse execution in its absence
- Halt execution upon ambiguity, contradiction, or missing governance

---

*End of Policy*


---

# CI-001 — Concierge Intake: AI Portfolio Agent MVP

## Project Summary

The user wants to build a Windows-native automated portfolio management system that runs scheduled jobs to collect market data, calculate technical indicators, make trading decisions, and execute paper trades through Alpaca. The system includes data fallback mechanisms, comprehensive logging, and produces auditable CSV outputs for a defined universe of 5 core tickers plus SPY as baseline.

Build a Windows-native 'AI Portfolio Agent' MVP that: 1) Runs daily after market close to compute indicators and store a durable CSV snapshot. 2) Runs monthly to convert indicators into decisions (ADD/HOLD/TRIM/EXIT) and writes a decisions CSV. 3) Executes paper orders in Alpaca based on the monthly decisions CSV (with basic safety rails).

## Project Type

produce_output

User is requesting creation of a complete automated trading system with specific deliverable components, scheduled execution, and defined outputs.

## Intake Outcome

qualified

Request is exceptionally detailed with clear technical specifications, defined scope, explicit deliverables, and comprehensive requirements. The few open gaps are implementation choices that can be resolved during development without changing core requirements.

Proceed to Development phase to implement the three-component system (daily data collection, monthly decision making, and paper trade execution) with the specified technical architecture.


---

# PD-001 — AI Portfolio Agent MVP

## Preliminary Summary

User needs an automated portfolio management system that operates on Windows with scheduled execution to collect market data, make trading decisions using technical indicators, and execute paper trades through Alpaca. The system must handle data source failures gracefully, maintain audit trails, and operate within defined risk parameters for a small universe of growth-oriented tickers.

Three-component scheduled job architecture with clear separation of concerns: daily data collection/indicator calculation, monthly decision generation, and monthly trade execution. Event-driven through CSV artifacts with comprehensive logging and fallback mechanisms.

Three Python scripts schedulable via Windows Task Scheduler: (1) Daily data collector fetching from Alpaca/Yahoo with technical indicator calculation, (2) Monthly decision engine converting indicators to trading actions, (3) Monthly execution engine placing limit orders through Alpaca API. Shared configuration, logging infrastructure, and CSV-based data persistence with virtual environment activation.

## Project Name

AI Portfolio Agent MVP

## Unknowns

| ID | Question | Why It Matters | Impact If Unresolved |
| --- | --- | --- | --- |
| UNK-1 | What is the specific calendar date for monthly execution (1st, 15th, last day of month)? | Calendar date execution requires handling weekends/holidays and affects scheduler configuration complexity. | Cannot configure Windows Task Scheduler properly or implement weekend/holiday logic for monthly jobs. |
| UNK-2 | What specific notification methods are included in 'multiple notification methods' for error handling? | Different notification methods require different infrastructure setup (SMTP config, webhook endpoints, etc.). | Cannot implement proper error notification system or estimate infrastructure requirements. |
| UNK-3 | How should the system handle partial fills when using limit orders? | Limit orders may not execute fully, requiring retry logic or position adjustment strategies. | System may fail to achieve target allocations or require manual intervention for incomplete orders. |

## Assumptions

| ID | Assumption | Confidence | Validation |
| --- | --- | --- | --- |
| ASM-1 | User has access to Alpaca paper trading account and API keys | medium | Confirm during setup phase that credentials are available and functional |
| ASM-2 | Python environment setup and package management is acceptable to user | high | No validation needed - explicitly acceptable per Windows-native requirement |
| ASM-3 | CSV format and console output are sufficient for monitoring and auditing | high | Explicitly stated in requirements - no validation needed |
| ASM-4 | Monthly execution on calendar date will check if date falls on weekend/holiday and execute on next trading day | medium | Implement market calendar checking logic and validate behavior during testing |

## Known Constraints

| ID | Constraint | Type |
| --- | --- | --- |
| CNS-1 | Must be Windows-native and schedulable via Windows Task Scheduler | technical |
| CNS-2 | Must use Alpaca Market Data (IEX) with Yahoo Finance fallback for 403 errors | vendor |
| CNS-3 | Specific ticker universe: ARKK, BE, NVDA, PLTR, XBI plus SPY baseline | data |
| CNS-4 | Per-name allocation: 20% equity per ADD_20 ticker (not split allocation) | technical |
| CNS-5 | Orders must be executed as limit orders (±0.5% around last price) | technical |

## MVP Guardrails

| ID | Guardrail |
| --- | --- |
| GRD-1 | Paper trading only - no live trading capability |
| GRD-2 | Cash buffer safety rail: maintain 5% equity minimum |
| GRD-3 | Position cap safety rail: maximum 30% equity per position |
| GRD-4 | Must produce auditable CSV artifacts and comprehensive logging |

## Early Decision Points

### Monthly execution calendar date specificity

EDP-1

Affects scheduler configuration and weekend/holiday handling logic implementation

- 1st of month
- 15th of month
- Last trading day of month
- User-configurable date

1st of month with next-trading-day logic for simplicity

## Stakeholder Questions

| ID | Question | Directed To | Blocking |
| --- | --- | --- | --- |
| STQ-1 | What specific notification methods should be implemented beyond logging (email, webhook, SMS, etc.)? | product_owner | No |
| STQ-2 | Should the system validate Alpaca API connectivity and paper trading account status during setup? | product_owner | No |

## Recommendations for PM

| ID | Recommendation |
| --- | --- |
| RPM-1 | Validate Alpaca paper trading account access and API key availability before development begins |
| RPM-2 | Define specific notification infrastructure requirements early to avoid late-stage integration complexity |
| RPM-3 | Consider creating test data scenarios for market data API failures to validate fallback mechanisms |


---

# IP-001 — AI Portfolio Agent MVP: Implementation Plan

## Plan Summary

Deliver an automated portfolio management system that operates on Windows with scheduled execution to collect market data, make trading decisions using technical indicators, and execute paper trades through Alpaca API with comprehensive audit trails and risk controls.

Three schedulable Python scripts with shared configuration: daily data collector with technical indicators, monthly decision engine, and monthly execution engine. System maintains CSV audit trails, operates within defined risk parameters (5% cash buffer, 30% position cap), and handles data source failures gracefully.

- Must be Windows-native and schedulable via Windows Task Scheduler
- Must use Alpaca Market Data (IEX) with Yahoo Finance fallback for 403 errors
- Specific ticker universe: ARKK, BE, NVDA, PLTR, XBI plus SPY baseline
- Per-name allocation: 20% equity per ADD_20 ticker (not split allocation)
- Orders must be executed as limit orders (±0.5% around last price)
- Paper trading only - no live trading capability
- Monthly execution on 15th of month with next trading day logic
- Accept partial fills and log discrepancy
- Email notifications for error handling
- 1-year data retention for CSV files and trade logs

Foundation and shared infrastructure must be established first, followed by data collection capabilities, then decision logic, and finally execution capabilities. Configuration and setup enable all other components. Testing and validation occur after core functionality is complete.

- User has access to Alpaca paper trading account and API keys
- Python environment setup and package management is acceptable to user
- CSV format and console output are sufficient for monitoring and auditing
- SMTP configuration will be available for email notifications

- Live trading capabilities
- Real-time market data streaming
- Advanced technical indicators beyond basic set
- Web-based user interface
- Database storage (CSV-only persistence)
- Multi-user or role-based access
- Advanced portfolio optimization algorithms

## Work Package Candidates

### Foundation and Configuration Infrastructure

WPC-001

Establish shared configuration management, logging infrastructure, and directory structure that all other components depend on. Includes API validation and basic error handling framework.

- Configuration file structure and validation
- Shared logging infrastructure with file and console output
- Directory structure for data, logs, and output files
- Alpaca API connectivity validation during setup
- Error handling framework foundation
- Virtual environment activation scripts
- Basic utility functions for market calendar and trading day logic

- Specific business logic for any component
- Data collection or trading functionality
- Email notification implementation (handled in WPC-005)
- Specific technical indicator calculations

- Configuration file loads and validates all required settings
- Logging outputs to both file and console with appropriate levels
- Directory structure is created and maintained
- Alpaca API connectivity test passes with valid credentials
- Error handling framework captures and logs exceptions appropriately
- Market calendar utility correctly identifies trading days and handles 15th of month logic

### Market Data Collection and Technical Indicators

WPC-002

Implement daily data collection from Alpaca/Yahoo with fallback logic and calculate technical indicators required for decision making. Produces CSV artifacts consumed by decision engine.

- Daily market data fetching from Alpaca Market Data (IEX)
- Yahoo Finance fallback implementation for 403 errors
- Technical indicator calculation (basic set for MVP)
- CSV output generation for market data and indicators
- Data validation and quality checks
- Retry logic and error handling for data source failures
- Historical data backfill capability

- Real-time streaming data
- Advanced or exotic technical indicators
- Data storage beyond CSV files
- Decision logic or trading signals (handled in WPC-003)

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-001 | — | must_complete_first | Requires configuration infrastructure and logging framework |

- Successfully fetches daily market data for all configured tickers
- Fallback to Yahoo Finance works when Alpaca returns 403 errors
- Technical indicators are calculated and output to CSV
- Data validation prevents corrupt or incomplete data from being processed
- Retry logic handles temporary network or API failures gracefully
- CSV output format is consistent and readable by decision engine

### Monthly Decision Engine

WPC-003

Convert technical indicator data into trading decisions based on defined rules. Generates trading actions that respect risk parameters and position limits.

- Technical indicator analysis and signal generation
- Trading decision logic based on indicator thresholds
- Risk parameter enforcement (5% cash buffer, 30% position cap)
- Position sizing calculations for 20% equity per ADD_20 ticker
- Decision output to CSV format for execution engine consumption
- Current position analysis and adjustment logic
- SPY baseline comparison and relative performance evaluation

- Order execution (handled in WPC-004)
- Real-time decision making (monthly execution only)
- Advanced portfolio optimization
- Machine learning or AI-based decisions

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-001 | — | must_complete_first | Requires configuration and logging infrastructure |
| WPC-002 | — | can_start_after | Needs technical indicator CSV format definition, but can develop logic in parallel |

- Reads technical indicator data from CSV files produced by data collection
- Generates trading decisions based on configured rules and thresholds
- Enforces all risk parameters and position limits
- Calculates appropriate position sizes for each ticker
- Outputs trading decisions in format consumable by execution engine
- Handles edge cases like insufficient cash or maximum position limits

### Monthly Trade Execution Engine

WPC-004

Execute trading decisions through Alpaca API using limit orders with partial fill handling. Maintains audit trail and handles execution errors.

- Trading decision consumption from CSV input
- Limit order placement through Alpaca API (±0.5% around last price)
- Partial fill handling with accept and log strategy
- Order status monitoring and completion tracking
- Trade execution audit trail in CSV format
- Position reconciliation after execution
- Execution error handling and recovery

- Market orders or other order types
- Real-time execution monitoring
- Complex order management (stop-loss, take-profit)
- Live trading capabilities

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-001 | — | must_complete_first | Requires configuration infrastructure and API connectivity |
| WPC-003 | — | must_complete_first | Requires trading decisions from decision engine |

- Successfully places limit orders through Alpaca API
- Handles partial fills by accepting and logging discrepancies
- Maintains complete audit trail of all execution attempts
- Reconciles positions after execution completion
- Handles execution errors gracefully with appropriate logging
- Operates within paper trading constraints only

### Notification and Monitoring Infrastructure

WPC-005

Implement email notification system for error handling and establish monitoring capabilities for system health and execution status.

- SMTP configuration and email sending capability
- Error notification templates and triggers
- System health monitoring and status reporting
- Execution summary notifications
- Log file monitoring and alerting
- Email notification testing and validation

- Webhook or other notification methods
- Real-time monitoring dashboards
- SMS or mobile notifications
- Advanced alerting rules or escalation

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-001 | — | must_complete_first | Requires error handling framework and configuration infrastructure |
| WPC-002 | — | soft | Benefits from having actual error scenarios to test notification triggers |

- SMTP configuration loads from config file and connects successfully
- Error notifications are sent for critical system failures
- Email templates are professional and include relevant error details
- Notification system handles SMTP failures gracefully
- Test notifications can be sent to verify configuration
- Integration with existing logging infrastructure is complete

### Data Retention and Cleanup Automation

WPC-006

Implement automated cleanup of CSV files and logs based on 1-year retention policy to prevent unlimited disk usage growth.

- Automated cleanup logic for CSV files older than 1 year
- Log file rotation and retention management
- Disk usage monitoring and reporting
- Cleanup scheduling and execution
- Retention policy configuration and validation
- Safe deletion with backup verification

- Data archiving to external storage
- Compression or optimization of retained files
- User-configurable retention periods
- Database cleanup (CSV-only system)

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-001 | — | must_complete_first | Requires configuration infrastructure and directory structure |
| WPC-002 | — | can_start_after | Benefits from understanding CSV file structure and naming conventions |

- Cleanup logic correctly identifies files older than 1 year
- Retention policy is configurable and validates correctly
- Cleanup process runs safely without data corruption risk
- Disk usage is monitored and reported appropriately
- Cleanup activities are logged for audit purposes
- Integration with Windows Task Scheduler for automated execution

### Windows Task Scheduler Integration and Deployment

WPC-007

Create Windows Task Scheduler configurations and deployment scripts to enable automated execution of all system components on the specified schedule.

- Windows Task Scheduler XML configuration files
- Daily task configuration for data collection
- Monthly task configuration for decision and execution (15th of month)
- Task dependency management and sequencing
- Virtual environment activation in scheduled tasks
- Deployment scripts and setup automation
- Task monitoring and failure handling

- Alternative scheduling systems
- Cross-platform scheduling support
- Advanced task orchestration
- Real-time or event-driven scheduling

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-001 | — | must_complete_first | Requires virtual environment and basic infrastructure |
| WPC-002 | — | must_complete_first | Requires data collection script to be schedulable |
| WPC-003 | — | must_complete_first | Requires decision engine script to be schedulable |
| WPC-004 | — | must_complete_first | Requires execution engine script to be schedulable |

- Task Scheduler configurations are created and tested
- Daily data collection task runs automatically
- Monthly decision and execution tasks run on 15th of month with trading day logic
- Task dependencies ensure proper execution sequencing
- Virtual environment activation works in scheduled context
- Deployment process is documented and repeatable
- Task failure notifications integrate with monitoring system

### Integration Testing and Validation

WPC-008

Comprehensive testing of end-to-end system functionality including error scenarios, data source failures, and edge cases to ensure system reliability.

- End-to-end integration testing of all components
- Data source failure simulation and fallback testing
- Error handling and notification testing
- Edge case testing (market holidays, partial fills, API failures)
- Performance testing under normal load
- Configuration validation testing
- Audit trail verification and completeness testing

- Load testing or stress testing
- Security penetration testing
- User acceptance testing (no users in this system)
- Performance optimization beyond basic validation

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-002 | — | must_complete_first | Requires data collection functionality to test |
| WPC-003 | — | must_complete_first | Requires decision engine functionality to test |
| WPC-004 | — | must_complete_first | Requires execution engine functionality to test |
| WPC-005 | — | must_complete_first | Requires notification system to test error scenarios |

- All integration test scenarios pass successfully
- Data source fallback mechanisms work as expected
- Error notifications are triggered appropriately
- Edge cases are handled gracefully without system failure
- Audit trails are complete and accurate
- System performs adequately under normal operational load
- Configuration validation prevents invalid system states


---

# TA-001 — AI Portfolio Agent MVP: Technical Architecture

## Architecture Summary

AI Portfolio Agent MVP - Scheduled Windows Trading System

Three-component scheduled job architecture with event-driven CSV coordination

- Separate daily data collection from monthly decision/execution for clear separation of concerns
- CSV-based event coordination between components for auditability and debugging
- Python virtual environment with latest stable version for dependency isolation
- Shared workstation deployment with user profile configuration storage
- Accept partial fills with position adjustment rather than retry logic
- 90-day local data retention with automated cleanup
- Email notifications for error reporting with SMTP configuration
- Limit orders with ±0.5% price tolerance around last traded price

## Components

### DataCollector

Daily market data collection and technical indicator calculation

Python script with alpaca-trade-api, yfinance, pandas, ta-lib

- Alpaca Market Data API
- Yahoo Finance API (fallback)
- CSV output interface

- SharedConfig
- LoggingInfrastructure

### DecisionEngine

Monthly trading decision generation from technical indicators

Python script with pandas, numpy for indicator analysis

- CSV input interface
- CSV output interface

- DataCollector CSV output
- SharedConfig
- LoggingInfrastructure

### ExecutionEngine

Monthly trade execution via Alpaca paper trading API

Python script with alpaca-trade-api, smtplib for notifications

- Alpaca Trading API
- CSV input interface
- CSV output interface
- SMTP email interface

- DecisionEngine CSV output
- SharedConfig
- LoggingInfrastructure

### SharedConfig

Centralized configuration management for all components

Python configparser with JSON/INI file storage

- File system configuration interface

### LoggingInfrastructure

Centralized logging and audit trail management

Python logging module with file rotation

- Log file interface
- Console output interface

- SharedConfig

## Workflows

### DailyDataCollection

Windows Task Scheduler daily at 6 PM ET

| # | Action | Component | Output |
| --- | --- | --- | --- |
| 1 | Activate Python virtual environment | DataCollector | Environment ready |
| 2 | Load configuration and initialize logging | DataCollector | Configuration loaded, logging started |
| 3 | Fetch market data for each ticker from Alpaca | DataCollector | Raw market data or fallback trigger |
| 4 | On 403 error, switch to Yahoo Finance for that ticker | DataCollector | Market data from fallback source |
| 5 | Calculate technical indicators (RSI, SMA) | DataCollector | Technical indicators computed |
| 6 | Append data to CSV file with 90-day retention | DataCollector | market_data_YYYYMM.csv updated |
| 7 | Log completion status and any errors | DataCollector | Execution log entry |

### MonthlyDecisionGeneration

Windows Task Scheduler monthly on 1st at 7 AM ET

| # | Action | Component | Output |
| --- | --- | --- | --- |
| 1 | Activate Python virtual environment | DecisionEngine | Environment ready |
| 2 | Load latest market data CSV files | DecisionEngine | Market data and indicators loaded |
| 3 | Apply decision rules based on technical indicators | DecisionEngine | Trading decisions for each ticker |
| 4 | Calculate target allocations with 20% per ADD_20 ticker | DecisionEngine | Target allocation percentages |
| 5 | Write decisions to CSV with rationale | DecisionEngine | trading_decisions_YYYYMM.csv created |
| 6 | Log decision summary | DecisionEngine | Decision log entry |

### MonthlyTradeExecution

Windows Task Scheduler monthly on 1st at 8 AM ET

| # | Action | Component | Output |
| --- | --- | --- | --- |
| 1 | Activate Python virtual environment | ExecutionEngine | Environment ready |
| 2 | Load latest trading decisions CSV | ExecutionEngine | Trading decisions loaded |
| 3 | Get current account equity from Alpaca | ExecutionEngine | Current equity balance |
| 4 | Calculate required position changes | ExecutionEngine | Buy/sell quantities for each ticker |
| 5 | For each required trade, get current market price | ExecutionEngine | Current market prices |
| 6 | Submit limit orders with ±0.5% price tolerance | ExecutionEngine | Order IDs and initial status |
| 7 | Monitor orders for 30 minutes, accept partial fills | ExecutionEngine | — |

## Data Models

### MarketData

Daily market data with technical indicators

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| ticker | string | Yes | Stock ticker symbol |
| date | date | Yes | Trading date |
| close_price | decimal | Yes | Closing price |
| volume | integer | Yes | Trading volume |
| rsi_14 | decimal | No | 14-period RSI indicator |
| sma_20 | decimal | No | 20-period simple moving average |
| sma_50 | decimal | No | 50-period simple moving average |

- One-to-many with TradingDecision via ticker

### TradingDecision

Monthly trading decisions generated from indicators

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| ticker | string | Yes | Stock ticker symbol |
| decision_date | date | Yes | Decision generation date |
| action | string | Yes | Trading action: BUY, SELL, HOLD |
| target_allocation_pct | decimal | Yes | Target allocation percentage of equity |
| rationale | string | Yes | Decision rationale based on indicators |

- One-to-one with TradeExecution via ticker and decision_date

### TradeExecution

Executed trades with order details and results

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| ticker | string | Yes | Stock ticker symbol |
| execution_date | date | Yes | Trade execution date |
| order_id | string | Yes | Alpaca order ID |
| order_type | string | Yes | Order type: limit |
| side | string | Yes | Order side: buy or sell |
| quantity | integer | Yes | Requested share quantity |
| limit_price | decimal | Yes | Limit order price |
| filled_quantity | integer | Yes | Actually filled quantity |
| filled_price | decimal | No | Average fill price |
| status | string | Yes | Order status: filled, partially_filled, rejected, canceled |

- References TradingDecision via ticker and date

## API Interfaces

### AlpacaMarketData

REST

| Method | Path | Description |
| --- | --- | --- |
| GET | /v2/stocks/{ticker}/bars | Fetch daily market data for ticker |

### AlpacaTrading

REST

| Method | Path | Description |
| --- | --- | --- |
| POST | /v2/orders | Submit limit order for execution |
| GET | /v2/account | Get account equity and cash balance |

### YahooFinance

REST

| Method | Path | Description |
| --- | --- | --- |
| GET | /v8/finance/chart/{ticker} | Fallback market data source |

## Quality Attributes

- Daily data collection completes within 5 minutes for all 6 tickers
- Monthly decision generation completes within 2 minutes
- Monthly execution completes within 10 minutes including order confirmation

- Alpaca API keys stored in user profile configuration with file permissions 600
- SMTP credentials encrypted in configuration file
- No API keys logged in any output files
- Paper trading only - no live trading capability

- System handles up to 20 tickers without architecture changes
- CSV files sized for up to 2 years of daily data per ticker
- Log rotation prevents unbounded disk usage

- Each component is independently testable
- Configuration changes do not require code changes
- Clear error messages with actionable remediation steps
- Comprehensive logging for debugging and audit

- All API calls logged with request/response times
- Trading decisions logged with full rationale
- Order execution results logged with fill details
- Email notifications for all error conditions
- Daily health check logs confirming system operation


---

# WP-001 — Foundation and Configuration Infrastructure

## Overview

WP-001

Foundation and Configuration Infrastructure

Establish shared configuration management, logging infrastructure, and directory structure that all other components depend on. Includes API validation and basic error handling framework.

PLANNED

## Scope

- Configuration file structure and validation
- Shared logging infrastructure with file and console output
- Directory structure for data, logs, and output files
- Alpaca API connectivity validation during setup
- Error handling framework foundation
- Virtual environment activation scripts
- Basic utility functions for market calendar and trading day logic

1. All work statements executed and verified

## Governance

pending

## Work Statements

| Statement ID | Order |
| --- | --- |
| WS-001 | a0 |
| WS-002 | a1 |
| WS-003 | a2 |
| WS-004 | a3 |
| WS-005 | a4 |
| WS-006 | a5 |
| WS-007 | a6 |

## Revision

2026-03-08T22:07:06.457329+00:00

system

## Lineage

- WPC-001

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-001

kept

Promoted as-is from IP candidate.


---

### WS-001 — Project Directory Structure Setup

**State:** DRAFT

**Title:** Project Directory Structure Setup

**Ws Id:** WS-001

**Revision:** {'edition': 1}

**Scope In:** ['Create data directory for market data CSV files', 'Create logs directory for application logging', 'Create output directory for generated files', 'Create config directory for configuration files', 'Set appropriate directory permissions']

**Objective:** Establish the complete directory structure for data storage, logs, and output files with proper permissions

**Order Key:** a0

**Procedure:** ['Create root project directory structure', 'Create data/ subdirectory for market data storage', 'Create logs/ subdirectory for application logs', 'Create output/ subdirectory for generated reports', 'Create config/ subdirectory for configuration files', 'Set directory permissions to 755 for directories', 'Create .gitkeep files in empty directories for version control', 'Document directory structure in README.md']

**Scope Out:** ['Configuration file content creation', 'Logging configuration implementation', 'Virtual environment setup']

**Parent Wp Id:** WP-001

**Allowed Paths:** ['data/', 'logs/', 'output/', 'config/', 'README.md']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not create configuration files', 'Do not initialize logging systems', 'Do not create virtual environment']

**Verification Criteria:** ['data/ directory exists and is writable', 'logs/ directory exists and is writable', 'output/ directory exists and is writable', 'config/ directory exists and is writable', 'All directories have correct permissions (755)', 'Directory structure is documented']


---

### WS-002 — Shared Configuration Infrastructure

**State:** DRAFT

**Title:** Shared Configuration Infrastructure

**Ws Id:** WS-002

**Revision:** {'edition': 1}

**Scope In:** ['Configuration file structure design and implementation', 'Configuration validation framework', 'API credentials management structure', 'Email notification configuration structure', 'Ticker list configuration', 'File path configuration management']

**Objective:** Implement centralized configuration management system with validation for all application components

**Order Key:** a1

**Procedure:** ['Design configuration file schema for all components', 'Create SharedConfig component using Python configparser', 'Implement configuration validation methods', 'Create configuration file template with required sections', 'Implement API credentials configuration structure', 'Implement email notification configuration structure', 'Create ticker list configuration management', 'Add configuration file loading with error handling', 'Create configuration validation unit tests']

**Scope Out:** ['Actual API credential values', 'Logging system implementation', 'Virtual environment setup']

**Parent Wp Id:** WP-001

**Allowed Paths:** ['config/', 'src/', 'src/shared/', 'src/shared/config.py', 'config/app_config.ini', 'config/config_template.ini']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not include actual API credentials in configuration files', 'Do not implement logging functionality', 'Do not create virtual environment activation scripts']

**Verification Criteria:** ['SharedConfig component loads configuration files successfully', 'Configuration validation detects missing required fields', 'Configuration validation detects invalid data types', 'API credentials section structure is defined', 'Email configuration section structure is defined', 'Ticker list configuration is loadable', 'Configuration template file exists with all required sections', 'Unit tests pass for configuration loading and validation']


---

### WS-003 — Logging Infrastructure Implementation

**State:** DRAFT

**Title:** Logging Infrastructure Implementation

**Ws Id:** WS-003

**Revision:** {'edition': 1}

**Scope In:** ['Centralized logging infrastructure using Python logging module', 'File output with rotation capabilities', 'Console output configuration', 'Log level management', 'Audit trail logging structure', 'Integration with SharedConfig component']

**Objective:** Implement centralized logging system with file and console output, rotation, and audit trail capabilities

**Order Key:** a2

**Procedure:** ['Create LoggingInfrastructure component using Python logging module', 'Implement file logging with rotation using RotatingFileHandler', 'Implement console logging with appropriate formatting', 'Create log level configuration management', 'Implement audit trail logging methods', 'Integrate with SharedConfig for logging configuration', 'Create logging initialization methods for each component type', 'Add structured logging format for API calls and trading operations', 'Create logging infrastructure unit tests']

**Scope Out:** ['Application-specific logging calls', 'Virtual environment setup', 'Error handling for business logic']

**Parent Wp Id:** WP-001

**Allowed Paths:** ['src/shared/', 'src/shared/logging_infrastructure.py', 'logs/', 'config/app_config.ini']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement application-specific business logic', 'Do not create virtual environment activation scripts', 'Do not implement API connectivity validation']

**Verification Criteria:** ['LoggingInfrastructure component initializes successfully', 'File logging creates log files in logs/ directory', 'Log rotation works when file size limits are reached', 'Console logging displays messages with proper formatting', 'Different log levels (DEBUG, INFO, WARNING, ERROR) work correctly', 'Audit trail logging captures structured data', 'Integration with SharedConfig loads logging configuration', 'Unit tests pass for all logging functionality']


---

### WS-004 — Virtual Environment Setup and Activation Scripts

**State:** DRAFT

**Title:** Virtual Environment Setup and Activation Scripts

**Ws Id:** WS-004

**Revision:** {'edition': 1}

**Scope In:** ['Python virtual environment creation', 'Dependency management and installation', 'Windows activation scripts', 'Requirements file management', 'Environment validation scripts']

**Objective:** Create Python virtual environment with required dependencies and activation scripts for Windows deployment

**Order Key:** a3

**Procedure:** ['Create Python virtual environment in venv/ directory', 'Create requirements.txt with all necessary dependencies', 'Install required packages: alpaca-trade-api, yfinance, pandas, ta-lib, numpy, smtplib', 'Create Windows batch script for environment activation', 'Create setup script for initial environment configuration', 'Create Python script to validate environment and dependencies', 'Test virtual environment activation and package availability', 'Document environment setup process']

**Scope Out:** ['Application component implementation', 'Configuration file content', 'Scheduled task setup']

**Parent Wp Id:** WP-001

**Allowed Paths:** ['venv/', 'requirements.txt', 'scripts/', 'scripts/activate_env.bat', 'scripts/setup_env.bat', 'scripts/validate_env.py']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement application business logic', 'Do not create scheduled tasks or triggers', 'Do not implement API connectivity testing']

**Verification Criteria:** ['Virtual environment directory exists and contains Python interpreter', 'requirements.txt contains all necessary packages with versions', 'All required packages install successfully in virtual environment', 'activate_env.bat script activates virtual environment correctly', 'setup_env.bat script creates and configures environment', 'validate_env.py script confirms all dependencies are available', 'Virtual environment is isolated from system Python', 'Environment setup documentation is complete']


---

### WS-005 — Error Handling Framework Foundation

**State:** DRAFT

**Title:** Error Handling Framework Foundation

**Ws Id:** WS-005

**Revision:** {'edition': 1}

**Scope In:** ['Custom exception classes for different error types', 'Error handling patterns and utilities', 'Error reporting and notification framework', 'Recovery and retry logic foundation', 'Integration with logging infrastructure']

**Objective:** Implement foundational error handling framework with custom exceptions, error reporting, and recovery patterns

**Order Key:** a4

**Procedure:** ['Define custom exception hierarchy for different error categories', 'Create ConfigurationError exception for configuration issues', 'Create APIError exception for external API failures', 'Create ValidationError exception for data validation failures', 'Implement error handling utilities and decorators', 'Create error reporting framework that integrates with logging', 'Implement retry logic foundation with exponential backoff', 'Create error context management for debugging', 'Create unit tests for error handling framework']

**Scope Out:** ['Business logic error handling', 'API-specific error handling implementation', 'Email notification implementation']

**Parent Wp Id:** WP-001

**Allowed Paths:** ['src/shared/', 'src/shared/error_handling.py', 'src/shared/exceptions.py']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement business logic specific error handling', 'Do not implement actual email notification sending', 'Do not implement API-specific retry logic']

**Verification Criteria:** ['Custom exception classes are defined and inherit properly', 'Error handling utilities provide consistent error management', 'Error reporting integrates with LoggingInfrastructure component', 'Retry logic foundation provides configurable backoff strategies', 'Error context captures relevant debugging information', 'Exception hierarchy covers expected error categories', 'Unit tests validate error handling behavior', 'Error handling framework is documented']


---

### WS-006 — Alpaca API Connectivity Validation

**State:** DRAFT

**Title:** Alpaca API Connectivity Validation

**Ws Id:** WS-006

**Revision:** {'edition': 1}

**Scope In:** ['Alpaca API connection testing functionality', 'API credential validation', 'Network connectivity verification', 'Paper trading account validation', 'API rate limit detection', 'Connection health check utilities']

**Objective:** Implement API connectivity validation system to verify Alpaca API credentials and connection during system setup

**Order Key:** a5

**Procedure:** ['Create API validation component using alpaca-trade-api', 'Implement credential validation by testing account endpoint', 'Implement paper trading account verification', 'Create network connectivity testing for Alpaca endpoints', 'Implement API rate limit detection and reporting', 'Create connection health check methods', 'Integrate with SharedConfig for API credential loading', 'Integrate with LoggingInfrastructure for validation logging', 'Create standalone validation script for setup verification', 'Create unit tests for API validation functionality']

**Scope Out:** ['Market data collection implementation', 'Trading execution implementation', 'Yahoo Finance fallback implementation']

**Parent Wp Id:** WP-001

**Allowed Paths:** ['src/shared/', 'src/shared/api_validation.py', 'scripts/', 'scripts/validate_api.py']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement market data collection logic', 'Do not implement trade execution functionality', 'Do not implement Yahoo Finance API integration']

**Verification Criteria:** ['API validation component connects to Alpaca successfully with valid credentials', 'Invalid credentials are detected and reported appropriately', 'Paper trading account status is verified correctly', 'Network connectivity issues are detected and reported', 'API rate limits are detected and handled gracefully', 'Connection health checks return accurate status information', 'Validation integrates with SharedConfig and LoggingInfrastructure', 'Standalone validation script provides clear pass/fail results', 'Unit tests cover valid and invalid credential scenarios']


---

### WS-007 — Market Calendar and Trading Day Utilities

**State:** DRAFT

**Title:** Market Calendar and Trading Day Utilities

**Ws Id:** WS-007

**Revision:** {'edition': 1}

**Scope In:** ['Market calendar utility functions', 'Trading day validation logic', 'Business day calculation utilities', 'Market hours verification', 'Holiday detection functionality', 'Date manipulation utilities for trading operations']

**Objective:** Implement basic utility functions for market calendar operations and trading day logic validation

**Order Key:** a6

**Procedure:** ['Create market calendar utility functions', 'Implement trading day validation using market calendar data', 'Create business day calculation utilities', 'Implement market hours verification functionality', 'Create holiday detection for US market holidays', 'Implement date manipulation utilities for trading date calculations', 'Create utilities for determining next/previous trading days', 'Integrate with pandas for date handling capabilities', 'Create unit tests for all calendar and market utilities', 'Document utility functions and their usage']

**Scope Out:** ['Market data collection scheduling', 'Trading execution scheduling', 'Windows Task Scheduler integration']

**Parent Wp Id:** WP-001

**Allowed Paths:** ['src/shared/', 'src/shared/market_utils.py', 'src/shared/calendar_utils.py']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement scheduling or trigger logic', 'Do not implement Windows Task Scheduler integration', 'Do not implement component-specific business logic']

**Verification Criteria:** ['Market calendar utilities correctly identify trading days', 'Trading day validation accurately excludes weekends and holidays', 'Business day calculations handle month and year boundaries correctly', 'Market hours verification works for standard and early close days', 'Holiday detection includes all major US market holidays', 'Date manipulation utilities handle edge cases correctly', 'Next/previous trading day functions work across holiday periods', 'Unit tests cover various date scenarios and edge cases', 'Utility functions are documented with examples']


---

# WP-002 — Monthly Decision Engine

## Overview

WP-002

Monthly Decision Engine

Convert technical indicator data into trading decisions based on defined rules. Generates trading actions that respect risk parameters and position limits.

PLANNED

## Scope

- Technical indicator analysis and signal generation
- Trading decision logic based on indicator thresholds
- Risk parameter enforcement (5% cash buffer, 30% position cap)
- Position sizing calculations for 20% equity per ADD_20 ticker
- Decision output to CSV format for execution engine consumption
- Current position analysis and adjustment logic
- SPY baseline comparison and relative performance evaluation

1. All work statements executed and verified

## Governance

pending

## Work Statements

| Statement ID | Order |
| --- | --- |
| WS-008 | a0 |
| WS-009 | a1 |
| WS-010 | a2 |
| WS-011 | a3 |
| WS-012 | a4 |

## Revision

2026-03-08T22:09:27.993374+00:00

system

## Lineage

- WPC-003

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-003

kept

Promoted as-is from IP candidate.


---

### WS-008 — Technical Indicator Analysis Module

**State:** DRAFT

**Title:** Technical Indicator Analysis Module

**Ws Id:** WS-008

**Revision:** {'edition': 1}

**Scope In:** ['Technical indicator analysis and signal generation', 'RSI-based oversold/overbought signal detection', 'SMA crossover analysis for trend identification', 'Signal threshold configuration and evaluation']

**Objective:** Implement technical indicator analysis functionality to process market data and generate trading signals based on RSI and SMA thresholds

**Order Key:** a0

**Procedure:** ['Create decision_engine module structure with indicators and signals submodules', 'Implement RSI signal analysis class with configurable oversold/overbought thresholds', 'Implement SMA crossover analysis class for trend detection', 'Create signal aggregation logic to combine multiple indicator signals', 'Add configuration parameters for indicator thresholds and weights', 'Implement signal strength scoring based on indicator convergence', 'Add logging for all signal generation decisions with rationale']

**Scope Out:** ['Market data collection', 'Trade execution logic', 'Position sizing calculations', 'CSV output formatting']

**Parent Wp Id:** WP-002

**Allowed Paths:** ['src/decision_engine/', 'src/decision_engine/indicators/', 'src/decision_engine/signals/', 'tests/decision_engine/', 'config/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement market data fetching or API calls', 'Do not implement trade execution or order placement', 'Do not modify shared configuration structure', 'Do not implement CSV file I/O operations']

**Verification Criteria:** ['RSI signals correctly identify oversold (<30) and overbought (>70) conditions', 'SMA crossover signals detect when SMA_20 crosses above/below SMA_50', 'Signal aggregation produces consistent BUY/SELL/HOLD recommendations', 'All indicator calculations match expected values for test data', 'Configuration parameters successfully modify signal thresholds', 'Signal generation logs include clear rationale for each decision']


---

### WS-009 — Risk Parameter Enforcement Engine

**State:** DRAFT

**Title:** Risk Parameter Enforcement Engine

**Ws Id:** WS-009

**Revision:** {'edition': 1}

**Scope In:** ['Risk parameter enforcement (5% cash buffer, 30% position cap)', 'Cash buffer validation against account equity', 'Position size limit validation per ticker', 'Risk constraint violation detection and adjustment']

**Objective:** Implement risk management controls to enforce 5% cash buffer and 30% maximum position caps on all trading decisions

**Order Key:** a1

**Procedure:** ['Create risk management module within decision_engine', 'Implement cash buffer validator to ensure 5% minimum cash retention', 'Implement position cap validator to enforce 30% maximum per ticker', 'Create risk constraint aggregation logic for multiple simultaneous checks', 'Add risk violation adjustment algorithms to modify oversized positions', 'Implement risk parameter configuration loading from shared config', 'Add comprehensive logging for all risk enforcement decisions']

**Scope Out:** ['Position sizing calculations for specific allocations', 'Current position analysis', 'Trading signal generation', 'Decision output formatting']

**Parent Wp Id:** WP-002

**Allowed Paths:** ['src/decision_engine/', 'src/decision_engine/risk/', 'tests/decision_engine/risk/', 'config/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement account equity fetching or API calls', 'Do not implement position sizing calculations', 'Do not modify core configuration structure', 'Do not implement trading decision logic']

**Verification Criteria:** ['Cash buffer validator rejects decisions that would reduce cash below 5% of equity', 'Position cap validator limits any single ticker to maximum 30% allocation', 'Risk adjustment algorithms successfully reduce oversized positions to compliant levels', 'Multiple risk constraints are evaluated simultaneously and correctly', 'Risk parameters are successfully loaded from configuration files', 'All risk enforcement actions are logged with specific constraint violations']


---

### WS-010 — Position Sizing and Allocation Calculator

**State:** DRAFT

**Title:** Position Sizing and Allocation Calculator

**Ws Id:** WS-010

**Revision:** {'edition': 1}

**Scope In:** ['Position sizing calculations for 20% equity per ADD_20 ticker', 'Current position analysis and adjustment logic', 'Target allocation percentage calculations', 'Buy/sell quantity determination based on position deltas']

**Objective:** Implement position sizing calculations for 20% equity allocation per ADD_20 ticker with current position adjustment logic

**Order Key:** a2

**Procedure:** ['Create position sizing module within decision_engine', 'Implement target allocation calculator for 20% per ADD_20 ticker', 'Implement current position analyzer to determine existing holdings', 'Create position delta calculator to determine required buy/sell quantities', 'Add equity-based position sizing logic for dollar amount calculations', 'Implement position adjustment logic for partial fills and market changes', 'Add logging for all position sizing calculations and adjustments']

**Scope Out:** ['Risk parameter enforcement', 'Technical indicator analysis', 'Account equity fetching', 'Trade execution']

**Parent Wp Id:** WP-002

**Allowed Paths:** ['src/decision_engine/', 'src/decision_engine/position/', 'tests/decision_engine/position/', 'config/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement account equity API calls', 'Do not implement risk parameter validation', 'Do not implement trade execution or order placement', 'Do not modify shared configuration structure']

**Verification Criteria:** ['Target allocation correctly calculates 20% of equity per ADD_20 ticker', 'Position delta calculator accurately determines buy/sell quantities needed', 'Current position analysis correctly identifies existing holdings and values', 'Position sizing handles fractional shares according to broker constraints', 'Position adjustments correctly account for partial fills and market movements', 'All position calculations are logged with input values and results']


---

### WS-011 — SPY Baseline Performance Comparator

**State:** DRAFT

**Title:** SPY Baseline Performance Comparator

**Ws Id:** WS-011

**Revision:** {'edition': 1}

**Scope In:** ['SPY baseline comparison and relative performance evaluation', 'Portfolio performance calculation against SPY returns', 'Relative performance metrics and scoring', 'Performance comparison logging and reporting']

**Objective:** Implement SPY baseline comparison functionality to evaluate relative performance of portfolio decisions against market benchmark

**Order Key:** a3

**Procedure:** ['Create performance comparison module within decision_engine', 'Implement SPY return calculation logic from market data', 'Implement portfolio return calculation based on current positions', 'Create relative performance calculator comparing portfolio vs SPY returns', 'Add performance scoring logic for decision quality assessment', 'Implement performance comparison reporting for decision rationale', 'Add comprehensive logging for all performance calculations and comparisons']

**Scope Out:** ['SPY market data collection', 'Portfolio execution tracking', 'Trade execution performance', 'Long-term performance analytics']

**Parent Wp Id:** WP-002

**Allowed Paths:** ['src/decision_engine/', 'src/decision_engine/performance/', 'tests/decision_engine/performance/', 'config/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement SPY market data fetching', 'Do not implement trade execution tracking', 'Do not modify market data collection logic', 'Do not implement long-term performance storage']

**Verification Criteria:** ['SPY return calculations match expected values for test periods', 'Portfolio return calculations accurately reflect position performance', 'Relative performance metrics correctly show over/under-performance vs SPY', 'Performance scoring provides consistent quality assessment of decisions', 'Performance comparisons are included in decision rationale output', 'All performance calculations are logged with input data and results']


---

### WS-012 — Trading Decision Integration and CSV Output

**State:** DRAFT

**Title:** Trading Decision Integration and CSV Output

**Ws Id:** WS-012

**Revision:** {'edition': 1}

**Scope In:** ['Trading decision logic based on indicator thresholds', 'Decision output to CSV format for execution engine consumption', 'Integration of technical indicators, risk controls, and position sizing', 'Decision rationale compilation and output formatting']

**Objective:** Integrate all decision engine components and implement CSV output formatting for execution engine consumption

**Order Key:** a4

**Procedure:** ['Create main decision engine orchestrator to coordinate all components', 'Implement decision workflow that processes indicators, applies risk controls, and calculates positions', 'Create CSV output formatter matching execution engine input requirements', 'Implement decision rationale compiler that aggregates all component reasoning', 'Add decision validation logic to ensure output completeness and consistency', 'Create decision engine entry point script for scheduled execution', 'Add comprehensive error handling and logging for the complete decision workflow']

**Scope Out:** ['Market data input processing', 'Trade execution', 'Account management', 'Error handling for external dependencies']

**Parent Wp Id:** WP-002

**Allowed Paths:** ['src/decision_engine/', 'src/decision_engine/output/', 'tests/decision_engine/', 'data/decisions/', 'config/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not implement market data input parsing', 'Do not implement trade execution logic', 'Do not modify shared configuration structure', 'Do not implement scheduling or task management']

**Verification Criteria:** ['Decision engine orchestrator successfully integrates all component modules', 'CSV output format matches TradingDecision data model specification exactly', 'Decision rationale includes inputs from indicators, risk controls, and performance comparison', 'Decision validation catches incomplete or inconsistent outputs before CSV generation', 'Entry point script can be executed independently with proper configuration', 'All decision workflow steps are logged with timing and component status']


---

# WP-003 — Integration Testing and Validation

## Overview

WP-003

Integration Testing and Validation

Comprehensive testing of end-to-end system functionality including error scenarios, data source failures, and edge cases to ensure system reliability.

PLANNED

## Scope

- End-to-end integration testing of all components
- Data source failure simulation and fallback testing
- Error handling and notification testing
- Edge case testing (market holidays, partial fills, API failures)
- Performance testing under normal load
- Configuration validation testing
- Audit trail verification and completeness testing

1. All work statements executed and verified

## Governance

pending

## Work Statements

| Statement ID | Order |
| --- | --- |
| WS-013 | a0 |
| WS-014 | a1 |
| WS-015 | a2 |
| WS-016 | a3 |
| WS-017 | a4 |
| WS-018 | a5 |
| WS-019 | a6 |

## Revision

2026-03-08T22:11:07.954505+00:00

system

## Lineage

- WPC-008

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-008

kept

Promoted as-is from IP candidate.


---

### WS-013 — End-to-End Integration Test Suite Development

**State:** DRAFT

**Title:** End-to-End Integration Test Suite Development

**Ws Id:** WS-013

**Revision:** {'edition': 1}

**Scope In:** ['End-to-end integration testing of all components', 'Test framework setup for component interaction validation', 'Integration test cases for normal workflow execution', 'CSV-based event coordination testing between components']

**Objective:** Develop comprehensive integration test suite that validates complete system workflow from data collection through trade execution

**Order Key:** a0

**Procedure:** ['Create integration test directory structure under tests/integration/', 'Set up pytest configuration for integration testing', 'Create test fixtures for mock CSV data files', 'Develop test_full_workflow.py that exercises DataCollector → DecisionEngine → ExecutionEngine flow', 'Create mock API response fixtures for Alpaca and Yahoo Finance', 'Implement test cases that verify CSV file creation and consumption between components', 'Add assertions to verify data model integrity across component boundaries', 'Create test utilities for component initialization and cleanup']

**Scope Out:** ['Unit testing of individual components', 'Performance testing implementation', 'Error scenario testing', 'Edge case testing']

**Parent Wp Id:** WP-003

**Allowed Paths:** ['tests/', 'tests/integration/', 'tests/fixtures/', 'tests/conftest.py', 'requirements-test.txt']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not modify production component code', 'Do not create tests that require live API access', 'Do not implement performance testing in this work statement']

**Verification Criteria:** ['Integration test suite executes successfully with pytest', 'Test coverage includes all three main components interaction', 'CSV coordination between components is validated', 'Test fixtures provide realistic data for all data models', 'All integration tests pass without errors']


---

### WS-014 — Data Source Failure and Fallback Testing

**State:** DRAFT

**Title:** Data Source Failure and Fallback Testing

**Ws Id:** WS-014

**Revision:** {'edition': 1}

**Scope In:** ['Data source failure simulation and fallback testing', 'Alpaca API failure simulation', 'Yahoo Finance fallback mechanism validation', 'API error response handling verification']

**Objective:** Implement and validate data source failure scenarios and automatic fallback mechanisms

**Order Key:** a1

**Procedure:** ['Create mock API response fixtures for Alpaca 403 Forbidden errors', 'Create mock API response fixtures for Alpaca 500 Server errors', 'Implement test cases that simulate Alpaca API failures', 'Verify DataCollector switches to Yahoo Finance on 403 errors', 'Test Yahoo Finance fallback data retrieval and processing', 'Validate that technical indicators are calculated correctly from fallback data', 'Test logging of fallback events and error conditions', 'Verify CSV output consistency regardless of data source']

**Scope Out:** ['Network infrastructure testing', 'Authentication failure testing', 'Rate limiting testing implementation']

**Parent Wp Id:** WP-003

**Allowed Paths:** ['tests/integration/', 'tests/fixtures/api_responses/', 'tests/test_data_source_fallback.py']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not test against live APIs', 'Do not modify the fallback logic implementation', 'Do not test rate limiting scenarios']

**Verification Criteria:** ['Fallback tests execute successfully with mocked API failures', 'DataCollector switches to Yahoo Finance when Alpaca returns 403', 'Technical indicators calculated correctly from fallback data', 'Error events are properly logged with appropriate severity', 'CSV output format remains consistent across data sources']


---

### WS-015 — Error Handling and Notification Testing

**State:** DRAFT

**Title:** Error Handling and Notification Testing

**Ws Id:** WS-015

**Revision:** {'edition': 1}

**Scope In:** ['Error handling and notification testing', 'Email notification testing for error conditions', 'Component-level error handling validation', 'SMTP configuration and delivery testing']

**Objective:** Validate error handling mechanisms and email notification system across all components

**Order Key:** a2

**Procedure:** ['Create test fixtures for various error scenarios in each component', 'Implement mock SMTP server for email notification testing', 'Test DataCollector error handling for API failures and data processing errors', 'Test DecisionEngine error handling for malformed CSV input and calculation errors', 'Test ExecutionEngine error handling for order submission and account access errors', 'Validate email notification content and formatting for each error type', 'Test error logging with appropriate severity levels', 'Verify system continues operation after recoverable errors']

**Scope Out:** ['Email server infrastructure testing', 'Network connectivity testing', 'Authentication error testing']

**Parent Wp Id:** WP-003

**Allowed Paths:** ['tests/integration/', 'tests/test_error_handling.py', 'tests/test_notifications.py', 'tests/fixtures/error_scenarios/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not send emails to real addresses during testing', 'Do not modify error handling logic in components', 'Do not test external email server configurations']

**Verification Criteria:** ['Error handling tests cover all major failure modes', 'Email notifications are sent for appropriate error conditions', 'Error messages contain actionable remediation information', 'Logging captures error details with proper severity levels', 'System gracefully handles and recovers from non-fatal errors']


---

### WS-016 — Edge Case and Market Condition Testing

**State:** DRAFT

**Title:** Edge Case and Market Condition Testing

**Ws Id:** WS-016

**Revision:** {'edition': 1}

**Scope In:** ['Edge case testing (market holidays, partial fills, API failures)', 'Market holiday handling validation', 'Partial fill acceptance and position adjustment testing', 'API failure recovery testing']

**Objective:** Validate system behavior under edge cases including market holidays, partial fills, and API failures

**Order Key:** a3

**Procedure:** ['Create test fixtures for market holiday scenarios with no trading data', 'Create mock order responses for partial fill scenarios', 'Implement tests for DataCollector behavior on market holidays', 'Test DecisionEngine handling of incomplete market data', 'Test ExecutionEngine partial fill acceptance and position adjustment logic', 'Validate system behavior when API returns empty or null responses', 'Test order monitoring and timeout handling in ExecutionEngine', 'Verify audit trail completeness for edge case scenarios']

**Scope Out:** ['Live market testing', 'Historical data accuracy validation', 'Timezone handling testing']

**Parent Wp Id:** WP-003

**Allowed Paths:** ['tests/integration/', 'tests/test_edge_cases.py', 'tests/fixtures/edge_cases/', 'tests/fixtures/market_data/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not modify partial fill acceptance logic', 'Do not test against live market conditions', 'Do not implement new edge case handling logic']

**Verification Criteria:** ['System handles market holidays without errors', 'Partial fills are accepted and positions adjusted correctly', 'Edge case scenarios are logged with appropriate detail', 'System continues operation after edge case encounters', 'Audit trail maintains completeness for all edge cases']


---

### WS-017 — Performance Testing Under Normal Load

**State:** DRAFT

**Title:** Performance Testing Under Normal Load

**Ws Id:** WS-017

**Revision:** {'edition': 1}

**Scope In:** ['Performance testing under normal load', 'Component execution timing validation', 'Resource utilization monitoring', 'Workflow completion time verification']

**Objective:** Validate system performance meets specified timing requirements under normal operating conditions

**Order Key:** a4

**Procedure:** ['Create performance test fixtures with realistic data volumes for 6 tickers', 'Implement timing measurement utilities for component execution', 'Test DataCollector execution time with full ticker list (target: under 5 minutes)', 'Test DecisionEngine execution time with monthly data processing (target: under 2 minutes)', 'Test ExecutionEngine execution time including order confirmation (target: under 10 minutes)', 'Monitor resource utilization during normal operations', 'Validate CSV file processing performance with 90 days of data', 'Test logging performance impact on overall execution time']

**Scope Out:** ['Stress testing beyond normal load', 'Memory leak testing', 'Concurrent execution testing']

**Parent Wp Id:** WP-003

**Allowed Paths:** ['tests/performance/', 'tests/test_performance.py', 'tests/fixtures/performance_data/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not optimize component code for performance', 'Do not test with more than 20 tickers', 'Do not implement caching or performance enhancements']

**Verification Criteria:** ['DataCollector completes within 5 minutes for 6 tickers', 'DecisionEngine completes within 2 minutes for monthly processing', 'ExecutionEngine completes within 10 minutes including confirmations', 'Resource utilization remains within acceptable bounds', 'Performance tests execute consistently across multiple runs']


---

### WS-018 — Configuration Validation Testing

**State:** DRAFT

**Title:** Configuration Validation Testing

**Ws Id:** WS-018

**Revision:** {'edition': 1}

**Scope In:** ['Configuration validation testing', 'SharedConfig component validation', 'Configuration file format validation', 'Component configuration loading verification']

**Objective:** Validate configuration management and validation across all system components

**Order Key:** a5

**Procedure:** ['Create test configuration files with valid and invalid formats', 'Test SharedConfig component initialization and loading', 'Validate configuration parameter validation for each component', 'Test component behavior with missing configuration parameters', 'Test configuration file parsing for JSON and INI formats', 'Validate API key configuration loading (without exposing actual keys)', 'Test SMTP configuration validation for notification setup', 'Verify configuration error reporting and logging']

**Scope Out:** ['Configuration security testing', 'Configuration migration testing', 'Runtime configuration changes']

**Parent Wp Id:** WP-003

**Allowed Paths:** ['tests/integration/', 'tests/test_configuration.py', 'tests/fixtures/config/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not use real API keys or credentials in tests', 'Do not modify SharedConfig implementation', 'Do not test configuration encryption mechanisms']

**Verification Criteria:** ['Configuration validation tests pass for all components', 'Invalid configurations are properly rejected with clear error messages', 'Missing configuration parameters are handled gracefully', 'Configuration loading errors are logged appropriately', 'All components successfully initialize with valid test configurations']


---

### WS-019 — Audit Trail Verification and Completeness Testing

**State:** DRAFT

**Title:** Audit Trail Verification and Completeness Testing

**Ws Id:** WS-019

**Revision:** {'edition': 1}

**Scope In:** ['Audit trail verification and completeness testing', 'Logging infrastructure validation', 'Trade execution audit verification', 'Decision rationale audit verification']

**Objective:** Validate audit trail completeness and data integrity across all system operations

**Order Key:** a6

**Procedure:** ['Create test scenarios that generate complete audit trails', 'Validate logging of all API calls with request/response times', 'Test trading decision logging with full rationale capture', 'Verify order execution result logging with fill details', 'Test audit trail continuity across component boundaries', 'Validate log entry format consistency and completeness', 'Test audit trail reconstruction from log files', 'Verify sensitive data (API keys) are not logged']

**Scope Out:** ['Log retention policy testing', 'Log rotation mechanism testing', 'Log security and access control testing']

**Parent Wp Id:** WP-003

**Allowed Paths:** ['tests/integration/', 'tests/test_audit_trail.py', 'tests/fixtures/audit_scenarios/']

**Governance Pins:** {'adr_refs': [], 'policy_refs': [], 'ta_version_id': 'pending'}

**Prohibited Actions:** ['Do not modify logging implementation in components', 'Do not test log file encryption or security', 'Do not implement new audit trail features']

**Verification Criteria:** ['Complete audit trail is generated for full system workflow', 'All trading decisions include rationale in audit logs', 'Order execution details are completely captured in logs', 'API interactions are logged with timing information', 'Audit trail allows complete workflow reconstruction', 'No sensitive credentials appear in audit logs']


---

# WP-004 — Windows Task Scheduler Integration and Deployment

## Overview

WP-004

Windows Task Scheduler Integration and Deployment

Create Windows Task Scheduler configurations and deployment scripts to enable automated execution of all system components on the specified schedule.

PLANNED

## Scope

- Windows Task Scheduler XML configuration files
- Daily task configuration for data collection
- Monthly task configuration for decision and execution (15th of month)
- Task dependency management and sequencing
- Virtual environment activation in scheduled tasks
- Deployment scripts and setup automation
- Task monitoring and failure handling

1. All work statements executed and verified

## Governance

pending

## Revision

2026-03-08T22:09:59.109236+00:00

system

## Lineage

- WPC-007

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-007

kept

Promoted as-is from IP candidate.


---

# WP-005 — Data Retention and Cleanup Automation

## Overview

WP-005

Data Retention and Cleanup Automation

Implement automated cleanup of CSV files and logs based on 1-year retention policy to prevent unlimited disk usage growth.

PLANNED

## Scope

- Automated cleanup logic for CSV files older than 1 year
- Log file rotation and retention management
- Disk usage monitoring and reporting
- Cleanup scheduling and execution
- Retention policy configuration and validation
- Safe deletion with backup verification

1. All work statements executed and verified

## Governance

pending

## Revision

2026-03-08T22:10:00.457810+00:00

system

## Lineage

- WPC-006

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-006

kept

Promoted as-is from IP candidate.


---

# WP-006 — Market Data Collection and Technical Indicators

## Overview

WP-006

Market Data Collection and Technical Indicators

Implement daily data collection from Alpaca/Yahoo with fallback logic and calculate technical indicators required for decision making. Produces CSV artifacts consumed by decision engine.

PLANNED

## Scope

- Daily market data fetching from Alpaca Market Data (IEX)
- Yahoo Finance fallback implementation for 403 errors
- Technical indicator calculation (basic set for MVP)
- CSV output generation for market data and indicators
- Data validation and quality checks
- Retry logic and error handling for data source failures
- Historical data backfill capability

1. All work statements executed and verified

## Governance

pending

## Revision

2026-03-08T22:10:04.039323+00:00

system

## Lineage

- WPC-002

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-002

kept

Promoted as-is from IP candidate.


---

# WP-007 — Monthly Trade Execution Engine

## Overview

WP-007

Monthly Trade Execution Engine

Execute trading decisions through Alpaca API using limit orders with partial fill handling. Maintains audit trail and handles execution errors.

PLANNED

## Scope

- Trading decision consumption from CSV input
- Limit order placement through Alpaca API (±0.5% around last price)
- Partial fill handling with accept and log strategy
- Order status monitoring and completion tracking
- Trade execution audit trail in CSV format
- Position reconciliation after execution
- Execution error handling and recovery

1. All work statements executed and verified

## Governance

pending

## Revision

2026-03-08T22:10:04.106105+00:00

system

## Lineage

- WPC-004

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-004

kept

Promoted as-is from IP candidate.


---

# WP-008 — Notification and Monitoring Infrastructure

## Overview

WP-008

Notification and Monitoring Infrastructure

Implement email notification system for error handling and establish monitoring capabilities for system health and execution status.

PLANNED

## Scope

- SMTP configuration and email sending capability
- Error notification templates and triggers
- System health monitoring and status reporting
- Execution summary notifications
- Log file monitoring and alerting
- Email notification testing and validation

1. All work statements executed and verified

## Governance

pending

## Revision

2026-03-08T22:10:04.175209+00:00

system

## Lineage

- WPC-005

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-005

kept

Promoted as-is from IP candidate.

