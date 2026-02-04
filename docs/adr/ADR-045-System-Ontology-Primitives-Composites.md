# ADR-045 -- System Ontology: Primitives, Composites, and Configuration Taxonomy

**Status:** Accepted
**Date:** 2026-02-04
**Decision Type:** Architectural / Ontological

**Related ADRs:**
- ADR-012 -- Interaction Model
- ADR-013 -- Seed Governance
- ADR-027 -- Workflow Definition & Governance
- ADR-031 -- Canonical Schema Types
- ADR-034 -- Document Composition Manifest & Canonical Components
- ADR-039 -- Document Interaction Workflow Model
- ADR-041 -- Prompt Template Include System

---

## 1. Context

The Combine has accumulated a rich set of architectural concepts across its ADR corpus. Schemas (ADR-031), prompt assembly (ADR-041), canonical components (ADR-034), interaction mechanics (ADR-012), document workflows (ADR-039), and project workflows (ADR-027) are each well-defined within their own ADR.

However, these concepts have never been formally classified into a unified taxonomy. This creates practical problems:

- The Admin Workbench left rail mixes primitives and composites, producing an overcrowded navigation that does not communicate the system's structure.
- New contributors cannot easily answer: "What kind of thing is this? Is it fundamental or composed?"
- Configuration UI design requires knowing what is independently editable versus what is assembled from parts.
- Conversations about the system lack precise shared vocabulary -- "prompt," "template," "fragment," and "schema" are used loosely.

A formal ontology is required -- not to introduce new mechanisms, but to name and classify what already exists.

---

## 2. Decision

The Combine adopts a formal classification of its artifacts into **Primitives** (irreducible, independently governed), **Composites** (assembled from primitives), and one **Ontological Term** (a vocabulary concept that names an execution event without creating a configurable artifact).

---

## 3. Primitives

Primitives are the irreducible building blocks of the system. Each is independently authored, versioned, governed, and reusable.

### 3.1 Prompt Fragment

A textual, authored, composable-at-runtime artifact that shapes how an LLM reasons and responds.

**Properties:**
- Versioned, governed, hashable (per ADR-013)
- Assembled into prompts via the include system (ADR-041)
- May be composed into larger assemblies but is authorable and governable in isolation

**Semantic subtypes** (not ontological -- all are Prompt Fragments):
- Role fragment -- behavioral posture and boundaries
- Task fragment -- outcome instructions and constraints
- PGC context fragment -- clarification scope and framing
- QA fragment -- evaluation criteria and judgment rules
- Safety / guard fragment -- prohibited behaviors, untrusted-context clauses

**Governing principle:** Prompt Fragments shape behavior.

**Alignment:** ADR-041 defines the mechanical assembly of fragments into prompts. ADR-034 defines generation_guidance bullets as the component-level fragment content. This ADR classifies both as instances of the Prompt Fragment primitive.

### 3.2 Schema

A structural, authoritative, machine-verifiable contract that defines what an acceptable outcome looks like.

**Properties:**
- JSON Schema format
- Versioned, governed (per ADR-031)
- Validates outputs post-execution
- Drives QA and stabilization
- Reusable across document types and DCWs

**Governing principle:** Schemas define acceptability.

**Boundary clarification -- schemas and prompts:** A schema's primary function is output validation. When schema content appears in prompt assembly (e.g., via `$$OUTPUT_SCHEMA` per ADR-041), it serves as reference material for the LLM -- informational context so the model knows the expected output structure. This does not make the schema a Prompt Fragment. The schema remains a validation artifact; the generation_guidance bullets (ADR-034) are the behavioral Prompt Fragments that describe how to produce output. Schemas and fragments serve different purposes even when they describe related structure.

**Alignment:** ADR-031 governs canonical schema types, the schema registry, and resolution. ADR-034 references schemas via component specifications. This ADR classifies Schema as an independent primitive reusable across document types.

---

## 4. Ontological Term

### 4.1 Interaction Pass

An Interaction Pass is an execution event that binds Prompt Fragments and a Schema. It is **not** a configurable artifact -- it is a vocabulary term for reasoning about what happens at a DCW node.

An Interaction Pass uses:
- One or more Prompt Fragments (role, task, context, guards)
- Exactly one canonical outcome Schema
- A role (established via role fragment)
- Inputs (documents, answers, structured context)

It produces:
- An Outcome Artifact (validated against the schema)

**Full assembly, stated explicitly:**

```
Prompt Assembly
  = Role Fragment
  + Task Fragment
  + Context / Guard Fragments
  + Input Payload

Outcome Contract
  = Canonical Schema
```

