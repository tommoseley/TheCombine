# WP-REGISTRY-001: Registry Integrity & Audit Remediation

## Status: Draft

## Governing References

- ADR-010 -- LLM Execution Logging
- ADR-053 -- Planning Before Architecture in Software Product Development
- Audit: `docs/audits/2026-02-26-audit-summary.md`
- Parent WSs: WS-PIPELINE-001, WS-PIPELINE-003 (adopted under this WP)

---

## Intent

The 2026-02-26 codebase audit revealed governance drift: artifacts declared in one layer but absent in another, orphaned pipeline and epic-layer remnants, and document types that exist in code but not in governed config (or vice versa).

This WP establishes a single invariant: **every document type in `active_releases` must have all declared assets resolvable from canonical global paths, verified by deterministic gates.** Then it cleans up everything that violates that invariant.

This is both a runtime safety correction (missing assets = runtime failure) and an ontology correction (half-governed artifacts = governance fiction).

---

## Corrected Invariant

For every `doc_type` in `active_releases`:
1. Global task prompt exists at `combine-config/prompts/tasks/{doc_type}/`
2. Global schema exists at `combine-config/schemas/{doc_type}/`
3. Schema parses successfully
4. Handler is registered (or `creation_mode` explicitly excludes handler)

Missing asset = deterministic **HARD_STOP**. No fallback to package-local artifacts for active releases.

---

## Scope In

- Create canonical global task prompt and schema directories for `work_package` and `work_statement`
- Populate from current authoritative versions (normalization only, no semantic rewrites)
- Update loader/resolution logic: active releases resolve from global canonical paths only
- Tier-0 integrity gate: missing asset = HARD_STOP
- Tier-1 tests: resolution succeeds, no fallback path used
- Collapse IPP/IPF into single IP (via WS-PIPELINE-001)
- Remove epic-layer artifacts (via WS-PIPELINE-003)
- Resolve `story_backlog`: fully govern or fully retire
- Remove backup files identified by audit
- Reduce unused imports via automated tooling (`ruff --fix`)

## Scope Out

- No semantic redesign of WP/WS schemas or prompts beyond canonicalization
- No multi-tenant fields (`tenant_id`) or multi-tenant refactors
- No Prometheus/OpenMetrics integration
- No new UI features
- SPA hardcoded hex colors (separate concern, separate WP)

---

## Definition of Done

1. Canonical global paths exist and are populated for all active doc_types
2. Tier-0 integrity gate verifies all active doc_types have required global assets
3. Missing asset causes deterministic HARD_STOP (no silent fallback)
4. `work_package` and `work_statement` load task + schema from global paths (proven by Tier-1 tests)
5. IPP/IPF split artifacts retired, no orphan references remain
6. Epic-layer artifacts removed, no orphan references remain
7. `story_backlog` is either fully governed or fully retired (no half-state)
8. Backup files removed or moved to `recycle/`
9. Unused import count materially reduced
10. Full test suite passes
11. Each downstream WS includes Audit Mapping section linking findings to remediation

---

## Work Statements (Execution Order)

### Phase 1: Build the Fence

**WS-REGISTRY-001** -- Canonical Paths & Integrity Gate *(new)*
- Create `combine-config/prompts/tasks/work_package/` and `work_statement/`
- Create `combine-config/schemas/work_package/` and `work_statement/`
- Populate from current authoritative versions
- Update loader logic: no fallback to package-local for active releases
- Implement Tier-0 integrity gate (missing asset = HARD_STOP)
- Tier-1 tests: resolution succeeds, no fallback exercised
- **Must execute first.** All subsequent WSs rely on the gate to catch breakage.

### Phase 2: Sweep the Yard

These can execute in parallel after WS-REGISTRY-001.

**WS-PIPELINE-001** -- Pipeline Config & Doc Type Consolidation *(existing, adopted)*
- Collapse IPP+IPF into single IP in combine-config
- Fix POW step ordering (PD -> IP -> TA -> WP -> WS)
- Add `execution_mode` to POW steps
- Schema/prompt audit (document changes, flag prompt updates)
- Parent: WP-REGISTRY-001

