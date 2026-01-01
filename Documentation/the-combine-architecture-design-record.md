# The Combine — Architectural Design Record

**Document Type:** Architecture Position Paper  
**Status:** Approved  
**Version:** 1.0  
**Date:** December 16, 2025  
**Author:** Chief Architect  

---

## Executive Summary

The Combine is a document production system. It exists to eliminate the manual labor of creating structured project documents—architecture specifications, epic definitions, story backlogs, implementation guides, and the many other artifacts that constitute software engineering work product.

This document establishes the governing architectural principle: **documents are the product; workers are anonymous labor.**

The system is document-centric, not worker-centric. Document types are the stable abstraction. The workers, prompts, and AI models that produce them are implementation details—interchangeable, versioned, and invisible to the user.

This inversion—from "run the Architect" to "build a Discovery Architecture"—is not a refactoring convenience. It is the foundation that makes the system extensible, maintainable, and aligned with how engineering organizations actually think about their work.

---

## 1. Core Architectural Principle

### 1.1 The Fundamental Insight

Software engineering organizations do not say "run the architect." They say "we need an architecture document."

They do not say "call the BA." They say "we need a breakdown of this epic."

The artifacts of work are primary. The roles that produce them are incidental.

Traditional AI orchestration systems invert this relationship. They model workers (agents, mentors, roles) as the primary abstraction and treat documents as side effects. This creates systems where:

- Adding a new artifact type requires new code, new routes, new classes
- Manual intervention feels like an exception rather than a normal operation
- The UI exposes implementation details (role names) instead of user goals (document types)
- Changing how a document is produced requires modifying routing logic

The Combine rejects this model.

### 1.2 Documents as the Stable Contract

In The Combine:

- **Document types** are the stable, public contract of the system
- **Schemas** define what a document contains
- **Handlers** define how a document is validated, transformed, and rendered
- **Workers** are anonymous functions that produce documents according to prompts
- **Prompts** are versioned data, not embedded code

A document type—"Discovery Architecture," "Story Backlog," "Method Profile"—is a permanent concept. The mechanism that produces it may change weekly. The schema may evolve across versions. The prompts will certainly be tuned. But the document type itself is stable.

This stability is what allows the system to grow without calcifying.

### 1.3 Workers as Implementation Details

A worker in The Combine is nothing more than:

1. A system prompt
2. A user prompt template
3. An LLM invocation
4. Output parsing

That is the complete definition. Everything else—the "Architect Mentor," the "PM Mentor," the "BA Mentor"—is naming convention, not architecture.

When workers are recognized as interchangeable labor, several things become possible:

- The same document type can be produced by different worker configurations (A/B testing)
- A document can be produced by multiple workers whose outputs are reconciled
- A document can be uploaded by a human, bypassing workers entirely
- Worker implementations can be swapped without touching any other code

The system does not know or care which worker produces a document. It knows only that a document of type X was requested, and a document conforming to schema X was delivered.

---

## 2. Document Lifecycle

Every document in The Combine follows a single lifecycle, regardless of how it is produced.

### 2.1 The Canonical Flow

```
Request
   ↓
Build Job Created (queued, async)
   ↓
Input Gathering (required upstream documents collected)
   ↓
Generation (LLM invocation or human upload)
   ↓
Parsing (raw text → structured data)
   ↓
Validation (schema conformance)
   ↓
Transformation (normalization, enrichment, derived fields)
   ↓
Persistence (stored as artifact with full provenance)
   ↓
Rendering (HTML visualization for UI)
   ↓
Summary (card/list representation)
```

### 2.2 Stage Definitions

**Request:** A user or system process requests a document of a specific type for a specific project (and optionally, epic). The request specifies only the document type and context—never the worker.

**Build Job:** The request becomes a job. Jobs can execute synchronously (blocking), asynchronously (webhook callback), or streaming (SSE progress). The execution mode is orthogonal to the document type.

**Input Gathering:** The registry specifies which upstream documents are required. The system collects them automatically. If required inputs are missing, the job fails with a clear dependency error.

