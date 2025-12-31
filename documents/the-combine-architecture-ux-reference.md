# The Combine: Architecture & User Experience Reference

**Document Type:** Internal Architecture & UX Reference  
**Status:** Living Document  
**Audience:** Architects, Product Designers, Maintainers  

---

## 1. System Philosophy

The Combine is a document-centric system for producing structured project artifacts. The system's organizing principle is that **documents are the product**. Everything else—workers, prompts, generation logic—exists to serve document production.

### Core Tenets

1. **Documents are first-class citizens.** The system is organized around what gets produced, not who produces it or how.

2. **Single source of truth.** For any project, there is exactly one canonical list of documents. This list appears in exactly one place in the UI.

3. **Manual control is first-class.** The system informs; the user decides. Automation assists but never overrides human judgment.

4. **The system never tells the user what to think.** It reports what is safe, what is risky, and what is missing. Interpretation belongs to the user.

5. **Workers are anonymous labor.** The user cares about the document, not the worker that produced it. Role-based UX is explicitly rejected.

---

## 2. User Experience

### 2.1 Navigation Model

The interface follows a **three-panel layout**:

```
┌─────────────────┬─────────────────┬────────────────────────────┐
│                 │                 │                            │
│    Projects     │    Documents    │     Document Detail        │
│    (Sidebar)    │    (List)       │     (Content + Actions)    │
│                 │                 │                            │
└─────────────────┴─────────────────┴────────────────────────────┘
```

**Left Panel: Project Sidebar**
- Flat alphabetical list of all projects
- Each project displays: icon, name
- Clicking a project loads the document list for that project
- The sidebar is resizable and collapsible
- When collapsed, shows only project icons

**Center Panel: Document List**
- The **single canonical list** of documents for the selected project
- Always visible when viewing any document within the project
- Shows document type, title, readiness status, and acceptance state
- Active document is highlighted
- This is the **only** place documents are listed

**Right Panel: Document Detail**
- Displays the selected document's content
- Shows generation actions (Generate, Regenerate)
- Shows acceptance actions (Accept, Reject) when applicable
- Shows document metadata (last updated, status)

### 2.2 The Canonical Document List

There is exactly one document list per project. This is not a design constraint—it is the design.

**Why one list:**
- Eliminates confusion about which view is authoritative
- Prevents UI-level duplication of navigation paths
- Ensures the user always knows where to find document status
- Supports the "glanceable dashboard" mental model

**What the list shows:**
- Document type icon
- Document title
- Readiness indicator (ready / stale / blocked / waiting)
- Acceptance indicator (accepted / pending / rejected), when applicable
- Subtitle with context (e.g., "Will need acceptance (PM)")

**What the list does NOT show:**
- Worker or role information
- Generation history
- Multiple versions of the same document type

### 2.3 Understanding Status at a Glance

The user should be able to look at the document list and immediately understand:

| Visual Indicator | Meaning |
|------------------|---------|
| ✓ Green check | Ready — safe to use |
| ⚠ Amber triangle | Stale — inputs changed, review recommended |
| ✗ Red circle | Blocked — missing required inputs |
| ○ Gray clock | Waiting — ready to build, not yet generated |
| ● Green dot | Accepted |
| ● Yellow dot | Needs acceptance |
| ● Red dot | Rejected — changes requested |

The user infers next steps from status, not from system directives.

### 2.4 Document View

When a document is selected:

1. The document list remains visible (center panel persists)
2. The document content appears in the right panel
3. Actions appear contextually:
   - **Generate** — when document does not exist and is not blocked
   - **Regenerate** — when document exists
   - **Accept / Reject** — when document requires acceptance and is pending

The document view never hides the document list. The user always maintains orientation within the project's document structure.

---

## 3. Document Model

### 3.1 What is a Document

A **document** is a structured artifact produced for a project. Each document:

