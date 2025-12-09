# PIPELINE-150: Baseline Implementation Summary

**Status:** Complete (Deployed)  
**Purpose:** Establish baseline for PIPELINE-175A/B refactor  
**Version:** 1.5  
**Date:** 2025-12-04

---

## Executive Summary

PIPELINE-150 delivered a working pipeline orchestration system with hardcoded role-specific execution methods. Pipeline advances through PM → Architect → BA → Dev → QA phases, with each phase producing validated artifacts stored in the database.

**Key Achievement:** Functional 5-phase pipeline with Pydantic artifact validation and state tracking.

**Limitation:** Hardcoded execution logic requires code changes to add roles or update prompts. PIPELINE-175A/B refactors this to data-driven configuration, enabling role addition via database inserts without code deployment.

**Success Metrics:** 20 integration tests passing, full pipeline execution in ~45 seconds, <10ms database operations.

---

## What Was Delivered

### Core Functionality

**Pipeline Orchestration:**
- Pipeline creation with unique pipeline_id and epic_id
- State management through 5 phases: pm_phase → arch_phase → ba_phase → dev_phase → qa_phase
- Automatic phase advancement via `advance_phase()` endpoint
- Phase transition tracking in database
- Error handling with retry logic

**Role Execution:**
- 5 hardcoded roles: PM, Architect, BA, Dev, QA
- Each role has dedicated execution method: `execute_pm_phase()`, `execute_architect_phase()`, etc.
- LLM integration via Anthropic Claude API (claude-sonnet-4-20250514)
- Hardcoded system prompts embedded in code
- JSON response parsing and validation

**Artifact Management:**
- Pydantic schemas for all artifact types: Epic, ArchNotes, BASpec, ProposedChangeSet, QAResult
- Schema validation before storage (ValidationError on failure)
- Artifact storage in database with pipeline_id foreign key
- Artifact retrieval by ID or pipeline_id
- Version tracking via created_at timestamps

**Database Persistence:**
- SQLite for development, PostgreSQL-ready via SQLAlchemy
- Tables: pipelines, artifacts, phase_transitions
- Foreign key constraints enforced
- Indexes on pipeline_id, artifact_type, created_at

### Key User Flow

1. **Pipeline Creation:**
   - POST /pipelines with `{"epic_id": "AUTH-100"}`
   - System creates pipeline record with status="active", current_phase="pm_phase"
   - Returns pipeline_id

2. **Phase Advancement:**
   - POST /pipelines/{id}/advance
   - System checks current_phase, routes to appropriate execute_X_phase() method
   - Role-specific logic executes (hardcoded prompt → LLM call → parse → validate → store)
   - Pipeline state updated to next phase
   - Phase transition logged

3. **Artifact Retrieval:**
   - GET /artifacts/{id} returns specific artifact with metadata
   - GET /pipelines/{id}/artifacts returns all artifacts for pipeline

4. **Complete Pipeline:**
   - User calls advance_phase() 5 times (once per phase)
   - Pipeline progresses: pm_phase → arch_phase → ba_phase → dev_phase → qa_phase → complete
   - 5 artifacts produced (Epic, ArchNotes, BASpec, ProposedChangeSet, QAResult)

### Acceptance Criteria Met

- ✅ Pipeline advances through all 5 phases without manual intervention (per phase)
- ✅ Each phase produces valid artifact matching Pydantic schema
- ✅ Artifacts stored in database with correct artifact_type
- ✅ State transitions tracked in phase_transitions table
- ✅ 20 integration tests passing (0 failures)
- ✅ API endpoints return consistent JSON responses
- ✅ Error handling returns 400/500 with clear messages
- ✅ Performance: Full pipeline <60 seconds (45s average)

---

## Current Code Structure

### File Organization

