# WS-CLEANUP-001: Debug Logging Cleanup

## Status: Draft

## Governing References

- Codex Code Review (2026-03-27) — Low finding: debug logging residue

## Verification Mode: A

## Allowed Paths

- spa/src/hooks/
- spa/src/components/
- app/api/services/email_service.py
- app/domain/registry/loader.py
- app/domain/workflow/registry.py
- app/domain/workflow/gates/
- tests/

---

## Objective

Remove debug `console.log` and `print()` residue from production code. Replace with proper `logger` calls where logging is still warranted, or remove entirely where it was debug-only.

---

## Preconditions

- 4857 tests passing
- SPA build passing

---

## Scope

### In Scope

1. Remove all debug `console.log` calls from SPA hooks and components:
   - `spa/src/hooks/useProductionStatus.js` (15 console.log calls — SSE event tracing)
   - `spa/src/components/Floor.jsx` (3 console.log calls — production start/cancel/submit)
   - `spa/src/hooks/useConciergeIntake.js` (3 console.log calls — intake events)
   - `spa/src/hooks/useFloorSSE.js` (2 console.log calls — SSE connect/reconnect)
   - `spa/src/components/FullDocumentViewer.jsx` (1 console.log — render model fallback)
   - `spa/src/components/DocumentViewer.jsx` (1 console.log — render model fallback)
   - `spa/src/components/admin/AdminWorkbench.jsx` (1 console.log — commit hash)

2. Remove debug `print()` calls from Python backend:
   - `app/domain/workflow/registry.py` line 40 — `print(wf_id)` debug output
   - `app/domain/workflow/gates/clarification.py` line 60 — `print(f"{q.id}: {q.text}")`
   - `app/domain/workflow/gates/qa.py` line 34 — `print(f"{finding.severity}: {finding.message}")`

3. Replace `print()` with `logger` where logging is still warranted:
   - `app/domain/registry/loader.py` line 412 — `print(f"Seeded {count} document types")` in CLI entry point → use `logger.info`

### Out of Scope

- `app/api/services/email_service.py` `_send_via_console()` method — these prints are intentional (console email backend for dev). Leave as-is.
- Adding new logging infrastructure
- Changing log levels or formats

---

## Prohibited Actions

- Do not add new logging frameworks or dependencies
- Do not change application behavior — only remove/replace debug output
- Do not modify email_service.py console backend prints

---

## Procedure

### Phase 1: Remove JavaScript console.log

1. Remove all `console.log` calls from `spa/src/hooks/useProductionStatus.js`
2. Remove all `console.log` calls from `spa/src/components/Floor.jsx`
3. Remove all `console.log` calls from `spa/src/hooks/useConciergeIntake.js`
4. Remove all `console.log` calls from `spa/src/hooks/useFloorSSE.js`
5. Remove the `console.log` from `spa/src/components/FullDocumentViewer.jsx`
6. Remove the `console.log` from `spa/src/components/DocumentViewer.jsx`
7. Remove the `console.log` from `spa/src/components/admin/AdminWorkbench.jsx`

### Phase 2: Remove/Replace Python print()

8. Remove `print(wf_id)` from `app/domain/workflow/registry.py`
9. Remove `print(f"{q.id}: {q.text}")` from `app/domain/workflow/gates/clarification.py`
10. Remove `print(f"{finding.severity}: {finding.message}")` from `app/domain/workflow/gates/qa.py`
11. Replace `print(f"Seeded {count} document types")` with `logger.info(f"Seeded {count} document types")` in `app/domain/registry/loader.py`, adding a logger import if not already present.

### Phase 3: Verify

12. Run `cd spa && npm run build` — must succeed
13. Run `python -m pytest tests/ -x -q` — all tests must pass
14. Run Tier 0

---

## Verification Checklist

- [ ] Zero `console.log` calls remain in listed SPA files
- [ ] Zero debug `print()` calls remain in listed Python files
- [ ] email_service.py console backend prints are untouched
- [ ] SPA build succeeds
- [ ] All tests pass
- [ ] Tier 0 passes

## Definition of Done

All debug logging residue removed from production code. No behavioral changes. All tests and SPA build pass.