**Execution:**
1. Prompt assembly binds fragments per ADR-041
2. LLM generates output under the interaction mechanics of ADR-012
3. Output is validated against the canonical schema
4. Result becomes an Outcome Artifact
5. Line state advances or blocks accordingly

**Why this term exists:** It answers "what kind of thing is this?" when examining a DCW node. A PGC node is an Interaction Pass configured with PGC fragments and a question-set schema. A QA node is an Interaction Pass configured with QA fragments and a verdict schema. A generation node is an Interaction Pass configured with role + task fragments and a document schema.

**What it is not:** Interaction Pass does not replace or modify ADR-012's interaction mechanics (execution loop, state transitions, clarification gates, QA gates). ADR-012 defines *how* execution proceeds. Interaction Pass names *what* is being executed.

### 4.2 Outcome Artifact

The typed, validated result of an Interaction Pass:

- Document draft
- QA verdict
- PGC question set
- Reflection result

Outcome Artifacts are **produced**, not configured. They do not appear in the Admin Workbench as editable items. Outcome Artifacts never live in `combine-config/`.

---

## 5. Composites

Composites are assembled from primitives. They are the primary objects users interact with in the Admin Workbench.

### 5.1 Role

A curated representation of a business function whose behavioral posture an LLM adopts.

**Composed of:** Role fragment(s) + metadata (authority boundaries, permitted actions, identity).

**Alignment:** Roles have existed as a concept since early ADRs. This ADR classifies them as composites assembled from Prompt Fragment primitives.

### 5.2 Task

A function with a desired outcome which an LLM produces while operating under a Role.

**Composed of:** Task fragment(s) + metadata (output expectations, scope constraints, prohibited actions).

**Alignment:** Tasks are the "what to produce" counterpart to Role's "who to be." Both are composites of Prompt Fragments.

### 5.3 Document Creation Workflow (DCW)

A graph of Interaction Passes that produces one stabilized document type. DCW is synonymous with "Document Production Workflow" -- both terms refer to the same concept, with "production" aligning to The Combine's industrial metaphor.

**Composed of:** Interaction Pass nodes (each binding fragments + schema), edges defining flow, gate conditions.

**Properties:**
- Implemented as a workflow plan (ADR-038)
- Standard phases: Clarification -> Generation -> QA -> Remediation -> Stabilization (ADR-039)
- Each node is an Interaction Pass
- Terminal outcomes: stabilized, blocked, abandoned
- Document-scoped -- does not manage project state

**Alignment:** ADR-039 defines the DCW concept and its relationship to project workflows. This ADR classifies it as a composite and names its constituent parts.

### 5.4 Project Orchestration Workflow (POW)

A sequence of DCW invocations with gating and dependency logic that advances project state.

**Composed of:** Steps referencing DCWs, gate conditions, dependency declarations.

**Properties:**
- Declares WHAT document to produce, not HOW
- Role and task prompt bindings belong on DCW nodes, not on POW steps
- Governs scope and permission (ADR-027)
- May include non-document steps (gates, approvals)

**Alignment:** ADR-027 defines workflows as scope/permission envelopes. ADR-039 established that project workflows invoke document workflows and react only to terminal outcomes. This ADR classifies the POW as the top-level composite.

---

## 6. Taxonomy Summary

### Primitives (independently authored, versioned, reusable)

| Primitive | Nature | Purpose |
|-----------|--------|---------|
| Prompt Fragment | Textual, composable | Shape LLM behavior |
| Schema | Structural, JSON | Define acceptable output |

### Ontological Terms (vocabulary, not configuration)

| Term | Nature | Purpose |
|------|--------|---------|
| Interaction Pass | Execution event | Bind fragments + schema, produce outcome |
| Outcome Artifact | Typed result | Validated output of a pass |

### Composites (assembled from primitives)

| Composite | Assembled From | Purpose |
|-----------|---------------|---------|
| Role | Prompt Fragment(s) + metadata | Behavioral posture for LLM |
| Task | Prompt Fragment(s) + metadata | Desired outcome function |
| DCW | Interaction Pass nodes + edges | Produce one stabilized document |
| POW | DCW references + gates | Sequence document production |

### Composition hierarchy

```
POW
  -> DCW (one per step)
       -> Interaction Pass (one per node)
            -> Prompt Fragments (role + task + context + guards)
            -> Schema (canonical outcome contract)
            -> Inputs (documents, answers, context)
            => Outcome Artifact (validated result)
```

---

## 7. Implications for Admin Workbench

