# WS-STORY-BACKLOG-COMMANDS-SLICE-1

| Field | Value |
|---|---|
| **Work Statement** | WS-STORY-BACKLOG-COMMANDS-SLICE-1 |
| **Status** | Draft |
| **Owner** | Document Pipeline |
| **Related ADRs** | ADR-034 (DocDef/Components), WS-STORY-BACKLOG-VIEW |
| **Type** | Command Endpoint + Document Type |
| **Expected Scope** | Single-commit |

---

## Purpose

Implement the **StoryBacklog stored document** and **init command** so that clicking "Story Backlog" shows epic cards with zero stories, with buttons ready for generation.

This is Slice 1 of 2. Slice 2 adds LLM generation + projection.

---

## Key Decisions (Frozen)

| Decision | Value |
|----------|-------|
| StoryBacklog = navigation/orchestration doc | NOT an LLM dump |
| StoryDetail = full BA payload per story | Source of truth for story details |
| Projection happens at write time | Handler converts BA output → summary before storing in StoryBacklog |
| One LLM call = one epic | By design, avoids multi-JSON parsing issues |

---

## Non-Negotiable Constraints

- ❌ StoryBacklog never stores raw LLM output
- ❌ No "two shapes" in fragments (viewer sees one canonical shape)
- ❌ No generate-all without locking
- ✅ Init is idempotent (calling again returns existing)
- ✅ StoryBacklog summaries are lossy projections with detail_ref
- ✅ Empty stories = card renders without story section

---

## In Scope (Slice 1 Only)

1. **New stored document type: `StoryBacklog`**
   - Canonical format: `{ project_id, source_epic_backlog_ref, epics[] }`
   - Epic format: `{ epic_id, name, intent, mvp_phase, stories[] }`
   - Story summary format: `{ story_id, title, intent, phase, risk_level?, detail_ref }`

2. **New command endpoint: `POST /api/commands/story-backlog/init`**
   - Input: `{ project_id }`
   - Loads EpicBacklog for project
   - Creates StoryBacklog with epics copied, `stories: []` for each
   - Idempotent: returns existing if already initialized
   - Response: `{ document_id, document_ref, epics_initialized }`

3. **Update document route for story_backlog**
   - If StoryBacklog doesn't exist → call init endpoint
   - Then render with StoryBacklogView

4. **Ensure StoryBacklogView renders the canonical format**
   - Fragment already handles `epic_name`, `stories[]`
   - Verify docdef `repeat_over: /epics` works

---

## Out of Scope (Slice 2)

- LLM generation (`generate-epic`, `generate-all`)
- StoryDetail document storage
- Projection handler (BA output → summary)
- Jobs table
- Locks table
- Progress tracking UI

---

## Design

### StoryBacklog Stored Document Schema

```json
{
  "document_type": "StoryBacklog",
  "params": { "project_id": "P-123" },
  "content": {
    "project_id": "P-123",
    "project_name": "Demo Project",
    "source_epic_backlog_ref": {
      "document_type": "EpicBacklog",
      "params": { "project_id": "P-123" }
    },
    "epics": [
      {
        "epic_id": "AUTH-100",
        "name": "User Authentication",
        "intent": "Enable users to securely access the system",
        "mvp_phase": "mvp",
        "stories": []
      },
      {
        "epic_id": "DASH-200",
        "name": "Dashboard",
        "intent": "Provide visibility into system state",
        "mvp_phase": "mvp",
        "stories": []
      }
    ]
  }
}
```

### Story Summary Format (after Slice 2 generates)

```json
{
  "story_id": "AUTH-101",
  "title": "Email Registration",
  "intent": "Users can register with email and password.",
  "phase": "mvp",
  "risk_level": "medium",
  "detail_ref": {
    "document_type": "StoryDetailView",
    "params": { "story_id": "AUTH-101" }
  }
}
```

### Init Command Endpoint

```
POST /api/commands/story-backlog/init

Request:
{
  "project_id": "uuid"
}

Response (200):
{
  "status": "created" | "exists",
  "document_id": "uuid",
  "document_ref": {
    "document_type": "StoryBacklog",
    "params": { "project_id": "uuid" }
  },
  "summary": {
    "epics_initialized": 3,
    "stories_existing": 0
  }
}

Errors:
- 404: EpicBacklog not found for project
- 422: EpicBacklog doesn't contain epics in expected format
```

### Init Behavior

1. Load EpicBacklog for project_id
2. Check if StoryBacklog already exists for project_id
   - If yes: return existing (idempotent)
   - If no: create new
3. For each epic in EpicBacklog:
   - Copy: epic_id, name (from title), intent, mvp_phase
   - Set: stories = []
4. Store StoryBacklog document
5. Return summary

### Route Update (document_routes.py)

```python
# In get_document() for story_backlog:
if doc_type_id == "story_backlog":
    # Try to load StoryBacklog
    story_backlog = await _get_document_by_type(db, proj_uuid, "StoryBacklog")
    
    if not story_backlog:
        # Auto-init from EpicBacklog
        init_result = await story_backlog_init(db, project_id)
        story_backlog = await _get_document_by_type(db, proj_uuid, "StoryBacklog")
    
    # Render with StoryBacklogView docdef
    return await _render_with_new_viewer(
        document_type="StoryBacklogView",
        document_data=story_backlog.content,
        ...
    )
```

---

## Files to Create/Modify

| File | Changes |
|------|---------|
| `app/api/routers/commands.py` | New - command endpoints |
| `app/domain/services/story_backlog_service.py` | New - init logic |
| `app/web/routes/public/document_routes.py` | Update - auto-init if missing |
| `app/domain/registry/loader.py` | Update - add StoryBacklog doc type |

---

## Test Plan

### Automated Tests

| Test | Assertion |
|------|-----------|
| test_init_creates_story_backlog | StoryBacklog created with epics, empty stories |
| test_init_idempotent | Second call returns existing, no duplicate |
| test_init_copies_epic_fields | epic_id, name, intent, mvp_phase copied |
| test_init_404_no_epic_backlog | Returns 404 if EpicBacklog missing |
| test_route_auto_inits | Visiting story_backlog auto-calls init |
| test_viewer_renders_empty_cards | Epic cards show without stories section |

### Manual Verification

1. Create project with EpicBacklog
2. Click "Story Backlog" in sidebar
3. Verify: Page shows epic cards, no stories
4. Refresh page - still works (idempotent)
5. Check database - StoryBacklog document exists

---

## Acceptance Criteria

1. ✅ StoryBacklog document type exists with canonical schema
2. ✅ `/api/commands/story-backlog/init` endpoint works
3. ✅ Init copies epics from EpicBacklog with stories: []
4. ✅ Init is idempotent (second call returns existing)
5. ✅ Route auto-inits if StoryBacklog missing
6. ✅ StoryBacklogView renders epic cards (no stories section when empty)
7. ✅ No LLM calls in this slice

---

## Failure Conditions (Automatic Reject)

- Init stores raw LLM output
- Init creates duplicate StoryBacklog documents
- Viewer shows "No document" instead of empty cards
- Epic fields not copied correctly from EpicBacklog

---

## Notes

- This sets up the structure for Slice 2 (generation)
- The "Generate Stories" buttons can be visible but disabled until Slice 2
- StoryBacklog is a NEW document type, separate from existing `story_backlog` (BA output)
- Consider renaming existing `story_backlog` to `ba_story_set` to avoid confusion
