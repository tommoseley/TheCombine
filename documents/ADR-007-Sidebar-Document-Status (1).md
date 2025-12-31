# ADR-007: Sidebar Document Status Visualization

**Status:** Proposed  
**Date:** 2025-12-18  
**Author:** Developer Mentor  
**Context:** PIPELINE-175C / UI Enhancement

---

## Executive Summary

This ADR defines the architecture for a document-centric sidebar that replaces the current mentor-centric navigation. The sidebar displays documents with derived **readiness status** and conditional **acceptance state**, enabling users to understand at a glance what's safe, what's risky, and what's missing.

**Key Principle:** The system never tells the user what to think. It only tells them what's safe, what's risky, and what's missing.

---

## Context

The current sidebar displays projects with epics underneath. As we transition to a document-centric architecture, the sidebar needs to:

1. Show documents organized by type/category
2. Display readiness status (can this document be built/used?)
3. Display acceptance state (has a human approved this?)
4. Enable/disable actions based on derived state
5. Support the "PM stays in control" philosophy

---

## Decision

### 1. Visual Hierarchy

```
📁 {Project Name}
────────────────────────────────────────────

📘 Product Discovery                ✅

📦 Epic Backlog                     ⚠️   🟡
   Needs acceptance (PM)

📐 Technical Architecture           ❌   🟡
   Needs acceptance (Architect)

🧩 Story Backlogs
   ├── Epic 1 Stories               ❌
   ├── Epic 2 Stories               ❌

📜 Applied Standards
   ├── Security Baseline v2         ⚠️   🟢
   └── Coding Standards v1          ✅   🟢
```

**Visual Conventions:**
- Left icon = document type (from `document_types.icon`)
- First status icon = readiness (derived)
- Second icon = acceptance state (shown only when `acceptance_required = true`)
- Subtitle = contextual hint when action needed

---

### 2. Status Icon System

#### Readiness Status (Always Derived)

| Icon | Status | Meaning | CSS Class |
|------|--------|---------|-----------|
| ✅ | `ready` | Exists, valid, safe to use | `text-green-500` |
| ⚠️ | `stale` | Exists, but upstream inputs changed | `text-amber-500` |
| ❌ | `blocked` | Cannot be built (missing requirements) | `text-red-500` |
| ⏳ | `waiting` | Buildable but not yet built (prerequisites met, awaiting action) | `text-gray-400` |

#### Acceptance State (Conditional)

| Icon | State | Meaning | CSS Class |
|------|-------|---------|-----------|
| 🟢 | `accepted` | Explicitly approved by responsible role | `text-green-600` |
| 🟡 | `needs_acceptance` | Acceptance required but not yet given | `text-yellow-500` |
| 🔴 | `rejected` | Reviewed, changes requested | `text-red-600` |

**Acceptance icons appear ONLY when `document_types.acceptance_required = true`.**

---

### 3. Schema Changes

#### 3.1 `document_types` Table Enhancement

```sql
ALTER TABLE document_types ADD COLUMN IF NOT EXISTS 
    acceptance_required BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE document_types ADD COLUMN IF NOT EXISTS 
    accepted_by_role VARCHAR(64);  -- Role that must accept (pm, architect, etc.)

ALTER TABLE document_types ADD COLUMN IF NOT EXISTS 
    icon VARCHAR(32);  -- Lucide icon name for sidebar display
```

**Example Data:**

| doc_type_id | acceptance_required | accepted_by_role | icon |
|-------------|---------------------|------------------|------|
| `project_discovery` | `false` | `null` | `search` |
| `epic_set` | `true` | `pm` | `layers` |
| `architecture_spec` | `true` | `architect` | `landmark` |
| `story_backlog` | `false` | `null` | `list-checks` |

#### 3.2 `documents` Table Enhancement

```sql
ALTER TABLE documents ADD COLUMN IF NOT EXISTS 
    accepted_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS 
    accepted_by VARCHAR(128);  -- User/role who accepted

ALTER TABLE documents ADD COLUMN IF NOT EXISTS 
    rejected_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS 
    rejected_by VARCHAR(128);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS 
    rejection_reason TEXT;

-- Note: is_stale already exists in current schema
```