**Generation:** For AI-generated documents, this is an LLM call. For human-authored documents, this is an upload. For imported documents, this is a format conversion. The generation mechanism is pluggable.

**Parsing:** LLM responses are messy—markdown fences, preambles, malformed JSON. Parsing strategies extract structured data from raw text. This is the one place where LLM-specific quirks are handled.

**Validation:** The extracted data is validated against the document type's schema. Validation is strict. A document that does not conform is rejected, not silently accepted.

**Transformation:** Valid documents may require normalization (consistent date formats, trimmed strings), enrichment (computed fields, cross-references), or business logic (status derivation). Transformation is document-type-specific.

**Persistence:** The transformed document is stored as an artifact with full metadata: document type, schema version, creation timestamp, source (AI model, human, import), input document references, and build job ID.

**Rendering:** Each document type has a visual representation. Rendering produces HTML for the UI. This is not a dump of JSON—it is a designed, purpose-built view.

**Summary:** For lists, cards, and navigation trees, documents need compact representations. Summaries are distinct from full renders.

### 2.3 Async Execution

Document generation—particularly AI generation—is inherently asynchronous. LLM calls take seconds to minutes. The lifecycle accommodates this naturally:

- The request returns immediately with a job ID
- Progress updates stream via SSE or poll
- Completion triggers a webhook callback or status change
- The UI reflects job state (queued, running, complete, failed)

Synchronous execution is a degenerate case of async, not a separate path.

---

## 3. Registry-Driven Design

### 3.1 The Document Type Registry

The registry is the central source of truth for what documents exist and how they are produced.

Each entry contains:

| Field | Purpose |
|-------|---------|
| `doc_type_id` | Stable identifier (e.g., `discovery_architecture`) |
| `name` | Human-readable name |
| `description` | What this document represents |
| `schema_id` | Reference to JSON schema (versioned) |
| `builder_role` | Which worker role produces this (e.g., `architect`) |
| `builder_task` | Which task within that role (e.g., `discovery`) |
| `prompt_template_id` | Reference to prompt (versioned) |
| `required_inputs` | Document types that must exist before building |
| `optional_inputs` | Document types that enhance output if present |
| `handler_id` | Which handler processes this document type |
| `gating_rules` | Conditions that must be met (optional) |
| `is_active` | Whether this document type is currently enabled |
| `version` | Registry entry version |

### 3.2 Adding a Document Type

To add a new document type to The Combine:

1. **Define the schema.** What fields does this document contain? What are the types and constraints?

2. **Write the prompts.** What system prompt guides the worker? What user prompt template structures the request?

3. **Implement the handler.** How is this document parsed, validated, transformed, and rendered?

4. **Add the registry entry.** Connect the schema, prompts, and handler. Specify dependencies.

Steps 1-3 are unavoidable work—they define what the document *is*. Step 4 is a data change, not a code change.

No new classes. No new routes. No new mentor files. No routing logic modifications.

### 3.3 Why This Matters

In a worker-centric system, adding a new artifact type requires:

- A new worker class (often hundreds of lines, mostly boilerplate)
- New API routes
- New UI routes
- Routing logic updates
- Tests for all of the above

In a document-centric system, the generic infrastructure handles all document types. The only work is defining what makes this document type unique.

The registry is not configuration. It is the system's understanding of its own capabilities.

---

## 4. Separation of Concerns

### 4.1 The Three Boundaries

The Combine enforces strict separation between three concerns:

**LLM Execution:** The mechanics of calling AI models—authentication, streaming, token counting, retry logic, provider-specific quirks. This is infrastructure.

**Domain Logic:** The business rules of document production—what a Discovery Architecture contains, what inputs it requires, how it relates to downstream documents. This is the core.

**Presentation:** How documents appear in the UI—HTML rendering, summary cards, navigation trees, status indicators. This is the surface.

These concerns have different rates of change, different expertise requirements, and different failure modes. Mixing them creates systems that are fragile everywhere instead of robust in layers.

### 4.2 Document Handlers

A document handler is the domain logic for a single document type. It implements:

