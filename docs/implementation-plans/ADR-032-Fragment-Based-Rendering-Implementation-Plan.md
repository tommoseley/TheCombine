# ADR-032 Implementation Plan: Fragment-Based Rendering

| | |
|---|---|
| **ADR** | ADR-032 |
| **Status** | Accepted |
| **Created** | 2026-01-06 |
| **Execution State** | Authorized |

---

## Scope

Implement fragment-based rendering infrastructure that allows documents to be rendered by composing canonical fragments bound to schema types.

---

## Affected Components

| Component | Change |
|-----------|--------|
| `alembic/versions/` | New migration for fragment tables |
| `app/api/models/` | FragmentArtifact, FragmentBinding models |
| `app/api/services/` | FragmentRegistryService |
| `app/web/bff/` | FragmentRenderer integration |
| `app/web/templates/fragments/` | Canonical fragment HTML partials |
| `tests/` | Fragment registry and renderer tests |

---

## Sequence

### Phase 1: Fragment Registry (DB layer)

- Migration: `fragment_artifacts`, `fragment_bindings` tables
- ORM models
- FragmentRegistryService (CRUD, binding lookup)
- Seed one fragment (OpenQuestionV1)
- Tests

### Phase 2: Fragment Renderer

- FragmentRenderer service (resolves type → fragment → HTML)
- Integration with Jinja2 environment
- Tests

### Phase 3: Proof of Concept

- Wire Epic Backlog to use fragment rendering for `open_questions`
- Verify existing UI unchanged
- Document pattern for future adoption

---

## Risks

| Risk | Mitigation |
|------|------------|
| Breaking existing templates | Phase 3 is additive; existing rendering stays until proven |
| Fragment HTML complexity | Start with simplest type (OpenQuestionV1) |
| Performance (DB lookups per render) | Cache fragments in memory; measure before optimizing |

---

## Dependencies

- ADR-031 complete ✅ (schema registry exists)
- ADR-030 complete ✅ (BFF pattern established)

---

## Estimated Effort

~6-8 hours across 3 phases

---

*End of Implementation Plan*