```
app/orchestrator_api/
├── services/
│   ├── pipeline_service.py         # ⚠️ WILL REFACTOR IN 175B
│   │   - PipelineService class
│   │   - advance_phase() method (hardcoded routing)
│   │   - execute_pm_phase() method (hardcoded PM logic)
│   │   - execute_architect_phase() method (hardcoded Architect logic)
│   │   - execute_ba_phase() method (hardcoded BA logic)
│   │   - execute_dev_phase() method (hardcoded Dev logic)
│   │   - execute_qa_phase() method (hardcoded QA logic)
│   │
│   ├── artifact_service.py         # ✅ KEEPING (no changes in 175A/B)
│   │   - ArtifactService class
│   │   - submit_artifact() method (validation + storage)
│   │   - get_artifact() method
│   │   - list_artifacts_for_pipeline() method
│   │
│   └── anthropic_service.py        # ✅ KEEPING (wraps LLM API calls)
│       - AnthropicService class
│       - call() method (async LLM invocation)
│       - Retry logic (exponential backoff)
│       - Token usage tracking
│
├── repositories/
│   ├── pipeline_repository.py      # ✅ KEEPING (extended in 175A)
│   │   - PipelineRepository class
│   │   - create() method
│   │   - get_by_id() method
│   │   - update_state() method
│   │   - list_all() method
│   │
│   ├── artifact_repository.py      # ✅ KEEPING (no changes)
│   │   - ArtifactRepository class
│   │   - create() method
│   │   - get_by_id() method
│   │   - list_by_pipeline() method
│   │
│   └── phase_transition_repository.py  # ✅ KEEPING (no changes)
│       - PhaseTransitionRepository class
│       - create() method (logs state transitions)
│       - list_by_pipeline() method
│
├── models/
│   ├── pipeline.py                 # ✅ KEEPING (no schema changes)
│   │   - Pipeline SQLAlchemy model
│   │   - Fields: pipeline_id, epic_id, current_phase, state, created_at, updated_at
│   │
│   ├── artifact.py                 # ✅ KEEPING (no schema changes)
│   │   - Artifact SQLAlchemy model
│   │   - Fields: artifact_id, pipeline_id, artifact_type, content (JSON), created_at
│   │
│   └── phase_transition.py         # ✅ KEEPING (no schema changes)
│       - PhaseTransition SQLAlchemy model
│       - Fields: id, pipeline_id, from_state, to_state, reason, transitioned_at
│
├── schemas/
│   └── artifacts.py                # ✅ KEEPING (no changes in 175A/B)
│       - EpicSchema (Pydantic)
│       - ArchNotesSchema (Pydantic)
│       - BASpecSchema (Pydantic)
│       - ProposedChangeSetSchema (Pydantic)
│       - QAResultSchema (Pydantic)
│
└── routers/
    └── pipelines.py                # ✅ KEEPING (no endpoint changes)
        - POST /pipelines (create)
        - GET /pipelines/{id} (retrieve)
        - POST /pipelines/{id}/advance (advance phase)
        - GET /pipelines/{id}/artifacts (list artifacts)
```

### Database Schema (PIPELINE-150)

```sql
-- Existing tables (KEPT in 175A/B)
CREATE TABLE pipelines (
    pipeline_id VARCHAR(64) PRIMARY KEY,
    epic_id VARCHAR(64) NOT NULL,
    current_phase VARCHAR(64) NOT NULL,
    state VARCHAR(32) NOT NULL,  -- active, complete, failed
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE artifacts (
    artifact_id VARCHAR(64) PRIMARY KEY,
    pipeline_id VARCHAR(64) NOT NULL REFERENCES pipelines(pipeline_id),
    artifact_type VARCHAR(64) NOT NULL,  -- epic, arch_notes, ba_spec, etc.
    content JSON NOT NULL,  -- Validated Pydantic schema
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE phase_transitions (
    id VARCHAR(64) PRIMARY KEY,
    pipeline_id VARCHAR(64) NOT NULL REFERENCES pipelines(pipeline_id),
    from_state VARCHAR(64) NOT NULL,
    to_state VARCHAR(64) NOT NULL,
    reason TEXT,
    transitioned_at TIMESTAMP NOT NULL
);

-- NEW tables in 175A (ADDED)
CREATE TABLE role_prompts (
    id VARCHAR(64) PRIMARY KEY,
    role_name VARCHAR(64) NOT NULL,
    version VARCHAR(16) NOT NULL,
    starting_prompt TEXT,
    bootstrapper TEXT NOT NULL,
    instructions TEXT NOT NULL,
    working_schema JSON,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    created_by VARCHAR(128),
    notes TEXT,
    UNIQUE (role_name, is_active) WHERE is_active = TRUE
);

CREATE TABLE phase_configurations (
    id VARCHAR(64) PRIMARY KEY,
    phase_name VARCHAR(64) NOT NULL UNIQUE,
    role_name VARCHAR(64) NOT NULL,
    artifact_type VARCHAR(64) NOT NULL,
    next_phase VARCHAR(64),  -- NULL = terminal phase
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    config JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE pipeline_prompt_usage (
    id VARCHAR(64) PRIMARY KEY,
    pipeline_id VARCHAR(64) NOT NULL REFERENCES pipelines(pipeline_id),
    prompt_id VARCHAR(64) NOT NULL REFERENCES role_prompts(id),
    role_name VARCHAR(64) NOT NULL,
    phase_name VARCHAR(64) NOT NULL,
    used_at TIMESTAMP NOT NULL
);
```

