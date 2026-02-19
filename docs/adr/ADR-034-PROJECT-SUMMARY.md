# ADR-034 Document Composition: Project Summary

**Last Updated:** 2026-01-09  
**Status:** Active Development  
**Tests:** 1176 passing

---

## Overview

ADR-034 establishes the document composition infrastructure for The Combine. Documents are views over canonical data, rendered through a pipeline of:
- **DocDefs** — Define sections and component bindings
- **Components** — Schema + generation guidance + fragment bindings
- **Fragments** — Jinja2 templates for web rendering
- **RenderModelBuilder** — Assembles data into renderable blocks

---

## Completed Work Statements

### WS-ADR-034-POC ✅
**Completed:** 2026-01-08

- Prompt assembly from docdef + component specs
- RenderModel building with shape semantics
- Fragment resolution via component bindings
- Golden-trace test infrastructure

### WS-ADR-034-DISCOVERY ✅
**Completed:** 2026-01-08

- ProjectDiscovery docdef (6 sections)
- Core block components: StringListBlockV1, SummaryBlockV1, RisksBlockV1

### WS-ADR-034-EPIC-DETAIL ✅
**Completed:** 2026-01-08

- EpicDetailView docdef (10 sections)
- DependenciesBlockV1, OpenQuestionsBlockV1 components

### WS-ADR-034-EPIC-BACKLOG ✅
**Completed:** 2026-01-08

- EpicSummaryView docdef (4 sections)
- EpicBacklogView docdef (multi-epic index)
- EpicSummaryBlockV1 component
- Derived fields: risk_level, complexity_level

### WS-ADR-034-EPIC-ARCHITECTURE ✅
**Completed:** 2026-01-08

- EpicArchitectureView docdef (10 sections)
- ArchitecturalSummaryView docdef (3 sections)
- Integration surface derivation

### WS-ADR-034-STORY-DETAIL ✅
**Completed:** 2026-01-09

- StoryDetailView docdef (9 sections)
- ParagraphBlockV1, IndicatorBlockV1 components

### WS-ADR-034-STORY-SUMMARY ✅
**Completed:** 2026-01-09

- StorySummaryView docdef (3 sections)
- omit_when_source_empty builder enhancement

### WS-ADR-034-STORY-BACKLOG ✅
**Completed:** 2026-01-09

- StoryBacklogView docdef (multi-story index)
- StorySummaryBlockV1, StoriesBlockV1 components

### WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS ✅
**Completed:** 2026-01-09

**Fragment Alias Elimination:**
- Removed FRAGMENT_ALIASES dict
- All fragment IDs now canonical format (`fragment:XxxV1:web:1.0.0`)
- Direct lookup, no translation layer

**Schema Fixes:**
- SummaryBlockV1: `additionalProperties: false`
- ParagraphBlockV1: `additionalProperties: false`, added `detail_ref`
- EpicSummaryBlockV1: `additionalProperties: false`

**Container Guidance Normalization:**
- All containers use: "Render-only container. Do not generate this block; items are provided upstream."
- No schema name references in guidance
- No rendering terms in guidance

**Governance Docs (Frozen):**
- COMPONENT_COMPLETENESS.md
- FRAGMENT_STANDARDS.md
- PROCEDURE_ADD_COMPONENT.md
- PROCEDURE_ADD_DOCUMENT.md

**Completeness Tests (10):**
- test_all_components_have_guidance_bullets
- test_all_components_have_web_binding
- test_all_fragment_ids_use_canonical_format
- test_guidance_bullets_are_declarative
- test_container_guidance_has_no_rendering_terms
- test_all_fragment_ids_resolve
- test_all_fragments_compile
- test_all_fragments_use_canonical_ids
- test_all_component_fragments_exist
- test_all_schemas_disallow_additional_properties

---

## In Progress

### WS-ADR-034-DOCUMENT-VIEWER 📋
**Status:** Contract frozen, implementation pending

**Goal:** Generic DocumentViewer that renders any document type using RenderModelV1.

