# combine-config

Git-canonical configuration repository for The Combine document production system.

**This repository is the single source of truth for all document type configuration.**

## Governance

- Per [ADR-044](../docs/adr/ADR-044-admin-workbench-git-canonical.md)
- If a configuration is not committed here, it does not exist
- Runtime systems read from DB-cached materializations derived from this repository
- All changes require explicit commit - no implicit saves

## Structure

```
combine-config/
├── _conventions/        # Naming, versioning, and promotion rules
├── _active/             # Active release pointers
├── document_types/      # Document Type Packages (one per doc type)
├── prompts/
│   ├── roles/           # Shared role prompts
│   ├── templates/       # Shared assembly templates
│   └── shared/          # Shared boilerplate includes
├── workflows/           # Master workflow definitions
├── components/          # Shared rendering components
└── schemas/
    └── registry/        # Schema registry metadata
```

## Quick Reference

| Task | Location |
|------|----------|
| Add/edit a document type | `document_types/{doc_type_id}/releases/{semver}/` |
| Add/edit a role prompt | `prompts/roles/{role_id}/releases/{semver}/` |
| Change active release | `_active/active_releases.json` |
| View conventions | `_conventions/` |

## Release Model

| State | Meaning |
|-------|---------|
| **Draft** | Uncommitted changes on a branch |
| **Staged** | Committed, validated, awaiting activation |
| **Released** | Active pointer updated, immutable |

Rollback = change active pointer via commit.

## See Also

- [ID Conventions](_conventions/ids.md)
- [Versioning Rules](_conventions/versioning.md)
- [Promotion Process](_conventions/promotion.md)
