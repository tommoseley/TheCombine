# Runbook: Adding a New Document Type

This runbook describes how to prepare and configure a new document type in The Combine's Production Line.

---

## Overview

A document type requires several components to function:

| Component | Required | Purpose |
|-----------|----------|---------|
| Role Prompt | Yes* | Defines the AI persona (architect, PM, BA, etc.) |
| Task Prompt | Yes* | Specific instructions for generating this document |
| Output Schema | Yes | Expected JSON structure of the output |
| QA Prompt | Recommended | Validates the generated document |
| PGC Context | Conditional | Constraint context for downstream propagation |
| Question Prompt | Optional | For documents that require clarification questions |

*Required for LLM-Generated documents only. Constructed documents do not need prompts.

---

## Prompt Architecture

The Production Line assembles prompts from modular components stored in `seed/prompts/`. Understanding each component's role is essential for consistent document generation.

### Prompt Types

| Type | Location | Purpose | When Created |
|------|----------|---------|--------------|
| **Role Prompt** | `seed/prompts/roles/` | Defines the AI persona, expertise, and behavioral constraints | Reuse existing; create only if no role fits |
| **Task Prompt** | `seed/prompts/tasks/` | Specific instructions for producing one document type | One per LLM-generated document type |
| **QA Prompt** | `seed/prompts/tasks/` | Validation instructions for the QA station | One per document type needing validation |
| **PGC Context** | `seed/prompts/pgc-contexts/` | Constraint context injected for downstream propagation | Required for Descriptive/Prescriptive docs |
| **Template** | `seed/prompts/templates/` | Assembly pattern combining role + task + schema | Rarely changed; defines prompt structure |

### How Prompts Are Assembled

The **Template** defines how components are combined into a final prompt:

```
$$ROLE_PROMPT      ← Injected from seed/prompts/roles/
---
$$TASK_PROMPT      ← Injected from seed/prompts/tasks/
---
## Output Schema
$$OUTPUT_SCHEMA    ← Injected from seed/schemas/
```

For documents requiring PGC, additional context is prepended or injected per the PGC rules.

### Role Prompts

**Location:** `seed/prompts/roles/{Role Name} {Version}.txt`

Role prompts define:
- The AI persona (Technical Architect, Project Manager, etc.)
- Domain expertise and perspective
- Behavioral constraints (what the role does NOT do)
- Quality standards for the role

**Existing roles:**
| Role | Use For |
|------|---------|
| `Technical Architect 1.0` | Architecture, discovery, technical decisions |
| `Project Manager 1.0` | Planning, backlog management, coordination |
| `Business Analyst 1.0` | Requirements, stories, feature decomposition |
| `Developer 1.0` | Implementation, code-level documents |
| `Quality Assurance 1.0` | Validation, QA prompts |

**Rule:** Only create a new role if existing roles cannot cover the required perspective. Roles are personas, not document types.

### Task Prompts

**Location:** `seed/prompts/tasks/{Document Name} v{Version}.txt`

Task prompts define:
- The specific document to produce
- Required inputs and their format
- Output structure requirements
- Constraints specific to this document type
- What NOT to include

**Naming convention:**
- Generation tasks: `{Document Name} v{Version}.txt`
- QA tasks: `{Document Name} QA v{Version}.txt`
- Question tasks: `{Document Name} Questions v{Version}.txt`

### PGC Contexts

**Location:** `seed/prompts/pgc-contexts/{document_type}.v{version}.txt`

PGC (Prompt Generation Component) contexts provide:
- Constraint summaries from upstream documents
- Domain-specific rules that must be honored
- Boundaries that cannot be crossed

**When required:** See PGC Requirements section below.

### Templates

**Location:** `seed/prompts/templates/{Template Name} v{Version}.txt`

Templates define the assembly structure. The canonical template is:

```
# Document Generator - Canonical Template v1.0

$$ROLE_PROMPT

---

$$TASK_PROMPT

---

## Output Schema

Your output must conform to the schema below.

$$OUTPUT_SCHEMA
```

**Rule:** Templates are rarely modified. Changes affect all document generation.

---

## Document Authority Levels

Before designing a new document type, determine its **authority level**. This classification governs PGC requirements, QA strictness, and UI treatment.