**Key Deliverables:**
1. RenderModelBuilder emits nested `sections[]` structure
2. Viewer routes: `GET /view/{document_type}?params`
3. Fragment resolution with graceful degradation
4. Golden-trace tests for 9 document types

**Contract highlights:**
- `detail_ref` URL rule: `/view/{document_type}?{params}`
- Document ID: UUID (stored) or hash (preview)
- Actions deferred to future WS

---

## Current Inventory

### DocDefs (9)

| DocDef | Sections | Purpose |
|--------|----------|---------|
| ProjectDiscovery:1.0.0 | 6 | Project discovery |
| EpicDetailView:1.0.0 | 10 | Comprehensive epic view |
| EpicSummaryView:1.0.0 | 4 | Epic scanning |
| EpicBacklogView:1.0.0 | 1 (N blocks) | Multi-epic index |
| EpicArchitectureView:1.0.0 | 10 | Technical architecture |
| ArchitecturalSummaryView:1.0.0 | 3 | Architecture scanning |
| StoryDetailView:1.0.0 | 9 | Single-story detail |
| StorySummaryView:1.0.0 | 3 | Story scanning |
| StoryBacklogView:1.0.0 | 1 (N blocks) | Multi-story index |

### Components (12)

| Component | Purpose |
|-----------|---------|
| OpenQuestionV1 | Single question item |
| OpenQuestionsBlockV1 | Questions container |
| StoryV1 | Story item |
| StoriesBlockV1 | Stories container |
| StringListBlockV1 | Generic string list |
| SummaryBlockV1 | Multi-field summary |
| RisksBlockV1 | Risks container |
| ParagraphBlockV1 | Paragraph text |
| IndicatorBlockV1 | Derived indicator |
| EpicSummaryBlockV1 | Epic summary item |
| DependenciesBlockV1 | Dependencies container |
| StorySummaryBlockV1 | Story summary item |

### Schemas (22)

All schemas have `additionalProperties: false`.

### Derivation Functions (3)

| Function | Input | Output |
|----------|-------|--------|
| derive_risk_level | risks[] | low/medium/high |
| derive_complexity_level | stories[], dependencies[] | low/medium/high |
| derive_integration_surface | integration_points[] | internal/external/hybrid |

---

## Governance Documents

| Document | Purpose | Status |
|----------|---------|--------|
| RENDER_SHAPES_SEMANTICS.md | Shape semantics + section_count | Frozen |
| DERIVED_FIELDS.md | Derivation rules | Frozen |
| SUMMARY_VIEW_CONTRACT.md | Summary constraints | Frozen |
| COMPONENT_COMPLETENESS.md | Component requirements | Frozen |
| FRAGMENT_STANDARDS.md | Fragment rules | Frozen |
| DOCUMENT_VIEWER_CONTRACT.md | Viewer contract | Frozen |
| PROCEDURE_ADD_COMPONENT.md | Add component steps | Frozen |
| PROCEDURE_ADD_DOCUMENT.md | Add document steps | Frozen |

---

## Test Coverage

| Category | Tests |
|----------|-------|
| Derivation rules | 25 |
| Golden traces | 16 |
| Component completeness | 10 |
| Schema artifacts | 4 |
| Fragment resolution | 13 |
| RenderModelBuilder | Various |
| **Total** | **1176** |

---

## Architecture Decisions

1. **Documents are views, not records** — Documents project canonical data, they don't define it
2. **Components own guidance + bindings** — Single source for LLM prompts and UI rendering
3. **Fragments are lenses** — No semantic meaning beyond `block.data` and `context`
4. **Canonical IDs everywhere** — `schema:X`, `component:X:1.0.0`, `fragment:X:web:1.0.0`
5. **additionalProperties: false** — All schemas are closed
6. **Graceful degradation** — Unknown blocks render placeholders, never crash

---

## Next Steps

1. **Implement WS-ADR-034-DOCUMENT-VIEWER**
   - Update RenderModelBuilder for nested sections
   - Create viewer routes
   - Add golden-trace tests

2. **Future WS (not yet scoped)**
   - RenderActionV1 implementation
   - Connect PromptAssembler to DocumentBuilder
   - Connect RenderModelBuilder to web UI
