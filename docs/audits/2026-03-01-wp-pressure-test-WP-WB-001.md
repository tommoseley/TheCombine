# WP Pressure Test -- WP-WB-001: Work Binder Operations

**Date:** 2026-03-01
**WP Location:** docs/work-statements/WP-WB-001.md
**Schema Bundle:** docs/work-statements/WP-WB-001-schemas.json
**WS Count:** 8
**Codebase Branch:** workbench/ws-b12f2a74613a

---

## Phase 0: Inventory

### WP Identity
- **WP ID:** WP-WB-001
- **Title:** Work Binder Operations
- **Status:** DRAFT

### Work Statements (8)

| WS ID | Title | Depends On |
|-------|-------|------------|
| WS-WB-001 | Schema Evolution + Versioning Model | None |
| WS-WB-002 | WP Candidate Handler + Persistence | WS-WB-001 |
| WS-WB-003 | Candidate Import from IP | WS-WB-002 |
| WS-WB-004 | Promotion Workflow | WS-WB-003 |
| WS-WB-005 | WP Edition Tracking + Change Summary | WS-WB-001 |
| WS-WB-006 | WS CRUD + Plane Separation | WS-WB-001, WS-WB-005 |
| WS-WB-007 | Work Binder Screen + Vertical Index | WS-WB-006 |
| WS-WB-008 | Audit Trail + Governance Invariants | WS-WB-004, WS-WB-005, WS-WB-006 |

### Doc Types Referenced

| Doc Type | Action | Current Version | Target Version |
|----------|--------|----------------|----------------|
| work_package | Evolve | 1.0.0 | 1.1.0 |
| work_statement | Evolve | 1.0.0 | 1.1.0 |
| work_package_candidate | Create | -- | 1.0.0 |

### Schema $id Values (from bundle)

| Schema | $id |
|--------|-----|
| WP v1.1.0 | `https://thecombine.dev/schemas/work_package.v1.1.json` |
| WS v1.1.0 | `https://thecombine.dev/schemas/work_statement.v1.1.json` |
| WPC v1.0.0 | `https://thecombine.dev/schemas/work_package_candidate.v1.json` |

### Existing $id Values (potential collision targets)

| Schema | $id |
|--------|-----|
| WP v1.0.0 | `https://thecombine.dev/schemas/work_package.v1.json` |
| WS v1.0.0 | `https://thecombine.dev/schemas/work_statement.v1.json` |

No collisions.

### ADR / Policy References

| Ref | File | Exists |
|-----|------|--------|
| ADR-051 | docs/adr/ADR-051-Work-Package-Runtime-Primitive.md | Yes |
| ADR-052 | docs/adr/ADR-052-Document-Pipeline-WP-WS-Integration.md | Yes |
| POL-WS-001 | docs/policies/POL-WS-001-Standard-Work-Statements.md | Yes |
| POL-ADR-EXEC-001 | docs/policies/POL-ADR-EXEC-001-ADR-Execution-Authorization.md | Yes |

### File Paths by Action

**Create (new files):**
- `combine-config/document_types/work_package/releases/1.1.0/` (dir + schemas)
- `combine-config/document_types/work_statement/releases/1.1.0/` (dir + schemas)
- `combine-config/document_types/work_package_candidate/` (dir + package + schemas)
- `app/domain/handlers/work_package_candidate_handler.py`
- `app/domain/services/candidate_import_service.py`
- `app/domain/services/wp_promotion_service.py`
- `app/domain/services/wp_edition_service.py`
- `app/domain/services/ws_crud_service.py`
- `app/domain/services/wb_audit_service.py`
- `app/api/v1/routers/work_binder.py`
- `spa/src/components/WorkBinder/` (directory with sub-components)
- 6+ test files in `tests/tier1/`

**Modify (existing files):**
- `combine-config/_active/active_releases.json`
- `app/domain/handlers/registry.py`
- `spa/src/components/Floor.jsx`

**Not listed but required (see findings):**
- `app/api/v1/routers/__init__.py` (router export)
- `app/api/v1/__init__.py` (router registration)
- `spa/src/components/ContentPanel.jsx` (WorkBinder wiring)

---

## Phase 1: Structural Validation