---

### 4. Derivation Logic

#### 4.1 Acceptance State Derivation

```python
def derive_acceptance_state(document: Document, doc_type: DocumentType) -> Optional[str]:
    """
    Derive acceptance state from document and type configuration.
    Returns None if acceptance not required OR if document doesn't exist yet.
    
    Rationale: You can't accept something that doesn't exist. The "waiting" 
    readiness status already signals the document isn't built. Acceptance 
    state only becomes relevant once the document exists.
    """
    if not doc_type.acceptance_required:
        return None
    
    # Can't accept what doesn't exist - let readiness carry the signal
    if document is None:
        return None
    
    if document.rejected_at is not None:
        return "rejected"
    
    if document.accepted_at is None:
        return "needs_acceptance"
    
    return "accepted"
```

**Note:** When `document is None` and `acceptance_required = true`, the subtitle can optionally display "Will need acceptance after build ({role})" to preview the workflow, but no acceptance icon is shown.

#### 4.2 Readiness Status Derivation

```python
async def derive_readiness_status(
    db: AsyncSession,
    doc_type_id: str,
    space_type: str,
    space_id: UUID,
    document: Optional[Document]
) -> str:
    """
    Derive readiness status from document state and dependencies.
    
    Status meanings:
    - blocked: Cannot build - missing required input documents
    - waiting: CAN build - prerequisites met, just not built yet
    - stale: Built but inputs changed - rebuild recommended
    - ready: Built and current - safe to use
    
    Note: "waiting" does NOT mean "user chose to defer" - it means 
    "buildable now, user hasn't triggered build yet."
    """
    # Get document type configuration
    doc_type = await get_document_config(db, doc_type_id)
    required_inputs = doc_type.get("required_inputs", [])
    
    # Check if required inputs exist
    if required_inputs:
        existing = await document_service.get_existing_doc_types(space_type, space_id)
        missing = [dep for dep in required_inputs if dep not in existing]
        if missing:
            return "blocked"
    
    # Document doesn't exist yet BUT could be built (prerequisites met)
    if document is None:
        return "waiting"
    
    # Document exists but is stale
    if document.is_stale:
        return "stale"
    
    # Document exists and is current
    return "ready"
```

#### 4.3 Downstream Gating Logic

```python
def can_be_used_as_input(document: Document, doc_type: DocumentType) -> bool:
    """
    Determine if a document can be used as input for downstream documents.
    """
    # Blocked documents can never be used
    readiness = derive_readiness_status(...)
    if readiness == "blocked":
        return False
    
    # If acceptance required, must be accepted
    if doc_type.acceptance_required:
        acceptance = derive_acceptance_state(document, doc_type)
        return acceptance == "accepted"
    
    # No acceptance required - can be used if exists
    return True
```

**Important Nuances:** 
- `stale + accepted` → allowed with warning (human previously approved, inputs changed but decision still valid until reviewed)
- **UI Rule:** When `readiness == stale` AND `acceptance_state == accepted`, always show subtitle: "Inputs changed — review recommended". This prevents silent risk.

---

### 5. UI Button Enablement

| Action | Condition | Notes |
|--------|-----------|-------|
| **Build** | `readiness in {waiting, stale}` AND not blocked | Can build if doesn't exist or needs rebuild |
| **Rebuild** | `readiness == stale` | Explicitly rebuild stale document |
| **Accept** | `acceptance_state == needs_acceptance` | Only shown when acceptance required |
| **Request Changes** | `acceptance_state in {needs_acceptance, accepted}` | Allows rejection/feedback |
| **Build Downstream** | `can_be_used_as_input == true` | Gate downstream document building |

---

### 6. Service Layer Changes

#### 6.1 New `DocumentStatusService`