| Level | Purpose | PGC | QA Strictness | Examples |
|-------|---------|-----|---------------|----------|
| **Descriptive** | Explains intent, surfaces unknowns | Mandatory | Standard | Project Discovery |
| **Prescriptive** | Constrains downstream work | Mandatory | Strict | Primary Implementation Plan |
| **Constructive** | Creates first-class workpieces | Conditional | Strict | Implementation Plan, Epic |
| **Elaborative** | Refines details within constraints | Never | Light | Feature, Story |

**Key principle:** Documents at Descriptive and Prescriptive levels propagate constraints. If your document's content limits what downstream documents can say or do, it requires PGC.

---

## Step 1: Determine Document Characteristics

### 1.1 Creation Mode

| Mode | Description | Example | Prompts Needed |
|------|-------------|---------|----------------|
| **LLM-Generated** | Document content is synthesized by an LLM | Project Discovery, Technical Architecture | Role + Task + Schema |
| **Constructed** | First-class document created via governed handler logic | Epic (created by Implementation Plan) | Schema only |
| **Extracted** | Read-only view or slice derived from parent | (future: Epic Summary View) | None |
| **User-Created** | Document created manually by users | (not covered here) | Schema only |

**Critical distinction:**
- **Constructed** documents are first-class artifacts with independent lifecycles. They are *authorized creations*, not passive derivations. Epics are Constructed.
- **Extracted** documents are projections or views. They have no independent lifecycle and can be regenerated from their source.

### 1.2 Production Mode

Each workflow step has a **production mode** that determines how the document is produced:

| Mode | Meaning | Audit Language | Example |
|------|---------|----------------|---------|
| `generate` | LLM synthesizes content | "The system wrote this" | Project Discovery |
| `authorize` | System validates and commits | "The system approved this" | Implementation Plan acceptance |
| `construct` | Handler creates child documents | "The system instantiated this" | Epic creation from IP |

This distinction is required for:
- Accurate audit trails
- Appropriate UI affordances
- Correct error handling

### 1.3 Workflow Position

Identify:
- **Required inputs**: What documents must exist before this one can be built?
- **Who uses it**: What documents depend on this one?
- **Scope**: Is it project-level, epic-level, or feature-level?
- **Authority level**: Does it constrain downstream production?

### 1.4 PGC Requirements

**PGC is mandatory for documents whose outputs constrain downstream production.**

This is not about complexity. It's about constraint propagation risk.

| Document Type | PGC Required | Rationale |
|---------------|--------------|-----------|
| Project Discovery | **Mandatory** | Surfaces constraints that shape all downstream work |
| Primary Implementation Plan | **Mandatory** | Defines epic candidates that inform architecture |
| Technical Architecture | **Mandatory** | Constrains implementation approaches |
| Implementation Plan | Conditional | Required if deviating from PIP constraints |
| Epic | Conditional | Required if scope exceeds threshold or violates PIP |
| Feature | Never | Elaborates within established constraints |
| Story | Never | Elaborates within established constraints |

**Rule:** If you're unsure whether PGC is needed, it is. Skipping PGC "because the doc felt simple" causes downstream drift.

---

## Special Document Classes

### Gating Documents (Descriptive/Prescriptive)

Documents like **Project Discovery** and **Primary Implementation Plan** are gating documents:

- Always LLM-Generated
- Always PGC-gated
- Never create child documents directly
- Must stabilize before downstream steps unlock
- Outputs constrain all subsequent production

### Implementation Plan (Constructive)

The **Implementation Plan** has special characteristics:

- Creation mode: `authorize` (validates and commits the plan)
- Does not require PGC if PIP is stabilized and constraints are honored
- Owns Epic construction authority via `get_child_documents()`
- Remains in "Assembling" state until all Epics are constructed

### Epics (Constructive)

**Epics are constructed documents**, not extractions:

- Created only by Implementation Plan handler
- First-class documents with independent lifecycle (`draft` → `ready` → `in_progress` → `blocked` → `complete`)
- May require PGC if:
  - Scope exceeds defined threshold
  - Content would violate PIP constraints
- Have their own gating rules and design status tracking

---

## Step 2: Create Seed Files

