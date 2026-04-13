# IP-BINDER-001 -- Binder Management & Presentation System

**Status:** Draft
**Date:** 2026-04-08
**Governing ADR:** ADR-071 (Binder Management & Presentation System)
**Scope:** Multi-commit (3 WPs, ~9 WSs)

---

## Overview

Implement the binder management and presentation system defined in ADR-071. This establishes first-class document links with version-pinned resolution and modal navigation, binder composition through the existing IA + block rendering system, and a final Work Plan viewer as the system's primary consumable artifact.

The existing IA/block rendering system is the foundation. No new rendering systems are introduced. Enhancements come through new block types, improved IA definitions, and link resolution infrastructure.

---

## Dependency Chain

```
WP-BINDER-001 (Link Resolution & Modal Navigation)
    |
    v
WP-BINDER-002 (Binder Composition via IA + Blocks)
    |
    v
WP-BINDER-003 (Work Plan Viewer)
```

WP-BINDER-001 is independent. WP-BINDER-002 depends on link resolution. WP-BINDER-003 depends on both.

---

## Desired Outcome

A user can open project documents and binders as readable, navigable artifacts. Document references are clickable, title-resolved, and open in modal overlays that preserve review context. Binders compose existing documents with grouping and sequencing. The Work Plan is a final, read-only artifact suitable for review, handoff, or presentation.

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Link resolution performance on large projects | Medium | Batch-resolve references on document load, cache in component state |
| Modal navigation depth (modal-in-modal) | Medium | Limit to single modal depth; clicking a link inside a modal replaces modal content |
| IA system overload with new block types | Low | Keep blocks modular; each block is self-contained |
| Server/client rendering divergence | High | Both paths consume same IA definitions per ADR-071 s3.7 |
| Scope creep into editing from viewer | Medium | Strict read-only boundary; no mutation from binder/modal views |

---

## Full Verification

After all WPs complete:

1. Document references throughout the system render as clickable, title-resolved links
2. Clicking a link opens a modal showing the referenced document at its pinned version
3. Binder documents compose child documents with grouping and navigation
4. Work Plan renders as a coherent, read-only artifact with summary, grouped work items, and decision log
5. Server-side binder rendering (markdown for LLM) and client-side rendering (UI) both consume the same IA structure
6. Tier 0 passes

---

# WP-BINDER-001 -- Link Resolution & Modal Navigation

**Status:** Draft
**Date:** 2026-04-08
**Governing ADR:** ADR-071
**Priority:** HIGH

## Objective

Implement first-class document link resolution and modal navigation. All document references (display_id, document_id) become clickable links that resolve to governed documents, display human-readable titles, and open in modal overlays without changing the user's navigation context.

## Scope

### In Scope
- Document reference detection and resolution service
- Version-pinned link resolution (resolve to version used at construction time)
- Title resolution for display_id references
- Modal document viewer component
- Inline link rendering in block components
- Link resolution API endpoint
- Server-side link resolution for markdown rendering

### Out of Scope
- Backlink analytics or graph visualization
- Hover preview panels
- Editing from modal views
- Changes to canonical document schemas

## Dependencies
- ADR-071 accepted

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-BINDER-001 | Document Reference Resolution Service | a0 |
| WS-BINDER-002 | Modal Document Viewer Component | a1 |
| WS-BINDER-003 | Inline Link Rendering in Block Components | a2 |

## Verification Criteria
- Display_id references (e.g., WS-142, TA-001) resolve to correct documents
- Links display human-readable titles
- Clicking a link opens a modal with the correct document at the pinned version
- Closing the modal returns the user to their previous context unchanged
- Server-side markdown rendering includes resolved titles in references

## Allowed Paths
- app/api/v1/routers/
- app/domain/services/
- spa/src/components/
- spa/src/api/
- tests/

## Definition of Done
- Document references render as navigable links throughout the system
- Modal navigation functional
- All tests pass (Tier 0)

---

## WS-BINDER-001 -- Document Reference Resolution Service

### Purpose

Create a service that resolves document references (display_id, document_id) to their governed documents with title, version, and doc_type_id. This is the backbone for all link rendering.

### Governing References
- ADR-071 (s3.4 First-Class Links, s3.5 Version-Pinned Resolution)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- app/domain/services/
- app/api/v1/routers/
- tests/tier1/
- tests/tier2/

### Scope

