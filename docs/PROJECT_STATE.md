# PROJECT_STATE.md

Last Updated: 2026-01-20

## Current Status

**Phase:** Intake workflow complete, raw SQL tech debt eliminated
**Test Suite:** 1,603 tests passing
**Deployment:** Production on AWS ECS Fargate (thecombine.ai:8000)
**Dev Environment:** Linux/WSL (~/dev/TheCombine)

## Recent Work

### 2026-01-20: Raw SQL Tech Debt Elimination

**Project Model Complete Alignment**
- Added 6 missing columns: owner_id, organization_id, icon, archived_at, archived_by, archived_reason
- Model now fully aligned with database schema
- `to_dict()` includes all fields including archive state

**Raw SQL to ORM Conversion (Complete)**
- `project_routes.py`: 10 queries converted to ORM
- `document_routes.py`: 2 queries converted to ORM
- `archive.py`: 1 query converted to ORM (with lazy import for circular dep)
- `intake_workflow_routes.py`: Project creation uses ORM
- Zero raw SQL remaining in project/document routes

**Test Updates**
- 14 new behavior tests for Project model
- All mock patterns updated for ORM (scalar_one_or_none, first())
- `test_concierge_intake_plan.py` rewritten for v1.2.0 schema
- `test_intake_workflow_bff.py` updated for async completion context

### 2026-01-19: Intake Workflow Auto-Project Creation

**Intake Workflow**
- Project ID format: hyphenated `{INITIALS}-{NUMBER}` (e.g., LIR-001)
- Auto-creates Project on workflow completion via ORM
- Ownership set correctly (owner_id, organization_id, created_by)

## Active Work Items

None - intake flow complete, tech debt resolved.

## Next Steps

1. Test full intake -> project -> document flow end-to-end in production
2. PM Discovery document workflow

## Architecture Snapshot

- **Document-centric model** with render manifests and canonical components
- **Intake workflow v1.2.0** auto-completes on QA pass, creates projects
- **Project model** fully aligned with database schema
- **Zero raw SQL** in project/document routes - all ORM