**WS-PIPELINE-003** -- Epic/Feature/Story Removal *(existing, adopted)*
- Remove epic-layer artifacts, workflows, doc types
- File-by-file inventory (100+ entries)
- Clean `active_releases.json`
- Parent: WP-REGISTRY-001

**WS-REGISTRY-002** -- story_backlog Resolution *(new)*
- Audit current state: handler registered, service exists, no config backing
- Decision: govern (create active_releases entry + combine-config directory) or retire (remove handler + service)
- Execute the decision
- Verify Tier-0 gate passes after change

### Phase 3: Mechanical Cleanup

**WS-REGISTRY-003** -- Dead Code & Backup Removal *(new)*
- Remove `document_builder_backup.py`, `llm_execution_logger_original.py`
- Run `ruff check app/ --select F401,F841 --fix` for unused imports/variables
- Verify full test suite green
- **Executes last.** Depends on Phase 2 completing (code removals may eliminate some dead imports).

---

## Execution Dependency Graph

```
WS-REGISTRY-001 (gate)
    |
    +---> WS-PIPELINE-001 (IPP/IPF collapse)    \
    |                                              } parallel
    +---> WS-PIPELINE-003 (epic removal)          /
    |
    +---> WS-REGISTRY-002 (story_backlog)
    |
    v
WS-REGISTRY-003 (mechanical cleanup -- after all above)
```

---

## Audit Finding Mapping

| Audit # | Finding | Addressed By |
|---------|---------|--------------|
| 1 | Missing task prompt dirs (work_package, work_statement) | WS-REGISTRY-001 |
| 2 | Missing global schema dirs (work_package, work_statement) | WS-REGISTRY-001 |
| 3 | Missing packaged task prompts (backlog_item, plan_explanation) | WS-PIPELINE-003 |
| 4 | 119 unused imports in API layer | WS-REGISTRY-003 |
| 5 | Mech handlers untested (11 files) | Out of scope (test coverage WP) |
| 6 | 358 hardcoded hex colors | Out of scope (theme compliance WP) |
| 7 | Orphan primary_implementation_plan chain | WS-PIPELINE-001 |
| 8 | story_backlog not in governed config | WS-REGISTRY-002 |
| 9 | Handler test coverage 33% | Out of scope (test coverage WP) |
| 10 | Tier 2 nearly empty | Out of scope |
| 11 | SPA zero JS test infrastructure | Out of scope |
| 12 | 3 orphan workflow dirs | WS-PIPELINE-001 + WS-PIPELINE-003 |
| 13 | Backup files on disk | WS-REGISTRY-003 |
| 14 | Auth provider coverage 50% | Out of scope |
| 15 | Web/BFF routes 73% untested | Out of scope |
| 16 | Stale workflow version dirs | WS-PIPELINE-001 |
| 17 | SPA orphan components | Out of scope (SPA cleanup WP) |
| 18 | Unused SPA utilities | Out of scope |
| 19 | 211 unused Python imports | WS-REGISTRY-003 |

**Coverage:** 12 of 19 findings addressed. Remaining 7 are test coverage or SPA concerns requiring separate WPs.

---

## Tech Debt (Acknowledged)

| Item | Current Approach | Preferred Approach | When |
|------|------------------|--------------------|------|
| IP prompt content | Audit only in WS-PIPELINE-001 | Updated prompts reflecting merged scope | WS-PIPELINE-004 |
| Handler test coverage | Out of scope | Tier-1 tests for all 15 handlers | Test coverage WP |
| SPA hex colors | Out of scope | Theme variables + lint rule | Theme compliance WP |
| Mech handler tests | Out of scope | Tier-1 tests for 11 mech handlers | Test coverage WP |
| Fallback removal for non-WP/WS types | WP/WS only in this WP | All active doc_types from global paths | Follow-up WS |

---

_End of WP-REGISTRY-001_
