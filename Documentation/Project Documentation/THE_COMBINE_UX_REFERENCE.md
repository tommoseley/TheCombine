# The Combine — UX Reference Documentation

**Document Type:** UX Behavioral Reference  
**Status:** Canonical  
**Version:** 1.0  
**Date:** December 2025  
**Audience:** Designers, Engineers, Product Partners  

---

## 1. Mental Model

### 1.1 What The Combine Is

The Combine is a document production workbench. Users create projects and produce structured documents within those projects. The system generates documents using AI; users review and accept them.

The Combine is **not**:
- A chat interface
- A project management tool
- A task tracker
- An autonomous agent system

### 1.2 Core Concepts

| Concept | Definition |
|---------|------------|
| **Project** | A container for documents. Has a name, description, and icon. Documents live inside projects. |
| **Document** | A structured artifact produced by the system. Has a type, content, and status. |
| **Document Type** | A category of document (e.g., "Project Discovery", "Epic Backlog"). Defines what the document contains, what it requires, and who must accept it. |
| **Readiness** | Whether a document can be built or used. Derived from document state and dependencies. |
| **Acceptance** | Whether a human has approved a document. Required for some document types before downstream use. |

### 1.3 User vs. System Responsibilities

**The user is responsible for:**
- Creating projects
- Triggering document generation
- Reviewing generated documents
- Accepting or rejecting documents
- Deciding when to rebuild stale documents

**The system is responsible for:**
- Generating document content via AI
- Tracking document dependencies
- Deriving document status
- Enforcing dependency gates
- Surfacing what is safe, risky, or missing

**The system explicitly does not:**
- Generate documents automatically
- Decide what the user should do next
- Hide problems or risks
- Make acceptance decisions

### 1.4 The Dossier Model

A project is a dossier—a collection of documents that together define what is being built. The user's job is to ensure the dossier is complete. The system's job is to help produce the documents.

This is not a pipeline to be "run." It is a checklist to be satisfied.

```
☐ Project Discovery
☐ Epic Backlog
☐ Technical Architecture
☐ Story Backlog
```

Each item knows what it depends on, what it unlocks, and whether it exists.

---

## 2. Navigation Model

### 2.1 Layout Structure

The interface uses a three-pane layout:

| Region | Position | Purpose |
|--------|----------|---------|
| **Sidebar** | Left | Project tree, document navigation |
| **Workspace** | Center | Current document content |
| **Activity** | Right | (Reserved for future: status, history) |

Panels are anchored. They do not float, overlap, or relocate. On smaller screens, panels stack or collapse but their roles remain unchanged.

### 2.2 Project Selection

The sidebar displays a tree of projects. Each project row contains:

1. **Chevron button** — Expands/collapses the document list
2. **Project icon** — Visual identifier
3. **Project name** — Clickable link to project detail page
4. **Status summary** — Counts of documents by status (visible in collapsed state)

**Interaction behavior:**
- Clicking the chevron toggles the document list open/closed
- Clicking the project name navigates to the project detail page
- Opening one project closes other open projects (accordion behavior)

### 2.3 Document Discovery

When a project is expanded, the sidebar displays all document types for that project:

| Element | Display |
|---------|---------|
| Document icon | From document type configuration |
| Document title | Document type name (or document title if exists) |
| Subtitle | Status hint (e.g., "Needs acceptance (PM)", "Missing: project_discovery") |
| Status icon | Readiness and/or acceptance indicator |

Documents are ordered by `display_order` from the document type configuration.

**Clicking a document** navigates to that document's view in the workspace.

### 2.4 Default Document Behavior

When a user navigates to a document that exists:
- The workspace displays the document content
- The document is rendered using its handler's template

When a user navigates to a document that does not exist:
- The workspace displays the "Not Created" state
- This is a normal UI state, not an error

### 2.5 URL Structure

```
/ui/projects/{project_id}                           → Project detail page
/ui/projects/{project_id}/documents/{doc_type_id}   → Document view
```

URLs support direct navigation. Browser refresh loads the full page. HTMX navigation loads partials.

---

## 3. Document Lifecycle UX

### 3.1 Document States

A document exists in one of four readiness states:

| State | Meaning | Visual |
|-------|---------|--------|
| **Waiting** | Can be built, not yet built | Gray clock icon |
| **Ready** | Exists, valid, safe to use | Green checkmark |
| **Stale** | Exists, but inputs changed | Amber warning |
| **Blocked** | Cannot be built (missing dependencies) | Red X |