#### In Scope
- `DocumentReferenceResolver` service: accepts a display_id or document_id, returns resolved metadata (id, display_id, title, doc_type_id, version)
- Batch resolution: resolve multiple references in a single call (performance)
- API endpoint: `GET /api/v1/documents/resolve?refs=WS-142,TA-001` returns resolved metadata for each
- Version-pinned resolution: when a `referenced_documents` entry specifies a version, resolve to that version
- Fallback: if no version specified, resolve to latest

#### Out of Scope
- UI components (WS-BINDER-002, WS-BINDER-003)
- Staleness detection (future work per ADR-071 s3.9)
- Modifying document schemas

### Preconditions
- ADR-071 accepted
- Documents have display_id populated (existing system)

### Procedure
1. Create `app/domain/services/document_reference_resolver.py`
2. Implement `resolve_reference(display_id_or_doc_id, version=None) -> ResolvedReference`
3. Implement `resolve_batch(refs: list[str]) -> dict[str, ResolvedReference]`
4. Query documents table by display_id or id, optionally filtered by version
5. Return `ResolvedReference(id, display_id, title, doc_type_id, version, space_id)`
6. Add API endpoint `GET /api/v1/documents/resolve` accepting `refs` query parameter
7. Write tests: single resolution, batch resolution, version-pinned resolution, unknown reference returns null

### Verification Criteria
1. `resolve_reference("WS-142")` returns correct document metadata
2. Batch resolution handles 10+ refs efficiently
3. Version-pinned resolution returns the specified version, not latest
4. Unknown references return null without error
5. API endpoint returns resolved metadata as JSON

### Definition of Done
- Reference resolution service created and tested
- API endpoint functional
- All tests pass

### Prohibited Actions
- Do not modify the Document model or database schema
- Do not add write operations to the resolver
- Do not resolve references via LLM

---

## WS-BINDER-002 -- Modal Document Viewer Component

### Purpose

Create a reusable modal component that renders any document using the existing IA + block viewer. This is the navigation target for all document links.

### Governing References
- ADR-071 (s3.6 Modal Navigation Model)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- spa/src/components/
- spa/src/api/
- tests/

### Scope

#### In Scope
- `DocumentModal` component: accepts a document ID (and optional version), fetches and renders the document
- Uses existing `RenderModelViewer` / block components for rendering
- Modal overlay with close button, title bar showing document display_id and title
- Single modal depth: clicking a link inside a modal replaces the modal content (does not stack modals)
- Loading and error states

#### Out of Scope
- Editing from modal
- Hover previews
- Navigation breadcrumbs inside modal

### Preconditions
- WS-BINDER-001 complete (reference resolution available)
- Existing RenderModelViewer functional

### Procedure
1. Create `spa/src/components/DocumentModal.jsx`
2. Accept props: `documentId`, `version` (optional), `onClose`
3. Fetch document content and render model via existing API
4. Render in modal overlay (fixed position, backdrop, close on Escape)
5. Title bar shows display_id and document title
6. If a link is clicked inside the modal, replace modal content with the new document (no stacking)
7. Handle loading state (skeleton or spinner) and error state (document not found)
8. Write tests: renders document, closes on Escape, replaces content on internal link click

### Verification Criteria
1. Modal renders any document type using existing viewer
2. Close button and Escape key dismiss the modal
3. Internal links replace modal content rather than stacking
4. Loading and error states handled

### Definition of Done
- DocumentModal component created and functional
- Works with any document type
- All tests pass

### Prohibited Actions
- Do not create a separate rendering system for the modal
- Do not allow editing from the modal
- Do not allow modal stacking

---

## WS-BINDER-003 -- Inline Link Rendering in Block Components

### Purpose

Update existing block components and content rendering to detect document references and render them as clickable links that open the DocumentModal.

### Governing References
- ADR-071 (s3.4 First-Class Document Links)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- spa/src/components/blocks/
- spa/src/components/
- app/domain/services/
- tests/

### Scope

#### In Scope
- Reference detection in rendered text: identify patterns like `WS-142`, `TA-001`, `PD-001`, `WP-025`
- Render detected references as clickable `<span>` or `<a>` elements with resolved titles
- On click, open DocumentModal with the resolved document
- Batch-resolve references on component mount for performance
- Update server-side markdown renderer to include resolved titles (e.g., `WS-142: Local Entity Extractor`)

