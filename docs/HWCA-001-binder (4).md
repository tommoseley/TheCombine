# HWCA-001 — Hello World CLI Application

> Generated: 2026-03-07T02:37:44.571484+00:00
> Renderer: render-md@1.0.0
> Documents: 5

## Table of Contents

### Project Governance
  - [GOV-SEC-T0-002 -- Tier-0 Secrets Handling and Ingress Control Policy](#gov-sec-t0-002)
  - [POL-ADR-EXEC-001: ADR Execution Authorization Process](#pol-adr-exec-001)
  - [POL-ARCH-001: Architectural Integrity Standard](#pol-arch-001)
  - [POL-CODE-001: Code Construction Standard](#pol-code-001)
  - [POL-QA-001: Testing & Verification Standard](#pol-qa-001)
  - [POL-WS-001: Standard Work Statements](#pol-ws-001)

### Pipeline Documents
- [CI-001 — Concierge Intake: Hello World CLI Application](#ci-001)
- [PD-001 — Hello World CLI Application](#pd-001)
- [IP-001 — Hello World CLI Application: Implementation Plan](#ip-001)
- [TA-001 — Hello World CLI Application: Technical Architecture](#ta-001)
- [WP-001 — Core Hello World CLI Implementation](#wp-001)

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

# CI-001 — Concierge Intake: Hello World CLI Application

**Outcome:** {'status': 'qualified', 'rationale': 'Request is straightforward and well-defined. A hello world CLI application is a standard, achievable project with clear success criteria.', 'next_action': 'Proceed to implementation phase with language/platform selection and basic CLI application development.'}

**Summary:** {'description': "The user wants to create a simple command-line interface application that outputs 'hello world' when executed. This is a basic greenfield development project, likely for learning purposes or as a starting point for CLI development.", 'user_statement': 'I want to build a hello world CLI application'}

**Version:** 1.0

**Open Gaps:** {'questions': ['Which programming language should be used (Python, Go, Node.js, etc.)?', 'What platform(s) should this run on (Windows, macOS, Linux)?', 'Are there any specific CLI framework preferences?'], 'missing_context': ['Developer experience level', 'Intended use case beyond hello world', 'Development environment setup'], 'assumptions_made': ['This is a learning or starter project', 'User has basic development environment available', 'Simple console output is sufficient']}

**Constraints:** {'explicit': ['Must be a command-line interface application', "Must output 'hello world' when executed"], 'inferred': [], 'none_stated': False}

**Project Name:** Hello World CLI Application

**Project Type:** {'category': 'produce_output', 'rationale': 'User wants to create a new CLI application from scratch, which is clearly a produce output scenario.', 'confidence': 'high'}

**Document Type:** concierge_intake_document


---

# PD-001 — Hello World CLI Application

## Preliminary Summary

User wants to create a simple Python command-line application that outputs 'hello world' when executed. This appears to be a foundational project, potentially for learning CLI development or as a starting point for more complex functionality. The application needs to run on Windows and should follow standard CLI conventions.

Minimal viable CLI application with clean, extensible structure that can serve as a foundation for future enhancements while remaining simple for the core hello world functionality.

Single Python script or simple package structure with entry point, argument parsing capability, and clean separation between CLI interface and core functionality. Standard Python packaging structure to support potential distribution methods.

## Project Name

Hello World CLI Application

## Unknowns

| ID | Question | Why It Matters | Impact If Unresolved |
| --- | --- | --- | --- |
| UNK-1 | What is the intended use case beyond hello world functionality? | Understanding future extensibility affects initial code structure and architectural decisions. | May result in over-engineering for a simple script or under-engineering for a foundation application. |
| UNK-2 | What is the developer's experience level with Python and CLI development? | Experience level determines appropriate complexity, patterns, and tooling recommendations. | May recommend approaches that are too complex or too simplistic for the developer's skill level. |
| UNK-3 | Is there an existing development environment setup or does it need to be established? | Environment setup affects initial project structure and dependency management approach. | May encounter blockers during initial development setup phase. |

## Assumptions

| ID | Assumption | Confidence | Validation |
| --- | --- | --- | --- |
| ASM-1 | This is a learning or starter project rather than production software | medium | Confirm with user during stakeholder questions |
| ASM-2 | User has basic development environment available | medium | Verify Python installation and development tools during setup |
| ASM-3 | Simple console output is sufficient for the hello world functionality | high | Confirmed by explicit requirement in intake |

## Known Constraints

| ID | Constraint | Type |
| --- | --- | --- |
| CNS-1 | Must be implemented in Python | technical |
| CNS-2 | Must support Windows platform | technical |

## MVP Guardrails

| ID | Guardrail |
| --- | --- |
| GRD-1 | Must be a command-line interface application |
| GRD-2 | Must output 'hello world' when executed |

## Early Decision Points

### CLI framework selection

EDP-1

Framework choice affects project structure, dependency management, and extensibility patterns from the start.

- Built-in argparse (no dependencies)
- Click framework (popular, feature-rich)
- Typer (modern, type-hint based)
- Fire (automatic CLI generation)

Start with built-in argparse for simplicity, can migrate to framework if extensibility is confirmed

### Distribution approach

EDP-2

Distribution method affects project structure, packaging requirements, and dependency management strategy.

- Source code only (simple .py file)
- Python package with setup.py/pyproject.toml
- Executable with PyInstaller
- pip-installable package

Start with simple .py file, establish package structure if distribution needs emerge

## Stakeholder Questions

| ID | Question | Directed To | Blocking |
| --- | --- | --- | --- |
| STQ-1 | Is this intended to be extended beyond hello world functionality in the future? | product_owner | No |
| STQ-2 | Are there any specific CLI framework or library preferences based on team standards or experience? | tech_lead | No |
| STQ-3 | How should the CLI application be distributed or installed for end users? | product_owner | No |

## Recommendations for PM

| ID | Recommendation |
| --- | --- |
| RPM-1 | Confirm developer experience level and available development environment to tailor implementation approach appropriately. |
| RPM-2 | Clarify extensibility intent early to determine appropriate initial architecture complexity. |
| RPM-3 | Consider scheduling a brief technical setup session to verify Python environment and development tools. |


---

# IP-001 — Hello World CLI Application: Implementation Plan

## Plan Summary

Create a minimal Python command-line application that outputs 'hello world' when executed, optimized for simplicity and immediate functionality rather than extensibility.

A single Python script that can be executed from the command line on Windows and outputs 'hello world' to the console.

- Must be implemented in Python
- Must support Windows platform
- Must be a command-line interface application
- Must output 'hello world' when executed
- Minimal scope - no CLI argument parsing, help text, or error handling required
- No future extensibility requirements

Single work package approach since minimal scope eliminates need for complex dependencies or parallel work streams. Core functionality and basic validation can be completed in one cohesive effort.

- User has Python installed and available in PATH
- Basic development environment is available
- Simple console output meets all requirements
- No distribution packaging required initially

- CLI argument parsing and help text
- Error handling and validation
- Extensible architecture for future features
- Automated testing infrastructure
- Documentation beyond basic usage
- Distribution packaging or installation mechanisms

## Work Package Candidates

### Core Hello World CLI Implementation

WPC-001

Implements the fundamental requirement to create a Python CLI application that outputs 'hello world' when executed, addressing all core functionality in a single minimal script.

- Create Python script with executable entry point
- Implement hello world output functionality
- Ensure Windows platform compatibility
- Verify script can be executed from command line
- Basic manual testing to confirm output

- Command-line argument parsing
- Help text or usage instructions
- Error handling for edge cases
- Automated test suite creation
- Package structure or distribution setup
- Documentation beyond inline comments

- Python script executes successfully on Windows
- Script outputs exactly 'hello world' when run
- Script can be invoked from command line using python command
- Code includes basic inline comments explaining functionality
- Manual verification confirms all requirements met

This is a self-contained implementation requiring no external dependencies or complex architecture decisions. Can proceed directly to implementation once basic Python environment is confirmed.

## Risk Summary

| Risk | Affected Candidates | Impact | Mitigation |
| --- | --- | --- | --- |
| Python environment not properly configured or accessible | ['WPC-001'] | medium | Verify Python installation and PATH configuration before beginning implementation. Document any environment setup requirements discovered during development. |
| Windows-specific execution issues or path handling problems | ['WPC-001'] | low | Test script execution on Windows environment early in development cycle. Use standard Python practices that are cross-platform compatible by default. |

## Architecture Recommendations

- Confirm Python version requirements and any Windows-specific considerations
- Validate that simple script approach meets all technical constraints
- Consider file naming and execution conventions for Windows CLI applications

## Open Questions

| Question | Why It Matters | Owner | Status |
| --- | --- | --- | --- |
| What Python version should be targeted for compatibility? | Different Python versions may have different availability or behavior on Windows systems | technical_lead | open |
| Should the script include a shebang line or other execution metadata? | May affect how the script is invoked on Windows systems | technical_lead | open |


---

# TA-001 — Hello World CLI Application: Technical Architecture

## Architecture Summary

Hello World CLI Application Architecture

Single-file monolithic script

- Use built-in argparse for CLI interface to avoid external dependencies
- Single Python file structure for local development simplicity
- Standard library only implementation for minimal complexity
- Direct console output without structured logging for MVP

## Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Python environment not available on target system | high | Document Python version requirements and installation instructions | identified |
| Path or execution permissions issues on Windows | medium | Provide clear execution instructions and troubleshooting guide | identified |
| Over-engineering for simple hello world requirement | low | Keep implementation minimal and focused on core requirement | mitigated |

## Open Questions

| Question | Impact | Default Assumption |
| --- | --- | --- |
| Should the application support additional command line options beyond help? | Affects CLI interface design and argument parsing complexity | Minimal options only - help and basic execution |
| Is there a preference for specific Python version compatibility? | Determines available language features and deployment requirements | Use modern Python 3.x features (3.8+) for clean code |
| Should the hello world message be configurable or always static? | Determines if configuration handling is needed | Static 'hello world' message as specified in requirements |

## MVP Scope

- Single Python file implementation
- Basic command line argument parsing
- Hello world console output
- Help text display
- Basic error handling with exit codes
- Windows platform compatibility

- Package structure and distribution
- Advanced CLI frameworks (Click, Typer)
- Configuration file support
- Structured logging
- Unit testing framework
- Executable packaging with PyInstaller

## Components

### CLI Interface

Parse command line arguments and coordinate application execution

Python argparse

- Command line argument parsing
- Help text generation
- Error message display

- Core Logic

### Core Logic

Execute the hello world functionality and handle basic application logic

Python standard library

- hello_world() function
- Error handling wrapper

### Entry Point

Application initialization and main execution flow

Python __main__ pattern

- if __name__ == '__main__' block

- CLI Interface

## Workflows

### Standard Execution

User runs python hello_world.py

| # | Action | Component | Output |
| --- | --- | --- | --- |
| 1 | Parse command line arguments | CLI Interface | Parsed arguments object |
| 2 | Execute hello world logic | Core Logic | hello world string |
| 3 | Output to console | CLI Interface | Console display and exit code 0 |

### Help Display

User runs python hello_world.py --help

| # | Action | Component | Output |
| --- | --- | --- | --- |
| 1 | Parse help flag | CLI Interface | Help request identified |
| 2 | Display usage information | CLI Interface | Help text to console and exit code 0 |

### Error Handling

Invalid arguments or runtime error

| # | Action | Component | Output |
| --- | --- | --- | --- |
| 1 | Catch exception or invalid input | CLI Interface | Error condition identified |
| 2 | Display error message | CLI Interface | Error message to stderr and non-zero exit code |

## Data Models

### CommandArguments

Parsed command line arguments structure

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| help | boolean | No | Display help message flag |
| version | boolean | No | Display version information flag |

## API Interfaces

### Command Line Interface

internal

| Method | Path | Description |
| --- | --- | --- |
| CLI | python hello_world.py | Main application execution |
| CLI | python hello_world.py --help | Display help information |

## Quality Attributes

- Sub-second execution time for hello world output
- Minimal memory footprint

- No external network access required
- No file system write operations
- No sensitive data handling

- Single-user local execution only
- No concurrent execution requirements

- Single file structure for easy modification
- Clear function separation for testability
- Standard Python conventions

- Console output for success indication
- Standard error stream for error messages
- Exit codes for script integration


---

# WP-001 — Core Hello World CLI Implementation

## Overview

WP-001

Core Hello World CLI Implementation

Implements the fundamental requirement to create a Python CLI application that outputs 'hello world' when executed, addressing all core functionality in a single minimal script.

PLANNED

## Scope

- Create Python script with executable entry point
- Implement hello world output functionality
- Ensure Windows platform compatibility
- Verify script can be executed from command line
- Basic manual testing to confirm output

1. All work statements executed and verified

## Governance

pending

## Revision

2026-03-04T22:27:15.751259+00:00

system

## Lineage

- WPC-001

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-001

kept

Promoted as-is from IP candidate.