- Belongs to exactly one project
- Has exactly one document type
- Contains structured JSON content
- Has a readiness status
- May have an acceptance state
- May depend on other documents

Documents are **not files**. There is no filesystem metaphor. Documents are records in a database with typed content.

### 3.2 Document Types vs Documents

A **document type** is a schema definition. It specifies:

- The structure of content the document will contain
- What other document types it requires (dependencies)
- What other document types it derives from
- Whether acceptance is required
- Who is responsible for acceptance (if applicable)
- The icon and display title

A **document** is an instance of a document type within a project. A project may have zero or one document of each type. There are no multiple versions visible to the user—only the current state.

### 3.3 Readiness Status

Readiness indicates whether a document can be safely used or generated.

| Status | Meaning |
|--------|---------|
| **ready** | Document exists and all inputs are current. Safe to use. |
| **stale** | Document exists but inputs have changed. Review recommended. |
| **blocked** | Cannot generate. Required dependencies are missing. |
| **waiting** | Can be generated. Dependencies are satisfied but document does not exist. |

Readiness is **computed**, not stored. It derives from:
- Whether the document exists
- Whether required dependencies exist
- Whether dependencies have been modified since this document was generated

### 3.4 Acceptance State

Acceptance indicates human approval status for documents that require review.

| State | Meaning |
|-------|---------|
| **accepted** | Human has approved this document |
| **needs_acceptance** | Document exists but awaits approval |
| **rejected** | Human has requested changes |
| **not_required** | This document type does not require acceptance |

Acceptance is **stored**, not computed. It is set by explicit user action.

### 3.5 Readiness and Acceptance are Orthogonal

These two dimensions are independent:

- A document can be **ready** (inputs current) but **needs_acceptance** (not yet approved)
- A document can be **accepted** but **stale** (inputs changed after approval)
- A document can be **blocked** regardless of acceptance state

The UI displays both indicators independently. The user interprets their combination.

### 3.6 Dependencies

Documents declare dependencies through two mechanisms:

**`requires`** — Hard dependency. The document cannot be generated until these exist.
- Enforces generation order
- Creates "blocked" status when missing

**`derived_from`** — Soft dependency. The document uses these as inputs.
- Does not block generation
- Triggers "stale" status when inputs change

Example:
```
epic_backlog:
  requires: [project_discovery]
  derived_from: [project_discovery]
  
technical_architecture:
  requires: [project_discovery]
  derived_from: [project_discovery, epic_backlog]
```

### 3.7 Staleness Propagation

When a document is regenerated, all documents that declare it in `derived_from` become **stale**.

Propagation is:
- Immediate (computed on read)
- Transitive (if A derives from B, and B derives from C, regenerating C makes both B and A stale)
- Non-blocking (stale documents can still be used)

The system reports staleness. The user decides whether to regenerate.

### 3.8 Downstream Gating

Documents that `require` another document cannot be generated until that document exists and is not blocked.

Gating is:
- Enforced at generation time
- Reflected in "blocked" status
- Not dependent on acceptance state

**Open Question:** Should downstream gating consider acceptance state? Current behavior: No. A document can be generated as soon as its requirements exist, regardless of whether those requirements are accepted.

---

## 4. Organization & Structure

### 4.1 Projects as Dossiers

A **project** is a container for a set of related documents. The metaphor is a **dossier**—a folder containing all the paperwork for a case.

A project has:
- A unique identifier
- A display name (editable)
- An icon (selectable)
- A description (optional)
- A set of documents (zero or more)

Projects do not have:
- Nested folders
- Tags or categories
- Workflows or stages
- Role assignments

### 4.2 No Filesystem Metaphor

Documents are not organized in folders. There is no hierarchy within a project. The document list is flat.

**Why:**
- Document types form a dependency graph, not a tree
- Folders imply organization by human; documents are organized by type
- Flat lists are glanceable; trees require expansion

### 4.3 No Role-Centric UI

