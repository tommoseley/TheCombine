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
