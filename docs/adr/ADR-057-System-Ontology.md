# ADR-057 — System Ontology

**Status:** Draft
**Date:** 2026-03-04
**Related:** ADR-055, ADR-056

---

## Context

The Combine uses the same English noun with different meanings in different subsystems:

- `instance_id` on `documents` means "document identity." `instance_id` on `workflow_instances` means "workflow execution identity." Same column name, different semantics, different tables.
- `NodeType.QA` and `NodeType.GATE` with `gate_kind="qa"` both mean "QA node" — a semantic mismatch that caused the QA gate infinite loop (RCA 2026-03-03, fixed in WS-RING0-001).

These are not naming style issues. They are **semantic mismatches** — the same term carrying different meanings depending on context. They create bugs that compile, pass schema validation, and fail silently at runtime.

As the system grows and multiple AI agents (Claude, CC, GPT) read and write code, imprecise terminology compounds. An agent that sees `instance_id` will infer meaning from the name. If the name lies, the agent writes wrong code confidently.

---

## Decision

### 1. Registered Ontology

The Combine maintains a registered set of terms. Each term has exactly one meaning, system-wide. No term may be reused with a different semantic in any subsystem, table, column, field, parameter, or class name.

### 2. The Registry

| Term | Meaning | Scope |
|------|---------|-------|
| `display_id` | Human-readable document identity. Format: `{TYPE}-{NNN}`. Immutable after creation. | Documents |
| `project_id` | Human-readable project identity (string, URL-safe, immutable). Format: `{PREFIX}-{NNN}`. Not the UUID primary key. | Projects |
| `instance` | A single execution of a workflow. One workflow definition may produce many instances. | Workflow engine |
| `version` | Document persistence version (DB row). Integer, auto-incremented on each save. Version 1 is the first, version N is the Nth save. | Document table |
| `edition` | Intentional content revision within a governed document's lifecycle. Tracked in `revision.edition` schema field. Distinct from `version` — a document may have many DB versions per edition. | WP/WS content |
| `node` | A step in a workflow definition. Has a type, may have a gate_kind. | Workflow definitions |
| `gate` | A validation node that evaluates a document against criteria. Can pass or fail. | Workflow definitions |
| `gate_kind` | The specific validation type a gate performs (`qa`, `pgc`). | Workflow definitions |
| `space` | A container that owns documents. Currently: a project or system scope. Identified by `space_id` + `space_type`. | Document ownership |
| `project` | A user-created container for work. A type of space. Has a `project_id`. | Project management |
| `document` | A governed artifact with a type, display_id, version, and content. The fundamental unit of work in The Combine. | Core domain |
| `doc_type` | The classification of a document. Determines schema, handler, and pipeline behavior. Identified by `doc_type_id`. | Document system |
| `handler` | The code that assembles inputs, invokes LLM, and persists output for a specific doc_type. | Pipeline execution |
| `station` | A pipeline stage that processes documents. Maps to a role (PM, BA, Developer, QA, TA). | Pipeline model |
| `worker` | An anonymous, interchangeable execution unit (human or AI) that performs work at a station. | Execution model |
| `work_binder` | The collection of promoted work packages and their work statements for a project. | Work management |
| `candidate` | A work package candidate (WPC) proposed by the Implementation Plan, not yet promoted to the work binder. | Work management |
| `promote` | The act of moving a candidate into the work binder as a work package. Creates a new WP document with lineage to the source WPC. | Work management |
| `remediation` | The act of regenerating a document after QA gate failure. | Quality gates |
| `circuit_breaker` | A threshold that stops remediation loops after N failures. Routes to escalation or terminal state. | Quality gates |
| `escalation` | A pause in workflow execution that requires operator decision (retry, abandon). | Workflow engine |
| `display_prefix` | The uppercase abbreviation (2-4 chars) registered per doc_type. Used as the first segment of `display_id`. | Document identity |

### 3. Rules

**One meaning per term.** If a term is registered, every use of that term in code, schema, config, and documentation MUST carry the registered meaning. If a different concept is needed, pick a different word.

**Registration before use.** New subsystems MUST check the ontology before naming columns, fields, classes, or parameters. If a suitable term exists, use it. If not, register a new one.

**No synonyms in code.** If the ontology says `version`, do not use `revision` or `iteration` for the same concept in column names or field names. Prose documentation may use natural language, but code identifiers must use the registered term. Note: `version` and `edition` are **distinct registered concepts** (DB persistence version vs. intentional content revision), not synonyms — both may appear in the same document schema.

**Compound terms inherit meaning.** `display_id` means document identity. `display_prefix` means the prefix component of `display_id`. A field named `display_*` must relate to the registered meaning of `display`.

### 4. Ontology Audit (Future Quality Instrument)

An automated audit tool SHOULD be built to verify ontology compliance:

- Parse all column names, field names, class names, and parameter names in the codebase
- Match each against the registered ontology
- Flag uses where a registered term carries a different meaning than registered
- Flag cases where a concept uses a synonym instead of the registered term

The registry itself provides the primary value — AI agents read the ADR before writing code and use the correct terms by construction. Mechanical enforcement is a quality-of-life improvement, not a blocker. When built, the audit runs read-only (Phase 1). Promotion to a blocking quality gate is a future decision.

---

## Consequences

### Positive

- **AI agents read code correctly.** When CC sees `display_id`, it knows exactly what it means. No inference, no guessing.
- **Semantic mismatches are caught.** The class of bug that caused the QA gate infinite loop (same concept, different names) is preventable by construction.
- **Onboarding is faster.** A new contributor (human or AI) reads 20 terms and understands the domain vocabulary.
- **Code review has a reference.** "This column is named X but the ontology says Y" is a concrete, reviewable objection.

### Negative

- **Naming is constrained.** Developers cannot freely choose column/field names — they must check the ontology. This is intentional friction.
- **Registry maintenance.** New terms must be registered. This is lightweight (add a row to the table) but requires discipline.
- **Retroactive fixes.** Existing code that violates the ontology (e.g., `instance_id` meaning document identity on the documents table) must be renamed. ADR-055 addresses the known case. The ontology registers terms that match the current codebase — no aspirational renames.

---

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Add a new term to the ontology | No |
| Change the meaning of an existing term | Yes |
| Remove a term | Yes |
| Promote ontology audit to blocking gate | Yes |

---

_Draft: 2026-03-04_
