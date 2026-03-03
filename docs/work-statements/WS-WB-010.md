# WS-WB-010: Work Binder — Propose Work Statements (LLM Draft Station)

## Overview

Introduce a new Work Binder station: **PROPOSE STATEMENTS**.

This is the **first intentional LLM boundary crossing inside the Work Binder**. Everything prior in WB has been purely mechanical (import → promote → CRUD → audit). This WS adds a controlled, explicitly-triggered LLM generation step that produces **DRAFT-only** Work Statements (WS), validated against schema **before** persistence, and fully auditable.

Promotion remains deterministic and mechanical. WS proposal is a separate operator action.

## Goals

1. Add an explicit operator-triggered action to propose WS drafts for a promoted WP.
2. Persist only schema-valid WS drafts (no partial writes).
3. Enforce **TA present + stabilized** as a hard prerequisite.
4. Preserve "no silent destruction": never delete or overwrite existing WS content as part of proposal.
5. Produce audit events for all mutations and for the LLM proposal run.

## Non-Goals

- No automatic WS proposal during WP promotion.
- No "force regenerate" behavior.
- No background jobs, retries, agent loops, or autonomous orchestration.
- No stabilization automation; operator must stabilize WS artifacts explicitly.
- No editing of candidate WPs inside WB (candidates remain lineage anchors).

---

## Key Governance Invariants

### INV-LLM-BOUNDARY-001 — Explicit LLM Station
LLM generation is permitted **only** in this station, behind an explicit operator action, and must:
- produce **DRAFT** WS artifacts only
- pass schema validation **before** persistence
- emit audit records for proposal and persistence

### INV-NO-DESTRUCTION-001 — No Silent Destruction
WS proposal MUST NOT delete, overwrite, or invalidate existing WS documents.
If WSs already exist for a WP (or WP ws_index is non-empty), proposal is blocked unless the operator resolves it explicitly.

### INV-TA-GATE-001 — TA Prerequisite
WS proposal is forbidden unless the project has a **stabilized** Technical Architecture (TA).

---

## Prerequisites / Dependencies

- WP + WS doc types are registered globally and handlers exist (post WP-WB-001 and WS-REGISTRY-001).
- WP schema includes `ws_index[]` and plane separation rules already implemented.
- TA doc type exists and can be queried for latest stabilized version for `space_id = project_id`.

---

## Architectural Decisions (Binding)

1. `/work-binder/promote` MUST remain mechanical; no LLM calls inside promotion.
2. WS proposal is a separate station endpoint: `POST /work-binder/propose-ws`.
3. WS proposal uses a **dedicated task prompt** (unambiguous; CC must not choose):
   - `combine-config/prompts/tasks/propose_work_statements/releases/1.0.0/task.prompt.txt`
4. Proposed WS artifacts are persisted as **DRAFT** and must be visually indicated as such in UI.
5. If the WP already has WSs (ws_index non-empty), proposal returns HARD_STOP and does nothing.

---

## Implementation Tasks

### 1) Seed Governance: Create the dedicated task prompt

**Create:**
- `combine-config/prompts/tasks/propose_work_statements/releases/1.0.0/task.prompt.txt`
- `combine-config/prompts/tasks/propose_work_statements/releases/1.0.0/meta.yaml`

**Prompt intent (must be explicit in task.prompt.txt):**
- Inputs: WP document + TA document only (and optional PD/IP context if your routing provides it as reference—must be declared)
- Output: JSON array of WS artifacts conforming to the **work_statement** schema
- Output WSs must be DRAFT-ready (no stabilization language, no execution claims)
- Must not include any fields not permitted by schema (`additionalProperties: false`)
- Must not emit WP fields or mutate ws_index (the caller handles persistence + ws_index update)

**Note:** This task prompt is not the same as `work_statement` task prompt. It is a proposal station prompt. Keep it narrow.

### 2) Backend: Add WS proposal endpoint

**Files:**
- `app/api/v1/routers/work_binder.py` (add route + models)
- `app/domain/services/ws_proposal_service.py` (new)
- (optional) shared doc lookup helpers if consistent with your existing WB services

**Route:**
- `POST /work-binder/propose-ws`

**Request model:**
```python
class ProposeWSRequest(BaseModel):
    project_id: str
    wp_id: str
```

**Response model:**
```python
class ProposeWSResponse(BaseModel):
    wp_id: str
    created: bool
    ws_ids: list[str]
```

**Endpoint logic (deterministic):**

1. **Resolve WP** (latest) by:
   - `space_id = project_id`
   - `doc_type_id = work_package`
   - `instance_id = wp_id`
   - `is_latest = True`