| Check | Result | Details |
|-------|--------|---------|
| 1.1 File References | PASS | All create paths have valid parent dirs; all modify paths exist |
| 1.2 Registry Paths | PASS | combine-config/ dirs exist; new dirs will be created by WS-WB-001 |
| 1.3 Active Releases | PASS | No doc_type_id or schema version collisions; WPC is new |
| 1.4 Dependency Chain | PASS | DAG is acyclic; all WS IDs valid; topological order correct |
| 1.5 Allowed Paths | **FAIL** | Router registration files missing from allowed_paths (Finding 1) |
| 1.6 ADR/Policy Refs | PASS | ADR-051, ADR-052, POL-WS-001, POL-ADR-EXEC-001 all exist |
| 1.7 Schema Conflicts | PASS | No $id collisions between new and existing schemas |
| 1.8 Handler/Registry | PASS | WPC handler created (WS-WB-002) and registered; existing WP/WS handlers sufficient |

**Structural Result:** FAIL -- 1 issue (allowed paths coverage)

---

## Phase 2: Architectural Pressure Test

| Check | Severity | Finding |
|-------|----------|---------|
| 2.1 Persistence | -- | Uses existing document store per D6. No new persistence plane. |
| 2.2 Dual Shape | -- | Additive schema evolution; single active version via active_releases. |
| 2.3 Prerequisites | HIGH | "Propose WS" LLM feature in scope but no WS implements backend (Finding 2) |
| 2.4 Governance Gaps | -- | WS-WB-008 provides comprehensive audit trail for all mutations. |
| 2.5 Invariant Contradictions | MEDIUM | ta_version_id/ws_index invariant not expressible in schema bundle (Finding 3) |
| 2.6 Blast Radius | LOW | 8 WSs, ~15 new + ~8 modified files. Well-segmented by WS boundaries. |
| 2.7 API Consistency | MEDIUM | Router registration requires files outside all WS allowed_paths (Finding 4) |
| 2.8 Migration/Rollback | LOW | All changes additive; active_releases revertible; no DB migrations. |

**Architectural Result:** 1 HIGH, 2 MEDIUM, 2 LOW findings

---

## Findings & Resolutions

### Finding 1: Router Registration Files Missing from Allowed Paths

**Severity:** HIGH
**Phase:** 1.5 (Allowed Paths Coverage)
**Description:** The new `work_binder.py` router must be registered in two files to be accessible at runtime, but neither file is in any WS's `allowed_paths`:
- `app/api/v1/routers/__init__.py` -- must export `work_binder_router`
- `app/api/v1/__init__.py` -- must call `api_router.include_router(work_binder_router)`

Without these edits, the `/api/v1/work-binder/` endpoints will be unreachable. Every WS that adds routes (WS-WB-003, 004, 005, 006, 008) is affected.

**Evidence:**
- `app/api/v1/__init__.py:5-26` -- explicit imports for every router
- `app/api/v1/__init__.py:31-48` -- explicit `include_router()` calls
- `app/api/v1/routers/__init__.py:3-16` -- explicit re-exports
- No WS `allowed_paths` includes either file

**Resolution Options:**

**A. Quick Fix** -- Add both files to WS-WB-003's allowed_paths
- Action: Add `app/api/v1/routers/__init__.py` and `app/api/v1/__init__.py` to WS-WB-003 allowed_paths (the WS that creates work_binder.py)
- Tradeoff: None -- this is the correct owner (first WS to create the router)
- Effort: Minimal (2 lines in WP)

**B. Correct Fix** -- Same as A (this is already the correct fix)
- Action: Same as A
- Effort: Minimal

**C. Eject** -- Defer router registration to a "wiring" WS
- Action: Create WS-WB-009 for router wiring
- Tradeoff: Unnecessary complexity; no benefit over Option A
- Effort: Small

**Recommendation: A** -- Add both files to WS-WB-003 allowed_paths. The WS that creates the router file should also wire it up.

---

### Finding 2: "Propose Work Statements" In Scope But No WS Implements Backend

**Severity:** HIGH
**Phase:** 2.3 (Missing Prerequisites)
**Description:** The WP Scope section lists "Propose Work Statements (LLM-assisted DRAFT creation)" as in-scope. WS-WB-007 includes a "PROPOSE WORK STATEMENTS" button in the UI. But no WS implements the backend service that:
- Accepts a WP context as input
- Invokes an LLM to generate candidate WS drafts
- Persists them as DRAFT work_statement documents

