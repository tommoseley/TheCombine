# ADR-068 Implementation Plan: Project Mockup Attachments

**Status:** Draft
**ADR:** ADR-068 — Project Mockup Attachments
**Scope:** Multi-commit (3 Work Packages, ~8 Work Statements)
**Estimated complexity:** Medium

---

## Overview

Implement project-scoped mockup attachments: upload during Concierge intake, store with metadata, display in workbench, and selectively inject into LLM prompt assembly as multimodal image content.

---

## Dependency Chain

```
WP-MOCKUP-001 (Storage + API)
    └── WP-MOCKUP-002 (UI — intake + workbench)
            └── WP-MOCKUP-003 (Prompt assembly integration)
```

WP-001 is foundational. WP-002 depends on WP-001 API. WP-003 depends on WP-001 storage model and can partially parallelize with WP-002.

---

## WP-MOCKUP-001: Storage and API Layer

**Objective:** Artifact persistence, upload/download/list/delete API endpoints, thumbnail generation.

### WS-MOCKUP-001: Database Schema and Domain Model

**Allowed Paths:**
- alembic/versions/
- app/api/models/
- app/domain/models/
- app/domain/repositories/
- app/core/database.py
- tests/

**Steps:**
1. Create Alembic migration for `project_artifacts` table (schema per ADR-068 §4.1, with `file_content` and `thumbnail_content` as `bytea` columns)
2. Create SQLAlchemy ORM model `ProjectArtifact` in `app/api/models/project_artifact.py`
3. Register ORM model in `app/core/database.py`
4. Write tests: ORM model round-trip (create, query, delete)

Note: No domain DTO or repository protocol needed for V1. This is a project-scoped CRUD resource — the ORM model + `MockupStorageService` (WS-002) is sufficient. Introduce a repository port only if artifact storage becomes a reusable domain boundary.

### WS-MOCKUP-002: Mockup Storage Service

**Allowed Paths:**
- app/api/services/
- app/core/
- tests/

**Steps:**
1. Create `app/api/services/mockup_storage_service.py` with protocol + DB implementation:
   - `save(project_id, file_content, mime_type, label) → ProjectArtifact` — validates, generates thumbnail, persists to `project_artifacts` table (bytea columns); returns the ORM instance
   - `load(artifact_id) → (bytes, mime_type)` — returns raw file content
   - `load_thumbnail(artifact_id) → (bytes, mime_type)` — returns thumbnail
   - `delete(artifact_id)` — removes row
   - `load_as_base64(artifact_id) → (base64_string, mime_type)` — for prompt injection
2. Thumbnail generation: Pillow for images (resize to 256px max dimension), pdf2image for PDF first page (optional — defer if complex)
3. File validation: check MIME type against allowlist (image/png, image/jpeg, application/pdf), enforce size limits (10MB images, 20MB PDF)
4. The service interface is storage-backend-agnostic — swap to S3 later without changing callers
5. Write tests: save/load/delete cycle, thumbnail generation, validation rejection, base64 encoding

### WS-MOCKUP-003: Upload/List/Download/Delete API

**Allowed Paths:**
- app/api/v1/routers/
- app/api/v1/__init__.py
- tests/

**Steps:**
1. Create `app/api/v1/routers/artifacts.py` with endpoints:
   - `POST /projects/{project_id}/artifacts` — multipart upload (file + label + artifact_type)
   - `GET /projects/{project_id}/artifacts` — list artifacts with metadata
   - `GET /projects/{project_id}/artifacts/{artifact_id}` — serve original file
   - `GET /projects/{project_id}/artifacts/{artifact_id}/thumbnail` — serve thumbnail
   - `DELETE /projects/{project_id}/artifacts/{artifact_id}` — remove artifact + file
2. Request validation: project exists, file type allowed, size within limits
3. Register router in `app/api/v1/__init__.py`
4. Write tests: upload flow, list, download, thumbnail, delete, validation errors (wrong type, too large, missing project)

---

## WP-MOCKUP-002: Upload UI (Concierge + Workbench)

**Objective:** Upload button in Concierge intake chat, mockup panel in project workbench.

### WS-MOCKUP-004: Concierge Intake Upload Button

**Allowed Paths:**
- spa/src/components/concierge/
- spa/src/components/ConciergeIntakeSidecar.jsx
- spa/src/api/client.js
- spa/src/hooks/useConciergeIntake.js
- tests/

**Steps:**
1. Add `uploadArtifact(projectId, file, label)` to `spa/src/api/client.js`
2. Add an "Attach mockup" button (image/paperclip icon) to the chat input area in the Concierge chat interface
3. On click: open file picker (accept: image/png, image/jpeg, application/pdf)
4. On file select: buffer the file client-side and show a thumbnail chip in the conversation
5. Allow label editing on the chip (default: filename without extension)
6. Handle validation errors (file too large, wrong type) with inline error message before buffering
7. On intake completion (project created): upload all buffered files to the API in sequence, associating them with the new project ID
8. If any upload fails post-creation: show error but do not block project creation — user can re-upload from workbench

### WS-MOCKUP-005: Project Workbench Mockup Panel

**Allowed Paths:**
- spa/src/components/
- spa/src/api/client.js
- tests/

