# WS-CLEANUP-005: Frontend Module Decomposition

## Status: Draft

## Governing References

- Codex Code Review (2026-03-27) — Medium finding: oversized frontend modules

## Verification Mode: A

## Allowed Paths

- spa/src/components/
- spa/src/utils/
- spa/src/constants/
- tests/

---

## Objective

Decompose two oversized frontend React modules into focused sub-components to reduce cognitive load:

1. `spa/src/components/admin/workflow/NodePropertiesPanel.jsx` (1698 LOC) → core + extracted sections
2. `spa/src/components/FullDocumentViewer.jsx` (1051 LOC) → core + extracted viewers

---

## Preconditions

- SPA build passing
- All tests passing

---

## Scope

### In Scope

#### NodePropertiesPanel.jsx Decomposition

Extract into `spa/src/components/admin/workflow/nodePropertySections/`:

| Extract | Target | Content |
|---------|--------|---------|
| Constants | `spa/src/constants/nodeConfig.js` | NODE_TYPES, INTERNAL_TYPES, PGC_GATE_KINDS, QA_MODES, TERMINAL_OUTCOMES |
| Reference utilities | `spa/src/utils/refFormatters.js` | Template/Fragment/Schema/MechOp reference builders and parsers |
| CollapsibleSection | `spa/src/components/common/CollapsibleSection.jsx` | Reusable collapsible wrapper |
| Node type sections | `nodePropertySections/TaskSection.jsx`, `QASection.jsx`, `PGCSection.jsx`, `GateSection.jsx`, `IntakeGateSection.jsx`, `EndSection.jsx` | One file per node type editor |
| Includes panel | `nodePropertySections/IncludesPanel.jsx` | Shared add/update/remove custom includes |

Core `NodePropertiesPanel.jsx` retains: state management, field updaters, conditional rendering of section components.

#### FullDocumentViewer.jsx Decomposition

Extract into `spa/src/components/viewer/`:

| Extract | Target | Content |
|---------|--------|---------|
| DocumentHeader | `viewer/DocumentHeader.jsx` | Title, badges, metadata, close/rewind buttons |
| SpawnedChildrenPanel | `viewer/SpawnedChildrenPanel.jsx` | Child document links |
| RawContentViewer | `viewer/RawContentViewer.jsx` | Fallback JSON display sections (Summary, Questions, Clarifications, PgcContext, Array, Structured, Object, ObjectFieldValue) |
| SectionHeader | `spa/src/components/common/SectionHeader.jsx` | Reusable section title with count |
| Helpers | `spa/src/utils/documentViewerUtils.js` | `extractText`, `formatLabel` |

Core `FullDocumentViewer.jsx` retains: state management, fetch logic, render routing (config-driven vs render-model vs fallback).

### Out of Scope

- Backend module decomposition (WS-CLEANUP-004)
- Changing any component behavior or visual output
- Adding new UI features

---

## Prohibited Actions

- Do not change any component visual output or behavior
- Do not change any props interfaces consumed by parent components
- Do not add new dependencies or libraries
- Do not modify component test expectations

---

## Procedure

### Phase 1: Shared Extractions

1. Create `spa/src/constants/nodeConfig.js` — move constants from NodePropertiesPanel
2. Create `spa/src/utils/refFormatters.js` — move reference builder/parser functions
3. Create `spa/src/utils/documentViewerUtils.js` — move `extractText`, `formatLabel`
4. Create `spa/src/components/common/CollapsibleSection.jsx`
5. Create `spa/src/components/common/SectionHeader.jsx`

### Phase 2: NodePropertiesPanel

6. Create `spa/src/components/admin/workflow/nodePropertySections/` directory
7. Extract each node type section into its own file (Task, QA, PGC, Gate, IntakeGate, End)
8. Extract IncludesPanel
9. Update NodePropertiesPanel to import and render sections
10. Run `cd spa && npm run build` — must succeed

### Phase 3: FullDocumentViewer

11. Create `spa/src/components/viewer/` directory
12. Extract DocumentHeader, SpawnedChildrenPanel, RawContentViewer
13. Update FullDocumentViewer to import and render sub-components
14. Run `cd spa && npm run build` — must succeed

### Phase 4: Verify

15. Run full test suite
16. Run SPA build
17. Run Tier 0

---

## Verification Checklist

- [ ] `NodePropertiesPanel.jsx` core is under 500 LOC
- [ ] `FullDocumentViewer.jsx` core is under 350 LOC
- [ ] All extracted components exist in specified locations
- [ ] SPA build succeeds with no warnings related to the refactor
- [ ] All tests pass
- [ ] Tier 0 passes

## Definition of Done

Two oversized frontend modules decomposed into focused sub-components. All visual behavior preserved. SPA build and all tests pass.