This is a functional gap: the UI button would have no backend to call.

**Evidence:**
- WP-WB-001.md:71 -- "Propose Work Statements (LLM-assisted DRAFT creation)" in scope_in
- WS-WB-007 scope: "PROPOSE WORK STATEMENTS button"
- WS-WB-006: WS CRUD only (manual create/update, no LLM generation)
- No WS mentions LLM invocation, prompt assembly, or task prompt for WS generation
- No `task_prompt` artifact referenced for WS proposal

**Resolution Options:**

**A. Quick Fix** -- Move "Propose WS" to out-of-scope and remove button from WS-WB-007
- Action: Move the line from scope_in to scope_out in WP; remove "PROPOSE WORK STATEMENTS" button from WS-WB-007 scope; add placeholder note for future WP
- Tradeoff: Defers LLM-assisted WS generation to a future WP
- Effort: Minimal (WP text edits)

**B. Correct Fix** -- Add WS-WB-009: WS Proposal via LLM
- Action: Draft a new WS covering: task prompt creation, LLM invocation service, API endpoint (`POST /api/v1/work-binder/wp/{wp_id}/propose-statements`), Tier-1 tests. Depends on WS-WB-006.
- Tradeoff: Adds scope (~1 additional WS); requires prompt governance (seed versioning)
- Effort: Medium (new WS + prompt + tests)

**C. Eject** -- Track as follow-up WP
- Action: Remove from scope; create WP-WB-002 stub for "LLM-Assisted WS Authoring"
- Tradeoff: WB ships without its most distinctive feature; manual WS creation still works
- Effort: Minimal

**Recommendation: A** -- Eject to out-of-scope. The WB is useful without LLM proposal (manual WS CRUD via WS-WB-006 is the foundation). LLM proposal is a natural follow-up WP after the binder infrastructure exists. Including it now adds prompt governance complexity and an LLM dependency that no other WS in this WP has.

---

### Finding 3: ta_version_id / ws_index Invariant Not in Schema

**Severity:** MEDIUM
**Phase:** 2.5 (Invariant Contradictions)
**Description:** WS-WB-001 verification criterion states: "WP schema disallows ws_index entries when ta_version_id is 'pending'". However, the schema bundle (`work_package_v1_1_0`) does not express this constraint. JSON Schema draft-07 supports `if/then/else` which could enforce this:

```json
"if": {
  "properties": {
    "governance_pins": {
      "properties": { "ta_version_id": { "const": "pending" } }
    }
  }
},
"then": {
  "properties": {
    "ws_index": { "maxItems": 0 }
  }
}
```

Without this, the invariant would need handler-level enforcement, which is weaker (can be bypassed by direct document store writes).

**Evidence:**
- WP-WB-001.md:107 -- "Ensure no contradictory states: if `governance_pins.ta_version_id` is 'pending', then `ws_index` must be empty"
- WP-WB-001.md:129 -- "WP schema disallows ws_index entries when ta_version_id is 'pending'"
- WP-WB-001-schemas.json: `work_package_v1_1_0` has no `if/then` clause
- WP-WB-001-schemas.json:75-86: `ws_index` defined without conditional restriction

**Resolution Options:**

**A. Quick Fix** -- Enforce in handler only
- Action: Add the check to `WorkPackageHandler.validate()`. Documented as handler-enforced invariant.
- Tradeoff: Invariant not in schema; documents written directly to store could violate it. But this matches current handler pattern.
- Effort: Small

**B. Correct Fix** -- Add `if/then` to schema bundle
- Action: Add the `if/then/else` clause to `work_package_v1_1_0` in the schema bundle before WS-WB-001 execution
- Tradeoff: None -- makes the constraint declarative and schema-enforceable
- Effort: Small (schema edit + validation test)

**C. Eject** -- Document as known gap
- Action: Add to WP Known Issues: "ta_version_id/ws_index invariant is handler-enforced, not schema-enforced"
- Tradeoff: Weaker enforcement
- Effort: Minimal

**Recommendation: B** -- The invariant is explicitly called out in verification criteria. The schema should express it. `if/then` in draft-07 is well-supported by Python jsonschema.

---

### Finding 4: Undeclared Dependency -- WS-WB-005 Needs work_binder.py

