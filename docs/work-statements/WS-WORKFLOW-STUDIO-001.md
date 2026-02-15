# WS-WORKFLOW-STUDIO-001: Technical Architecture Workflow Studio

## Status: Complete

## Context

Technical Architecture documents contain multiple workflow specifications (e.g., "Teacher Session Setup", "Student Problem Solving", "Authentication Flow"). The current approach renders these as stacked React Flow diagrams in a scrolling document view. This doesn't scale:

- Workflows compete for vertical space
- No way to focus on a single workflow without losing context of others
- Complex diagrams are cramped in document-width containers
- No lineage visibility (which DCW/gate/operation backs each step)

The Admin Workbench already establishes a pattern for this: vertical rail navigation with expanded detail panels. We should apply the same pattern to workflow visualization within documents.

## Objective

Create a dedicated "Workflow Studio" experience within Technical Architecture documents that:
1. Segregates behavioral specifications (workflows) from static architecture content
2. Provides a vertical rail for navigating multiple workflows
3. Renders selected workflows in high-fidelity expanded diagrams
4. Supports lineage tracing from diagram nodes back to DCW/gate/operation definitions

---

## Phase 1: Tabbed Document Viewer

**Objective:** Add tab navigation to Technical Architecture document viewer, separating content by abstraction level.

**Tab Structure:**
- **Overview** - Executive summary, key decisions, constraints
- **Components** - System blocks, integrations, data flows  
- **Workflows** - Behavioral specifications (workflow diagrams)

**Implementation:**

1. Create `TechnicalArchitectureViewer.jsx` component
   - Detects document type and renders tabbed layout
   - Tab state managed locally (or via URL hash for bookmarkability)
   - Each tab renders appropriate RenderModel blocks

2. Update `FullDocumentViewer.jsx` to route Technical Architecture documents to new viewer

3. Content routing logic:
   - Overview tab: `executive_summary`, `key_decisions`, `constraints`, `assumptions`
   - Components tab: `system_components`, `integrations`, `data_flows`, `security_considerations`
   - Workflows tab: `workflows[]` array (entire block)

**Files to Create/Modify:**
- `spa/src/components/viewers/TechnicalArchitectureViewer.jsx` (create)
- `spa/src/components/FullDocumentViewer.jsx` (modify - add routing)

**Verification:**
- [ ] Technical Architecture document renders with 3 tabs
- [ ] Tab navigation persists selected tab
- [ ] Content correctly distributed across tabs
- [ ] Other document types unaffected

---

## Phase 2: Workflow Vertical Rail

**Objective:** Within the Workflows tab, implement a vertical rail for navigating multiple workflows.

**Layout:**
```
+------------------+----------------------------------------+
| Workflows Tab                                             |
+------------------+----------------------------------------+
| [Rail]           | [Active Workspace]                     |
|                  |                                        |
| > Session Setup  |  +----------------------------------+  |
|   Problem Solve  |  |  Session Setup Workflow          |  |
|   Auth Flow      |  |  [React Flow Diagram]            |  |
|   Error Recovery |  |                                  |  |
|                  |  |  [Expand] [Lineage] [Audit]      |  |
|                  |  +----------------------------------+  |
+------------------+----------------------------------------+
```

**Implementation:**

1. Create `WorkflowStudioPanel.jsx`
   - Left rail: workflow names from `workflows[].name`
   - Center: selected workflow diagram (WorkflowBlockV2)
   - Rail selection state, keyboard navigation (up/down arrows)

2. Rail item display:
   - Workflow name
   - Node count badge (e.g., "8 steps")
   - Type indicator if available (linear vs branching)

3. Active workspace:
   - Full-width diagram rendering
   - Control bar: Expand (fullscreen), Lineage toggle, Audit button

**Files to Create/Modify:**
- `spa/src/components/viewers/WorkflowStudioPanel.jsx` (create)
- `spa/src/components/viewers/TechnicalArchitectureViewer.jsx` (modify - integrate panel)

**Verification:**
- [ ] Vertical rail shows all workflows from document
- [ ] Clicking rail item switches active diagram
- [ ] Keyboard navigation works (arrow keys)
- [ ] Diagram fills available space properly
- [ ] Works with 1 workflow, 5 workflows, 10+ workflows

---

## Phase 3: Lineage Toggle and Audit Controls

**Objective:** Add lineage visibility showing how diagram nodes trace back to DCW/gate/operation definitions.

**Lineage Display (per node):**
- **Collapsed (default):** Step name + type badge
- **Expanded (lineage on):** 
  - DCW reference (e.g., `dcw:project_discovery:2.0.0`)
  - Gate profile internals (e.g., `pass_a/LLM, entry/UI, merge/MECH`)
  - Operation refs (e.g., `op:pgc_clarification_processor`)
  - Task prompt ref (e.g., `prompt:task:project_discovery:1.4.0`)

**Implementation:**

1. Enhance `ArchWorkflowNode.jsx` with lineage mode:
   - Accept `showLineage` prop
   - Render expanded node with reference details
   - Visual treatment: subtle background, monospace refs

2. Add Lineage toggle to WorkflowStudioPanel control bar:
   - Toggle state passed to WorkflowBlockV2
   - Persists per-session (or per-workflow)

3. Add Audit button:
   - Opens modal/drawer with full workflow definition JSON
   - Useful for debugging and verification

**Files to Create/Modify:**
- `spa/src/components/blocks/ArchWorkflowNode.jsx` (modify - lineage mode)
- `spa/src/components/blocks/WorkflowBlockV2.jsx` (modify - accept lineage prop)
- `spa/src/components/viewers/WorkflowStudioPanel.jsx` (modify - controls)
- `spa/src/components/viewers/WorkflowAuditDrawer.jsx` (create)

**Verification:**
- [ ] Lineage toggle expands all nodes with reference details
- [ ] Node sizing adjusts for expanded content
- [ ] Audit button shows raw workflow definition
- [ ] Toggle state persists during session

---

## Files Summary

| Phase | File | Action |
|-------|------|--------|
| 1 | `spa/src/components/viewers/TechnicalArchitectureViewer.jsx` | Create |
| 1 | `spa/src/components/FullDocumentViewer.jsx` | Modify |
| 2 | `spa/src/components/viewers/WorkflowStudioPanel.jsx` | Create |
| 2 | `spa/src/components/viewers/TechnicalArchitectureViewer.jsx` | Modify |
| 3 | `spa/src/components/blocks/ArchWorkflowNode.jsx` | Modify |
| 3 | `spa/src/components/blocks/WorkflowBlockV2.jsx` | Modify |
| 3 | `spa/src/components/viewers/WorkflowStudioPanel.jsx` | Modify |
| 3 | `spa/src/components/viewers/WorkflowAuditDrawer.jsx` | Create |

---

## Prohibited

- Do not modify RenderModel or document content structure
- Do not change how workflows are stored in documents
- Do not affect other document types (Project Discovery, etc.)
- Do not add external dependencies for tab/rail components
- Do not break existing WorkflowBlockV2 rendering in other contexts

---

## Design Principles

1. **Separation of concerns:** Static content (what) vs behavioral specs (how)
2. **Scalability:** Handle 1-20 workflows without UI degradation  
3. **Consistency:** Mirror Workbench patterns (vertical rail, expanded detail)
4. **Traceability:** Every diagram node traceable to source definition
5. **Progressive disclosure:** Simple view by default, detail on demand
