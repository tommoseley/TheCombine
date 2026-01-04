# ADR-028 — Reference Document Management

**Status:** Draft  
**Date:** 2026-01-02  
**Priority:** Post-MVP  
**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-011 — Document Ownership Model
- ADR-012 — Interaction Model
- ADR-017 — Prompt Certification & Trust Levels
- ADR-027 — Workflow Definition & Governance

---

## 1. Decision Summary

The Combine supports user-provided reference documents that may inform workflow execution without becoming owned system artifacts.

Reference documents are:

- Explicitly scoped (User, Project, Organization)
- Treated as uncertified external inputs
- Linked by reference, not copied
- Evaluated and consumed explicitly per workflow step
- Never silently persisted as authoritative context

**This ADR governs storage, ownership, scope, and availability of reference documents.**  
**It does not govern how reference documents are interpreted or condensed (see ADR-029).**

---

## 2. Definitions

**Reference Document**  
A user-supplied file or text provided to inform system execution, but not produced by a governed workflow step.

**Owned Document**  
A document produced by a workflow step and governed by ADR-011 ownership rules.

**Reference (Link)**  
A pointer from a workflow context to an external document, without transferring ownership.

---

## 3. Upload Scopes

Reference documents may be uploaded at one of three scopes:

| Scope | Owner | Visibility | Example |
|-------|-------|------------|---------|
| User | Individual user | User only | Personal notes, examples |
| Project | Project | Project participants | Client standards, specs |
| Organization | Organization | All org projects | Company policies, templates |

Scope determines availability, not ownership.

---

## 4. Availability Rules

- User-scoped documents MAY be linked to one or more projects
- Project-scoped documents are visible only within that project
- Organization-scoped documents are visible to all projects in the organization
- Reference documents do not inherit ownership or scope from workflows

Child scopes may access parent-scope reference documents:
- Story steps can access Project and Org docs
- Epic steps can access Project and Org docs
- Project steps can access Org docs

**Availability does not imply relevance or validity.**

---

## 5. Ownership & Linking Semantics

- Reference documents retain their original owner
- Linking a document to a project creates a reference, not a copy
- Ownership is never transferred
- Deleting a reference document removes its availability immediately

This preserves ADR-011's rule: ownership is exclusive and explicit.

**Reference documents are not workflow document types.** They do not appear in workflow `document_types` declarations and are not produced by workflow steps.

---

## 6. Trust Classification

All reference documents are treated as uncertified external inputs:

| Source | Trust Level |
|--------|-------------|
| System-generated document | Certified |
| User-uploaded document | Uncertified |
| Organization-uploaded document | Uncertified (endorsed source) |

Reference documents:

- MUST NOT override certified system artifacts
- MUST NOT be treated as authoritative without evaluation
- MAY be rejected, ignored, or partially used by workflow steps

Trust classification is metadata, not enforcement logic.

---

## 7. Workflow Interaction

- Reference documents are not automatic inputs
- A workflow step MUST explicitly receive reference documents as part of its invocation context
- Reference documents are not implicitly inherited from prior steps or ambient state
- If a reference document is required but missing, the step MUST fail explicitly or enter clarification
- No workflow step may silently depend on reference material

During clarification (ADR-012 §4.2), users MAY provide new reference documents as part of their response. These documents are scoped to the current step unless explicitly promoted to Project or Org scope.

---

## 8. Audit & Logging

For every workflow step that uses reference documents:

- Document IDs MUST be logged
- Scope and owner MUST be recorded
- Whether the document influenced output MUST be traceable

Reference document content itself MAY be stored or re-derived depending on ADR-029.

---

## 9. MVP Constraints

For MVP:

- Reference documents are provided per step
- No automatic persistence across steps is assumed
- Users may re-provide documents manually (e.g., copy/paste)
- No background ingestion or pre-processing is required

This ensures deterministic, replayable execution.

Future iterations may support automatic reference document persistence across steps (see ADR-029).

---

## 10. Out of Scope

This ADR explicitly does not cover:

- Condensing or summarization logic (ADR-029)
- Role-specific interpretation of documents
- Long-lived conversational memory
- Automatic document reuse across steps
- Knowledge base construction

---

## 11. Consequences

### Positive

- Clear trust boundaries
- No hidden state
- Simple, auditable MVP
- No premature optimization

### Negative

- Some manual repetition for users
- Larger prompts when documents are pasted repeatedly
- No automatic continuity across steps

These tradeoffs are intentional.