#### Out of Scope
- References inside code blocks or monospace sections (leave as-is)
- Custom styling per document type
- Graph or relationship visualization

### Preconditions
- WS-BINDER-001 complete (resolution service)
- WS-BINDER-002 complete (modal component)

### Procedure
1. Create a `DocumentLink` component: accepts display_id, renders as clickable element with resolved title
2. Create a `useResolvedReferences` hook: batch-resolves all display_ids found in a content block
3. Update paragraph and text block components to detect display_id patterns and render as `DocumentLink`
4. Wire `DocumentLink` click to open `DocumentModal`
5. Update `render_project_binder` in `app/domain/services/binder_renderer.py` to resolve titles server-side
6. Write tests: reference detection, link rendering, modal opening, server-side title resolution

### Verification Criteria
1. Text containing "WS-142" renders as a clickable link showing "WS-142: Local Entity Extractor"
2. Clicking the link opens DocumentModal with WS-142's content
3. Multiple references in one paragraph all resolve correctly
4. Server-side markdown includes resolved titles
5. Performance: batch resolution prevents N+1 queries

### Definition of Done
- Document references render as interactive links throughout the system
- Modal navigation functional from inline links
- Server-side title resolution functional
- All tests pass

### Prohibited Actions
- Do not modify canonical document content to embed links
- Do not use regex-only detection without resolution verification
- Do not create separate link rendering for binder vs document views

---

# WP-BINDER-002 -- Binder Composition via IA + Blocks

**Status:** Draft
**Date:** 2026-04-08
**Governing ADR:** ADR-071
**Priority:** NORMAL

## Objective

Implement binder documents as composition layers over existing documents. Binders reference, group, and sequence child documents using the existing IA + block rendering system. No separate binder renderer is created.

## Scope

### In Scope
- Binder document type with `referenced_documents` schema
- New block types for document composition: `document-reference-list`, `grouped-documents`
- IA definitions for binder documents
- Version-pinned document references stored in binder content
- Binder assembly service (builds binder content from project documents)

### Out of Scope
- Work Plan specific features (WP-BINDER-003)
- Editing from binder views
- Advanced visualization blocks

## Dependencies
- WP-BINDER-001 complete (link resolution and modal navigation)

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-BINDER-004 | Binder Document Schema and Assembly Service | a0 |
| WS-BINDER-005 | Composition Block Components | a1 |
| WS-BINDER-006 | Binder IA Definitions and Rendering | a2 |

## Verification Criteria
- Binder documents store version-pinned references to child documents
- Binder renders through IA + blocks showing grouped, sequenced documents
- Clicking a document reference opens modal with pinned version
- Binder assembly produces correct content from project state

## Allowed Paths
- app/domain/services/
- app/api/v1/routers/
- spa/src/components/
- spa/src/components/blocks/
- combine-config/document_types/
- combine-config/schemas/
- tests/

## Definition of Done
- Binder documents render as navigable composition of project documents
- All tests pass (Tier 0)

---

## WS-BINDER-004 -- Binder Document Schema and Assembly Service

### Purpose

Define the binder document schema with `referenced_documents` as a first-class structured field (per ADR-071 s3.5), and create the assembly service that builds binder content from current project documents.

### Governing References
- ADR-071 (s3.2 Binder = Composition Layer, s3.5 Version-Pinned Link Resolution)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- combine-config/schemas/
- combine-config/document_types/
- app/domain/services/
- tests/tier1/

### Scope

#### In Scope
- JSON Schema for binder documents: `referenced_documents` array with `{document_id, version, display_id, title, doc_type_id, group}`
- `group` field for logical grouping (e.g., "Architecture", "Work Packages", "Work Statements")
- Binder assembly service: queries project documents, builds binder content with version-pinned references
- Document type package for `work_binder`

#### Out of Scope
- UI rendering (WS-BINDER-005, WS-BINDER-006)
- Work Plan specific schema extensions (WP-BINDER-003)
- Staleness detection

### Preconditions
- ADR-071 accepted
- WP-BINDER-001 complete (link resolution available)

### Procedure
1. Create `combine-config/schemas/work_binder/releases/1.0.0/schema.json`
2. Define `referenced_documents` array with required fields: document_id, version, display_id, title, doc_type_id
3. Add optional `group` field for logical grouping
4. Add `summary` section for binder-level metadata (project_id, assembled_at, document_count)
5. Create document type package `combine-config/document_types/work_binder/releases/1.0.0/package.yaml`
6. Create `app/domain/services/binder_assembly_service.py`
7. Implement `assemble_binder(project_id) -> BinderContent`: queries latest stabilized documents, builds referenced_documents with pinned versions
8. Register in active_releases.json
9. Write tests: schema validation, assembly produces correct references, version pinning works