### 3.2 The "Not Created" Screen

When a document does not exist, the workspace displays:

1. **Document type icon** (large)
2. **Document type name** (heading)
3. **Document type description** (from database)
4. **Generate button** (primary action)

The Generate button triggers document creation via streaming SSE.

**If the document is blocked:**
- The Generate button is disabled
- The missing dependencies are listed
- The user cannot proceed until dependencies are satisfied

### 3.3 Document Generation Flow

1. User clicks "Generate {Document Type}"
2. System checks dependencies
3. If blocked: display error, list missing dependencies
4. If ready: begin streaming build
5. Progress updates display via SSE:
   - Loading configuration
   - Checking dependencies
   - Gathering inputs
   - Loading prompts
   - Generating (with preview)
   - Parsing
   - Saving
   - Complete
6. On completion: workspace refreshes to show new document

### 3.4 Blocking vs. Non-Blocking Documents

**Blocking (readiness = blocked):**
- Cannot be built
- Generate button disabled
- Missing dependencies listed in subtitle
- Row appears dimmed in sidebar

**Non-blocking (readiness = waiting):**
- Can be built immediately
- Generate button enabled
- No subtitle or neutral subtitle

### 3.5 Staleness

When an upstream document changes, downstream documents become stale:

| Display | Meaning |
|---------|---------|
| Amber warning icon | Document exists but inputs have changed |
| Subtitle: "Inputs changed — review recommended" | (When stale + accepted) |

Stale documents remain usable. The system does not force rebuilds.

### 3.6 Acceptance

Some document types require human acceptance before downstream use.

**Acceptance states:**

| State | Meaning | Icon |
|-------|---------|------|
| `needs_acceptance` | Document exists, awaiting approval | Amber warning |
| `accepted` | Document approved | Green dot |
| `rejected` | Changes requested | Red dot |

**Acceptance rules:**
- Acceptance icons appear only when `acceptance_required = true`
- Documents without acceptance requirements show only readiness icons
- Rejected documents display subtitle: "Changes requested"
- Stale + accepted documents display subtitle: "Inputs changed — review recommended"

### 3.7 What "Done" Means

A document is "done" when:
1. It exists (readiness = ready or stale)
2. If acceptance required: it is accepted

A project is "complete" when all required document types are done.

The system does not define "done" for the user. It surfaces state; the user decides significance.

---

## 4. Status & Truthfulness

### 4.1 Status Display Principles

The system never tells the user what to think. It tells them:
- What's **safe** (ready, accepted)
- What's **risky** (stale, needs review)
- What's **missing** (blocked, waiting)

Status is derived, never stored. Every render computes status from current state.

### 4.2 Status Icon System

**Readiness icons (always shown):**

| Icon | Color | Status |
|------|-------|--------|
| ✓ | Green | Ready |
| ⚠ | Amber | Stale |
| ✕ | Red | Blocked |
| ○ | Gray | Waiting |

**Acceptance icons (shown only when required):**

| Icon | Color | State |
|------|-------|-------|
| ● | Green | Accepted |
| ● | Amber | Needs acceptance |
| ● | Red | Rejected |

### 4.3 Sidebar Status Summary

The collapsed project row shows aggregate counts:

```
{Project Name}                    ✓2  ⚠1  ✕1  ○1
```

This allows scanning project health without expansion.

### 4.4 What the System Refuses to Hide

The system always displays:

| Condition | Display |
|-----------|---------|
| Missing dependencies | Listed explicitly in subtitle |
| Stale documents | Amber warning, even if accepted |
| Rejected documents | Red indicator, subtitle explains |
| Blocked documents | Dimmed row, disabled actions |

The system does not:
- Collapse warnings into generic "issues" counts
- Hide staleness after acceptance
- Suppress rejection reasons
- Default to optimistic status

### 4.5 Subtitle Rules

Subtitles provide actionable context:

| Condition | Subtitle |
|-----------|----------|
| Blocked | "Missing: {dependency1}, {dependency2}" |
| Needs acceptance | "Needs acceptance ({role})" |
| Rejected | "Changes requested" |
| Stale + Accepted | "Inputs changed — review recommended" |
| Waiting + Acceptance required | "Will need acceptance ({role})" |

