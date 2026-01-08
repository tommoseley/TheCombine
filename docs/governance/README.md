# Governance Documents

This directory contains canonical governance specifications for The Combine.

## Document Composition (ADR-034)

| Document | Purpose | Status |
|----------|---------|--------|
| [RENDER_SHAPES_SEMANTICS.md](./RENDER_SHAPES_SEMANTICS.md) | Authoritative shape semantics for docdefs | Frozen |
| [DOCUMENT_MIGRATION_CHECKLIST.md](./DOCUMENT_MIGRATION_CHECKLIST.md) | Required playbook for document type migrations | Canonical |
| [DERIVED_FIELDS.md](./DERIVED_FIELDS.md) | Frozen derivation rules for view fields | Frozen |
| [SUMMARY_VIEW_CONTRACT.md](./SUMMARY_VIEW_CONTRACT.md) | Summary view constraints (exclude_fields, no arrays) | Frozen |

## Usage

### Adding a New Document Type

1. Follow [DOCUMENT_MIGRATION_CHECKLIST.md](./DOCUMENT_MIGRATION_CHECKLIST.md)
2. Reference it in your PR description
3. Ensure all checklist items are complete before merge

### Changing Shape Semantics

Shape semantics in [RENDER_SHAPES_SEMANTICS.md](./RENDER_SHAPES_SEMANTICS.md) are **frozen**.
Changes require explicit governance approval via ADR amendment.

---

*Last updated: 2026-01-08*


