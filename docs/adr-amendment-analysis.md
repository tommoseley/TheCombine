# ADR & Governance Amendment Analysis

> **Governing Document**: [Document System Charter](./document-system-charter.md)
> 
> **Implementation**: [Document Cleanup Plan](./document-cleanup-plan.md)

**Purpose**: Identify amendments required to align existing governance documents with the Document System Charter v3.

---

## Summary of Required Amendments

| Document | Amendment Type | Priority | Description |
|----------|---------------|----------|-------------|
| **WS-DOCUMENT-VIEWER-TABS** | Supersede | High | Replace enum tabs with data-driven tabs |
| **DOCUMENT_VIEWER_CONTRACT** | Amend | High | Add document state rendering rules |
| **ADR-034-A** | Amend (or -C) | Medium | Add data-driven UX section fields |
| **ADR-031** | Amend | Medium | Clarify document-level schema hash persistence |
| **ADR-033** | Amend | Medium | Add `state` to RenderModelV1 |
| **ADR-INVENTORY** | Update | Low | Add ADR-030 through ADR-034 |
| **(New) ADR-036** | Create | Medium | Document Lifecycle & Staleness |

---

## Detailed Analysis

### 1. WS-DOCUMENT-VIEWER-TABS -> Superseded by D.5

**Current State**:
```json
"viewer_tab": "overview" | "details" | "both"
```
- Hardcoded enum
- Fixed two-tab model
- Default: `"details"`

**Cleanup Plan (D.5)**:
```json
"viewer_tab": {
  "id": "epics",
  "label": "Epics",
  "order": 20
}
```
- Data-driven object
- Unlimited tabs
- No predefined tab set

**Action Required**: 
- Mark WS-DOCUMENT-VIEWER-TABS as **Superseded**
- Create new governance doc: `VIEWER_TABS_CONTRACT.md` (as specified in D.5)
- Update `schema:DocumentDefinitionV2` to use object format

**Migration Path**:
```
Old: "viewer_tab": "overview"
New: "viewer_tab": { "id": "overview", "label": "Overview", "order": 10 }

Old: "viewer_tab": "details" (or absent)
New: "viewer_tab": { "id": "details", "label": "Details", "order": 20 }

Old: "viewer_tab": "both"
New: Include section in multiple tabs via duplication or special handling
```

---

### 2. DOCUMENT_VIEWER_CONTRACT -> Amendment Required

**Current State**: No mention of document lifecycle states

**Cleanup Plan (B.3, D.4)**:
- Five states: `missing`, `generating`, `partial`, `complete`, `stale`
- Each state has specific rendering behavior

**Action Required**: Add section for state-based rendering with metadata extension.

---

### 3. ADR-034-A -> Amendment Required (or ADR-034-C)

**Current State**: Section definition fields do not include UX presentation fields.

**Cleanup Plan (B.5, B.9, D.5, D.6)**: New fields required:
- `viewer_tab` (object with id, label, order)
- `display_variant` (compact, expanded, card, etc.)
- `default_collapsed` (boolean)
- `visibility_rules` (show_if_empty, min_items)

**Action Required**: Create ADR-034-C or amend ADR-034-A.

---

### 4. ADR-031 -> Clarification Amendment

**Current State**: Mentions bundle_sha256 for logging but not document persistence.

**Cleanup Plan**: Documents MUST persist schema_bundle_sha256 for viewer resolution.

**Action Required**: Add Section 2.5.1 clarifying document-level hash persistence.

---

### 5. ADR-033 -> RenderModelV1 Amendment

**Current State**: RenderModelV1 metadata contains only `section_count`

**Cleanup Plan**: Requires `state` for rendering decisions

**Action Required**: Add `state` and `state_changed_at` to metadata schema.

---

### 6. ADR-INVENTORY -> Update Required

**Current State**: Shows ADR-030+ as "available"

**Actual State**: ADR-030 through ADR-034 exist and are active

**Action Required**: Update inventory with ADR-030 through ADR-035.

---

### 7. (New) ADR-036: Document Lifecycle & Staleness

**Gap**: No ADR covers document state machine, transitions, or staleness propagation.

**Action Required**: Create new ADR-036 covering:
- Five document states
- State transition rules  
- Staleness propagation via dependency graph
- Invariants (partial documents valid, staleness downstream only)

---

## Documents Requiring NO Amendment

| Document | Reason |
|----------|--------|
| RENDER_SHAPES_SEMANTICS.md | Unchanged - shapes are separate from tabs/UX |
| SUMMARY_VIEW_CONTRACT.md | Already defines `detail_ref` - aligns with projection layer |
| FRAGMENT_STANDARDS.md | Unchanged - fragments receive variant via CSS class |
| ADR-034-B (Flatten-First) | Unchanged - orthogonal to UX concerns |

---

## Schema Changes Required

| Schema | Change |
|--------|--------|
| `schema:DocumentDefinitionV2` | Add `viewer_tab` object, `display_variant`, `default_collapsed`, `visibility_rules` |
| `schema:RenderModelV1` | Add `state`, `state_changed_at` to metadata |
| `documents` table | Add `state` enum, `state_changed_at`, `schema_bundle_sha256` |
| `document_types` table | Add `state_badges` JSONB, `view_docdef_prefix` |

---

## Recommended Amendment Order

1. **WS-DOCUMENT-VIEWER-TABS** -> Mark superseded, create VIEWER_TABS_CONTRACT.md
2. **DOCUMENT_VIEWER_CONTRACT** -> Add state rendering section
3. **ADR-034-A** -> Add data-driven UX fields (or create ADR-034-C)
4. **ADR-033** -> Add state to RenderModelV1 metadata
5. **ADR-031** -> Add document-level hash persistence clause
6. **(New) ADR-036** -> Document Lifecycle & Staleness
7. **ADR-INVENTORY** -> Update with ADR-030-035

---

## Summary

The cleanup plan introduces several concepts not yet covered by existing governance:

1. **Data-driven tabs** (supersedes WS-DOCUMENT-VIEWER-TABS)
2. **Document lifecycle states** (requires new ADR-036)
3. **Schema hash persistence in documents** (requires ADR-031 amendment)
4. **Data-driven UX fields** (requires ADR-034 amendment)
5. **State in RenderModel** (requires ADR-033 amendment)

Most amendments are additive and backward-compatible. The only breaking change is the viewer_tab format (enum -> object), which requires migration of existing docdefs.
