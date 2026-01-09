# Governance Documents

This directory contains canonical governance specifications for The Combine.

## Document Composition (ADR-034)

| Document | Purpose | Status |
|----------|---------|--------|
| [RENDER_SHAPES_SEMANTICS.md](./RENDER_SHAPES_SEMANTICS.md) | Authoritative shape semantics for docdefs | Frozen |
| [DOCUMENT_MIGRATION_CHECKLIST.md](./DOCUMENT_MIGRATION_CHECKLIST.md) | Required playbook for document type migrations | Canonical |
| [DERIVED_FIELDS.md](./DERIVED_FIELDS.md) | Frozen derivation rules for view fields | Frozen |
| [SUMMARY_VIEW_CONTRACT.md](./SUMMARY_VIEW_CONTRACT.md) | Summary view constraints (exclude_fields, no arrays) | Frozen |

## Component & Fragment Standards (WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS)

| Document | Purpose | Status |
|----------|---------|--------|
| [COMPONENT_COMPLETENESS.md](./COMPONENT_COMPLETENESS.md) | Required fields and guidance style guide | Frozen |
| [FRAGMENT_STANDARDS.md](./FRAGMENT_STANDARDS.md) | Variable naming, data-only guarantee | Frozen |

## Document Viewer (WS-ADR-034-DOCUMENT-VIEWER)

| Document | Purpose | Status |
|----------|---------|--------|
| [DOCUMENT_VIEWER_CONTRACT.md](./DOCUMENT_VIEWER_CONTRACT.md) | Generic viewer contract, RenderModelV1 structure | Frozen |
| [WS-ADR-034-DOCUMENT-VIEWER.md](./WS-ADR-034-DOCUMENT-VIEWER.md) | Work statement for viewer implementation | Draft |

## Operating Procedures

| Procedure | Purpose | Status |
|-----------|---------|--------|
| [PROCEDURE_ADD_COMPONENT.md](./PROCEDURE_ADD_COMPONENT.md) | Step-by-step: schema → component → fragment → tests | Frozen |
| [PROCEDURE_ADD_DOCUMENT.md](./PROCEDURE_ADD_DOCUMENT.md) | Step-by-step: docdef → render checks → golden traces | Frozen |

## Usage

### Adding a New Component

Follow [PROCEDURE_ADD_COMPONENT.md](./PROCEDURE_ADD_COMPONENT.md):
1. Create schema with `additionalProperties: false`
2. Create component with non-empty `generation_guidance.bullets`
3. Create fragment with canonical ID format
4. Seed database
5. Add tests

### Adding a New Document Type

Follow [PROCEDURE_ADD_DOCUMENT.md](./PROCEDURE_ADD_DOCUMENT.md):
1. Identify canonical record (documents are views, not records)
2. Create docdef using existing components only
3. Verify prompt assembly
4. Verify render output
5. Add golden trace tests

### Changing Shape Semantics

Shape semantics in [RENDER_SHAPES_SEMANTICS.md](./RENDER_SHAPES_SEMANTICS.md) are **frozen**.
Changes require explicit governance approval via ADR amendment.

---

*Last updated: 2026-01-09*