### Verification Criteria
1. Binder schema validates correctly with referenced_documents
2. Assembly service produces version-pinned references for all project documents
3. Each reference includes document_id, version, display_id, title, doc_type_id
4. Schema rejects references missing required fields
5. Document type package resolves through package loader

### Definition of Done
- Binder schema created and validated
- Assembly service produces correct binder content
- All tests pass

### Prohibited Actions
- Do not store references as ad-hoc text
- Do not resolve references at render time instead of assembly time
- Do not include full document content in the binder (references only)

---

## WS-BINDER-005 -- Composition Block Components

### Purpose

Create new block components for rendering binder-specific IA sections: document reference lists and grouped document displays.

### Governing References
- ADR-071 (s3.2 Binder = Composition Layer, s3.3 Presentation via IA + Blocks)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- spa/src/components/blocks/
- spa/src/components/
- tests/

### Scope

#### In Scope
- `DocumentReferenceListBlock`: renders a list of document references as clickable cards with display_id, title, doc_type_id
- `GroupedDocumentsBlock`: renders documents grouped by `group` field with section headers
- Both blocks use DocumentLink for click-to-modal navigation
- Both blocks are reusable from any IA definition (not binder-specific)

#### Out of Scope
- Work Plan specific blocks (summary, decision log)
- Inline document content embedding
- Visualization widgets

### Preconditions
- WS-BINDER-004 complete (binder schema defines the data)
- WP-BINDER-001 complete (DocumentLink and DocumentModal available)

### Procedure
1. Create `spa/src/components/blocks/DocumentReferenceListBlock.jsx`
2. Render each reference as a card: display_id badge, title, doc_type_id label
3. Click opens DocumentModal with the referenced document at pinned version
4. Create `spa/src/components/blocks/GroupedDocumentsBlock.jsx`
5. Group references by `group` field, render section headers, then DocumentReferenceListBlock per group
6. Register both blocks in the block component registry
7. Write tests: list renders references, grouped view creates correct sections, click triggers modal

### Verification Criteria
1. DocumentReferenceListBlock renders all referenced documents as clickable cards
2. GroupedDocumentsBlock groups correctly by group field
3. Clicking a card opens DocumentModal with correct document and version
4. Both blocks are reusable from any IA section with appropriate render_as

### Definition of Done
- Both block components created and registered
- Functional with binder data
- All tests pass

### Prohibited Actions
- Do not create binder-specific rendering logic outside the block system
- Do not embed full document content in the block (reference + modal only)

---

## WS-BINDER-006 -- Binder IA Definitions and Rendering

### Purpose

Create IA definitions for the work_binder document type so binders render correctly through the existing IA + block viewer.

### Governing References
- ADR-071 (s3.3 Presentation via IA + Blocks, s3.7 Dual Rendering Contract)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- combine-config/document_types/work_binder/
- app/domain/services/
- tests/tier1/config/

### Scope

#### In Scope
- IA definition for work_binder document type with sections: summary, grouped documents
- `render_as` hints for new block types: `document-reference-list`, `grouped-documents`
- Update server-side binder renderer to consume IA definitions (per ADR-071 s3.7 dual rendering contract)

#### Out of Scope
- Work Plan IA (WP-BINDER-003)
- Custom visualization sections

### Preconditions
- WS-BINDER-004 complete (schema exists)
- WS-BINDER-005 complete (block components exist)

### Procedure
1. Add `information_architecture` to `combine-config/document_types/work_binder/releases/1.0.0/package.yaml`
2. Define sections: summary (render_as: paragraph), documents (render_as: grouped-documents)
3. Update server-side `render_project_binder` to consume IA section definitions for structure
4. Verify client-side rendering picks up IA and renders through blocks
5. Write tests: IA golden contract tests for work_binder

### Verification Criteria
1. Binder renders through IA + blocks on the client
2. Server-side markdown rendering follows same IA structure
3. IA golden contract tests pass

### Definition of Done
- IA definitions created for work_binder
- Both client and server rendering consume same IA structure
- All tests pass