- **Parsing:** Extract structured data from raw LLM output
- **Validation:** Verify conformance to schema
- **Transformation:** Normalize and enrich data
- **Rendering:** Produce HTML for full view
- **Summary:** Produce HTML for compact view

Handlers are the only place where document-type-specific logic lives. They are deliberately isolated so that changes to one document type cannot affect others.

Handlers do not call LLMs. They do not manage persistence. They do not handle HTTP requests. They receive data and return data.

### 4.3 Prompts and Schemas as Versioned Artifacts

Prompts are not embedded in code. They are stored, versioned, and referenced by ID.

This allows:

- Prompt changes without deployment
- A/B testing of prompt variations
- Rollback to previous prompt versions
- Audit trail of what prompt produced what output

Schemas follow the same pattern. A document stores the schema version it was validated against. When schemas evolve, historical documents remain valid against their original schema.

This versioning is not optional. It is how the system maintains integrity while evolving.

---

## 5. Manual Control as First-Class

### 5.1 The Design Principle

Manual intervention is not an exception. It is a normal mode of operation.

The Combine produces documents. Sometimes those documents are generated by AI. Sometimes they are written by humans. Sometimes they are imported from other systems. The source is metadata, not a special case.

### 5.2 Supported Operations

**Upload:** A user can upload a document of any type. The document passes through validation and transformation but skips generation. It is stored with source = "human."

**Edit:** A user can modify any document. Edits are tracked. Downstream dependencies may be marked stale.

**Freeze:** A user can freeze a document, preventing regeneration. This is how architectural decisions become stable foundations rather than shifting sand.

**Skip:** A user can skip a document type entirely, marking it as "not applicable" for this project.

**Re-run:** A user can regenerate a document, discarding the current version. The system gathers fresh inputs and runs the build job again.

### 5.3 Why This Matters

Worker-centric systems treat human input as an interruption. The workflow expects AI to produce everything; humans are edge cases to be handled.

Document-centric systems treat human input as normal. The workflow expects documents to exist; the source is incidental.

This aligns with reality. Real projects have constraints that come from humans—legal requirements, architectural decisions made in meetings, strategic pivots communicated in email. The system must accommodate these without friction.

---

## 6. System Boundaries

### 6.1 The Architectural Split

The Combine separates into two distinct systems:

**The Core Application:** Domain logic, persistence, UI, API, document handlers, registry, project management. This is a long-lived, maintainable system. It benefits from strong typing, compile-time checks, proper OOP, and mature frameworks.

**The AI Execution Layer:** LLM client wrappers, prompt rendering, streaming, response parsing, token counting. This is a thin, fast-changing service. It benefits from dynamic typing, rapid iteration, and direct access to AI SDK updates.

These systems communicate over HTTP. The contract is:

```
Request:  { doc_type, inputs, callback_url? }
Response: { raw_content, usage_metadata }
```

The AI layer does not know about projects, epics, or schemas. It receives a document type and inputs, calls an LLM, and returns raw output.

The core application does not know about Anthropic, OpenAI, or prompt engineering. It requests a document and receives text.

### 6.2 Why This Split Exists

**Rate of change:** AI APIs evolve monthly. Business domain logic evolves quarterly. Coupling them forces the stable parts to change at the rate of the unstable parts.

**Expertise:** AI prompt engineering and domain modeling are different skills. Separating the systems allows specialists to work independently.

**Language fit:** LLM work involves text manipulation, dynamic structures, and rapid prototyping—Python excels here. Domain modeling involves type hierarchies, validation, and long-term maintenance—C#, Java, or TypeScript excel here.

**Deployment:** The AI layer can be serverless (Lambda, Cloud Functions). The core application can be containerized or traditional. Different scaling characteristics, different cost models.

**Testing:** The core application can be tested with mock AI responses. The AI layer can be tested with fixture inputs. Neither requires the other.

### 6.3 The Contract Boundary

The contract between systems is:

- The core application sends: document type, rendered inputs, callback URL
- The AI layer returns: raw LLM response, token usage, model metadata