---

## 5. Button Enablement

### 5.1 Action Conditions

| Action | Enabled When |
|--------|--------------|
| **Generate** | `readiness = waiting` or `readiness = stale` |
| **Rebuild** | `readiness = stale` |
| **Accept** | `acceptance_state = needs_acceptance` |
| **Request Changes** | `acceptance_state = needs_acceptance` or `acceptance_state = accepted` |

### 5.2 Disabled State Behavior

Disabled buttons remain visible but inactive. The UI does not hide actions that are temporarily unavailable.

This allows users to understand the full action space even when some actions are gated.

---

## 6. Integration Posture

### 6.1 What The Combine Produces

The Combine produces structured project documents:
- Project Discovery (architectural exploration)
- Epic Backlog (work stream decomposition)
- Technical Architecture (component specification)
- Story Backlog (implementation-ready stories)

These documents are self-contained artifacts with full content in JSON format.

### 6.2 Export Capabilities

Documents can be exported as:
- **Markdown** — Human-readable format for sharing
- **JSON** — Machine-readable format for import into other tools

Export is one-way. The Combine does not import from external systems.

### 6.3 Relationship to Other Tools

| Tool Category | The Combine's Position |
|---------------|------------------------|
| **Jira, Linear, Asana** | The Combine produces documents that can be exported to these tools. It does not sync with them. |
| **Notion, Confluence** | The Combine produces structured documents. Export to these tools is manual (copy/paste or import). |
| **GitHub, GitLab** | The Combine does not interact with source control. Documents are about what to build, not how to build it. |
| **Figma, design tools** | No integration. The Combine produces specifications, not designs. |

### 6.4 Where The System Intentionally Stops

The Combine stops at document production. It does not:

- **Track work progress** — No sprint boards, burndown charts, or velocity
- **Manage assignments** — No user assignment, workload, or capacity
- **Sync bidirectionally** — Export only, no import or sync
- **Execute implementation** — Documents describe work; they do not perform it
- **Provide collaboration** — Single-user workflows only (MVP)

### 6.5 Handoff Model

The expected workflow:

1. User creates project in The Combine
2. User generates documents through the pipeline
3. User reviews and accepts documents
4. User exports documents (Markdown or JSON)
5. User imports into work management tool (Jira, Linear, etc.)
6. Work proceeds in external tool

The Combine's job is complete after step 4. Steps 5-6 happen outside the system.

---

## 7. Design Constraints

### 7.1 Governing Principles

From the Design Manifesto:

| Principle | Meaning |
|-----------|---------|
| **Calm Authority** | The interface communicates competence through restraint, not excitement through novelty |
| **Spatial over Temporal** | Three-pane structure, not chat flow |
| **Boring Buttons** | Clear verbs, no personality, predictable behavior |
| **Dense but Legible** | High information density with strict readability rules |

### 7.2 What the UI Never Does

- Gradients
- AI personality avatars
- Marketing language
- Thin fonts or pure white backgrounds
- Surprises in interaction patterns
- Clever animations
- Tooltips as primary information (all critical status is always visible)

### 7.3 Color as Information

Status colors are reserved strictly for state:

| Color | Meaning |
|-------|---------|
| Green | Complete, validated, safe |
| Amber | Needs attention, review, input |
| Red | Error, blocked, failed |
| Blue | In progress, active |
| Gray | Neutral, not yet acted upon |

Color is never decoration. When color is rare, it becomes trustworthy.

---

## 8. Behavioral Specifications

### 8.1 HTMX Navigation

- HTMX requests return partial HTML (content only)
- Browser requests return full page HTML
- Detection: `HX-Request: true` header
- URL updates via `hx-push-url="true"`

### 8.2 Accordion Behavior

- Only one project expanded at a time
- Opening a project closes others
- Chevron rotates to indicate state
- Content area uses CSS max-height transition

### 8.3 Active State Tracking

- Current document highlighted in sidebar
- Parent project expanded when document selected
- Active states update on URL change (popstate, htmx:pushedIntoHistory)

### 8.4 Streaming Build UX

- SSE connection opened on build start
- Progress updates rendered incrementally
- Status messages include emoji prefixes for quick scanning
- Completion triggers content refresh
- Errors display in stream, not as separate modals

---

*This document describes The Combine's UX as it currently behaves. It does not propose changes or improvements.*
