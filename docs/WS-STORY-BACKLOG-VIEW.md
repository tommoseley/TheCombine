# WS-STORY-BACKLOG-VIEW

| Field | Value |
|---|---|
| **Work Statement** | WS-STORY-BACKLOG-VIEW |
| **Status** | Draft |
| **Owner** | Document Viewer |
| **Related ADRs** | ADR-033 (Render/Fragments), ADR-034 (DocDef/Components), WS-DOCUMENT-VIEWER-TABS |
| **Type** | Schema + Component + Fragment + DocDef |
| **Expected Scope** | Single-commit |

---

## Purpose

Implement **StoryBacklogView** as a page of Epic Cards with nested Story Summaries, following the principle that "the viewer is not a layout engine."

This WS introduces a single composite block (`EpicStoriesCardBlockV1`) that renders an epic card with its stories nested inside, avoiding the need for grouping/interleaving rules.

---

## Non-Negotiable Constraints

- ❌ No detail-level fields in story items (AC, dependencies, notes belong in StoryDetailView)
- ❌ No rigid story ID regex enforcement
- ❌ No single mega-LLM call requirement (generation is separate from view)
- ❌ No new render shapes or layout engine semantics
- ✅ Summary ≠ mini-detail (story items are StorySummary-level only)
- ✅ Reuse existing components for overview sections
- ✅ View renders whatever exists (empty epics = card without stories)

---

## In Scope

1. **New Schema: `schema:EpicStoriesCardBlockV1`**
   - Epic card fields: epic_id, name, intent, phase, risk_level, detail_ref, stories[]
   - Story item fields: story_id, title, intent, phase, detail_ref, risk_level (optional)
   - Explicitly excludes: acceptance_criteria, related_arch_components, notes

2. **New Component: `component:EpicStoriesCardBlockV1:1.0.0`**
   - Binds schema to fragment
   - View projection, not canonical storage

3. **New Fragment: `fragment:EpicStoriesCardBlockV1:web:1.0.0`**
   - Renders epic card header (name, intent, phase badge, risk badge)
   - Iterates `block.data.stories` for nested story list
   - Omits stories section entirely if empty array

4. **DocDef: `docdef:StoryBacklogView:1.0.0`**
   - Overview tab: epic_set_summary, key_constraints, risks_overview, recommendations
   - Details tab: epic story cards via repeat_over /epics

---

## Out of Scope

- LLM prompt changes for story generation (separate WS)
- StoryDetailView implementation
- Generation orchestration UI ("Generate Stories" buttons)
- Per-epic generation strategy (handled by orchestration layer)

---

## Design

### Schema: EpicStoriesCardBlockV1

```json
{
  "$id": "schema:EpicStoriesCardBlockV1",
  "type": "object",
  "required": ["epic_id", "name", "stories"],
  "properties": {
    "epic_id": { "type": "string", "minLength": 1 },
    "name": { "type": "string", "minLength": 1 },
    "intent": { "type": "string" },
    "phase": { "type": "string", "enum": ["mvp", "later"] },
    "risk_level": { "type": "string", "enum": ["low", "medium", "high"] },
    "detail_ref": { "$ref": "#/$defs/DocumentRefV1" },
    "stories": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["story_id", "title", "intent", "phase", "detail_ref"],
        "properties": {
          "story_id": { "type": "string", "minLength": 1 },
          "title": { "type": "string", "minLength": 1 },
          "intent": { "type": "string", "minLength": 1 },
          "phase": { "type": "string", "enum": ["mvp", "later"] },
          "risk_level": { "type": "string", "enum": ["low", "medium", "high"] },
          "detail_ref": { "$ref": "#/$defs/DocumentRefV1" }
        }
      }
    }
  },
  "$defs": {
    "DocumentRefV1": {
      "type": "object",
      "required": ["document_type"],
      "properties": {
        "document_type": { "type": "string" },
        "params": { "type": "object" }
      }
    }
  }
}
```

### DocDef Sections

| Order | Section ID | Component | Source | Tab |
|-------|------------|-----------|--------|-----|
| 10 | epic_set_summary | SummaryBlockV1 | /epic_set_summary | overview |
| 20 | key_constraints | StringListBlockV1 | /epic_set_summary/key_constraints | overview |
| 30 | out_of_scope | StringListBlockV1 | /epic_set_summary/out_of_scope | overview |
| 40 | risks_overview | RisksBlockV1 | /risks_overview | overview |
| 50 | recommendations | StringListBlockV1 | /recommendations_for_architecture | overview |
| 100 | epic_stories | EpicStoriesCardBlockV1 | repeat_over: /epics | details |

### Fragment Visual Structure

```
┌─────────────────────────────────────────────────────────────┐
│ [Epic Name]                              [MVP] [Risk Badge] │
│ Intent text here...                           [View Epic →] │
│                                                             │
│ Stories (3)                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ DEMO-001: Story Title                     [MVP] [View →]│ │
│ │ Brief intent...                                         │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ DEMO-002: Another Story                   [MVP] [View →]│ │
│ │ Brief intent...                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Test Plan

### Automated Tests

| Test | Assertion |
|------|-----------|
| test_epic_card_renders_with_stories | Card shows epic header + story list |
| test_epic_card_empty_stories_omits_section | No stories section when array empty |
| test_story_items_summary_level_only | No AC, no components in story items |
| test_story_backlog_view_has_overview_tab | Overview sections render |
| test_story_backlog_view_has_details_tab | Epic cards render in details |
| test_phase_badge_renders_correctly | MVP = blue, later = gray |
| test_risk_badge_renders_correctly | Color-coded by level |

### Manual Verification

1. Navigate to Story Backlog for a project with epics
2. Verify Overview tab shows: summary, constraints, risks, recommendations
3. Verify Details tab shows epic cards
4. Verify epic with stories shows nested story list
5. Verify epic without stories shows card only (no empty section)
6. Verify "View →" links are present (non-functional until detail views wired)

---

## Acceptance Criteria

1. ✅ Schema `EpicStoriesCardBlockV1` created with summary-level story items only
2. ✅ Component binds schema to fragment
3. ✅ Fragment renders epic card with nested stories iteration
4. ✅ Empty stories array omits stories section (not "No stories" message)
5. ✅ DocDef has overview sections reusing existing components
6. ✅ DocDef has details section with epic cards via repeat_over
7. ✅ No detail-level fields (AC, components) in story items
8. ✅ Story ID validation is non-empty string only (no rigid regex)

---

## Failure Conditions (Automatic Reject)

- Story items include acceptance_criteria or related_arch_components
- Rigid story ID regex enforced in schema
- New render shape introduced
- Layout engine semantics added
- Generation strategy coupled to view

---

## Deliverables

1. `schema:EpicStoriesCardBlockV1` in seed_schema_artifacts.py
2. `component:EpicStoriesCardBlockV1:1.0.0` in seed_component_artifacts.py
3. `fragment:EpicStoriesCardBlockV1:web:1.0.0` in seed_fragment_artifacts.py
4. `docdef:StoryBacklogView:1.0.0` in seed_component_artifacts.py
5. This WS document in docs/

---

## Notes

- Generation strategy (per-epic vs batch) is an orchestration concern, not a view concern
- View renders whatever stories exist; mixed state (some epics generated, some not) is valid
- detail_ref links are placeholders until StoryDetailView is implemented
- This composite block is a UX primitive, not a new architectural pattern