2. **Enforce TA gate:**
   - Find latest TA doc for `space_id = project_id`
   - If missing or not stabilized → 400 HARD_STOP:
     - `"HARD_STOP: Cannot propose work statements until Technical Architecture is stabilized for this project."`

3. **Enforce "no silent destruction":**
   - If WP `ws_index` is non-empty → 409 HARD_STOP with explanation:
     - `"HARD_STOP: Work Package already has Work Statements. Delete drafts (or resolve ws_index) before proposing again."`

4. **Integrity check** (prevent hidden corruption):
   - If `ws_index` is non-empty (should be caught above), additionally verify all references resolve; if any dangling → 409 HARD_STOP:
     - `"HARD_STOP: Work Package ws_index contains dangling references. Repair ws_index before proposing."`

5. **LLM call** (proposal station):
   - Invoke Combine task execution using exact prompt id:
     - `propose_work_statements@1.0.0`
   - Provide inputs: WP doc + TA doc
   - Receive output: list of WS JSON objects

6. **Validate before persistence:**
   - Validate each WS object against the registered `work_statement` schema
   - If any fail → 400 and persist nothing

7. **Persist WS documents:**
   - Persist each WS as a new WS document instance (DRAFT state) with stable ws_id strategy:
     - `WS-{wp_id}-{NNN}` or your existing WS id convention (must be deterministic and unique)

8. **Update WP ws_index:**
   - Persist a new WP edition where `ws_index[]` is set to the ordered list of created ws_ids

9. **Audit events:**
   - `WB_WS_PROPOSAL_REQUESTED` (once) including wp_id and ta_version
   - `WS_PROPOSED` (per WS) including ws_id
   - `WP_WS_INDEX_UPDATED` (once) including before/after counts
   - All events include correlation/run ids when available

### 3) SPA: Add explicit "PROPOSE STATEMENTS" action

**Files:**
- `spa/src/api/client.js`
- `spa/src/components/WorkBinder/WPContentArea.jsx` (or equivalent WP action area)

**API client:**
```javascript
proposeWorkStatements: (projectId, wpId) =>
  request('/work-binder/propose-ws', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, wp_id: wpId }),
  }),
```

**UI behavior:**
- Show PROPOSE STATEMENTS only when:
  - WP is selected
  - WP has empty `ws_index`
  - TA is not pending (backend is source of truth; UI can be optimistic but must handle errors)
- On click:
  - call endpoint
  - refresh WP + WS list
  - show WS entries as DRAFT

---

## Tier-1 Tests (Bug-First Rule)

Write failing tests first.

**Backend test cases:**
- TA missing → 400 HARD_STOP, no persistence
- TA not stabilized (if status exists) → 400 HARD_STOP, no persistence
- WP ws_index non-empty → 409 HARD_STOP, no LLM call, no persistence
- Schema validation failure from proposal output → 400, persist nothing
- Happy path:
  - creates N WS docs (DRAFT)
  - creates new WP edition with ws_index set
  - emits audit events (verify called)
- Deterministic id strategy:
  - stable format and uniqueness for ws_ids; no random suffixes

---

## Acceptance Criteria

- A promoted WP with empty ws_index shows PROPOSE STATEMENTS in WB.
- Clicking PROPOSE STATEMENTS:
  - calls `POST /work-binder/propose-ws`
  - persists schema-valid WS documents in DRAFT state
  - updates WP ws_index in a new WP edition
- If TA missing/not stabilized → 400 HARD_STOP, no persistence.
- If WP already has WSs (ws_index non-empty) → 409 HARD_STOP, no LLM call, no persistence.
- Audit events are emitted for proposal request and each persisted WS.
- Tier-1 tests pass; SPA builds clean.

---

## Allowed Paths

**Seed / prompts:**
- `combine-config/prompts/tasks/propose_work_statements/**`
- `combine-config/_active/active_releases.json` (only if required by your prompt registry)

**Backend:**
- `app/api/v1/routers/work_binder.py`
- `app/domain/services/ws_proposal_service.py`
- `tests/**`

**Frontend:**
- `spa/src/api/client.js`
- `spa/src/components/WorkBinder/**`

---

## Verification Steps

**Backend:**
- Run Tier-1 tests for propose endpoint
- Verify no persistence occurs on TA-missing and ws_index-nonempty cases

**UI:**
- Select a promoted WP with empty ws_index
- Click PROPOSE STATEMENTS
- Confirm WS list appears as DRAFT and WP ws_index is populated

**Run:**
- `ops/scripts/tier0.sh --frontend`
- backend Tier 0 subset as applicable