---

## Current Execution Flow

### Hardcoded Role-Specific Methods (PIPELINE-150)

**PipelineService.advance_phase() - Routing Logic:**

```python
# app/orchestrator_api/services/pipeline_service.py

class PipelineService:
    def __init__(self):
        self.pipeline_repo = PipelineRepository()
        self.artifact_service = ArtifactService()
        self.anthropic_service = AnthropicService()
        self.phase_transition_repo = PhaseTransitionRepository()
    
    async def advance_phase(self, pipeline_id: str) -> PhaseAdvancedResponse:
        """
        Advance pipeline to next phase (HARDCODED ROUTING).
        
        This is what PIPELINE-175B will refactor to use PhaseConfiguration.
        """
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        previous_phase = pipeline.current_phase
        
        # ⚠️ HARDCODED PHASE ROUTING (PROBLEM #1)
        if pipeline.current_phase == "pm_phase":
            await self.execute_pm_phase(pipeline_id)
            next_phase = "arch_phase"
        elif pipeline.current_phase == "arch_phase":
            await self.execute_architect_phase(pipeline_id)
            next_phase = "ba_phase"
        elif pipeline.current_phase == "ba_phase":
            await self.execute_ba_phase(pipeline_id)
            next_phase = "dev_phase"
        elif pipeline.current_phase == "dev_phase":
            await self.execute_dev_phase(pipeline_id)
            next_phase = "qa_phase"
        elif pipeline.current_phase == "qa_phase":
            await self.execute_qa_phase(pipeline_id)
            next_phase = "complete"
        else:
            raise ValueError(f"Unknown phase: {pipeline.current_phase}")
        
        # Update pipeline state
        updated_pipeline = self.pipeline_repo.update_state(
            pipeline_id=pipeline_id,
            new_state=next_phase,
            new_phase=next_phase
        )
        
        # Record transition
        self.phase_transition_repo.create(
            pipeline_id=pipeline_id,
            from_state=previous_phase,
            to_state=next_phase,
            reason="Phase advancement"
        )
        
        return PhaseAdvancedResponse(
            pipeline_id=updated_pipeline.pipeline_id,
            previous_phase=previous_phase,
            current_phase=updated_pipeline.current_phase,
            state=updated_pipeline.state,
            updated_at=updated_pipeline.updated_at
        )
```

**Example: execute_pm_phase() - Hardcoded PM Logic:**