> **Reference:** See [Prompt Architecture](#prompt-architecture) above for conceptual overview of each prompt type.

This section covers the practical steps to create each seed file.

### 2.1 Role Prompt (if new role needed)

**Location:** `seed/prompts/roles/{Role Name} {Version}.txt`

**Example:** `seed/prompts/roles/Technical Architect 1.0.txt`

Only create a new role if an existing role doesn't fit. Existing roles:
- `Technical Architect 1.0` - For architecture and discovery documents
- `Project Manager 1.0` - For planning and backlog documents
- `Business Analyst 1.0` - For requirements and story documents
- `Developer 1.0` - For implementation documents
- `Quality Assurance 1.0` - For QA and validation

### 2.2 Task Prompt (required for LLM-generated)

**Location:** `seed/prompts/tasks/{Document Name} v{Version}.txt`

**Example:** `seed/prompts/tasks/Project Discovery v1.4.txt`

**Contents should include:**
```
# Task: {Document Name}

## Purpose
{What this document is for}

## Inputs
{What context/documents you will receive}

## Output Requirements
{What sections/content must be produced}

## Constraints
{Rules and limitations}

## Output Format
{JSON structure expectations - reference the schema}
```

### 2.3 Output Schema (required)

**Location:** `seed/schemas/{document_type}.v{version}.json`

**Example:** `seed/schemas/project_discovery.v1.json`

This is a JSON Schema that defines the expected output structure.

### 2.4 QA Prompt (recommended)

**Location:** `seed/prompts/tasks/{Document Name} QA v{Version}.txt`

**Example:** `seed/prompts/tasks/Project Discovery QA v1.1.txt`

Used by the QA station to validate the generated document.

**QA strictness by authority level:**
- Descriptive/Prescriptive: Strict validation, constraint checking
- Constructive: Strict validation, lifecycle consistency
- Elaborative: Light validation, format compliance

### 2.5 PGC Context (conditional)

**Location:** `seed/prompts/pgc-contexts/{document_type}.v{version}.txt`

**Example:** `seed/prompts/pgc-contexts/project_discovery.v1.txt`

Required for Descriptive and Prescriptive documents. See PGC Requirements above.

### 2.6 Template (rarely needed)

**Location:** `seed/prompts/templates/{Template Name} v{Version}.txt`

**Example:** `seed/prompts/templates/Document Generator v1.0.txt`

Templates define how prompt components are assembled. The canonical template combines:
- `$$ROLE_PROMPT` - The role prompt content
- `$$TASK_PROMPT` - The task prompt content
- `$$OUTPUT_SCHEMA` - The JSON schema

**Rule:** Use the existing `Document Generator v1.0.txt` template unless you have a specific reason for a different assembly pattern. Template changes affect all documents using that template.

---

## Step 3: Register Document Type

### 3.1 Add to Document Types Registry

**File:** `seed/registry/document_types.py`

Add entry to `INITIAL_DOCUMENT_TYPES`:

```python
{
    "doc_type_id": "your_document_type",
    "name": "Your Document Type",
    "view_docdef": "YourDocumentTypeView",
    "description": "What this document is for",
    "category": "planning",  # planning, architecture, implementation, intake
    "icon": "file-text",     # Lucide icon name
    "builder_role": "architect",  # Role name (lowercase), or None for constructed docs
    "builder_task": "your_task_name",  # Task identifier, or None for constructed docs
    "handler_id": "your_document_type",
    "required_inputs": ["dependency_doc_type"],
    "optional_inputs": [],
    "gating_rules": {},
    "scope": "project",  # project, epic, feature
    "display_order": 25,
    "schema_definition": {
        "$ref": "schema:YourDocumentSchemaV1"
    },
    "schema_version": "1.0",
},
```

**For Constructed documents** (created by a parent handler's `get_child_documents()`):
- Set `builder_role` and `builder_task` to `None`
- Add `parent_doc_type` to indicate which document creates this one
- Optionally add `creates_children` if this document also creates child documents
- Add `gating_rules` for lifecycle states if applicable

**Example (Epic):**
```python
{
    "doc_type_id": "epic",
    "name": "Epic",
    "builder_role": None,  # Constructed, not LLM-generated
    "builder_task": None,
    "parent_doc_type": "implementation_plan",
    "creates_children": ["feature"],
    "gating_rules": {
        "lifecycle_states": ["draft", "ready", "in_progress", "blocked", "complete"],
        "design_status": ["not_needed", "recommended", "required", "complete"],
    },
    # ...
}
```

### 3.2 Create Handler

**File:** `app/domain/handlers/{document_type}_handler.py`

```python
from typing import Dict, Any, List
from app.domain.handlers.base_handler import BaseDocumentHandler

class YourDocumentHandler(BaseDocumentHandler):
    @property
    def doc_type_id(self) -> str:
        return "your_document_type"

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Add computed fields if needed
        return data

    def render(self, data: Dict[str, Any]) -> str:
        return f"Your Document: {data.get('title', 'Untitled')}"

    def render_summary(self, data: Dict[str, Any]) -> str:
        return data.get('title', 'Untitled')
```

**For Constructive documents** that create children, implement `get_child_documents()`:

```python
def get_child_documents(
    self,
    data: Dict[str, Any],
    parent_title: str
) -> List[Dict[str, Any]]:
    """Extract child documents to create when this document is created."""
    children = []
    for item in data.get("items", []):
        children.append({
            "doc_type_id": "child_type",
            "title": item.get("name"),
            "content": {
                # Child document content
            },
            "identifier": item.get("id"),
        })
    return children
```

### 3.3 Register Handler

**File:** `app/domain/handlers/registry.py`

```python
from app.domain.handlers.your_document_handler import YourDocumentHandler

HANDLERS: Dict[str, BaseDocumentHandler] = {
    # ... existing handlers ...
    "your_document_type": YourDocumentHandler(),
}
```

---

## Step 4: Add to Workflow Definition

**File:** `seed/workflows/software_product_development.v1.json`

### 4.1 Add Document Type Definition

```json
"document_types": {
    "your_document_type": {
        "name": "Your Document Type",
        "scope": "project",
        "may_own": [],
        "acceptance_required": false
    }
}
```

### 4.2 Add Workflow Step

Include the **production_mode** to specify how the document is produced:

```json
"steps": [
    {
        "step_id": "your_step",
        "role": "Technical Architect 1.0",
        "task_prompt": "Your Document v1.0",
        "produces": "your_document_type",
        "production_mode": "generate",
        "scope": "project",
        "inputs": [
            { "doc_type": "required_input", "scope": "project" }
        ]
    }
]
```

**Production mode values:**

| Mode | Use When |
|------|----------|
| `generate` | LLM synthesizes the document content |
| `authorize` | System validates and commits (e.g., plan acceptance) |
| `construct` | Handler creates child documents from parent content |

**Examples from current workflow:**

```json
// Project Discovery - LLM generates content
{ "step_id": "discovery", "production_mode": "generate", ... }

// Implementation Plan - authorizes the plan, constructs Epics
{ "step_id": "implementation_plan", "production_mode": "authorize", "creates_entities": "epic", ... }
```

---

## Step 5: Create View DocDef (for rendering)

**File:** `seed/registry/component_artifacts.py`

```python
YOUR_DOCUMENT_VIEW_DOCDEF = {
    "document_def_id": "docdef:YourDocumentView:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "You are producing a Your Document.",
        "constraints": ["..."]
    },
    "sections": [
        {
            "section_id": "summary",
            "title": "Summary",
            "order": 10,
            "component_id": "component:SummaryBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/summary",
            "viewer_tab": "overview",
        },
        # Add more sections...
    ],
    "status": "accepted"
}
```

Add to `INITIAL_DOCUMENT_DEFINITIONS` list at the bottom of the file.

---

## Step 6: Seed Database

Run the seeding scripts to populate the database:

```bash
# Seed document types
python -m seed.registry.document_types

# Seed document definitions (docdefs)
python -c "
import asyncio
from seed.registry.component_artifacts import seed_document_definitions
from app.core.database import async_session_factory

async def main():
    async with async_session_factory() as db:
        await seed_document_definitions(db)
        await db.commit()

asyncio.run(main())
"
```

**Note:** Role and task prompts in `seed/prompts/` are loaded at runtime from the filesystem, not seeded to the database. The prompt files just need to exist at the correct paths.

---

## Decision Tree: What Do I Need?

```
What is the document's creation mode?
│
├── LLM-Generated
│   ├── Determine authority level (Descriptive/Prescriptive/Constructive/Elaborative)
│   ├── Does an appropriate Role exist?
│   │   ├── YES → Use existing role
│   │   └── NO → Create new Role Prompt
│   ├── Create Task Prompt (required)
│   ├── Create Output Schema (required)
│   ├── Is authority level Descriptive or Prescriptive?
│   │   ├── YES → Create PGC Context (mandatory)
│   │   └── NO → PGC optional (Constructive) or skip (Elaborative)
│   ├── Does it need validation?
│   │   ├── YES → Create QA Prompt (strictness per authority level)
│   │   └── NO → Skip
│   └── Set production_mode: "generate"
│
├── Constructed (authorized creation with independent lifecycle)
│   ├── Create Handler with get_child_documents() in parent
│   ├── Create Output Schema (required)
│   ├── Define gating_rules for lifecycle states
│   ├── Set builder_role and builder_task to None
│   ├── Set parent_doc_type
│   ├── No prompts needed (content comes from parent)
│   └── Set production_mode: "construct" (on parent step)
│
└── Extracted (read-only view/slice)
    ├── No independent document type needed
    ├── Implement as a view/projection in handler
    └── No prompts, no lifecycle, no gating
```

---

## File Naming Conventions

| Type | Location | Pattern | Example |
|------|----------|---------|---------|
| Role Prompt | `seed/prompts/roles/` | `{Role Name} {Major}.{Minor}.txt` | `Technical Architect 1.0.txt` |
| Task Prompt | `seed/prompts/tasks/` | `{Document Name} v{Major}.{Minor}.txt` | `Project Discovery v1.4.txt` |
| QA Prompt | `seed/prompts/tasks/` | `{Document Name} QA v{Major}.{Minor}.txt` | `Project Discovery QA v1.1.txt` |
| Question Prompt | `seed/prompts/tasks/` | `{Document Name} Questions v{Major}.{Minor}.txt` | `Project Discovery Questions v1.0.txt` |
| PGC Context | `seed/prompts/pgc-contexts/` | `{document_type}.v{version}.txt` | `project_discovery.v1.txt` |
| Template | `seed/prompts/templates/` | `{Template Name} v{Major}.{Minor}.txt` | `Document Generator v1.0.txt` |
| Schema | `seed/schemas/` | `{document_type}.v{version}.json` | `project_discovery.v1.json` |

---

## Checklist

### All Document Types
- [ ] Determined creation mode (LLM-Generated / Constructed / Extracted)
- [ ] Determined authority level (Descriptive / Prescriptive / Constructive / Elaborative)
- [ ] Identified required inputs and dependents
- [ ] Created Output Schema
- [ ] Added to `seed/registry/document_types.py`
- [ ] Created Handler in `app/domain/handlers/`
- [ ] Registered Handler in `registry.py`
- [ ] Added to workflow definition with correct `production_mode`
- [ ] Created View DocDef
- [ ] Seeded database

### LLM-Generated Documents Only
- [ ] Created/reused Role Prompt
- [ ] Created Task Prompt
- [ ] Created PGC Context (if Descriptive or Prescriptive)
- [ ] Created QA Prompt with appropriate strictness

### Constructed Documents Only
- [ ] Parent handler implements `get_child_documents()`
- [ ] Set `builder_role` and `builder_task` to `None`
- [ ] Set `parent_doc_type` in registry
- [ ] Defined `gating_rules` for lifecycle states
- [ ] Tested child document creation

---

## Quick Reference: Current Document Types

| Document | Authority | Creation | Production Mode | PGC |
|----------|-----------|----------|-----------------|-----|
| Project Discovery | Descriptive | LLM-Generated | generate | Mandatory |
| Primary Implementation Plan | Prescriptive | LLM-Generated | generate | Mandatory |
| Technical Architecture | Prescriptive | LLM-Generated | generate | Mandatory |
| Implementation Plan | Constructive | LLM-Generated | authorize | Conditional |
| Epic | Constructive | Constructed | construct | Conditional |
| Feature | Elaborative | LLM-Generated | generate | Never |
| Story | Elaborative | Constructed | construct | Never |

---

*Last updated: 2026-02-02*
