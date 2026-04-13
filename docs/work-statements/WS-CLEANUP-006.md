# WS-CLEANUP-006: Broader Domain/API Boundary Cleanup

## Status: Draft

## Governing References

- Codex Code Review (2026-03-27) — Remaining finding: broader domain/API coupling outside `app/domain/workflow/`
- POL-ARCH-001

## Verification Mode: A

## Allowed Paths

- app/domain/
- app/tasks/
- app/api/services/
- app/api/models/
- tests/

---

## Objective

Reduce remaining architectural leakage where domain and task-layer code still imports `app.api.services.*` and `app.api.models.*` outside the already-cleaned `app/domain/workflow/` slice.

This WS does **not** require a full persistence-model rewrite. It focuses on the highest-value seams:

1. Remove `app.api.services.*` imports from domain/task modules by introducing domain-owned protocols and API-layer adapters.
2. Isolate unavoidable ORM usage behind repository or persistence adapters where feasible.
3. Eliminate the most obvious API-layer service dependencies in:
   - `app/domain/services/document_builder.py`
   - `app/domain/services/prompt_assembler.py`
   - `app/domain/services/render_model_builder.py`
   - `app/tasks/document_builder.py`

---

## Preconditions

- 4843 tests passing
- WS-CLEANUP-003 completed
- `app/domain/workflow/` has zero imports from `app.api.services` and `app.api.v1`
- Existing decomposition work (WS-CLEANUP-004 / 005) merged and green

---

## Scope

### In Scope

#### 1. Domain service protocol extraction

Create domain-owned protocols for the following responsibilities:

- Document persistence / document CRUD
- Document definition lookup
- Component registry lookup
- Schema registry lookup
- Prompt loading where domain code currently depends on API services

Place protocols in focused domain modules such as:

- `app/domain/services/document_ports.py`
- `app/domain/services/render_ports.py`

Exact filenames may vary if a better grouping is clearer.

#### 2. API adapter implementations

Create API-layer adapter classes that satisfy the new domain protocols while wrapping existing services:

- `DocumentService`
- `DocumentDefinitionService`
- `ComponentRegistryService`
- `SchemaRegistryService`
- Any prompt-loading service still imported by domain/task code

Adapters remain in `app/api/services/`.

#### 3. Domain/task call-site cleanup

Update the following modules to depend on domain-level protocols instead of API services directly:

- `app/domain/services/document_builder.py`
- `app/domain/services/prompt_assembler.py`
- `app/domain/services/render_model_builder.py`
- `app/tasks/document_builder.py`

#### 4. Import-boundary verification

After refactor, the following should be true:

- Zero `app.api.services.*` imports remain in `app/domain/services/` for the in-scope modules
- Zero `app.api.services.*` imports remain in `app/tasks/document_builder.py`

### Out of Scope

- Eliminating all `app.api.models.*` imports across the entire domain layer
- Full ORM/domain separation for every repository
- Rewriting SQLAlchemy model ownership
- Refactoring unrelated repositories that already legitimately act as persistence adapters
- Behavior changes to document building, render-model generation, prompt assembly, or task execution

---

## Prohibited Actions

- Do not change business logic or API behavior
- Do not rename public API endpoints or request/response schemas
- Do not move SQLAlchemy models out of `app/api/models/`
- Do not attempt a repo-wide purity pass on every `app.api.models.*` import in this WS
- Do not refactor unrelated modules just because they also import API-layer code

---

## Procedure

### Phase 1: Inventory and target the service imports

1. Grep `app/domain/services/` and `app/tasks/` for `from app.api.services`
2. Confirm the concrete in-scope import sites and group them by responsibility:
   - document persistence
   - document-definition lookup
   - component/schema lookup
   - prompt loading

### Phase 2: Define domain ports

3. Create domain-owned protocol modules for the required responsibilities
4. Keep the interfaces narrow: only methods actually needed by current call sites
5. Add small domain-owned result/value types only where necessary

### Phase 3: Implement API adapters

6. Create adapter classes/functions in `app/api/services/` that wrap existing services and satisfy the new protocols
7. Preserve all current behavior
8. Avoid creating adapters with extra methods “just in case”

### Phase 4: Rewire domain and task modules

9. Update `document_builder.py` to accept protocol dependencies instead of direct API services
10. Update `prompt_assembler.py` similarly
11. Update `render_model_builder.py` similarly
12. Update `app/tasks/document_builder.py` similarly
13. Update construction sites to inject the adapters

### Phase 5: Verify

14. Run `python -m pytest tests/ -x -q`
15. Grep for `from app.api.services` in the in-scope modules — must return zero
16. Run Tier 0

---

## Verification Checklist

- [ ] Domain-owned protocols exist for each in-scope dependency seam
- [ ] API-layer adapters exist and wrap the existing service implementations
- [ ] `app/domain/services/document_builder.py` has zero `app.api.services` imports
- [ ] `app/domain/services/prompt_assembler.py` has zero `app.api.services` imports
- [ ] `app/domain/services/render_model_builder.py` has zero `app.api.services` imports
- [ ] `app/tasks/document_builder.py` has zero `app.api.services` imports
- [ ] No behavior changes observed
- [ ] All tests pass
- [ ] Tier 0 passes

## Definition of Done

The highest-value remaining domain/task service-boundary leaks are removed. In-scope domain and task modules depend on domain-owned protocols, with API-layer adapters satisfying those protocols. All tests pass and behavior is unchanged.
