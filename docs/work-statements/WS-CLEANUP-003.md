# WS-CLEANUP-003: Domain/API Boundary — Mechanical Operations Protocol Extraction

## Status: Draft

## Governing References

- Codex Code Review (2026-03-27) — High finding: domain/API boundary leakage
- POL-ARCH-001

## Verification Mode: A

## Allowed Paths

- app/domain/workflow/
- app/api/services/mechanical_ops_service.py
- app/api/services/mech_handlers/
- tests/

---

## Objective

Invert the dependency between domain workflow code and API-layer mechanical operations services. Domain code (`plan_executor.py`, `intake_gate_profile.py`) currently imports `MechanicalOpsService` and `execute_operation` directly from `app.api.services`. This violates the architectural boundary (domain must not depend on API layer).

Fix: Define domain-level protocols, inject implementations via constructor, eliminate all `app.api.services` imports from `app/domain/workflow/`.

---

## Preconditions

- 4857 tests passing
- Domain already uses Protocol pattern for `StatePersistence`, `LLMService`, `PromptLoader`, `DocumentStore`

---

## Scope

### In Scope

1. Create `app/domain/workflow/operations.py` with domain-level protocols:
   - `OperationProvider` protocol (replaces direct `MechanicalOpsService` usage)
   - `OperationExecutor` protocol (replaces direct `execute_operation` calls)
   - `OperationResult` dataclass (domain-owned result type)

2. Update `app/domain/workflow/plan_executor.py`:
   - Accept `OperationProvider` and `OperationExecutor` via constructor
   - Replace all lazy imports of `MechanicalOpsService` and `execute_operation`
   - Replace `apply_exclusion_filter` import with injected executor or inline domain function

3. Update `app/domain/workflow/nodes/intake_gate_profile.py`:
   - Accept `OperationProvider` and `OperationExecutor` via constructor/params
   - Replace all imports from `app.api.services`

4. Create adapter implementations in `app/api/services/` that wrap existing classes to satisfy the domain protocols

5. Update all call sites that construct `PlanExecutor` and intake gate profile nodes to inject the adapters

### Out of Scope

- Moving `MechanicalOpsService` or `mech_handlers` themselves — they stay in `app/api/services/`
- Registry service protocols (`DocumentDefinitionService`, `ComponentRegistryService`, `SchemaRegistryService`) — separate WS
- Data model imports (`app.api.models.*`) — separate concern, lower priority
- Refactoring mech_handlers internals

---

## Prohibited Actions

- Do not move or rename `MechanicalOpsService` or `mech_handlers`
- Do not change mechanical operation behavior
- Do not modify the API-layer service implementations (only add adapter wrappers)
- Do not address data model imports (`app.api.models.*`) — out of scope

---

## Procedure

### Phase 1: Define Domain Protocols

1. Create `app/domain/workflow/operations.py`:
   - `OperationResult` dataclass with fields: `success: bool`, `output: Optional[Dict]`, `error: Optional[str]`, `outcome: str`
   - `OperationProvider` protocol with methods: `get_operation(op_id, version=None)`, `get_operation_by_ref(op_ref)`
   - `OperationExecutor` protocol with method: `execute(operation, inputs) -> OperationResult`

### Phase 2: Create Adapters

2. Create adapter class(es) in `app/api/services/mechanical_ops_adapter.py` that wrap `MechanicalOpsService` and `execute_operation` to satisfy the domain protocols

### Phase 3: Update Domain Code

3. Update `PlanExecutor.__init__` to accept `operation_provider: OperationProvider` and `operation_executor: OperationExecutor`
4. Replace all lazy imports in `plan_executor.py`:
   - Lines using `MechanicalOpsService()` → use `self._operation_provider`
   - Lines using `execute_operation(...)` → use `self._operation_executor.execute(...)`
   - Line using `apply_exclusion_filter(...)` → use executor or extract to domain utility
5. Update `intake_gate_profile.py` similarly — accept protocols, replace imports
6. Verify zero imports from `app.api.services` remain in `app/domain/workflow/`

### Phase 4: Wire Injection

7. Find all call sites that construct `PlanExecutor` (likely in routers or service layer)
8. Inject the adapter implementations at construction time

### Phase 5: Verify

9. Run `python -m pytest tests/ -x -q` — all tests must pass
10. Grep `app/domain/workflow/` for `from app.api.services` — must return zero results (excluding `app.api.models` which is out of scope)
11. Run Tier 0

---

## Verification Checklist

- [ ] `app/domain/workflow/operations.py` exists with protocols and result dataclass
- [ ] Adapter implementation exists in `app/api/services/`
- [ ] `plan_executor.py` has zero imports from `app.api.services`
- [ ] `intake_gate_profile.py` has zero imports from `app.api.services`
- [ ] All `PlanExecutor` construction sites inject adapters
- [ ] All tests pass
- [ ] Tier 0 passes

## Definition of Done

Domain workflow code depends only on domain-level protocols for mechanical operations. API-layer adapters satisfy those protocols. No `app.api.services` imports remain in `app/domain/workflow/`. All tests pass.