All parsing, validation, transformation, and storage happens in the core application. The AI layer is stateless and document-agnostic.

This boundary is sacred. Violating it—letting the AI layer know about schemas, or letting the core application know about prompt structure—recreates the coupling this architecture exists to prevent.

---

## 7. Non-Goals

### 7.1 What This Architecture Explicitly Avoids

**Workflow BPM Engines:** The Combine is not a workflow orchestrator. There are no swimlanes, no BPMN diagrams, no state machines with transition rules. Documents have dependencies, not workflows.

**Role Hardcoding:** The system does not have an "Architect" that exists independently of documents. Roles are builder metadata, not first-class entities.

**Mentor Proliferation:** There is no `PreliminaryArchitectMentor`, `DetailedArchitectMentor`, `DiscoveryArchitectMentor`. There is one generic builder that executes any document type.

**Opaque Agent Behavior:** The system does not have autonomous agents that decide what to do next. Document production is explicit—requested by users or required by dependencies.

**Chat-Based Interfaces:** The Combine produces documents, not conversations. Chat may be an input mechanism, but the output is always structured artifacts.

**Provider Lock-In:** The architecture does not assume Anthropic, OpenAI, or any specific model. The AI layer abstracts providers; the core application is provider-agnostic.

### 7.2 Why These Are Non-Goals

Each of these represents an architectural path that optimizes for something other than document production:

- BPM engines optimize for process compliance
- Role-centric systems optimize for human org-chart mapping
- Mentor proliferation optimizes for per-task customization at the cost of maintenance
- Autonomous agents optimize for minimal human involvement
- Chat interfaces optimize for exploration over production
- Provider lock-in optimizes for short-term development speed

The Combine optimizes for **producing correct documents efficiently, with full human control, and minimal maintenance burden.**

This is a different goal, and it requires a different architecture.

---

## 8. Alignment with Reality

### 8.1 How Engineering Organizations Actually Work

Engineering organizations think in documents:

- "We need an architecture doc before we start building"
- "The epic breakdown is missing—can you write that up?"
- "Send me the QA strategy when it's ready"

They do not think in workers:

- "Run the architect" (no one says this)
- "Execute the BA mentor" (meaningless outside our system)

By modeling documents as primary, The Combine speaks the language of its users.

### 8.2 The Project as Dossier

A project in The Combine is not a workflow. It is a dossier—a collection of documents that together define what is being built and how.

The UI reflects this:

- ☐ Discovery Architecture
- ☐ Architecture Specification  
- ☐ Epic Set
- ☐ Story Backlog (per epic)
- ☐ Implementation Plan
- ☐ QA Strategy

Each item knows what it depends on, what it unlocks, and whether it exists. The user's job is to ensure the dossier is complete. The system's job is to help produce the documents.

This is not a pipeline to be "run." It is a checklist to be satisfied.

### 8.3 Why This Feels Right

When an architecture aligns with the mental model of its users, it becomes invisible. Users do not fight the system; they use it.

The document-centric model feels obvious because it matches how people already think about project work. The inversion from worker-centric to document-centric is not a technical refactoring. It is a recognition of what was true all along.

---

## 9. Conclusion

The Combine is a document factory.

Documents are the product. Workers are anonymous labor. The registry defines what can be built. Handlers define how each document type behaves. The AI layer is a stateless service. The core application owns domain logic and persistence.

This architecture is not clever. It is simple in the way that correct abstractions are simple—obvious in retrospect, invisible in use.

It will remain valid as:

- New document types are added (data changes, not code changes)
- AI providers are swapped (AI layer changes, core unchanged)
- Prompts are tuned (versioned data, no deployment)
- Schemas evolve (versioned, backward-compatible)
- The UI is redesigned (rendering changes, domain unchanged)
- Manual workflows increase (first-class, not exceptional)

The measure of this architecture is not elegance. It is longevity.

Build documents. Ship documents. The rest is implementation.

---

*This document is itself an artifact of The Combine architecture—a structured record that defines a concept, versioned and stored, independent of the mechanism that produced it.*