```python
# app/api/services/document_status_service.py

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

@dataclass
class DocumentStatus:
    """Complete status for a document in the sidebar."""
    doc_type_id: str
    document_id: Optional[UUID]
    title: str
    icon: str
    
    # Derived states
    readiness: str  # ready, stale, blocked, waiting
    acceptance_state: Optional[str]  # accepted, needs_acceptance, rejected, None
    
    # Context for UI
    subtitle: Optional[str]  # "Needs acceptance (PM)", "Missing: project_discovery"
    can_build: bool
    can_accept: bool
    can_use_as_input: bool
    
    # Missing dependencies (for blocked state)
    missing_inputs: List[str]


class DocumentStatusService:
    """Service for deriving document status for sidebar display."""
    
    async def get_project_document_statuses(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> List[DocumentStatus]:
        """
        Get status for all document types in a project.
        Returns ordered list for sidebar display.
        """
        ...
    
    async def get_document_status(
        self,
        db: AsyncSession,
        doc_type_id: str,
        space_type: str,
        space_id: UUID
    ) -> DocumentStatus:
        """Get status for a single document type."""
        ...
```

---

### 7. API Endpoints

#### 7.1 Get Project Document Statuses

```
GET /api/projects/{project_id}/document-statuses
```

**Response:**
```json
{
  "project_id": "734fda6f-1418-48b9-b93b-6bd58c0d4f97",
  "documents": [
    {
      "doc_type_id": "project_discovery",
      "document_id": "abc123",
      "title": "Product Discovery",
      "icon": "search",
      "readiness": "ready",
      "acceptance_state": null,
      "subtitle": null,
      "can_build": false,
      "can_accept": false,
      "can_use_as_input": true,
      "missing_inputs": []
    },
    {
      "doc_type_id": "architecture_spec",
      "document_id": null,
      "title": "Technical Architecture",
      "icon": "landmark",
      "readiness": "waiting",
      "acceptance_state": "needs_acceptance",
      "subtitle": "Needs acceptance (Architect)",
      "can_build": true,
      "can_accept": false,
      "can_use_as_input": false,
      "missing_inputs": []
    }
  ]
}
```

#### 7.2 Accept Document

```
POST /api/documents/{document_id}/accept
```

**Request:**
```json
{
  "accepted_by": "user@example.com"
}
```

**Response:**
```json
{
  "document_id": "abc123",
  "accepted_at": "2025-12-18T12:00:00Z",
  "accepted_by": "user@example.com"
}
```

#### 7.3 Reject Document

```
POST /api/documents/{document_id}/reject
```

**Request:**
```json
{
  "rejected_by": "user@example.com",
  "reason": "Missing error handling for edge cases"
}
```

---

### 8. Template Changes

#### 8.1 Sidebar Component

```html
<!-- components/sidebar/document_list.html -->

{% for doc_status in document_statuses %}
<div class="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded-lg cursor-pointer"
     hx-get="/ui/projects/{{ project.id }}/documents/{{ doc_status.doc_type_id }}"
     hx-target="#main-content"
     hx-push-url="true">
    
    <!-- Document Type Icon + Title -->
    <div class="flex items-center gap-2">
        <i data-lucide="{{ doc_status.icon }}" class="w-4 h-4 text-gray-500"></i>
        <span class="text-sm text-gray-700">{{ doc_status.title }}</span>
    </div>
    
    <!-- Status Icons -->
    <div class="flex items-center gap-1">
        <!-- Readiness Status -->
        {% if doc_status.readiness == 'ready' %}
            <span class="text-green-500" title="Ready">✅</span>
        {% elif doc_status.readiness == 'stale' %}
            <span class="text-amber-500" title="Stale - inputs changed">⚠️</span>
        {% elif doc_status.readiness == 'blocked' %}
            <span class="text-red-500" title="Blocked - missing {{ doc_status.missing_inputs | join(', ') }}">❌</span>
        {% elif doc_status.readiness == 'waiting' %}
            <span class="text-gray-400" title="Not built yet">⏳</span>
        {% endif %}
        
        <!-- Acceptance State (only if required) -->
        {% if doc_status.acceptance_state %}
            {% if doc_status.acceptance_state == 'accepted' %}
                <span class="text-green-600" title="Accepted">🟢</span>
            {% elif doc_status.acceptance_state == 'needs_acceptance' %}
                <span class="text-yellow-500" title="Needs acceptance">🟡</span>
            {% elif doc_status.acceptance_state == 'rejected' %}
                <span class="text-red-600" title="Rejected">🔴</span>
            {% endif %}
        {% endif %}
    </div>
</div>

<!-- Subtitle (if present) -->
{% if doc_status.subtitle %}
<div class="pl-9 text-xs text-gray-500 -mt-1 mb-1">
    {{ doc_status.subtitle }}
</div>
{% endif %}
{% endfor %}
```

