# ADR-046: POW Instance Storage and Runtime Binding

**Status:** Accepted
**Created:** 2026-02-04
**Supersedes:** None
**Related:** ADR-045 (System Ontology), ADR-044 (Admin Workbench), ADR-027 (Workflow Definition)

---

## Context

ADR-045 establishes the system ontology for configuration artifacts: Primitives (Prompt Fragment, Schema), Composites (Role, Task, DCW, POW). WS-ADR-045-002 introduces POW classification (`reference`, `template`, `instance`) and derivation lineage.

Reference and template POWs live in `combine-config/workflows/` -- they are governed, versioned, Git-canonical configuration. But **instance POWs** are fundamentally different:

- They are **project-scoped** -- each project has its own workflow instance
- They **drift** from their source template over time (steps added, removed, reordered)
- They are **runtime data** -- they change as a project progresses
- They must be **auditable** -- the history of what workflow a project followed matters

Instance POWs cannot live in `combine-config/` because:
1. That repository is governed configuration, not project state
2. Hundreds of project instances would pollute the config namespace
3. Instance changes don't go through the workspace/commit/release cycle
4. Instances may contain project-specific data (customer names, dates, custom steps)

This ADR defines where instance POWs live and how they relate to their source templates.

---

## Decision

### Instance POWs are stored in the database as project-scoped runtime data.

When a project is created (or a workflow is assigned to an existing project), an **instance** is created by:

1. Copying the full definition from the source template (or reference) POW
2. Recording the source reference (`base_workflow_ref`)
3. Storing the snapshot as the project's `effective_workflow`

The instance is then mutable within the project context. Changes to the instance do not affect the source template or reference.

### Data Model

```
WorkflowInstance
  id: UUID
  project_id: UUID (FK -> projects)
  base_workflow_ref: { workflow_id, version, pow_class }
  effective_workflow: JSON (full definition snapshot)
  created_at: datetime
  updated_at: datetime
  status: active | completed | archived

WorkflowInstanceHistory (append-only)
  id: UUID
  instance_id: UUID (FK -> WorkflowInstance)
  change_type: created | step_added | step_removed | step_reordered | metadata_changed
  change_detail: JSON
  changed_at: datetime
  changed_by: string (user or system)
```

### Drift Tracking

Drift is **computed, not stored**. Given an instance's `effective_workflow` and `base_workflow_ref`, the system can compute:

- Steps added (not in source)
- Steps removed (in source but not instance)
- Steps reordered
- Metadata changes

This is a read-time operation, not a write-time one. No `drift_summary` column is needed.

### Governance Boundary

| Artifact | Storage | Mutability | Governance |
|----------|---------|------------|------------|
| Reference POW | `combine-config/workflows/` | Versioned releases | Full (workspace, commit, review) |
| Template POW | `combine-config/workflows/` | Versioned releases | Full (workspace, commit, review) |
| Instance POW | Database (`workflow_instances`) | Mutable per project | Audit trail only |

### API Surface

- `POST /api/v1/projects/{id}/workflow` -- Create instance from template/reference
- `GET /api/v1/projects/{id}/workflow` -- Get current effective workflow
- `PUT /api/v1/projects/{id}/workflow` -- Update instance (step changes)
- `GET /api/v1/projects/{id}/workflow/drift` -- Compute drift from source
- `GET /api/v1/projects/{id}/workflow/history` -- Audit trail

### What This Does NOT Cover

- Syncing instances with updated templates ("upgrade path")
- AI-assisted drift detection or consolidation
- Cross-project workflow analytics
- Tag normalization or search infrastructure

These are future enhancements that build on this foundation.

---

## Consequences

### Positive

- Clean governance boundary: config repo stays clean, instances are runtime data
- Project-scoped mutability without polluting the governed config namespace
- Full audit trail of instance changes
- Drift is computable without storing redundant data
- Forward-compatible with upgrade paths (instance knows its source)

### Negative

- Two storage locations for "the same kind of thing" (POW) -- requires clear mental model
- Instance editing UI is distinct from config editing UI (no workspace/commit flow)
- Initial implementation requires DB migration, new repository, new service layer

### Risks

- If the `effective_workflow` snapshot is too large, we may need a delta model instead of full copy
- Without upgrade tooling, instances will silently diverge from improved templates over time

---

## Implementation

Implementation requires a Work Statement (WS-ADR-046-001) covering:

1. Database migration (WorkflowInstance, WorkflowInstanceHistory tables)
2. Domain model and repository
3. Service layer (create, update, drift computation)
4. API endpoints
5. Frontend: instance creation flow, instance editor, drift view
6. Integration with project lifecycle

Estimated scope: multi-commit, significant.

---

*End of ADR-046*
