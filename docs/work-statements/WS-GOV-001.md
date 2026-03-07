# WS-GOV-001: Formalize Governance Policy Documents

**Parent:** Governance foundation
**Depends on:** None (extracts from existing rules in AI.md, ADRs, and established practices)
**Blocks:** Nothing (standalone governance hygiene — future work may reference these policies as inputs)

---

## Objective

Extract and formalize the three missing governance policies from existing documented rules and established practices. These are not new rules — they are rules already enforced through AI.md, ADRs, WS templates, and session conventions that have never been published as standalone policy documents.

---

## Context

The Combine currently has two published policies:

- **POL-WS-001** — Work Statement Standard (exists in `docs/policies/`)
- **POL-ADR-EXEC-001** — ADR Execution Authorization (exists in `docs/policies/`)

Three policies are missing but their rules are already enforced through tribal knowledge, AI.md constraints, and ADR decisions:

| Policy | Governs | Rules Already Exist In |
|--------|---------|----------------------|
| POL-QA-001 | Testing & Verification | AI.md (Bug-First Testing Rule, Testing Strategy), ADR-010, session practices |
| POL-CODE-001 | Code Construction | AI.md (Reuse-First Rule), WP-CRAP-001/002 practices, ADR-057 (Ontology) |
| POL-ARCH-001 | Architectural Integrity | AI.md (Execution Constraints), ADRs (009, 010, 039, 049), established layer boundaries |

These policies are needed because:

1. **The WS generation station** should reference governance documents as inputs, not invent rules
2. **The binder export** should include a Project Governance section so external agents/teams know the factory standards
3. **QA gates** should validate against published standards, not implicit knowledge

---

## Scope

**In scope:**

- Draft POL-QA-001 (Testing & Verification Standard)
- Draft POL-CODE-001 (Code Construction Standard)
- Draft POL-ARCH-001 (Architectural Integrity Standard)
- Place all policies in `docs/policies/`

**Out of scope:**