---

### 9. Interpretation Guide (For Human Users)

| Combined State | User Interpretation |
|----------------|---------------------|
| ✅ (no acceptance shown) | "This document is fine and doesn't need sign-off." |
| ✅ + 🟢 | "Built, current, and approved — fully trusted." |
| ⚠️ + 🟢 | "Approved, but inputs changed — review recommended." (subtitle always shown) |
| ⚠️ + 🟡 | "Stale and needs approval — review before trusting." |
| ❌ (no acceptance shown) | "You can't build this yet — prerequisites missing." |
| ⏳ (no acceptance shown) | "Ready to build — prerequisites met, awaiting your action." |
| ⏳ (acceptance required) | "Ready to build — will need acceptance after build." (subtitle hint)

---

## Consequences

### Positive

1. **Derived, not stored:** Status is computed from document state, never drifts
2. **PM stays in control:** No hardcoded workflows, acceptance signals trust
3. **Self-documenting UI:** Icons immediately convey what's safe/risky/missing
4. **Extensible:** New document types automatically get status visualization
5. **Auditable:** `accepted_at`, `accepted_by` provide audit trail

### Negative

1. **Schema migration required:** Need to add columns to `documents` and `document_types`
2. **Computation on every render:** Status derived on each sidebar load (mitigated by caching)
3. **Visual density:** Multiple indicators per row requires careful spacing and accessible tooltips

### Mitigations

- Cache document statuses per project (invalidate on document change)
- **Icon rendering:** Emoji (✅⚠️❌⏳🟢🟡🔴) are ADR placeholders only. Production uses Lucide icons + CSS color classes + tooltips + accessible `aria-label` text. This aligns with the Design Constitution's "Calm Authority" principle.
- Provide tooltip explanations on hover

---

## Implementation Plan

### Phase 1: Schema & Data (1 day)
1. Add columns to `document_types` table
2. Add columns to `documents` table
3. Seed `acceptance_required` and `icon` for existing document types

### Phase 2: Service Layer (1 day)
1. Create `DocumentStatusService`
2. Implement derivation logic
3. Add unit tests for all status combinations

### Phase 3: API Endpoints (0.5 day)
1. Add `/document-statuses` endpoint
2. Add `/accept` and `/reject` endpoints
3. Add integration tests

### Phase 4: UI Templates (1 day)
1. Create sidebar document list component
2. Update project detail page to use new sidebar
3. Add button enable/disable logic based on status

### Phase 5: Testing & Polish (0.5 day)
1. End-to-end testing of all status combinations
2. Visual polish and accessibility
3. Documentation

**Total Estimate:** 4 days

---

## Alternatives Considered

### 1. Stored Status Instead of Derived

**Rejected:** Would require status synchronization logic and could drift from actual state.

### 2. Single Combined Status Icon

**Rejected:** Loses information density. Users need to see both readiness AND acceptance at a glance.

### 3. Text Labels Instead of Icons

**Rejected:** Takes more space, slower to scan. Icons with tooltips provide better UX.

---

## References

- [ADR-006: Self-Hosted, Not SaaS](/mnt/project/ARCHITECTURE-V2.md)
- [Document-Centric Architecture](/mnt/project/PIPELINE-175B-Data-Driven-Pipeline-Execution.md)
- [The Combine Design Manifesto](/mnt/project/the-combine-design-manifesto.md)

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-18  
**Status:** Proposed - Ready for Review