The UI does not organize by worker role. There is no "PM View" or "Architect View."

**Why:**
- The user cares about the document, not who made it
- Role-based views create multiple paths to the same document
- Collective ownership means anyone can view anything

### 4.4 Workers as Anonymous Labor

The system uses AI workers (LLMs) to generate documents. These workers are invisible to the user.

The user sees:
- A "Generate" button
- A "Regenerate" button
- The resulting document

The user does not see:
- Which model was used
- What prompts were sent
- How long generation took
- Cost attribution (in the document view)

Workers exist. They do work. The user does not manage them.

### 4.5 Documents are the Product

Everything in the system serves document production:

- Projects exist to group documents
- Workers exist to generate documents
- Dependencies exist to order document generation
- Acceptance exists to validate documents

The document is what the user came for. The document is what gets exported. The document is what has value.

---

## 5. User Intent & Philosophy

### 5.1 UI-DRY: One Path to Each Action

The system avoids multiple navigation paths to the same action.

**Principle:** If the user can do X from location A, they should not also be able to do X from location B.

**Application:**
- Documents are listed in exactly one place (the document list)
- Generate actions appear in exactly one place (the document detail panel)
- Acceptance actions appear in exactly one place (the document detail panel)

**Why:**
- Multiple paths create confusion about which is authoritative
- Multiple paths create maintenance burden
- Multiple paths suggest the paths might behave differently

### 5.2 Manual Control is First-Class

The system never auto-generates documents. The system never auto-accepts documents. The system never auto-advances workflows.

Every state change requires user action.

**Why:**
- The user is accountable for project outcomes
- Automation without consent erodes trust
- Manual control enables experimentation and recovery

The user may choose to automate via external tooling. The UI does not.

### 5.3 Informing Without Directing

The system tells the user:
- What is ready (safe to use)
- What is stale (may need review)
- What is blocked (cannot proceed)
- What is waiting (can be generated)
- What needs acceptance (awaiting approval)

The system does not tell the user:
- What to do next
- Which document is most important
- Whether a stale document should be regenerated
- Whether a rejected document should be revised

**Why:**
- The user has context the system lacks
- Different projects have different priorities
- Prescriptive UX assumes uniform workflows

### 5.4 Alignment with Agile and Collective Ownership

The system supports agile practices:

- **Collective ownership:** No role-based permissions. Anyone can view and act on any document.
- **Working software over documentation:** Documents are working artifacts, not bureaucratic overhead.
- **Responding to change:** Staleness tracking makes change visible without blocking progress.
- **Trust:** The system trusts users to make decisions. It provides information, not guardrails.

---

## 6. Visual & Mental Model

### 6.1 The Canonical Project View

When a user selects a project, they see:

```
┌─────────────────┬─────────────────┬────────────────────────────┐
│ PROJECTS        │ iPhone Auto...  │ iPhone Autocorrect         │
│                 │                 │                            │
│ ☆ Demo Project  │ DOCUMENTS       │ DOCUMENTS                  │
│ □ iPhone Auto.. │ ◉ Project Disc. │ ◉ Project Discovery    ✓   │
│ ⬡ MathTest     │   Epic Backlog  │ ◐ Epic Backlog         ○   │
│ ⚡ WarmPulse    │   Tech Arch     │   Will need acceptance     │
│                 │                 │ ◐ Technical Arch       ○   │
│                 │                 │   Will need acceptance     │
│                 │                 │                            │
│ + New Project   │                 │ [Refresh status]           │
│                 │                 │                            │
│   Legend        │                 │                            │
└─────────────────┴─────────────────┴────────────────────────────┘
```

**Left sidebar:** Project list. Flat. Alphabetical. The active project is highlighted.

**Center panel:** Document list. This is the canonical list. It persists when viewing documents.

**Right panel:** Project overview (when no document selected) or document detail (when document selected).

### 6.2 What Users Infer at a Glance

