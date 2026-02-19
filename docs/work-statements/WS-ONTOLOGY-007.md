# WS-ONTOLOGY-007: Production Floor UI -- WP ? WS Hierarchy

## Status: Accepted

## Parent Work Package: WP-ONTOLOGY-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline Integration for WP/WS

## Verification Mode: A

---

## Objective

Replace Epic nodes in the Production Floor with Work Package nodes. Show WP state, progress, dependencies, and Mode B health. Expanding a WP shows child Work Statements with status and verification mode indicators. No Epic UI elements remain.

---

## Preconditions

- WS-ONTOLOGY-001 complete (Work Package document type exists)
- WS-ONTOLOGY-002 complete (Work Statement document type exists with parent enforcement)
- WS-ONTOLOGY-006 complete (Epic pipeline removed)
- WP and WS API endpoints available for Production Floor to query
- Tier 0 harness operational

---

## Scope

### Includes

- Production Floor renders Work Package nodes instead of Epic nodes
- WP node displays: state badge, dependency count, progress (ws_done/ws_total), Mode B count
- Expanding WP node shows child WS list
- WS child items display: title/id, status, Mode A/B indicator, last updated timestamp
- No Epic UI elements remain anywhere in Production Floor
- Regression guard test

### Excludes

- Project Logbook rendering in Production Floor (future WS)
- WP/WS creation UI (WPs and WSs are created via API or document pipeline, not via Production Floor)
- Advanced WP dependency graph visualization
- Drag-and-drop WS reordering

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **WP nodes rendered**: Production Floor API returns Work Package data for a project; UI renders WP nodes with title and state badge
2. **WP progress displayed**: Each WP node shows `ws_done/ws_total` progress indicator
3. **WP Mode B count displayed**: Each WP node shows Mode B count (may be zero)
4. **WP dependency count displayed**: Each WP node shows count of upstream dependencies
5. **WS children rendered on expand**: Expanding a WP node shows child WS list with:
   - WS title or ID
   - Status (DRAFT / READY / IN_PROGRESS / ACCEPTED / REJECTED / BLOCKED)
   - Verification mode indicator (A or B)
   - Last updated timestamp
6. **No Epic UI elements**: No Production Floor component renders Epic nodes, Epic labels, or Epic-specific UI
7. **Regression guard**: A test confirms no React components in `spa/src/` reference "Epic" as a document type or node type (excluding comments and historical references)

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting all seven Tier 1 criteria. Verify all tests fail.

Test approach: Use route-level or component rendering tests consistent with the existing SPA test pattern. If no React test harness exists (Mode B debt from WS-ADMIN-EXEC-UI-001), use API integration tests for data shape and grep-based tests for UI regression guards.

### Phase 2: Implement

1. Update Production Floor data transformer to produce WP nodes instead of Epic nodes
2. Create or update WP node component:
   - State badge (PLANNED / READY / IN_PROGRESS / AWAITING_GATE / DONE)
   - Progress bar or count (ws_done/ws_total)
   - Mode B count badge
   - Dependency count
3. Create WS child list component (rendered on WP expand):
   - WS title/id
   - Status badge
   - Mode A/B indicator
   - Last updated timestamp
4. Remove all Epic node rendering code
5. Update any Production Floor API calls to fetch WP/WS data instead of Epic data
6. Update Production Floor navigation and routing if affected

### Phase 3: Verify

1. All Tier 1 tests pass
2. Run Tier 0 harness with `--frontend` flag -- must return zero (SPA files touched)

---

## Prohibited Actions

- Do not add WP/WS creation UI in Production Floor (out of scope)
- Do not implement WP dependency graph visualization (future scope)
- Do not modify WP or WS document types or schemas
- Do not modify backend API endpoints (consume existing ones)
- Do not retain any Epic rendering code "just in case"

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] Production Floor renders WP nodes with state, progress, Mode B count, dependencies
- [ ] Expanding WP shows child WS list with status and verification mode
- [ ] No Epic UI elements remain
- [ ] Regression guard passes (no Epic type references in SPA components)
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero (with --frontend flag)

---

_End of WS-ONTOLOGY-007_
