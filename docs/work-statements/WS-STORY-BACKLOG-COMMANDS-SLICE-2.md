# WS-STORY-BACKLOG-COMMANDS-SLICE-2

| Field | Value |
|---|---|
| **Work Statement** | WS-STORY-BACKLOG-COMMANDS-SLICE-2 |
| **Status** | Draft |
| **Owner** | Document Pipeline |
| **Related ADRs** | ADR-034, WS-STORY-BACKLOG-COMMANDS-SLICE-1 |
| **Type** | Command Endpoints + LLM Integration + Projection |
| **Expected Scope** | Single-commit |

---

## Purpose

Implement story generation commands that:
1. Call LLM for one epic at a time
2. Store full BA output as StoryDetail documents
3. Project summaries into StoryBacklog

---

## Prerequisites (from Slice 1)

- ✅ `story_backlog` document type exists
- ✅ `POST /api/commands/story-backlog/init` works
- ✅ StoryBacklog renders epic cards with empty stories
- ✅ `StoryBacklogView` docdef renders correctly

---

## In Scope

### 1. Command: `POST /api/commands/story-backlog/generate-epic`

**Request:**
```json
{
  "project_id": "uuid",
  "epic_id": "demo-core-system"
}
```

**Behavior:**
1. Load StoryBacklog for project
2. Verify epic exists in StoryBacklog
3. Load context (EpicDetail, Architecture if available)
4. Call BA LLM for that epic only (single JSON output)
5. For each story in LLM output:
   - Store full story as `story_detail` document
   - Project summary into StoryBacklog.epics[i].stories[]
6. Update StoryBacklog document (increment version)

**Response (200):**
```json
{
  "status": "completed",
  "epic_id": "demo-core-system",
  "summary": {
    "stories_generated": 4,
    "stories_written": 4
  }
}
```

**Errors:**
- 404: StoryBacklog not found (call init first)
- 404: Epic not in StoryBacklog
- 422: LLM output invalid

### 2. Command: `POST /api/commands/story-backlog/generate-all`

**Request:**
```json
{
  "project_id": "uuid"
}
```

**Behavior:**
1. Load StoryBacklog
2. For each epic in StoryBacklog.epics[]:
   - Call generate-epic logic (reuse, don't duplicate)
   - Update StoryBacklog after each epic (incremental)
3. Return summary

**Response (200):**
```json
{
  "status": "completed",
  "summary": {
    "epics_processed": 3,
    "total_stories_generated": 12
  }
}
```

### 3. StoryDetail Document Type

**doc_type_id:** `story_detail`

**Schema:** Full BA story output
```json
{
  "story_id": "demo-core-system-001",
  "epic_id": "demo-core-system",
  "title": "...",
  "description": "...",
  "acceptance_criteria": [...],
  "related_arch_components": [...],
  "related_pm_story_ids": [...],
  "notes": [...],
  "mvp_phase": "mvp"
}
```

**Scope:** Per-story (parent = StoryBacklog)

### 4. Projection Rules (Frozen)

**LLM Output → StoryBacklog Summary:**

| LLM Field | Summary Field |
|-----------|---------------|
| `id` | `story_id` |
| `title` | `title` |
| `description` (truncated) | `intent` |
| `mvp_phase` | `phase` |
| (derived) | `risk_level` (optional) |
| (generated) | `detail_ref` → StoryDetailView |

**Explicitly NOT in summary:**
- ❌ acceptance_criteria
- ❌ related_arch_components
- ❌ related_pm_story_ids
- ❌ notes

---

## Out of Scope

- Locking (defer to Slice 3)
- Jobs table / async tracking (defer)
- Progress UI (defer)
- Retry logic (defer)

---

## Design

### Service: StoryBacklogService

```python
class StoryBacklogService:
    async def generate_epic_stories(
        self,
        project_id: UUID,
        epic_id: str,
    ) -> GenerateEpicResult:
        # 1. Load StoryBacklog
        # 2. Find epic
        # 3. Build LLM prompt with context
        # 4. Call LLM
        # 5. Store StoryDetails
        # 6. Project summaries
        # 7. Update StoryBacklog
        
    async def generate_all_stories(
        self,
        project_id: UUID,
    ) -> GenerateAllResult:
        # Loop epics, call generate_epic_stories for each
```

### Projection Function

```python
def project_story_to_summary(full_story: dict, epic_id: str) -> dict:
    """Convert full BA story to summary for StoryBacklog."""
    return {
        "story_id": full_story["id"],
        "title": full_story["title"],
        "intent": full_story["description"][:200],  # Truncate
        "phase": full_story["mvp_phase"].replace("-", "_"),
        "detail_ref": {
            "document_type": "StoryDetailView",
            "params": {"story_id": full_story["id"]}
        }
    }
```

---

## Files to Create/Modify

| File | Changes |
|------|---------|
| `app/api/routers/commands.py` | Add generate-epic, generate-all endpoints |
| `app/domain/services/story_backlog_service.py` | New - generation logic |
| `app/domain/registry/loader.py` | Add story_detail document type |

---

## Test Plan

| Test | Assertion |
|------|-----------|
| test_generate_epic_creates_stories | Stories appear in StoryBacklog |
| test_generate_epic_stores_details | StoryDetail documents created |
| test_generate_epic_projects_correctly | Summary has correct fields |
| test_generate_epic_404_no_backlog | Returns 404 if no StoryBacklog |
| test_generate_epic_404_no_epic | Returns 404 if epic not found |
| test_generate_all_processes_all_epics | All epics get stories |
| test_summary_excludes_detail_fields | No AC, no components in summary |

---

## Acceptance Criteria

1. ✅ `generate-epic` calls LLM for single epic
2. ✅ `generate-epic` stores StoryDetail per story
3. ✅ `generate-epic` projects summaries to StoryBacklog
4. ✅ `generate-all` loops all epics
5. ✅ Summaries exclude detail fields (AC, components, notes)
6. ✅ `detail_ref` points to StoryDetailView
7. ✅ StoryBacklog version incremented after update

---

## Notes

- Reuses existing BA role prompts for LLM call
- One LLM call = one epic (avoids multi-JSON parsing)
- Projection is lossy by design
- StoryDetail is source of truth for full story
