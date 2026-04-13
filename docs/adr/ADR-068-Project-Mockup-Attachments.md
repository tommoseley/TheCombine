# ADR-068 — Project Mockup Attachments

**Status:** Draft
**Date:** 2026-04-02
**Priority:** Current
**Related ADRs:**

- ADR-028 — Reference Document Management (governance model)
- ADR-010 — LLM Execution Logging (audit)
- ADR-040 — Stateless LLM Execution (context injection, not replay)
- ADR-042 — PGC Gates (explicit context selection)
- ADR-064 — Durable Authority Context (governed inputs)

---

## 1. Decision Summary

The Combine supports project-scoped mockup attachments — binary image files that represent UX design intent. Mockups are uploaded during Concierge intake, stored as governed project artifacts, and selectively injected into LLM prompt assembly as multimodal image content.

Mockups are **governed context, not instructions**. They inform UX-aware pipeline stages (PD, TA, WP, WS) but do not override system rules or prompt governance.

This ADR implements a narrow, concrete slice of ADR-028 (Reference Document Management) focused on image-based UX artifacts.

---

## 2. Definitions

**Mockup Attachment**
A user-uploaded image file (PNG, JPG, PDF) representing UX design intent for a project. Stored as a binary artifact with metadata. Not a workflow-produced document.

**Selective Injection**
Mockups are only included in LLM prompt assembly when explicitly selected for a given pipeline stage. They are not automatically included in every stage.

---

## 3. What This ADR Makes True

1. A user can upload one or more image files during Concierge intake
2. Each upload is stored as a project-scoped artifact with:
   - Stable artifact ID (UUID)
   - User-provided label (e.g., "dashboard mock", "mobile checkout flow")
   - MIME type, file size, upload timestamp, uploader
3. Uploaded mockups are visible in the project workbench (list + thumbnail preview)
4. Mockups can be selectively injected into prompt assembly as multimodal image blocks
5. Upload events are recorded for lineage/audit
6. Mockups are treated as uncertified external inputs (per ADR-028 §6)

---

## 4. Storage Model

### 4.1 Metadata Table: `project_artifacts`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Artifact ID |
| project_id | UUID (FK) | Owning project |
| label | VARCHAR(255) | User-provided display label |
| artifact_type | VARCHAR(50) | `mockup` (extensible for future types) |
| mime_type | VARCHAR(100) | e.g., `image/png`, `image/jpeg`, `application/pdf` |
| file_size_bytes | INTEGER | Original file size |
| file_content | BYTEA | Binary file content |
| thumbnail_content | BYTEA | Resized thumbnail (256px max, nullable) |
| uploaded_by | VARCHAR(100) | Uploader identity (nullable for V1) |
| created_at | TIMESTAMP | Upload time |
| metadata | JSONB | Optional: stage hints, notes |

### 4.2 File Storage

**V1:** PostgreSQL `bytea` columns in the `project_artifacts` table. At current scale (handful of mockups per project, few projects), DB blob storage is simpler than external file storage — no new infrastructure, no S3 bucket, works identically in dev and production.

File access is mediated by a `MockupStorageService` that abstracts the storage backend. If scale demands it, the service implementation can be swapped to S3 without schema or API changes.

**Future:** If DB size becomes a concern, migrate blobs to S3 and replace `file_content`/`thumbnail_content` with a `storage_path` reference. The service interface remains unchanged.

### 4.3 Accepted Formats

| Format | MIME Type | Max Size |
|--------|-----------|----------|
| PNG | image/png | 10 MB |
| JPEG | image/jpeg | 10 MB |
| PDF | application/pdf | 20 MB |

Other formats are rejected at upload time.

---

## 5. Upload Flow (Concierge Integration)

### 5.1 User Experience

During Concierge intake's conversational phase, the chat input area includes an "Attach mockup" button (paperclip or image icon). The user:

1. Clicks the button → file picker opens
2. Selects one or more image files
3. Provides a label per file (or accepts auto-generated from filename)
4. Files are buffered client-side and appear as thumbnail chips in the conversation

### 5.2 Ownership Decision: Client-Side Buffering

**Architectural decision:** Mockup files are held in browser memory during intake and uploaded to the API only after the project is created.

**Rationale:** The current intake flow (`app/api/v1/routers/intake.py`) does not create the project until the workflow completes successfully. Introducing pre-project artifact storage (e.g., binding to `execution_id` then rebinding to `project_id`) would add lifecycle complexity for no user-facing benefit.

**Behavior:**
- During intake: files are validated client-side (type, size) and rendered as thumbnail chips
- On project creation: buffered files are uploaded sequentially via the artifacts API
- If any upload fails: the project still exists; user can re-upload from the workbench
- If the user abandons intake: buffered files are discarded with no server-side residue

### 5.3 Upload Timing

Mockups can be uploaded:
- During Concierge intake (primary path — buffered, uploaded on project creation)
- After project creation, from the project workbench (secondary path — direct upload)

Both paths use the same API endpoint and storage model.

### 5.4 API

```
POST /api/v1/projects/{project_id}/artifacts
Content-Type: multipart/form-data

Fields:
  file: binary
  label: string (optional, defaults to filename stem)
  artifact_type: string (default: "mockup")

Response: 201 Created
{
  "id": "uuid",
  "project_id": "uuid",
  "label": "dashboard mock",
  "artifact_type": "mockup",
  "mime_type": "image/png",
  "file_size_bytes": 245760,
  "created_at": "2026-04-02T...",
  "thumbnail_url": "/api/v1/projects/{id}/artifacts/{id}/thumbnail"
}
```