### Prohibited Actions
- Do not create a separate binder rendering path
- Do not bypass IA for binder presentation

---

# WP-BINDER-003 -- Work Plan Viewer

**Status:** Draft
**Date:** 2026-04-08
**Governing ADR:** ADR-071
**Priority:** NORMAL

## Objective

Create the Work Plan as the system's primary consumable artifact: a read-only binder with an executive summary, grouped work items, decision log, and dependency context. This is the final stage of the operator-facing pipeline.

## Scope

### In Scope
- Work Plan document type (extends binder with summary layer)
- Executive summary section (auto-composed from project documents)
- Grouped work items with dependency and sequencing context
- Decision log (synthesis decisions embedded as governed content)
- Read-only presentation suitable for review and handoff
- Pipeline integration: Work Plan as final stage

### Out of Scope
- Editing from Work Plan view
- Export to PDF or external formats
- Advanced dependency graph visualization
- Workflow execution from Work Plan

## Dependencies
- WP-BINDER-001 complete (link resolution and modal navigation)
- WP-BINDER-002 complete (binder composition and rendering)

## Work Statements

| WS ID | Title | Order |
|-------|-------|-------|
| WS-BINDER-007 | Work Plan Document Type and Assembly | a0 |
| WS-BINDER-008 | Work Plan Summary and Decision Log Blocks | a1 |
| WS-BINDER-009 | Pipeline Integration and Final Presentation | a2 |

## Verification Criteria
- Work Plan renders as a coherent, read-only artifact
- Executive summary accurately reflects project scope
- Grouped work items show dependencies and sequencing
- Decision log shows synthesis decisions with operator resolutions
- Work Plan is accessible as the final pipeline stage

## Allowed Paths
- app/domain/services/
- app/api/v1/routers/
- spa/src/components/
- spa/src/components/blocks/
- combine-config/document_types/
- combine-config/schemas/
- tests/

## Definition of Done
- Work Plan renders as a professional, readable artifact
- Operator can review the complete plan in one view
- All tests pass (Tier 0)

---

## WS-BINDER-007 -- Work Plan Document Type and Assembly

### Purpose

Define the Work Plan document type as an extended binder with summary fields, and create the assembly service that composes the Work Plan from project state including synthesis decisions.

### Governing References
- ADR-071 (s3.8 Work Plan as Final Binder Artifact)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- combine-config/schemas/
- combine-config/document_types/
- app/domain/services/
- tests/tier1/

### Scope

#### In Scope
- JSON Schema for work_plan: extends binder schema with executive_summary, decision_log, dependency_summary
- Document type package for work_plan
- Assembly service: builds Work Plan from binder content + synthesis decisions + dependency graph
- Executive summary composed from PD scope, TA components, WP/WS counts

#### Out of Scope
- UI rendering (WS-BINDER-008, WS-BINDER-009)
- LLM-generated summaries (mechanical composition only)

### Preconditions
- WP-BINDER-002 complete (binder assembly functional)
- Synthesis decisions available (ADR-070)

### Procedure
1. Create `combine-config/schemas/work_plan/releases/1.0.0/schema.json`
2. Extend binder schema with: executive_summary (object), decision_log (array of decisions), dependency_summary (array of dependency edges)
3. Create document type package `combine-config/document_types/work_plan/releases/1.0.0/package.yaml`
4. Create `app/domain/services/work_plan_assembly_service.py`
5. Implement `assemble_work_plan(project_id) -> WorkPlanContent`
6. Compose executive_summary from: PD objectives/scope, TA component count, WP count, WS count, key constraints
7. Build decision_log from synthesis delta operator decisions
8. Build dependency_summary from WP/WS dependency references
9. Register in active_releases.json
10. Write tests: schema validation, assembly produces correct structure, decision log populated correctly

### Verification Criteria
1. Work Plan schema validates correctly
2. Assembly produces executive summary from project documents
3. Decision log includes synthesis decisions with operator notes
4. Dependency summary captures WP/WS relationships
5. Document type package resolves

### Definition of Done
- Work Plan schema and document type created
- Assembly service produces correct Work Plan content
- All tests pass

### Prohibited Actions
- Do not use LLM to generate the executive summary (mechanical composition only)
- Do not embed full document content (references only, consistent with binder model)
- Do not allow Work Plan to mutate source documents

---

## WS-BINDER-008 -- Work Plan Summary and Decision Log Blocks

### Purpose