```python
async def execute_pm_phase(self, pipeline_id: str):
    """
    Execute PM phase with HARDCODED prompt and logic.
    
    This is what PIPELINE-175B will replace with:
    PhaseExecutorService.execute_phase(pipeline_id, "pm", "pm_phase", "epic")
    """
    # ⚠️ HARDCODED PROMPT (PROBLEM #2)
    system_prompt = """You are the PM Mentor in The Combine Workforce.

Your role is to create a comprehensive Epic definition based on the provided epic_id.

# Your Responsibilities
- Define clear vision and problem statement
- Specify business goals and success metrics
- Define scope (in scope / out of scope)
- Write detailed requirements
- Identify risks and constraints
- Create high-level roadmap

# Output Format
Return JSON matching this schema:
{
  "epic_id": "string (e.g., AUTH-100)",
  "title": "string",
  "description": "string (detailed)",
  "acceptance_criteria": ["string", "string", ...],
  "scope": {
    "in_scope": ["string", ...],
    "out_of_scope": ["string", ...]
  },
  "business_goals": ["string", ...],
  "risks": ["string", ...]
}
"""
    
    # Get pipeline context
    pipeline = self.pipeline_repo.get_by_id(pipeline_id)
    user_message = f"Create an Epic for epic_id: {pipeline.epic_id}"
    
    # ⚠️ HARDCODED LLM CALL (PROBLEM #3)
    response = await self.anthropic_service.call(
        system_prompt=system_prompt,
        user_message=user_message
    )
    
    # Parse JSON response
    try:
        artifact_data = json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse PM response: {e}")
    
    # Validate against Pydantic schema
    try:
        epic = EpicSchema(**artifact_data)
    except ValidationError as e:
        raise ValueError(f"PM artifact validation failed: {e}")
    
    # Submit artifact (validation + storage)
    self.artifact_service.submit_artifact(
        pipeline_id=pipeline_id,
        artifact_type="epic",
        content=epic.dict()
    )
```

**Example: execute_architect_phase() - Similar Pattern:**

```python
async def execute_architect_phase(self, pipeline_id: str):
    """
    Execute Architect phase with HARDCODED prompt.
    
    Same pattern as PM, different prompt.
    """
    # ⚠️ HARDCODED ARCHITECT PROMPT
    system_prompt = """You are the Architect Mentor in The Combine Workforce.

Your role is to design the technical architecture for the Epic.

# Your Responsibilities
- Review Epic for technical feasibility
- Design system architecture
- Define technology stack
- Identify integration points
- Document key decisions

# Output Format
Return JSON matching ArchNotesSchema...
"""
    
    # Load Epic artifact as context
    epic_artifact = self.artifact_service.get_latest_artifact(
        pipeline_id=pipeline_id,
        artifact_type="epic"
    )
    
    user_message = f"Design architecture for this Epic:\n\n{json.dumps(epic_artifact.content)}"
    
    # Call LLM (same as PM)
    response = await self.anthropic_service.call(
        system_prompt=system_prompt,
        user_message=user_message
    )
    
    # Parse, validate, submit (same as PM)
    artifact_data = json.loads(response)
    arch_notes = ArchNotesSchema(**artifact_data)
    self.artifact_service.submit_artifact(
        pipeline_id=pipeline_id,
        artifact_type="arch_notes",
        content=arch_notes.dict()
    )
```

**Pattern Repeated for BA, Dev, QA:**
- execute_ba_phase() - Hardcoded BA prompt
- execute_dev_phase() - Hardcoded Dev prompt
- execute_qa_phase() - Hardcoded QA prompt

**Total Code Duplication:** ~400 lines across 5 methods with nearly identical structure.

---

### Problems with Hardcoded Approach

**Problem #1: Hardcoded Phase Routing**
```python
if pipeline.current_phase == "pm_phase":
    await self.execute_pm_phase(pipeline_id)
    next_phase = "arch_phase"
elif pipeline.current_phase == "arch_phase":
    # ...
```
- ❌ Adding new role requires modifying advance_phase() method
- ❌ Phase flow hidden in code (not visible as data)
- ❌ Can't customize flow per customer