**Severity:** MEDIUM
**Phase:** 2.3 + 2.7 (Prerequisites + API Consistency)
**Description:** WS-WB-005 (Edition Tracking) includes `app/api/v1/routers/work_binder.py` in its allowed_paths to add the `GET /api/v1/work-binder/wp/{wp_id}/history` endpoint. But WS-WB-005 depends only on WS-WB-001 and is flagged as parallelizable with WS-WB-002.

The file `work_binder.py` is created by WS-WB-003, which depends on WS-WB-002. In the parallelized execution model, WS-WB-005 would run before WS-WB-003, so the router file wouldn't exist yet.

The WP's listed execution order (sequential) avoids this: WS-WB-005 is step 3, WS-WB-003 is step 4. But the declared dependency graph doesn't capture this implicit ordering.

Similarly, WS-WB-006 depends on WS-WB-001 + WS-WB-005 but not WS-WB-003, yet it also modifies work_binder.py.

**Evidence:**
- WP-WB-001.md:417 -- WS-WB-005 at position 3, WS-WB-003 at position 4
- WP-WB-001.md:424 -- "Parallelizable: WS-WB-002 + WS-WB-005 can run in parallel"
- WS-WB-005 allowed_paths includes `app/api/v1/routers/work_binder.py`
- WS-WB-003 creates `app/api/v1/routers/work_binder.py`
- WS-WB-005 depends_on: WS-WB-001 only
- WS-WB-006 depends_on: WS-WB-001, WS-WB-005 (not WS-WB-003)

**Resolution Options:**

**A. Quick Fix** -- Split API route from service in WS-WB-005 and WS-WB-006
- Action: WS-WB-005 creates only the edition service (`wp_edition_service.py` + tests). The history API endpoint is deferred to WS-WB-006 or WS-WB-008 (which run after WS-WB-003). Remove `app/api/v1/routers/work_binder.py` from WS-WB-005 allowed_paths.
- Tradeoff: Endpoint added later; service is testable immediately without API layer
- Effort: Small (WP text edits)

**B. Correct Fix** -- Add WS-WB-003 as explicit dependency for WS-WB-005 and WS-WB-006
- Action: WS-WB-005 depends_on: WS-WB-001, WS-WB-003. WS-WB-006 depends_on: WS-WB-001, WS-WB-003, WS-WB-005. Remove parallel claim for WS-WB-002 + WS-WB-005.
- Tradeoff: Reduces parallelism (WS-WB-005 must wait for WS-WB-002 + WS-WB-003 chain). Execution becomes more serial.
- Effort: Small (WP text edits)

**C. Eject** -- Let WS-WB-005 create work_binder.py if it doesn't exist
- Action: WS-WB-005 creates a minimal router file if not present; WS-WB-003 extends it.
- Tradeoff: File ownership ambiguity; merge complexity if parallelized
- Effort: Minimal (implementation-time decision)

**Recommendation: A** -- Split the API route out of WS-WB-005. The edition service is pure business logic that doesn't need an API endpoint to be useful. The history endpoint can be added in WS-WB-006 (which runs after WS-WB-003 in all orderings). This preserves parallelism between WS-WB-002 and WS-WB-005.

---

### Finding 5: WorkBinder.jsx / WorkBinder/ Naming Conflict

**Severity:** LOW
**Phase:** 1.1 (File References) + 2.6 (Blast Radius)
**Description:** WS-WB-007 creates components in `spa/src/components/WorkBinder/` (directory). An existing file `spa/src/components/WorkBinder.jsx` (14KB, active) already exists at the same path prefix. On Linux, a file and directory with the same base name can coexist, but:

1. Import resolution: `import WorkBinder from './WorkBinder'` resolves to the `.jsx` file, not the directory's `index.jsx`
2. The existing `WorkBinder.jsx` is imported by `ContentPanel.jsx:15` and actively rendered
3. If the WS intends to replace the file with a directory, `WorkBinder.jsx` must be deleted/moved, but it's not in WS-WB-007's allowed_paths

**Evidence:**
- `spa/src/components/WorkBinder.jsx` -- 14KB, active file
- `spa/src/components/ContentPanel.jsx:15` -- `import WorkBinder from './WorkBinder'`
- WS-WB-007 allowed_paths: `spa/src/components/WorkBinder/` (directory)
- WS-WB-007 allowed_paths does NOT include: `spa/src/components/WorkBinder.jsx` or `spa/src/components/ContentPanel.jsx`