The Admin Workbench left rail MUST be organized by **abstraction level**, not by artifact type or file structure.

```
CONFIGURATION

> Production Workflows
    > Project Workflows        (POWs)
    > Document Workflows       (DCWs)

> Building Blocks
    > Roles
    > Tasks
    > Schemas
    > Templates

> Governance
    > Active Releases
    > Git Status
```

**Rules:**
- Production Workflows are top-level navigation targets -- this is where most users work
- Building Blocks contains independently editable primitives and composites
- Governance contains control-plane artifacts
- Outcome Artifacts, Interaction Passes, and runtime instances do NOT appear in the left rail
- The left rail reflects the system's abstraction layers, not its file structure

**One sentence to pin:** The left rail mirrors the composition hierarchy -- workflows at the top, building blocks below, governance at the bottom.

---

## 8. Schema Extraction (Migration)

To enable schema reuse across DCWs, schemas SHALL be extractable from document type packages into a standalone governed location.

**Current state:** Schemas are embedded in document type packages at `combine-config/document_types/{type}/releases/{ver}/schemas/output.schema.json`.

**Target state:** Schemas are independently addressable at `combine-config/schemas/{name}/releases/{ver}/schema.json`. Document type packages reference schemas by name + version.

This aligns with ADR-031's vision of a canonical schema registry and follows the Reuse-First Rule.

**Guardrails:**
- Schema extraction MUST preserve semantic identity -- the extracted schema is the same artifact, not a new one.
- Extraction MUST include a reference update in the originating document type package pointing to the new standalone location.
- A breaking schema change (structural incompatibility) requires a major version bump per existing governance rules.

Migration is incremental and governed via Work Statements per POL-WS-001.

---

## 9. Relationship to Existing ADRs

This ADR does not supersede any existing ADR. It provides the unifying taxonomy they implicitly share.

| ADR | What It Defines | Relationship to This ADR |
|-----|----------------|--------------------------|
| ADR-012 | Interaction mechanics (execution loop, gates, states) | Defines *how* an Interaction Pass executes |
| ADR-013 | Seed governance (versioning, certification, hashing) | Governs all primitives |
| ADR-027 | Workflow as scope/permission envelope | Defines the POW concept |
| ADR-031 | Canonical schema types and registry | Governs the Schema primitive |
| ADR-034 | Component specifications and composition manifests | Composes primitives into generation/validation/rendering units |
| ADR-039 | Document Interaction Workflows | Defines the DCW concept |
| ADR-041 | Prompt template include system | Defines assembly mechanics for Prompt Fragments |

---

## 10. One-Liner

> Prompt Fragments shape behavior; Schemas define acceptability; Interaction Passes bind and execute both.

---

## 11. Consequences

### Positive
- Unambiguous shared vocabulary for all system artifacts
- Admin Workbench UI organized by abstraction level, not file type
- New contributors can orient by asking "is this a primitive or a composite?"
- Schema reuse across document types becomes structurally supported
- Future evolution (e.g., if Interaction Passes become independently configurable) has a clear place in the taxonomy

### Tradeoffs
- Existing documentation uses varied terminology that must converge over time
- Schema extraction requires incremental config migration
- The ontological distinction (Interaction Pass is vocabulary, not configuration) requires discipline to maintain

---

## 12. Non-Goals

This ADR does NOT:
- Change interaction mechanics (ADR-012)
- Change workflow definitions (ADR-027, ADR-039)
- Change prompt assembly mechanics (ADR-041)
- Change schema governance (ADR-031)
- Introduce new configurable artifact types beyond what already exists
- Define Admin Workbench implementation details beyond the left-rail organizing principle

---

## 13. Acceptance Criteria

ADR-045 is considered satisfied when:

1. The taxonomy (primitives, composites, ontological terms) is documented and referenced by CLAUDE.md
2. Admin Workbench left rail is reorganized per the abstraction-level structure defined in Section 7
3. Schemas are extractable from document type packages into a standalone governed location
4. The terms "Prompt Fragment," "Schema," "Interaction Pass," "DCW," and "POW" are used consistently in new documentation and ADRs

---

## 14. Drift Risks

| Risk | Mitigation |
|------|------------|
| Treating Interaction Pass as a configurable artifact | This ADR explicitly classifies it as ontological only |
| Mixing primitives and composites in the workbench UI | Left rail structure enforces abstraction-level separation |
| Schema content in prompts blurring the primitive boundary | Boundary clarification in Section 3.2 distinguishes informational inclusion from behavioral function |
| Terminology regression in new ADRs | Acceptance criteria require consistent usage |

---

_End of ADR-045_