**Problem #2: Hardcoded Prompts**
```python
system_prompt = """You are the PM Mentor..."""
```
- ❌ Prompts embedded in code (can't see without reading source)
- ❌ Prompt updates require code deployment
- ❌ Can't A/B test prompt variations
- ❌ No version tracking (which prompt produced which artifact?)

**Problem #3: Role-Specific Methods**
```python
async def execute_pm_phase(...)
async def execute_architect_phase(...)
async def execute_ba_phase(...)
# ... 5 nearly identical methods
```
- ❌ Code duplication (~400 lines)
- ❌ Adding new role requires new method
- ❌ Engineering bottleneck (2-3 days per new role)
- ❌ Maintenance burden (fix bug in 5 places)

**Problem #4: No Audit Trail**
- ❌ Can't determine which prompt version produced which artifact
- ❌ Compliance gap for regulated industries
- ❌ No prompt performance analysis (which version works best?)

**Problem #5: No Configuration Visibility**
- ❌ Phase flow not queryable (locked in code)
- ❌ Role assignments not visible as data
- ❌ Artifact type mappings not explicit

---

## Test Coverage Baseline

### Test Suite (20 Tests Passing)

```
tests/test_orchestrator_api/
├── test_pipeline_service.py          # 8 tests
│   ├── test_create_pipeline()
│   ├── test_advance_phase_pm_to_arch()
│   ├── test_advance_phase_full_pipeline()
│   ├── test_advance_phase_invalid_state()
│   ├── test_execute_pm_phase()
│   ├── test_execute_architect_phase()
│   ├── test_pipeline_state_transitions()
│   └── test_error_handling_invalid_json()
│
├── test_artifact_service.py          # 5 tests
│   ├── test_submit_artifact_valid()
│   ├── test_submit_artifact_invalid_schema()
│   ├── test_get_artifact_by_id()
│   ├── test_list_artifacts_for_pipeline()
│   └── test_artifact_validation_errors()
│
├── test_repositories.py              # 4 tests
│   ├── test_pipeline_repository_create()
│   ├── test_pipeline_repository_update_state()
│   ├── test_artifact_repository_create()
│   └── test_phase_transition_repository_create()
│
└── test_integration.py               # 3 tests
    ├── test_full_pipeline_pm_to_qa()
    ├── test_artifact_chain_dependencies()
    └── test_error_recovery()
```

### Key Test Scenarios

**Pipeline State Transitions:**
- ✅ Create pipeline initializes to pm_phase with state="active"
- ✅ advance_phase() from pm_phase executes PM logic and transitions to arch_phase
- ✅ advance_phase() from arch_phase executes Architect logic and transitions to ba_phase
- ✅ Subsequent advances: ba_phase → dev_phase → qa_phase → complete
- ✅ State transitions logged in phase_transitions table

**Artifact Validation:**
- ✅ Valid Epic JSON passes EpicSchema validation
- ✅ Invalid Epic JSON (missing required field) raises ValidationError
- ✅ Invalid Epic JSON (wrong type) raises ValidationError
- ✅ Each artifact type (Epic, ArchNotes, BASpec, etc.) validated against correct schema
- ✅ Artifacts stored with correct artifact_type field

**Error Handling:**
- ✅ Invalid phase name raises ValueError with clear message
- ✅ LLM timeout retries once, then fails gracefully
- ✅ JSON parse errors captured and logged
- ✅ ValidationError returns 400 with validation details

**Integration:**
- ✅ Full pipeline (PM → Arch → BA → Dev → QA) completes successfully
- ✅ Each phase produces artifact that next phase can consume
- ✅ Pipeline state consistently tracked across phases

### Performance Baseline

**Measured on Development Environment (MacBook Pro M1):**
- Full 5-phase pipeline: 42-48 seconds (average 45s)
- Individual phase execution: 5-10 seconds
  - PM phase: 8s (longest prompt)
  - Architect phase: 9s (includes Epic context)
  - BA phase: 7s
  - Dev phase: 6s
  - QA phase: 5s
- Database operations: <10ms per operation
- LLM API calls: 5-9 seconds each (network + generation time)

**Performance is LLM-dominated:** 95% of time spent waiting for Anthropic API responses.

**CRITICAL for 175A/B:** All 20 tests must pass after 175A deployment. Zero behavior change during 175A. Performance must remain within 10% of baseline.

---

## API Endpoints (PIPELINE-150)

### Endpoints

```
POST   /pipelines              # Create new pipeline
GET    /pipelines/{id}         # Get pipeline details
POST   /pipelines/{id}/advance # Advance to next phase
GET    /artifacts/{id}         # Get artifact by ID
GET    /pipelines/{id}/artifacts # List all artifacts for pipeline
```

### Request/Response Examples

**Create Pipeline:**
```json
POST /pipelines
{
  "epic_id": "AUTH-100"
}

Response 200:
{
  "pipeline_id": "pip_abc123",
  "epic_id": "AUTH-100",
  "current_phase": "pm_phase",
  "state": "active",
  "created_at": "2025-12-04T10:00:00Z",
  "updated_at": "2025-12-04T10:00:00Z"
}
```

**Advance Phase:**
```json
POST /pipelines/pip_abc123/advance

Response 200:
{
  "pipeline_id": "pip_abc123",
  "previous_phase": "pm_phase",
  "current_phase": "arch_phase",
  "state": "active",
  "updated_at": "2025-12-04T10:00:15Z"
}
```

**Get Artifacts:**
```json
GET /pipelines/pip_abc123/artifacts

Response 200:
{
  "artifacts": [
    {
      "artifact_id": "art_xyz789",
      "pipeline_id": "pip_abc123",
      "artifact_type": "epic",
      "content": { "epic_id": "AUTH-100", ... },
      "created_at": "2025-12-04T10:00:08Z"
    }
  ]
}
```

**No changes to API contracts in 175A/B.** Internal refactoring only. Responses remain identical.

---

## Known Limitations (Why We're Refactoring)

### 1. Engineering Bottleneck for New Roles

**Current Process to Add New Role:**
1. Write new `execute_X_phase()` method in pipeline_service.py (~80 lines)
2. Add hardcoded prompt in method (~40 lines)
3. Add new phase case to `advance_phase()` routing (~5 lines)
4. Create Pydantic schema in schemas/artifacts.py (~30 lines)
5. Write tests (~40 lines)
6. Deploy code

**Estimated Time:** 2-3 days per new role (includes testing and deployment)

**Impact:** Slow iteration on role experimentation. Customer-specific roles require engineering time.

### 2. No Prompt Visibility

**Problem:**
- Prompts hidden in code (must read source to see them)
- Can't query "what's the active PM prompt?"
- Product managers can't review/edit prompts without engineering

**Impact:**
- Prompt quality issues discovered late (after deployment)
- Non-technical stakeholders can't contribute to prompt improvement
- Prompt iterations slow (requires code changes)

### 3. No Audit Trail

**Problem:**
- Can't determine which prompt version produced which artifact
- Can't track prompt performance (success rate per version)
- Can't correlate artifact quality with prompt changes

**Impact:**
- Compliance gap for regulated industries (financial, healthcare)
- Can't A/B test prompts (no version tracking)
- Can't roll back to previous prompt version

### 4. Deployment Required for Prompt Changes

**Problem:**
- Typo in prompt → full deployment cycle
- Prompt iteration = code deployment (slow, risky)
- Can't hot-fix prompt issues in production

**Impact:**
- Slow prompt iteration (days, not hours)
- Deployment risk for minor prompt changes
- Can't respond quickly to prompt quality issues

### 5. No Configuration Flexibility

**Problem:**
- Phase flow hardcoded (can't reorder phases)
- Role assignments hardcoded (can't swap roles per customer)
- Pipeline structure same for all users

**Impact:**
- Can't customize pipeline per customer
- Can't experiment with alternative flows
- No multi-tenant flexibility

### 6. Code Duplication & Maintenance Burden

**Problem:**
- ~400 lines duplicated across 5 execute_X_phase() methods
- Bug fixes require changes in 5 places
- Inconsistent error handling across methods

**Impact:**
- Maintenance complexity
- Higher bug risk (fix in 4 places, miss 5th)
- Code review overhead

---

## Migration Path (150 → 175A → 175B)

### PIPELINE-175A: Data Layer Foundation

**Goal:** Add configuration infrastructure with zero behavior change.

**Changes:**
- ✅ Add 3 new tables: role_prompts, phase_configurations, pipeline_prompt_usage
- ✅ Add 3 new repositories: RolePromptRepository, PhaseConfigurationRepository, PipelinePromptUsageRepository
- ✅ Add RolePromptService.build_prompt() (reads from database)
- ✅ Seed baseline data: 6 roles, 6 phase configs
- ✅ Run all PIPELINE-150 tests → 20/20 pass (zero behavior change)

**Impact:**
- Database has new tables (populated)
- New code available but not used by pipeline execution
- Old code still runs (execute_pm_phase() etc. unchanged)
- No API changes
- No performance impact

**Success Criteria:**
- All PIPELINE-150 tests pass (20/20)
- Seed scripts populate 6 prompts + 6 configs
- RolePromptService.build_prompt() functional but unused
- Performance within 5% of baseline

### PIPELINE-175B: Data-Driven Execution

**Goal:** Replace hardcoded execution with data-driven PhaseExecutorService.

**Changes:**
- ✅ Implement PhaseExecutorService.execute_phase() (generic execution)
- ✅ Refactor PipelineService.advance_phase() to use PhaseConfiguration
- ✅ Delete execute_pm_phase(), execute_architect_phase(), etc. (5 methods removed)
- ✅ Feature flag: DATA_DRIVEN_ORCHESTRATION (true/false)
- ✅ Gradual rollout: 10% → 50% → 100% over 2 weeks

**Impact:**
- Pipeline execution uses PhaseConfiguration to determine flow
- PhaseExecutorService builds prompts from role_prompts table
- Prompt usage recorded in pipeline_prompt_usage table
- Same artifacts produced (validated by regression tests)
- ~400 lines of code removed (execute_X_phase methods)

**Rollback:**
- Set DATA_DRIVEN_ORCHESTRATION=false
- Legacy code available for 30 days (marked deprecated)
- Delete legacy code after 30 days (scheduled cleanup)

**Success Criteria:**
- All PIPELINE-150 tests pass in both modes (20/20)
- Outputs identical between legacy and data-driven modes
- Performance within 10% of baseline
- Zero production incidents during rollout

### Post-Migration Benefits

**After 175B Complete:**
- ✅ Add new role via database insert (no code changes)
- ✅ Update prompts without deployment (hot-fix capability)
- ✅ Track prompt versions (full audit trail)
- ✅ A/B test prompts (version comparison)
- ✅ Customize pipeline per customer (configuration-driven)
- ✅ ~400 lines of code removed (simpler codebase)
- ✅ Foundation ready for REPO-200, LLM-300, CONNECTOR-100

---

## References

**Related Epics:**
- **PIPELINE-175A:** Data-Described Pipeline Infrastructure (adds tables, repositories, services)
- **PIPELINE-175B:** Data-Driven Pipeline Execution (refactors execution to use 175A data)
- **REPO-200:** Repository Provider Abstraction (commit role becomes data-driven)
- **LLM-300:** Pluggable LLM Providers (model selection per role)

**Related Documents:**
- **Canonical Architecture v1.4:** Current system architecture (includes PIPELINE-001)
- **PIPELINE-175A Architecture:** Database schema, repository layer, service design
- **PIPELINE-175A BA Backlog:** Test scenarios and acceptance criteria

**Code References:**
- `app/orchestrator_api/services/pipeline_service.py` - Main orchestration (to be refactored)
- `app/orchestrator_api/schemas/artifacts.py` - Pydantic artifact schemas (keeping)
- `tests/test_orchestrator_api/` - Test suite (20 tests, all must pass post-175A)

---

## Document Purpose

**Target Audience:** Developers implementing PIPELINE-175A and PIPELINE-175B.

**Goals:**
1. Understand what currently exists (PIPELINE-150 baseline)
2. Understand current execution flow (hardcoded routing and prompts)
3. Understand known limitations (why we're refactoring)
4. Understand migration path (150 → 175A → 175B)
5. Understand acceptance criteria (all 20 tests must pass post-175A)

**Next Steps:**
1. Review PIPELINE-175A Architecture document (database schema, repositories, services)
2. Review PIPELINE-175A BA Backlog (test scenarios, acceptance criteria)
3. Implement PIPELINE-175A Story 0: RolePrompt Model and Repository
4. Verify zero behavior change (all PIPELINE-150 tests pass)

---

**Document Version:** 1.0  
**Created:** 2025-12-04  
**Last Updated:** 2025-12-04  
**Status:** Complete - Ready for Dev Phase