Create block components for Work Plan specific sections: executive summary display, decision log with operator resolutions, and dependency overview.

### Governing References
- ADR-071 (s3.3 Presentation via IA + Blocks, s3.8 Work Plan)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- spa/src/components/blocks/
- spa/src/components/
- tests/

### Scope

#### In Scope
- `ExecutiveSummaryBlock`: renders project objectives, scope, component count, WS count, key constraints
- `DecisionLogBlock`: renders synthesis decisions with severity, headline, operator decision, and resolution note
- `DependencySummaryBlock`: renders WP/WS dependency relationships as a readable list with sequencing context
- All blocks reusable from any IA definition

#### Out of Scope
- Interactive dependency graph
- Decision editing (read-only)
- Gantt or timeline visualization

### Preconditions
- WS-BINDER-007 complete (Work Plan schema and assembly)

### Procedure
1. Create `spa/src/components/blocks/ExecutiveSummaryBlock.jsx`
2. Render: project name, objectives, key constraints, component/WS counts, scope summary
3. Create `spa/src/components/blocks/DecisionLogBlock.jsx`
4. Render each decision: severity badge, headline, operator decision (accepted/rejected/resolved), resolution note
5. Create `spa/src/components/blocks/DependencySummaryBlock.jsx`
6. Render dependency edges as readable list: "WS-148 depends on WS-139 (Basic Journal Display)"
7. Register all blocks in block component registry
8. Write tests: each block renders correct content, handles empty data gracefully

### Verification Criteria
1. Executive summary renders project overview in readable form
2. Decision log shows all decisions with operator context
3. Dependency summary shows relationships with document titles
4. All blocks handle missing/empty data without error

### Definition of Done
- All three block components created and registered
- Functional with Work Plan data
- All tests pass

### Prohibited Actions
- Do not allow editing from these blocks
- Do not create separate rendering paths for Work Plan vs other documents

---

## WS-BINDER-009 -- Pipeline Integration and Final Presentation

### Purpose

Wire the Work Plan into the operator-facing pipeline as the final stage, rename pipeline stages for operator legibility, and ensure the Work Plan is accessible as the system's primary output artifact.

### Governing References
- ADR-071 (s3.8 Work Plan as Final Binder Artifact)
- POL-WS-001

### Verification Mode
A

### Allowed Paths
- spa/src/components/
- spa/src/hooks/
- app/api/v1/routers/
- app/domain/services/
- tests/

### Scope

#### In Scope
- Pipeline stage renaming: current "Work Binder" -> "Work Items", "Synthesis" -> "Review & Resolve", add "Work Plan" as final stage
- Work Plan trigger: after synthesis is resolved, operator can generate the Work Plan
- Work Plan display via existing document viewer (IA + blocks)
- Read-only enforcement: no edit controls on Work Plan view

#### Out of Scope
- PDF export
- Pipeline stage reordering beyond the three renames
- Changes to upstream pipeline stages

### Preconditions
- WS-BINDER-007 complete (Work Plan assembly)
- WS-BINDER-008 complete (block components)

### Procedure
1. Update pipeline stage labels in `spa/src/hooks/useProductionStatus.js` and `spa/src/components/Floor.jsx`
2. Rename: "Work Binder" -> "Work Items", "Synthesis" -> "Review & Resolve"
3. Add "Work Plan" as final virtual pipeline node (same pattern as synthesis)
4. Add trigger: "Generate Work Plan" button after synthesis is resolved
5. Wire trigger to Work Plan assembly service endpoint
6. Work Plan renders through existing document viewer using its IA definitions
7. Ensure Work Plan view has no edit controls
8. Write tests: pipeline labels correct, Work Plan generation trigger works, read-only enforcement

### Verification Criteria
1. Pipeline shows: ... -> Work Items -> Review & Resolve -> Work Plan
2. Work Plan can be generated after synthesis resolution
3. Work Plan renders through existing IA + block viewer
4. No edit controls appear on Work Plan view
5. Pipeline state reflects Work Plan generation status

### Definition of Done
- Pipeline stages renamed for operator legibility
- Work Plan accessible as final pipeline stage
- Read-only presentation enforced
- All tests pass

### Prohibited Actions
- Do not add Work Plan as a PipelineStage enum value (virtual node, same as synthesis)
- Do not allow Work Plan to trigger workflow re-execution
- Do not add edit controls to the Work Plan view
