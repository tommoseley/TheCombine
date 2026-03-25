# CHWA-002 — CLI Hello World Application

> Generated: 2026-03-07T02:33:53.665184+00:00
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
- [CI-001 — Concierge Intake: CLI Hello World Application](#ci-001)
- [PD-001 — CLI Hello World Application](#pd-001)
- [IP-001 — CLI Hello World Application: Implementation Plan](#ip-001)
- [TA-001 — CLI Hello World Application: Technical Architecture](#ta-001)
- [WP-001 — Core Python Implementation](#wp-001)

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

# CI-001 — Concierge Intake: CLI Hello World Application

**Outcome:** {'status': 'qualified', 'rationale': 'Request is clear and straightforward - create a CLI application that outputs hello world. This is a well-defined, basic programming task that can proceed with reasonable defaults for missing technical details.', 'next_action': 'Proceed to implementation phase with a common language choice (e.g., Python, Go, or C) and cross-platform approach.'}

**Summary:** {'description': "The user wants a simple command-line interface application that outputs 'hello world' when executed. This is a basic CLI tool development request for creating a minimal executable program.", 'user_statement': 'I need an application that gives me a CLI hello world.'}

**Version:** 1.0

**Open Gaps:** {'questions': ['What programming language should be used?', 'What operating system should this target?', 'Should this be a standalone executable or require a runtime?'], 'missing_context': ['Target platform and environment', 'Programming language preference', 'Packaging requirements'], 'assumptions_made': ['User wants a simple, basic implementation', "Standard 'Hello, World!' output format is acceptable"]}

**Constraints:** {'explicit': ['Must be a command-line interface application', "Must output 'hello world' when executed"], 'inferred': [], 'none_stated': False}

**Project Name:** CLI Hello World Application

**Project Type:** {'category': 'produce_output', 'rationale': 'User is requesting creation of a specific deliverable - a CLI application that produces output.', 'confidence': 'high'}

**Document Type:** concierge_intake_document


---

# PD-001 — CLI Hello World Application

## Preliminary Summary

User needs a simple command-line application that outputs 'hello world' when executed. This is a basic CLI tool development request for personal use on Windows platform. The application should be minimal and straightforward without complex features.

Minimal executable approach - single-purpose CLI tool with no external dependencies or complex architecture required

Single executable file that can be invoked from command line, outputs specified text to stdout, and exits cleanly. No configuration files, databases, or network components required.

## Project Name

CLI Hello World Application

## Unknowns

| ID | Question | Why It Matters | Impact If Unresolved |
| --- | --- | --- | --- |
| UNK-1 | What programming language should be used for implementation? | Language choice affects tooling, build processes, runtime dependencies, and distribution strategy | Cannot determine build pipeline, packaging approach, or runtime requirements |
| UNK-2 | Should this be a standalone executable or is requiring a runtime environment acceptable? | Executable type affects packaging strategies, distribution methods, and user installation requirements | Cannot determine deployment approach or user installation complexity |

## Assumptions

| ID | Assumption | Confidence | Validation |
| --- | --- | --- | --- |
| ASM-1 | Standard 'Hello, World!' output format is acceptable rather than exact 'hello world' formatting | medium | Confirm acceptable output format with stakeholder |
| ASM-2 | Simple, basic implementation is sufficient without advanced CLI features | high | Review original intake statement for complexity indicators |

## Known Constraints

| ID | Constraint | Type |
| --- | --- | --- |
| CNS-1 | Must be a command-line interface application | technical |
| CNS-2 | Must output 'hello world' when executed | technical |
| CNS-3 | Target platform is Windows | technical |
| CNS-4 | Intended for personal use only | other |

## Early Decision Points

### Programming language selection

EDP-1

Language choice constrains all subsequent tooling, build process, and distribution decisions

- Python
- Go
- Rust
- C
- C++
- JavaScript/Node.js

Go or C for standalone executable capability on Windows

### Executable packaging approach

EDP-2

Determines user installation experience and runtime dependencies

- Standalone executable (no runtime required)
- Runtime dependency acceptable

Standalone executable for simplest personal use experience

## Stakeholder Questions

| ID | Question | Directed To | Blocking |
| --- | --- | --- | --- |
| STQ-1 | Should the output be exactly 'hello world' (lowercase, no punctuation) or is 'Hello, World!' standard formatting acceptable? | product_owner | No |

## Recommendations for PM

| ID | Recommendation |
| --- | --- |
| RPM-1 | Prioritize language selection decision as it affects all downstream technical choices |
| RPM-2 | Confirm output format requirements to avoid rework after implementation |


---

# IP-001 — CLI Hello World Application: Implementation Plan

## Plan Summary

Deliver a standalone Python-based CLI executable that outputs 'hello world' when executed, packaged without runtime dependencies for personal use on Windows

A single executable file that can be invoked from Windows command line, outputs the specified text to stdout, and exits cleanly without requiring Python runtime installation

- Must be implemented in Python
- Must be packaged as standalone executable with no runtime dependencies
- Target platform is Windows
- Must output 'hello world' when executed
- Intended for personal use only

Implementation must precede packaging since executable creation depends on source code. Testing follows packaging to validate standalone executable behavior. Distribution preparation is final since it depends on validated executable.

## Work Package Candidates

### Core Python Implementation

WPC-001

Implement the basic Python script that outputs the required text when executed

- Create Python script that prints 'hello world' to stdout
- Implement clean exit behavior
- Add basic script structure and entry point

- Command line argument parsing
- Configuration file handling
- Advanced error handling beyond basic execution
- Logging or debugging features

- Python script executes successfully with python command
- Script outputs specified text to stdout
- Script exits with status code 0
- Code is ready for packaging tools

### Standalone Executable Packaging

WPC-002

Package Python script into standalone Windows executable that runs without Python runtime dependencies

- Configure packaging tool for Python-to-executable conversion
- Generate standalone Windows executable
- Ensure executable includes all required Python runtime components
- Validate executable runs on Windows without Python installation

- Multi-platform executable generation
- Executable compression or optimization
- Digital signing or code certificates
- Installer creation

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-001 | — | must_complete_first | Python implementation must be complete before packaging can begin |

- Executable file (.exe) is generated successfully
- Executable runs on Windows without Python runtime installed
- Executable produces correct output when invoked from command line
- Executable file is self-contained with no external dependencies

Packaging approach may need architecture review for tool selection and build pipeline integration

### Executable Testing and Validation

WPC-003

Verify the standalone executable meets all requirements and functions correctly in target environment

- Test executable functionality on clean Windows environment
- Verify output format matches requirements
- Validate executable behavior without Python runtime
- Test command line invocation methods

- Performance testing or benchmarking
- Security scanning or vulnerability assessment
- Cross-platform compatibility testing
- Load testing or stress testing

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-002 | — | must_complete_first | Standalone executable must exist before testing can be performed |

- Executable tested on Windows system without Python installed
- Output format verified against requirements
- Command line invocation confirmed working
- Test results documented and approved

### Distribution Preparation

WPC-004

Prepare the validated executable for personal use distribution

- Package executable for easy distribution
- Create basic usage documentation
- Prepare distribution format suitable for personal use

- Automated distribution systems
- Version management or update mechanisms
- Installation wizards or setup programs
- Distribution to public repositories

| Depends On | External Dep | Type | Notes |
| --- | --- | --- | --- |
| WPC-003 | — | must_complete_first | Executable must be tested and validated before distribution preparation |

- Executable is packaged in appropriate format for personal use
- Basic usage instructions are documented
- Distribution package is ready for deployment

## Risk Summary

| Risk | Affected Candidates | Impact | Mitigation |
| --- | --- | --- | --- |
| Python packaging tools may not successfully create truly standalone executable | ['WPC-002', 'WPC-003'] | high | Research and test packaging tools early, have fallback options identified, validate on clean test environment |
| Executable size may be unexpectedly large due to Python runtime bundling | ['WPC-002', 'WPC-004'] | medium | Set expectations for executable size, explore packaging optimization options if needed |
| Windows security features may block unsigned executable execution | ['WPC-003', 'WPC-004'] | medium | Test on typical Windows configurations, document any security warnings users may encounter |

## Cross-Cutting Concerns

- Output format consistency across all phases
- Windows compatibility verification throughout development
- Standalone executable requirement validation at each stage

## Architecture Recommendations

- Evaluate Python packaging tools (PyInstaller, cx_Freeze, Nuitka) for Windows standalone executable generation
- Define build pipeline approach for Python-to-executable conversion
- Consider executable optimization strategies if size becomes a concern

## Open Questions

| Question | Why It Matters | Owner | Status |
| --- | --- | --- | --- |
| Should the output be exactly 'hello world' (lowercase, no punctuation) or 'Hello, World!' (standard capitalization with punctuation)? | Output format specification affects implementation and testing criteria | Product Owner | — |
| How should the executable be distributed for personal use? | Distribution method determines packaging requirements and delivery approach | Product Owner | — |
| What level of error handling and validation is required? | Error handling requirements affect implementation complexity and scope | Product Owner | — |


---

# TA-001 — CLI Hello World Application: Technical Architecture

## Architecture Summary

CLI Hello World Application

Single executable monolith

- Python implementation with runtime dependency acceptable
- Simple script approach without packaging complexity
- Standard output to console with clean exit
- No configuration files or external dependencies required

## Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Python runtime not installed on target Windows system | high | Document Python installation requirements and provide installation instructions | accepted |
| Path configuration issues preventing execution | medium | Provide execution instructions including full path usage | accepted |

## Open Questions

| Question | Impact | Default Assumption |
| --- | --- | --- |
| Should output be exactly 'hello world' or 'Hello, World!' formatting? | Low - affects only the string literal in implementation | Standard 'Hello, World!' formatting will be used |
| Which Windows versions need support? | Low - Python 3.x runs on all modern Windows versions | Windows 10+ with Python 3.7+ compatibility |
| Any specific build tool constraints? | Low - simple Python script requires minimal tooling | Standard Python interpreter execution, no build tools required |

## MVP Scope

- Single Python script file
- Command line execution capability
- Hello world message output to stdout
- Clean exit after execution
- Basic execution documentation

- Standalone executable packaging
- Advanced CLI argument parsing
- Configuration file support
- Logging capabilities
- Error handling beyond basic Python defaults

## Components

### HelloWorldMain

Entry point that outputs hello world message and exits

Python 3.x

- Command line execution interface
- Standard output stream

## Workflows

### ExecuteHelloWorld

Command line invocation

| # | Action | Component | Output |
| --- | --- | --- | --- |
| 1 | Initialize Python interpreter | HelloWorldMain | Runtime environment ready |
| 2 | Output hello world message to stdout | HelloWorldMain | Message printed to console |
| 3 | Exit with status code 0 | HelloWorldMain | Clean program termination |

## Quality Attributes

- Execution time under 100ms
- Memory usage under 50MB

- No network access required
- No file system writes required
- Read-only execution model

- Single-user personal use only
- No concurrent execution requirements

- Single Python file implementation
- No external dependencies beyond Python runtime
- Self-contained executable logic

- Standard output for message delivery
- Standard error for any runtime issues
- Clean exit codes (0 for success)


---

# WP-001 — Core Python Implementation

## Overview

WP-001

Core Python Implementation

Implement the basic Python script that outputs the required text when executed

PLANNED

## Scope

- Create Python script that prints 'hello world' to stdout
- Implement clean exit behavior
- Add basic script structure and entry point

1. All work statements executed and verified

## Governance

pending

## Revision

2026-03-05T17:30:48.142185+00:00

system

## Lineage

- WPC-001

kept

Promoted as-is from IP candidate.

work_package_candidate

- WPC-001

kept

Promoted as-is from IP candidate.

