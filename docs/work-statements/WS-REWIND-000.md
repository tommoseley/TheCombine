# WS-REWIND-000 — Do No Harm Audit: Document Versioning Assumptions

**Status:** Draft
**Parent WP:** WP-REWIND-001
**Governing ADR:** ADR-063

## Objective

Inventory all code paths that assume single-document-per-type and classify the migration complexity for versioned document storage. This audit determines whether WP-REWIND-002 is a contained migration or a deeper document-model refactor.

## Scope

### In Scope
- Identify all unique constraints on the documents table
- Inventory every query/service that uses `is_latest == True` or `scalar_one_or_none()`
- Identify stabilization/promotion flows coupled to single-document assumption
- Classify each finding by blast radius (LOW/MEDIUM/HIGH)
- Produce written audit report with file paths and line numbers

### Out of Scope
- Fixing any of the identified issues
- Schema migration design
- Code changes of any kind

## Procedure

### Step 1: Database constraints
- Read `app/api/models/document.py` for table definition and constraints
- Read alembic migrations for partial unique indexes on `is_latest`
- Document all unique constraints that enforce single-document-per-type

### Step 2: Repository layer
- Search `app/persistence/` for `get_by_scope_type`, `scalar_one_or_none`, `is_latest`
- For each occurrence, classify: does it assume at most one result?

### Step 3: Service layer
- Search `app/api/services/document_service.py` and `app/domain/services/` for document queries
- Identify `get_latest()` and all callers
- Identify `create_document()` versioning logic

### Step 4: API layer
- Search `app/api/v1/routers/` for `is_latest == True` and `scalar_one_or_none`
- Count and list all endpoints affected

### Step 5: Workflow layer
- Search `app/domain/workflow/plan_executor.py` for document creation
- Identify hardcoded `version=1` and `is_latest=True`
- Check child document upsert logic

### Step 6: Stabilization
- Identify where stabilization state is tracked
- Determine if stabilization is per-document or per-version

### Step 7: Binder renderer
- Check how `render_pure.py` and binder routers collect documents
- Determine version selection behavior

### Step 8: Produce audit report
- Write findings to `docs/audits/YYYY-MM-DD-rewind-do-no-harm.md`
- Include blast radius summary table
- Include key architectural decisions needed
- Include existing infrastructure that helps

## Verification Criteria
- Audit report exists with all sections populated
- Every `is_latest` usage is catalogued with file/line
- Blast radius classified for each component
- Architectural decisions explicitly listed (not answered — just listed)

## Allowed Paths
- docs/audits/ (write report)
- All source files (read only)

## Prohibited Actions
- Do not modify any source files
- Do not create migrations
- Do not make architectural decisions — only surface them