Looking at the document list, a user can immediately answer:

1. **What exists?** — Documents without "waiting" status exist
2. **What's safe?** — Green checkmarks indicate ready documents
3. **What needs attention?** — Amber warnings indicate stale documents
4. **What's blocked?** — Red indicators show blocked documents
5. **What can I do now?** — "Waiting" documents can be generated
6. **What needs approval?** — Yellow dots indicate pending acceptance

The user does not need to click into each document to understand project status.

### 6.3 Document Detail View

When a document is selected:

```
┌─────────────────┬─────────────────┬────────────────────────────┐
│ PROJECTS        │ iPhone Auto...  │ Projects > iPhone > Proj.. │
│                 │                 │                            │
│ ☆ Demo Project  │ DOCUMENTS       │ ◉ Project Discovery        │
│ □ iPhone Auto.. │ ◉ Project Disc. │                            │
│ ⬡ MathTest     │   Epic Backlog  │ [Document Content]         │
│ ⚡ WarmPulse    │   Tech Arch     │                            │
│                 │                 │ ...                        │
│                 │                 │                            │
│                 │                 │ [Regenerate]               │
│ + New Project   │                 │                            │
│                 │                 │ < Back to iPhone Auto...   │
│   Legend        │                 │                            │
└─────────────────┴─────────────────┴────────────────────────────┘
```

The document list remains visible. The user can switch documents without returning to the project overview.

---

## 7. Explicit Non-Goals

The following are intentionally excluded from the system:

### 7.1 No Workflows

The system does not define or enforce workflows. There is no "PM phase" followed by "Architecture phase." Documents have dependencies, but dependencies are not stages.

**Why:** Workflows assume a fixed process. Projects vary. Dependencies are sufficient.

### 7.2 No Agent-Driven Next Steps

The system does not recommend what to do next. There is no "suggested actions" panel. There is no AI deciding priorities.

**Why:** The user has context. The system has data. Recommendations conflate the two.

### 7.3 No Multiple Document Trees

There is exactly one document list per project. There is no "by role" view, "by status" view, or "by dependency" view.

**Why:** Multiple views create multiple truths. One list is the list.

### 7.4 No Role-Driven UI

The interface does not change based on user role. There are no "PM screens" vs "Developer screens."

**Why:** Collective ownership. Everyone sees everything. Roles are organizational, not technical.

### 7.5 No Version History in UI

The user sees the current document. There is no "view previous versions" feature in the standard UI.

**Why:** The current document is what matters. History is an audit concern, not a workflow concern.

### 7.6 No Folder Organization

Documents are not placed in folders. Projects are not placed in folders.

**Why:** Folders are a filesystem metaphor. Documents are typed records. Types provide structure.

### 7.7 No Automated Generation

The system does not auto-generate documents on any trigger. Generation requires a button click.

**Why:** Manual control. Accountability. Cost awareness.

---

## 8. Open Questions

The following aspects are not fully specified in current documentation:

1. **Acceptance and downstream gating:** Should a document that requires an unaccepted document be blocked, or merely warned?

2. **Staleness depth:** Should the UI indicate how stale a document is (e.g., "stale by 1 generation" vs "stale by 3 generations")?

3. **Rejection workflow:** When a document is rejected, what happens? Is there a "revision requested" state distinct from "rejected"?

4. **Bulk operations:** Can the user regenerate multiple stale documents at once? Current answer appears to be: No.

5. **Cost visibility:** Where, if anywhere, does the user see generation costs? Current answer: Not in the document view.

---

## 9. Summary

The Combine is a document-centric system. Its design follows from one premise: **documents are the product**.

- Projects are dossiers of documents
- The document list is the single source of truth
- Status indicators inform without directing
- Manual control is non-negotiable
- Workers are invisible
- The UI has one path to each action

The system trusts users to make decisions. It provides the information they need to make those decisions well.

---

*End of document.*
