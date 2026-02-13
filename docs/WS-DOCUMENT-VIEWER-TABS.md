# WS-DOCUMENT-VIEWER-TABS

| Field | Value |
|---|---|
| **Work Statement** | WS-DOCUMENT-VIEWER-TABS |
| **Status** | Draft |
| **Owner** | Document Viewer |
| **Related ADRs** | ADR-033 (Render / Fragments), ADR-034 (DocDef / Components / RenderModel), ADR-034-B (Flatten-first) |
| **Type** | UX + Contract + Minimal Engine Extension |
| **Expected Scope** | Single-commit (preferred) |

---

## Purpose

Introduce **tab-aware rendering** in the base Document Viewer so a single viewer can present "Overview" vs "Details" content **without creating per-document views**, while preserving all frozen RenderModel semantics and "omit if empty" behavior.

This WS adds **only docdef-driven tab grouping** and **tab suppression** rules.

---

## Non-Negotiable Constraints

- ❌ No new block shapes
- ❌ No new docdef semantics besides *tab designation*
- ❌ No PromptAssembler changes
- ❌ No RenderModelBuilder behavior changes (other than *including section metadata if already in contract*)
- ❌ No fragment behavior changes required
- ✅ Use existing schemas/components/fragments
- ✅ Tabs are purely a **viewer concern** driven by docdef section metadata

---

## In Scope

1. **DocDef extension (minimal)**
   - Add optional `viewer_tab` to `DocumentDefinitionV2.sections[]`:
     - Allowed values: `"overview" | "details" | "both"`
     - Default behavior when absent: `"details"`

2. **Document Viewer behavior**
   - Group rendered sections into tabs based on `viewer_tab`
   - Suppress any tab with zero rendered blocks
   - If only one tab remains, render without tabs (no tab chrome)

3. **Golden-trace fixtures + tests**
   - Confirm:
     - correct grouping
     - suppression
     - single-tab collapse
     - "both" behavior
     - stable ordering

4. **Governance**
   - Add/extend a frozen governance doc describing:
     - allowed values
     - defaults
     - suppression rules
     - single-tab collapse
     - ordering rules

---

## Out of Scope

- New render shapes, new derivation functions, or changes to derivation semantics
- New docdef fields beyond `viewer_tab`
- Switching Jinja2 → React (explicitly deferred)
- Client-side fragment rendering; this WS assumes current server-side fragment usage continues
- Any "Raw" JSON viewer mode

---

## Design: Frozen Tab Semantics

### 1) Tab designation (docdef-driven)

Each section MAY specify:

```json
"viewer_tab": "overview" | "details" | "both"
```

Default if omitted: `"details"`.

### 2) Tab contents

- **overview** tab shows sections tagged `overview` + `both`
- **details** tab shows sections tagged `details` + `both`

### 3) Empty tab suppression

After normal render omission rules apply (null/empty source omitted, empty containers omitted, derived omissions applied):

- If a tab has 0 blocks, it is not displayed.

### 4) Single-tab collapse

If, after suppression, only one tab remains:

- Do not show tabs; render the remaining sections inline.

### 5) Ordering

- Tab order: `overview` then `details`
- Section ordering within a tab uses existing `section.order`

---

## Required Implementation Changes

### A) Schema change (DocumentDefinitionV2)

Update `schema:DocumentDefinitionV2`:

In `sections.items.properties`, add:

```json
"viewer_tab": {
  "type": "string",
  "enum": ["overview", "details", "both"],
  "description": "Viewer-only grouping for tab rendering. Default is 'details'."
}
```

No other schema changes.

### B) Document Viewer implementation

Update base Document Viewer to:

1. Read docdef sections and their `viewer_tab`
2. Group the already-rendered section outputs accordingly
3. Apply suppression and collapse rules
4. Render tab chrome only if 2+ tabs remain

**Important:** This WS does not require changing fragment resolution or block rendering. It only changes how sections are presented.

---

## Test Plan

### Test fixtures (minimum)

Create/extend fixtures for these document types:

1. **docdef:EpicBacklogView:1.0.0**
   - Tag:
     - Header-like sections (Project Name, Epic Set Summary, Risks Overview, Recommendations) as `overview`
     - Epics list section as `details` (or `overview` if desired, but must be explicit)
   - Expected: Both tabs visible

2. **docdef:EpicDetailView:1.0.0**
   - Keep most sections as `details`
   - Optionally tag 1–2 sections as `overview` (or none)
   - Expected: If no overview blocks render → tabs suppressed → no tab chrome

3. **docdef:ArchitecturalSummaryView:1.0.0**
   - Tag all sections as `overview`
   - Expected: only overview exists → no tab chrome

4. **Synthetic "both" docdef fixture**
   - One section tagged `both`
   - Expected: section appears in both tabs (when both tabs exist)

5. **Empty tab suppression fixture**
   - A docdef where overview sections are present in docdef but omitted at render (e.g., sources empty)
   - Expected: overview tab not displayed

### Automated tests (required)

| Test | Assertion |
|------|-----------|
| `test_viewer_tab_default_is_details` | sections without `viewer_tab` behave as `details` |
| `test_viewer_groups_sections_into_tabs` | correct grouping overview/details/both |
| `test_viewer_suppresses_empty_tabs` | empty tab removed |
| `test_viewer_collapses_single_tab` | if one tab remains, no tabs rendered |
| `test_viewer_section_order_preserved` | tab content respects `section.order` |
| `test_both_sections_appear_in_both_tabs` | "both" displayed twice, same block data |

Golden trace tests must include:
- EpicBacklogView (to prevent regression of the "missing header" issue)
- ArchitecturalSummaryView
- EpicDetailView

---

## Acceptance Criteria

1. `schema:DocumentDefinitionV2` updated to include `viewer_tab` with allowed values and default behavior documented.

2. Base Document Viewer renders:
   - Overview + Details tabs when both have content
   - No tabs when only one remains
   - No empty tabs

3. Epic Backlog display includes:
   - Overview content (Project Name, Epic Set Summary, Risks Overview, Recommendations)
   - Details content (Epics list)

4. No changes to:
   - PromptAssembler
   - RenderModelBuilder block production semantics
   - fragment rendering logic

5. All tests pass (including updated golden traces).

---

## Failure Conditions (Automatic Reject)

- Any new render shape introduced
- Any docdef semantics added beyond `viewer_tab`
- Any PromptAssembler or RenderModelBuilder behavioral change unrelated to tab display
- Any HTML included in JSON payloads
- Tabs shown with no content, or a single tab shown alone (no collapse)

---

## Deliverables

1. Updated `schema:DocumentDefinitionV2` (accepted)
2. Updated Document Viewer behavior (tabs, suppression, collapse)
3. Updated docdefs with `viewer_tab` annotations for:
   - EpicBacklogView
   - ArchitecturalSummaryView
   - (Optional) EpicDetailView if you want an overview section
4. Governance doc:
   - `VIEWER_TABS.md` (frozen)
5. Tests:
   - Unit tests for tab rules
   - Golden traces for EpicBacklogView / EpicDetailView / ArchitecturalSummaryView

---

## Notes

This WS intentionally keeps the viewer implementation agnostic to Jinja2 vs React.
Once the engine proves stable and fragment rules are fully normalized, a separate WS/ADR can cover the React migration without mixing variables.