**Resolution Options:**

**A. Quick Fix** -- Add `WorkBinder.jsx` and `ContentPanel.jsx` to WS-WB-007 allowed_paths
- Action: Expand allowed_paths to include both files. WS-WB-007 deletes or renames the old file and rewires ContentPanel imports.
- Tradeoff: None -- these files are directly in scope of the WB screen work
- Effort: Minimal (2 lines in WP)

**B. Correct Fix** -- Same as A, with explicit migration step in WS-WB-007 procedure
- Action: Add "Step 1: Migrate existing WorkBinder.jsx content to WorkBinder/index.jsx, update imports" as first procedure step
- Tradeoff: None
- Effort: Minimal

**C. Eject** -- Keep WorkBinder.jsx, create directory as WorkBinderV2/
- Action: New components go in `WorkBinderV2/`, old file retained
- Tradeoff: Naming inconsistency; two WorkBinder concepts coexist temporarily
- Effort: Minimal

**Recommendation: A** -- Add both files to allowed_paths. The WB screen replacement is the core purpose of WS-WB-007; the existing file is the thing being replaced.

---

### Finding 6: WP v1.1.0 Schema Missing additionalProperties

**Severity:** LOW
**Phase:** 2.5 (Invariant Contradictions)
**Description:** WS-WB-001 prohibited actions state: "Allowing `additionalProperties: true` on any new schema". The WPC schema correctly sets `additionalProperties: false`. However, the WP v1.1.0 and WS v1.1.0 schemas in the bundle do not set `additionalProperties: false`.

This is consistent with the existing v1.0.0 schemas (which also omit it), so the evolved schemas maintain the same pattern. The prohibition may have been intended only for the genuinely new WPC schema.

**Evidence:**
- WP-WB-001.md:134 -- "Allowing `additionalProperties: true` on any new schema" is prohibited
- WP-WB-001-schemas.json: WPC has `"additionalProperties": false` (line 216)
- WP-WB-001-schemas.json: WP v1.1.0 has no `additionalProperties` key
- WP-WB-001-schemas.json: WS v1.1.0 has no `additionalProperties` key
- Existing v1.0.0 schemas also omit `additionalProperties`

**Resolution Options:**

**A. Quick Fix** -- Clarify prohibition applies to new doc types only
- Action: Rephrase to "Allowing `additionalProperties: true` on the work_package_candidate schema"
- Tradeoff: Clear intent; evolved schemas remain backward-compatible
- Effort: Minimal

**B. Correct Fix** -- Add `additionalProperties: false` to all three schemas
- Action: Add the constraint to WP v1.1.0, WS v1.1.0, and WPC v1.0.0
- Tradeoff: May break existing documents if they have extra fields from handler transforms or legacy data
- Effort: Small (requires audit of existing document content)

**C. Eject** -- Accept current state
- Action: Leave as-is; note that `additionalProperties` is intentionally omitted on evolved schemas for backward compat
- Effort: Minimal

**Recommendation: A** -- Clarify the prohibition language. Adding `additionalProperties: false` to evolved schemas risks breaking existing documents. The prohibition should target genuinely new schemas only.

---

## Summary

**Verdict:** READY WITH CONDITIONS

**Blocking issues (must resolve before execution):**
- **Finding 1 (HIGH):** Add `app/api/v1/routers/__init__.py` and `app/api/v1/__init__.py` to WS-WB-003 allowed_paths
- **Finding 2 (HIGH):** Either add WS-WB-009 for LLM-assisted WS proposal OR move "Propose Work Statements" to out-of-scope

**Conditions (resolve during execution or before affected WS):**
- **Finding 3 (MEDIUM):** Add `if/then` clause to WP v1.1.0 schema for ta_version_id/ws_index invariant (before WS-WB-001 execution)
- **Finding 4 (MEDIUM):** Remove `work_binder.py` from WS-WB-005 allowed_paths; defer history endpoint to WS-WB-006 (or add WS-WB-003 dependency)

**Accepted risks (tracked as debt):**
- **Finding 5 (LOW):** Add `WorkBinder.jsx` and `ContentPanel.jsx` to WS-WB-007 allowed_paths
- **Finding 6 (LOW):** Clarify `additionalProperties` prohibition applies to new doc types only