- Modifying POL-WS-001 (already exists and is stable)
- Modifying AI.md (policies supplement AI.md, they don't replace it)
- Building mechanical enforcement of policies (future quality gate work)
- Creating policy versioning infrastructure

---

## Prohibited

- Do not invent new rules — extract from existing documented practices only
- Do not exceed 2 pages per policy — factories use clear standards, not essays
- Do not create enforcement mechanisms — these policies are reference documents for now
- Do not modify existing ADRs or AI.md
- Do not create policy management tooling

---

## Steps

### Step 1: Draft POL-QA-001 — Testing & Verification Standard

File: `docs/policies/POL-QA-001.md`

Extract from: AI.md "Bug-First Testing Rule" section, AI.md "Testing Strategy" section, WS-RING0-001/WS-CRAP practices

Required content:

**Core Rules:**

- Tests-first rule: Tests must exist and fail before implementation code is written
- Bug-first remediation: Every runtime defect must first be expressed as a failing test that reproduces the observed behavior
- Verification before completion: Work is not complete until all tests pass and acceptance criteria are verified
- Regression protection: Fixes must not reduce existing test coverage
- Deterministic tests: Tests must not depend on external services or non-deterministic inputs
- No vibe-based fixes: Code must not be changed before a reproducing test exists

**Testing Tiers:**

- Tier-1: In-memory repositories, no DB, pure business logic (fast unit tests)
- Tier-2: Spy repositories for call contract verification (wiring tests)
- Tier-3: Real PostgreSQL (deferred, requires test DB infrastructure)

**Money Tests:**

- Bug fixes must include a "money test" that reproduces the exact RCA scenario
- The money test must fail before the fix and pass after

**Constraints:**

- Do not suggest SQLite as a substitute for PostgreSQL testing
- Tests written after the fix to prove correctness are not acceptable

### Step 2: Draft POL-CODE-001 — Code Construction Standard

File: `docs/policies/POL-CODE-001.md`

Extract from: AI.md "Reuse-First Rule", WP-CRAP-001/002 practices, ADR-057 (Ontology)

Required content:

**Reuse-First Rule:**

- Before creating anything new (file, module, schema, service, prompt): search the codebase and existing docs/ADRs
- Prefer extending or refactoring over creating
- Only create something new when reuse is not viable
- Creating something new when a suitable existing artifact exists is a defect

**Complexity Management:**

- Functions exceeding CRAP score > 30 are flagged as critical and require remediation
- Remediation path: decompose into focused sub-methods (CC reduction) or add test coverage (coverage increase), or both
- No god functions: business logic must be modular and testable
- Mechanical/deterministic checks preferred over LLM-based validation wherever possible

**Ontology Compliance (ADR-057):**

- One meaning per term, system-wide
- Registration before use: check the ontology before naming columns, fields, classes, parameters
- No synonyms in code: use the registered term, not alternatives
- Code identifiers must use registered terms; prose documentation may use natural language

**Code Style:**

- Explicit dependencies: all imports and dependencies must be declared
- Readability over cleverness: favor clarity and maintainability
- No silent failures: errors must be surfaced, not swallowed

### Step 3: Draft POL-ARCH-001 — Architectural Integrity Standard

File: `docs/policies/POL-ARCH-001.md`

Extract from: AI.md "Execution Constraints" and "Non-Negotiables", ADRs (009, 039, 049), established layer conventions

Required content:

**Separation of Concerns:**

- Documents are memory, not LLM context
- Workers are anonymous, interchangeable components
- LLMs handle creative/synthesis tasks; code handles mechanical tasks (storage, validation, rendering)
- UI, domain, and infrastructure layers must remain distinct

**Schema Authority:**

- All document structures must originate from governed schemas in `seed/schemas/`
- Prompts live in `seed/prompts/` — they are governed inputs, not documentation
- Prompt changes require: explicit intent, version bump, re-certification, manifest regeneration

**Workflow Integrity:**

- Declarative workflow definitions (JSON) with engine-enforced constraints
- Retry/circuit-breaker logic belongs to the engine, not the plan
- Handlers own input assembly, prompt selection, LLM invocation, output persistence
- Handlers do not infer missing inputs — they fail explicitly

**API & Interface Contracts:**

- Routes are API contracts — no silent route removal (deprecation protocol required)
- All API routes under `/api/v1/`
- Kebab-case in URL paths, snake_case in JSON fields
- Command routes are async, idempotent, and return task_id

**Traceability:**

- All state changes must be explicit and traceable (ADR-009)
- LLM execution must be logged with inputs, outputs, tokens, timing (ADR-010)
- Every execution is replayable via `/api/admin/llm-runs/{id}/replay`

**Git & Deployment:**

- Session summaries are immutable logs — never edit after writing
- ADRs are append-only governance records

### Step 4: Review and verify

- Read each drafted policy against its source material (AI.md sections, relevant ADRs)
- Verify no rule is invented — every statement must trace to an existing documented practice
- Verify each policy is ≤ 2 pages
- Verify policies do not contradict each other or existing POL-WS-001

---

## Allowed Paths

```
docs/policies/POL-QA-001.md       (new)
docs/policies/POL-CODE-001.md     (new)
docs/policies/POL-ARCH-001.md     (new)
```

---

## Verification

- [ ] POL-QA-001.md exists in `docs/policies/` and covers testing rules, tiers, money tests, constraints
- [ ] POL-CODE-001.md exists in `docs/policies/` and covers reuse-first, CRAP thresholds, ontology, code style
- [ ] POL-ARCH-001.md exists in `docs/policies/` and covers separation of concerns, schema authority, workflow integrity, API contracts, traceability, git/deployment rules
- [ ] Each policy is ≤ 2 pages
- [ ] No policy contains invented rules — all trace to AI.md, ADRs, or established session practices
- [ ] Policies do not contradict POL-WS-001 or each other
- [ ] All policies follow the same structural format (title, status, purpose, rules, governance boundary)

---

_Draft: 2026-03-06_