```
GET /api/v1/projects/{project_id}/artifacts
→ List all artifacts for a project

GET /api/v1/projects/{project_id}/artifacts/{artifact_id}
→ Serve the original file (Content-Type from mime_type)

GET /api/v1/projects/{project_id}/artifacts/{artifact_id}/thumbnail
→ Serve a resized thumbnail (256px max dimension)

DELETE /api/v1/projects/{project_id}/artifacts/{artifact_id}
→ Remove artifact and file
```

---

## 6. Prompt Assembly Integration

### 6.1 Prerequisite: Multimodal Message Support

**Architectural decision:** The current `Message` model (`app/llm/models.py`) has `content: str`. The Anthropic Messages API accepts `content` as either a string or an array of content blocks (text + image). To support mockup injection, `Message.content` must be widened to `Union[str, List[Dict]]` and `to_dict()` must pass the value through unchanged.

**Scope of change:**
- `app/llm/models.py`: Change `Message.content` type to `Union[str, List[Dict[str, Any]]]`
- `Message.to_dict()`: Already returns `{"role": ..., "content": self.content}` — no change needed (Anthropic API accepts both forms)
- `app/llm/providers/anthropic.py`: `_format_messages` already calls `msg.to_dict()` — no change needed
- Text-only callers (`Message.user("...")`) continue to work — string is still valid

**Constrained scope:** Only workflow nodes that explicitly build multimodal messages will use content block arrays. All existing text-only paths remain unchanged. V1 multimodal injection targets only PD and TA document generation nodes.

### 6.2 Injection Model

When prompt assembly runs for a stage with selected mockups, each mockup is injected as a multimodal content block in the user message:

```python
# In prompt assembly, when mockups are selected for this stage:
content_blocks = [
    {"type": "text", "text": "## Reference Mockups\n"
     "The following mockups represent intended UX design for this project.\n"
     "Treat them as design intent, not implementation specification.\n"},
]
for mockup in selected_mockups:
    content_blocks.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mockup.mime_type,
            "data": mockup.base64_content,
        },
    })
    content_blocks.append({
        "type": "text",
        "text": f"[Mockup: {mockup.label}]\n",
    })
# Create message with content block array instead of string
message = Message(role=MessageRole.USER, content=content_blocks)
```

### 6.2 Selection Rules

- Mockups are **not** auto-injected into every stage
- V1 default: mockups uploaded during intake are available to PD and TA
- Selection is stored as `metadata.stage_hints` on the artifact (e.g., `["project_discovery", "technical_architecture"]`)
- Future: PGC question "Which mockups are relevant to this stage?" for explicit per-stage selection

### 6.3 Safety

Per ADR-028 §6 and ADR-040:

- Mockup content is framed as "design intent context," not instructions
- The prompt explicitly states: "Treat them as design intent, not implementation specification"
- Mockup-derived text (OCR, labels in images) is not extracted or treated as authoritative
- Mockups do not override prompt governance or system rules

---

## 7. Lineage and Audit

### 7.1 Durable Persistence (required)

- The `project_artifacts` table itself is the durable record of upload lifecycle (created_at, uploaded_by, metadata)
- When a pipeline stage consumes a mockup, the `llm_runs` log (ADR-010) records which artifact IDs were included in the prompt via `input_refs`
- If a produced document references a mockup by label, that reference is traceable through the document content

### 7.2 UI Notification (optional)

- Upload/delete events MAY be published via the domain event bus for real-time UI updates (e.g., refreshing a mockup panel)
- The domain event bus is transport infrastructure, not durable storage — it does not replace the audit trail in §7.1

---

## 8. Workbench Display

The project workbench shows an "Attachments" or "Mockups" panel:

- Thumbnail grid or list view
- Label, upload date, file size
- Click to view full-size in a lightbox/modal
- Delete button (with confirmation)
- Upload button for adding more after project creation

---

## 9. Out of Scope (V1)

- Annotation or markup tools on mockups
- OCR / text extraction from images
- Figma, Sketch, or design tool sync
- Automatic component extraction from mockups
- Cross-project mockup sharing
- Version history for mockups (replace = delete old + upload new)
- Non-image reference artifacts (API specs, TAs — future ADR)

---

## 10. Consequences

### Positive

- TA and other stages can reason about UX intent from actual visual designs
- Upload happens naturally during the intake conversation flow
- Governed, auditable, selective — not a dump of untracked files
- Extensible: `artifact_type` field allows future reference artifact types

### Negative

- Large images increase prompt token usage (multimodal image tokens)
- PDF mockups may not render well as multimodal content (image conversion needed)
- DB blob storage increases database size (mitigated by file size limits and low volume)

### Mitigations

- File size limits enforce reasonable prompt sizes
- PDF → image conversion at upload time (first page as thumbnail, full pages as separate images)
- `MockupStorageService` abstraction makes S3 migration a service-swap, not a rewrite

---

## 11. Future Direction

This ADR establishes binary project-scoped artifact plumbing and multimodal prompt injection. It does not establish the reference binder or source artifact ingestion architecture — those are separate, materially different ADRs. The `project_artifacts` table and `MockupStorageService` created here may be reused by future artifact types, but no commitment to that reuse is made in this ADR.