**Steps:**
1. Add `listArtifacts(projectId)` and `deleteArtifact(projectId, artifactId)` to API client
2. Create `spa/src/components/MockupPanel.jsx`:
   - Thumbnail grid showing uploaded mockups
   - Each card: thumbnail, label, upload date, file size
   - Click thumbnail → full-size lightbox/modal
   - Delete button with confirmation
   - Upload button for adding more mockups post-intake
3. Wire MockupPanel into the project workbench/Floor layout (tab or side panel)
4. Handle empty state ("No mockups uploaded yet")

---

## WP-MOCKUP-003: Prompt Assembly Integration

**Objective:** Widen the LLM message model to support multimodal content, then selectively inject mockup images into prompt context.

### WS-MOCKUP-006A: Multimodal Message Support

**Allowed Paths:**
- app/llm/models.py
- app/llm/providers/
- tests/

**Steps:**
1. Widen `Message.content` type from `str` to `Union[str, List[Dict[str, Any]]]` in `app/llm/models.py`
2. `Message.to_dict()` already returns `{"role": ..., "content": self.content}` — verify this passes content blocks through unchanged (Anthropic API accepts both string and array)
3. Keep `Message.user(text)` and other class methods unchanged — they still produce string content
4. Add `Message.user_multimodal(content_blocks)` class method for constructing multimodal messages
5. Verify `_format_messages` in `app/llm/providers/anthropic.py` works with both forms (should require no changes)
6. Write tests: multimodal message construction, to_dict with content blocks, provider formatting

**Scope constraint:** Only PD and TA document generation nodes will use multimodal messages in V1. All other paths remain text-only.

### WS-MOCKUP-006B: Prompt Assembly Multimodal Injection

**Allowed Paths:**
- app/domain/services/
- app/domain/workflow/
- app/api/services/
- tests/

**Steps:**
1. `MockupStorageService.load_as_base64()` already exists from WS-MOCKUP-002
2. Create `app/domain/services/mockup_context_builder.py`:
   - `build_mockup_context(project_id, stage, db_session) → List[ContentBlock]`
   - Loads artifacts for project where stage_hints includes the current stage (or all if no hints)
   - Returns multimodal content blocks (text framing + base64 images)
   - Framing text per ADR-068 §6.1: "Reference Mockups... Treat as design intent, not implementation specification"
3. Wire into prompt assembly: when building context for PD or TA, call mockup_context_builder and append blocks to user message content
4. Log which artifact IDs were included (ADR-010 compliance)
5. Write tests: context builder produces correct content blocks, respects stage hints, empty when no mockups

### WS-MOCKUP-007: Stage Selection Defaults

**Allowed Paths:**
- app/api/v1/routers/artifacts.py
- app/api/models/project_artifact.py
- tests/

**Steps:**
1. Add `stage_hints` field to artifact metadata (JSONB): list of stage IDs where this mockup should be injected
2. Default for new uploads: `["project_discovery", "technical_architecture"]`
3. Add `PATCH /projects/{project_id}/artifacts/{artifact_id}` endpoint for updating label and stage_hints
4. Write tests: stage hint filtering, default assignment

### WS-MOCKUP-008: Lineage Event Recording

**Allowed Paths:**
- app/domain/services/
- app/api/v1/routers/artifacts.py
- tests/

**Steps:**

Durable audit (required):
1. The `project_artifacts` table is the durable record of artifact lifecycle (created_at, uploaded_by columns)
2. On prompt injection: extend `llm_runs` input_refs (ADR-010) to include artifact IDs consumed by the stage
3. Write tests: artifact IDs recorded in LLM run logs when mockups are injected

UI notification (optional):
4. On upload/delete: optionally publish via domain event bus for real-time UI refresh (e.g., mockup panel updates)
5. Note: the domain event bus is transport, not durable storage — it supplements but does not replace the audit trail above

---

## Verification

After all WPs:

1. `python -m pytest tests/ -x -q` — all tests pass
2. `cd spa && npm run build` — SPA builds clean
3. `ops/scripts/tier0.sh --frontend` — Tier 0 passes
4. Manual smoke test:
   - Start Concierge intake → upload a PNG mockup → complete intake
   - View mockup in workbench panel
   - Run PD → verify mockup appears in LLM run log as input
   - Run TA → verify mockup image is in prompt context
   - Delete mockup → verify removed from DB

---

## Dependencies and Prerequisites

- **Pillow** (Python): For image thumbnail generation. Add to requirements.txt.
- **pdf2image** (Python, optional): For PDF first-page thumbnail. Can defer PDF support to V1.1 if this adds complexity.
- No new infrastructure needed — storage is in existing RDS PostgreSQL (bytea columns).
- No new frontend dependencies needed (native File API + existing fetch client).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Large images blow up prompt token budget | Medium | Medium | File size limits (10MB), warn user if total mockup size is high |
| PDF multimodal support is poor | Low | Low | Convert PDF to images at upload time; defer if complex |
| Concierge project not yet created at upload time | Known | Low | Buffer files client-side during intake, upload after project creation |
| DB blob storage grows database size | Low | Low | File size limits cap growth; MockupStorageService abstraction enables S3 migration if needed |
