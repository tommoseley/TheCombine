# PIPELINE-175A: Data-Described Pipeline Infrastructure

**Epic Type:** Infrastructure/Foundation  
**Priority:** P0 - Critical Foundation  
**Estimated Effort:** 4-5 days  
**Status:** Approved for Architect Phase  
**Version:** 1.1 (Surgical Tweaks Applied)

---

## Epic Summary

Establish the foundational data layer for configuration-driven pipeline orchestration. Create database tables, repositories, and services to store and retrieve role prompts and phase configurations as data rather than code. This epic delivers the **infrastructure** but does **not yet change** pipeline execution behavior—existing hardcoded logic remains intact.

**Key Deliverable:** A fully seeded database with role prompts and phase configurations, plus a service that can build prompts from stored data. Pipeline execution continues using PIPELINE-150 logic.

---

## Business Rationale

### Problem Statement

The current system has role prompts and phase flow hardcoded in application logic. This creates:
- No visibility into what prompts are active
- No audit trail of prompt changes
- No ability to A/B test prompt variations
- No path to multi-tenant customization

### Business Value

This epic establishes the **data foundation** without disrupting current operations:
- Prompts become visible, versionable data
- Configuration changes trackable via database
- Foundation ready for 175B to switch execution logic
- Zero risk to existing pipelines (no behavior changes)

### Strategic Positioning

**PIPELINE-175A is prerequisite for:**
- PIPELINE-175B (data-driven execution)
- REPO-200 (commit role as data)
- LLM-300 (model selection per role via config)
- CONNECTOR-100 (prompts migrate to Knowledge Plane)

---

## User Stories

### Story 0: Define RolePrompt Model and Repository

**As a** System Architect  
**I want** role prompts stored in database with versioning  
**So that** we have a foundation for data-driven prompt management and audit trails

#### Implementation Requirements

**Database Models:**

1. **`role_prompts` Table:**
   - `id` (String, PK) - Unique identifier (e.g., `rp_<ulid>`)
   - `role_name` (String, indexed) - Role identifier (pm, architect, ba, dev, qa, commit)
   - `version` (String) - Semantic version (1.0, 1.1, 2.0)
   - `starting_prompt` (Text, nullable) - Optional opening context
   - `bootstrapper` (Text, required) - Role identity and framing
   - `instructions` (Text, required) - Detailed role instructions
   - `working_schema` (JSON, nullable) - Expected input/output schemas
   - `is_active` (Boolean, indexed) - Only one active version per role
   - `created_at` (DateTime) - Creation timestamp
   - `updated_at` (DateTime) - Last modification timestamp
   - `created_by` (String, nullable) - Creator identifier
   - `notes` (Text, nullable) - Version changelog/notes
   - **Constraint:** Only one active prompt per role

2. **`pipeline_prompt_usage` Table:**
   - `id` (String, PK) - Unique identifier
   - `pipeline_id` (String, FK to pipelines, indexed) - Pipeline reference
   - `role_name` (String) - Role that was executed
   - `prompt_id` (String, FK to role_prompts) - Prompt version used
   - `phase_name` (String) - Phase where prompt was used
   - `used_at` (DateTime) - Execution timestamp

**Repository Interface:**

```python
class RolePromptRepository:
    def get_active_prompt(role_name: str) -> Optional[RolePrompt]
    def get_by_id(prompt_id: str) -> Optional[RolePrompt]
    def list_versions(role_name: str) -> List[RolePrompt]
    def create(...) -> RolePrompt
    def set_active(prompt_id: str) -> RolePrompt

class PipelinePromptUsageRepository:
    def record_usage(pipeline_id, role_name, prompt_id, phase_name)
    def get_by_pipeline(pipeline_id: str) -> List[PipelinePromptUsage]
```

#### Acceptance Criteria

**AC-0.1: Database Schema Creation**
- Tables created with all specified fields and constraints
- Indexes on `role_name` and `is_active` for query performance
- Unique constraint on `(role_name, is_active=true)` ensures one active version per role
- Migration script creates tables idempotently

**AC-0.2: Repository CRUD Operations**
- `get_active_prompt("pm")` returns active prompt or None
- `list_versions("pm")` returns all versions ordered by created_at desc
- `create()` successfully stores new prompt with all fields
- `set_active()` deactivates old version and activates new version atomically
- Constraint violations raise appropriate errors

**AC-0.3: Audit Trail Schema & Repository (REVISED)**
- `pipeline_prompt_usage` table created with correct schema
- Foreign key constraints to `pipelines` and `role_prompts` enforced
- `PipelinePromptUsageRepository.record_usage()` successfully stores test records
- Can query usage by pipeline_id (returns list)
- Can query usage by prompt_id (returns list)
- **Note:** Actual runtime usage recording begins in 175B when `PhaseExecutorService` is integrated; this AC validates schema and repository operations only

**AC-0.4: Data Validation**
- Cannot create prompt with missing `bootstrapper` or `instructions`
- Cannot have two active prompts for same role simultaneously
- `working_schema` field accepts valid JSON or null

---

### Story 1: Create PhaseConfiguration Model and Repository

**As a** Pipeline Orchestrator  
**I want** phase flow defined as database configuration  
**So that** pipeline structure is visible data rather than hidden code

#### Implementation Requirements

**Database Model:**

**`phase_configurations` Table:**
- `id` (String, PK) - Unique identifier (e.g., `pc_<ulid>`)
- `phase_name` (String, unique, indexed) - Phase identifier (pm_phase, arch_phase, etc.)
- `role_name` (String, required) - Which role executes this phase
- `artifact_type` (String, required) - Expected artifact output (epic, arch_notes, etc.)
- `next_phase` (String, nullable) - Next phase in sequence (null = terminal phase)
- `is_active` (Boolean) - Whether this configuration is active
- `config` (JSON, nullable) - Phase-specific configuration (timeouts, retries, etc.)
- `created_at` (DateTime) - Creation timestamp
- `updated_at` (DateTime) - Last modification timestamp

**Repository Interface:**

```python
class PhaseConfigurationRepository:
    def get_by_phase(phase_name: str) -> Optional[PhaseConfiguration]
    def get_all_active() -> List[PhaseConfiguration]
    def create(...) -> PhaseConfiguration
    def update_next_phase(phase_name: str, next_phase: str)
    
    # NEW: Separate validation method
    @staticmethod
    def validate_configuration_graph() -> ValidationResult:
        """
        Validates entire phase configuration graph:
        - All role_names exist in role_prompts
        - All next_phases exist in phase_configurations (or null)
        - No circular references (max 20 hops)
        
        Returns:
            ValidationResult with errors list (empty if valid)
        """
```

#### Acceptance Criteria

**AC-1.1: Database Schema Creation**
- Table created with all fields
- Unique index on `phase_name` prevents duplicate phase definitions
- Migration script is idempotent

**AC-1.2: Repository Operations**
- `get_by_phase("pm_phase")` returns config or None
- `get_all_active()` returns all active configs
- `create()` stores new configuration with basic validation only
- `update_next_phase()` modifies flow

**AC-1.3: Basic Field Validation**
- Cannot create phase without required fields (`phase_name`, `role_name`, `artifact_type`)
- `config` accepts valid JSON or null
- Can create terminal phase with `next_phase=null`

**AC-1.4: Configuration Validation Helper (REVISED)**
- Repository provides `validate_configuration_graph()` method
- Validates all `role_name` fields reference existing prompts in `role_prompts`
- Validates all `next_phase` fields reference existing configs in `phase_configurations` (or null)
- Detects circular references (follows chain max 20 hops, fails if loops)
- Returns structured `ValidationResult` with clear error messages
- Seed scripts call validator after creating all configs
- Validator used in tests to ensure graph consistency

**Seed Script Pattern:**
```python
def seed_phase_configuration():
    repo = PhaseConfigurationRepository()
    
    # Create all configs first (no cross-validation during creation)
    repo.create(phase_name="pm_phase", role_name="pm", ...)
    repo.create(phase_name="arch_phase", role_name="architect", ...)
    # ... create all 6
    
    # Then validate the complete graph
    validation = repo.validate_configuration_graph()
    if not validation.is_valid:
        raise ValueError(f"Configuration invalid: {validation.errors}")
    
    print("✓ All configs created and validated")
```

---

### Story 2: Seed Scripts for Role Prompts & Phase Configuration

**As a** System Administrator  
**I want** baseline configuration seeded automatically  
**So that** new deployments have functional pipeline data

#### Implementation Requirements

**Seed Scripts:**

1. **`scripts/seed_role_prompts.py`:**
   - Seeds 6 roles: pm, architect, ba, dev, qa, commit (stub)
   - Complete prompt content embedded or loaded from files in `app/orchestrator_api/prompts/defaults/`
   - All marked `is_active=true`, `version="1.0"`
   - Idempotent (checks existing, skips if present)

2. **`scripts/seed_phase_configuration.py`:**
   - Seeds 6-phase pipeline:
     - `pm_phase` → role `pm` → artifact `epic` → next `arch_phase`
     - `arch_phase` → role `architect` → artifact `arch_notes` → next `ba_phase`
     - `ba_phase` → role `ba` → artifact `ba_spec` → next `dev_phase`
     - `dev_phase` → role `dev` → artifact `proposed_change_set` → next `qa_phase`
     - `qa_phase` → role `qa` → artifact `qa_result` → next `commit_phase`
     - `commit_phase` → role `commit` → artifact `commit_result` → next `null`
   - Calls `validate_configuration_graph()` after all configs created
   - Idempotent

**Commit Role Stub:**
- Prompt: "You are the Commit Mentor. Your role is to finalize the pipeline. For now, simply mark the pipeline as complete. Full PR creation functionality will be added in REPO-200."
- Returns: `{"success": true, "message": "Pipeline complete - PR creation pending REPO-200"}`

**Integration:**
- `init_database()` calls both seed scripts on first run
- Checks for sentinel data before seeding
- Logs: "Seeding baseline data..." or "Baseline data exists, skipping..."

#### Acceptance Criteria

**AC-2.1: Role Prompt Seeding**
- Creates 6 role prompts successfully (pm, architect, ba, dev, qa, commit)
- All prompts have complete content (bootstrapper, instructions)
- All marked `is_active=true`, `version="1.0"`
- Idempotent (safe re-run, skips existing)

**AC-2.2: Phase Configuration Seeding**
- Creates 6 phase configs successfully
- Phase chain: pm → arch → ba → dev → qa → commit → null
- All configs `is_active=true`
- Calls `validate_configuration_graph()` and passes
- Idempotent

**AC-2.3: Commit Stub Functional**
- Stub prompt clearly indicates temporary nature
- Includes reference to REPO-200 for full implementation
- Artifact structure matches expected schema
- Can query and retrieve stub prompt from database

**AC-2.4: Error Handling**
- Logs progress for each item created
- Logs warnings for skipped items (already exist)
- Continues on non-critical errors
- Exit code 0 only if all critical seeds succeeded
- Summary: "✓ 6/6 roles, ✓ 6/6 phases" or "✓ 6/6 roles (0 created, 6 existing)"

**AC-2.5: Database Init Integration**
- `init_database()` automatically calls both seed scripts
- Only runs on first initialization (sentinel check)
- Manual re-run safe (idempotent behavior)
- Clear logging of seed status

---

### Story 3: Implement RolePromptService

**As a** Phase Executor  
**I want** prompts built from database data  
**So that** prompt updates don't require code deployment

#### Implementation Requirements

**Service Interface:**

```python
class RolePromptService:
    def __init__(self):
        self.prompt_repo = RolePromptRepository()
    
    def build_prompt(
        self,
        role_name: str,
        pipeline_id: str,
        phase: str,
        epic_context: Optional[str] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """
        Build complete role prompt with context injection.
        
        Returns:
            (prompt_text, prompt_id) - Assembled prompt and version ID
        """
```

**Assembly Strategy:**
1. Load active `RolePrompt` from database for specified role
2. Build sections: starting_prompt, bootstrapper, instructions, working_schema
3. Inject context: epic_context, pipeline_state, artifacts
4. Return assembled prompt text + prompt_id

**Section Order:**
1. Starting prompt (if present)
2. Bootstrapper (role identity)
3. Instructions (how to perform role)
4. Working schema (expected formats, as JSON code block)
5. Epic context (what we're building)
6. Pipeline state (current status as JSON)
7. Artifacts (previous work as JSON)

#### Acceptance Criteria

**AC-3.1: Prompt Loading**
- Loads active prompt from database for specified role
- Returns both prompt text and prompt_id
- Raises clear error if no active prompt exists for role
- Logs warning if prompt version is >1 year old

**AC-3.2: Section Assembly**
- All non-null sections included in correct order
- Starting prompt appears first (if present)
- Bootstrapper and instructions always present (required fields)
- Working schema formatted as JSON code block (if present)
- Context sections appear after role-specific content

**AC-3.3: Context Injection**
- Epic context injected as `# Epic Context` markdown section
- Pipeline state formatted as JSON code block under `# Pipeline State`
- Artifacts formatted as JSON with artifact_type as keys under `# Previous Artifacts`
- Empty/null context gracefully omitted (no empty sections)

**AC-3.4: Output Format Quality**
- Prompt uses consistent markdown formatting throughout
- JSON code blocks properly fenced with ` ```json ` and ` ``` `
- Sections clearly separated with markdown headers and blank lines
- Total prompt length reasonable (<50KB for typical cases)

**AC-3.5: No Hardcoded Prompts**
- Zero prompt text hardcoded in service code
- All content loaded from database via repository
- Service code contains only assembly/formatting logic
- Grep codebase finds no role-specific instruction text outside database

---

### Story 4: Comprehensive Testing

**As a** Quality Engineer  
**I want** thorough testing of data layer  
**So that** 175B can build on solid foundation

#### Implementation Requirements

**Test Coverage:**

1. **Repository Unit Tests:**
   - RolePromptRepository CRUD operations
   - PhaseConfigurationRepository CRUD operations
   - Constraint validation
   - Error handling

2. **Service Unit Tests:**
   - RolePromptService.build_prompt() with various context combinations
   - Missing prompt handling
   - Output format validation

3. **Integration Tests:**
   - Seed scripts execution (empty DB → seeded DB)
   - Database queries with indexes
   - Referential integrity enforcement
   - Configuration graph validation

4. **Performance Tests:**
   - Prompt building <100ms (p95)
   - Config lookup <10ms (p95)

#### Acceptance Criteria

**AC-4.1: Repository Tests**
- **RolePromptRepository:**
  - CRUD operations (create, get, list, set_active) tested
  - Unique constraint violations tested
  - Foreign key constraints tested
  - Edge cases (missing role, duplicate active) tested
  - 100% code coverage for repository

- **PhaseConfigurationRepository:**
  - CRUD operations tested
  - `validate_configuration_graph()` tested with:
    - Valid graph (passes)
    - Missing role_name reference (fails with clear error)
    - Missing next_phase reference (fails with clear error)
    - Circular reference (fails with clear error)
    - Long but valid chain (20 hops, passes)
  - 100% code coverage for repository

**AC-4.2: Service Tests**
- Prompt building with all contexts (epic, state, artifacts) tested
- Prompt building with no contexts tested
- Prompt building with partial contexts tested
- Missing prompts raise clear errors
- Output format validated (markdown sections, JSON formatting)
- 100% code coverage for service

**AC-4.3: Seed Script Tests**
- Scripts run successfully on empty database
- Idempotency verified (re-run safe, skips existing)
- Error handling verified (logs but continues on non-critical errors)
- Can seed empty database from scratch
- Can re-run without errors or duplicates
- Graph validation called and passes after seeding

**AC-4.4: Integration Tests**
- End-to-end flow: seed scripts → query role → build prompt
- Database constraints enforced at runtime
- Indexes used in queries (query plan verification)
- Foreign keys prevent orphaned records
- Can create, retrieve, and use all 6 roles

**AC-4.5: Performance Validation**
- Prompt build with full context: <100ms (p95)
- Prompt build with no context: <50ms (p95)
- Config lookup by phase_name: <10ms (p95)
- 1000 iterations tested for statistical validity
- Percentiles (p50, p95, p99) reported

---

## Epic-Level Acceptance Criteria

### AC-E1: Complete Data Layer Functional

**Given** empty database  
**When** running `init_database()`  
**Then** database contains 6 role prompts, 6 phase configs, all properly linked and queryable

**Verification:**
- Query `role_prompts` WHERE `is_active=true`: Returns 6 records
- Query `phase_configurations` WHERE `is_active=true`: Returns 6 records
- All foreign key relationships valid (no orphaned references)
- Can retrieve each role's active prompt by name
- Can retrieve each phase's configuration by name
- `validate_configuration_graph()` passes for seeded data

---

### AC-E2: Prompt Building Works End-to-End

**Given** seeded database  
**When** calling `RolePromptService.build_prompt("pm", pipeline_id, "pm_phase", epic_context="...", pipeline_state={...}, artifacts={...})`  
**Then** returns complete formatted prompt with all sections and context injected correctly

**Verification:**
- Prompt includes PM bootstrapper text from database
- Prompt includes PM instructions from database
- Epic context present in `# Epic Context` section
- Pipeline state present as JSON in `# Pipeline State` section
- Artifacts present as JSON in `# Previous Artifacts` section
- Prompt ID returned matches active PM prompt ID in database
- Total execution time <100ms

---

### AC-E3: Zero Impact on Existing Pipelines

**Given** PIPELINE-175A deployed  
**When** running existing pipeline tests  
**Then** all PIPELINE-150 tests pass without modification and pipelines execute identically

**Verification:**
- All 20 PIPELINE-150 tests pass (100% green)
- No test modifications required
- Pipeline execution behavior unchanged (still uses hardcoded logic)
- API responses identical in format and content
- Performance within 5% variance of baseline

---

### AC-E4: Audit Trail Foundation Ready

**Given** completed epic  
**When** 175B begins recording prompt usage  
**Then** `pipeline_prompt_usage` table structure fully supports audit requirements

**Verification:**
- Table exists with correct schema and constraints
- Foreign keys to `pipelines` and `role_prompts` tables enforced
- Can insert usage records programmatically
- Can query by `pipeline_id` (returns all usages for that pipeline)
- Can query by `prompt_id` (returns all pipelines using that prompt)
- Indexes support efficient queries (<10ms for typical queries)

---

### AC-E5: Documentation Complete

**Given** epic completion  
**When** reviewing deliverables  
**Then** documentation covers data schema, seeding process, and service usage

**Verification:**
- Database schema documented:
  - ERD (Entity Relationship Diagram) showing all tables and relationships
  - Field descriptions for each table
  - Constraint documentation (unique, foreign keys, indexes)
- Seed script usage documented:
  - How to run seed scripts manually
  - How to verify successful seeding
  - Troubleshooting common seed failures
- RolePromptService API documented:
  - Method signature and parameters
  - Return value format
  - Example usage with code snippets
- Example queries provided for common operations
- Migration notes from PIPELINE-150 included

---

## Dependencies

### Internal Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| **PIPELINE-150 Complete** | ✅ Ready | Baseline implementation exists |
| **Database JSON Support** | ✅ Ready | SQLite/PostgreSQL both support JSON columns |
| **Artifact Schemas** | ✅ Ready | Pydantic models in `workforce/schemas/artifacts.py` |

### Blocks These Epics

- ✋ **PIPELINE-175B** - Data-driven execution (requires this data layer)
- ✋ **REPO-200** - RepoProvider abstraction (commit role will be added as data)

---

## Risks & Mitigation

### Risk 1: Seed Script Failures in Production

**Risk Level:** 🟢 Low  
**Likelihood:** Low (controlled environment)  
**Impact:** High (can't run pipelines without seed data)

**Mitigation:**
- Comprehensive error handling in seed scripts (logs, continues on non-critical errors)
- Idempotency ensures safe re-runs
- Integration with `init_database()` ensures automatic seeding
- Test coverage validates seed scripts work on empty database
- Deployment checklist includes seed verification step

---

### Risk 2: Schema Changes During Development

**Risk Level:** 🟢 Low  
**Likelihood:** Medium (requirements may evolve)  
**Impact:** Low (handled by migrations)

**Mitigation:**
- Use proper database migrations (not direct schema changes)
- Version all DDL scripts
- Test migrations on copy of production data
- Rollback procedures documented for each migration

---

### Risk 3: Performance Issues with Prompt Building

**Risk Level:** 🟢 Low  
**Likelihood:** Low (simple queries and string concatenation)  
**Impact:** Low (slightly slower prompt building)

**Mitigation:**
- Indexes on frequently queried fields (`role_name`, `is_active`, `phase_name`)
- Performance tests validate <100ms for typical operations
- Database connection pooling configured
- Query optimization if needed (already simple queries)

---

### Risk 4: Validation Logic Complexity

**Risk Level:** 🟢 Low  
**Likelihood:** Low (validation logic is straightforward)  
**Impact:** Low (validation might miss edge cases)

**Mitigation:**
- Comprehensive test coverage for `validate_configuration_graph()`
- Clear error messages for all validation failures
- Validation runs after seeding (catches issues immediately)
- Manual verification during QA phase

---

## Success Metrics

### Functional Metrics
- ✅ All 4 stories completed with ACs satisfied
- ✅ All 5 epic-level ACs verified
- ✅ Database seeded successfully with all 6 roles and 6 phases
- ✅ RolePromptService builds prompts correctly with context injection
- ✅ Zero impact on existing pipeline execution (PIPELINE-150 tests pass)

### Quality Metrics
- ✅ Code coverage >90% for new code (repositories, service)
- ✅ All unit tests pass (repositories, service)
- ✅ All integration tests pass (seed scripts, end-to-end)
- ✅ Performance tests pass (prompt building <100ms, lookups <10ms)
- ✅ Zero critical bugs in QA phase

### Business Metrics
- ✅ Foundation ready for 175B (data layer complete)
- ✅ Prompts visible as data (can query and inspect)
- ✅ Configuration visible as data (can query phase flow)
- ✅ Audit trail schema ready (175B will use)

---

## Technical Notes

### Database Schema Overview

```sql
-- Role prompts with versioning and audit
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
    
    -- Indexes
    INDEX idx_role_prompts_role (role_name),
    INDEX idx_role_prompts_active (is_active),
    INDEX idx_role_prompts_role_active (role_name, is_active),
    
    -- Constraints
    UNIQUE (role_name, is_active) WHERE is_active = TRUE
);

-- Phase flow configuration
CREATE TABLE phase_configurations (
    id VARCHAR(64) PRIMARY KEY,
    phase_name VARCHAR(64) NOT NULL UNIQUE,
    role_name VARCHAR(64) NOT NULL,
    artifact_type VARCHAR(64) NOT NULL,
    next_phase VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    config JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    -- Indexes
    INDEX idx_phase_config_phase (phase_name),
    INDEX idx_phase_config_active (is_active)
);

-- Audit trail of prompt usage (schema only in 175A, wired in 175B)
CREATE TABLE pipeline_prompt_usage (
    id VARCHAR(64) PRIMARY KEY,
    pipeline_id VARCHAR(64) NOT NULL,
    role_name VARCHAR(64) NOT NULL,
    prompt_id VARCHAR(64) NOT NULL,
    phase_name VARCHAR(64) NOT NULL,
    used_at TIMESTAMP NOT NULL,
    
    -- Indexes
    INDEX idx_prompt_usage_pipeline (pipeline_id),
    INDEX idx_prompt_usage_prompt (prompt_id),
    
    -- Foreign Keys
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id),
    FOREIGN KEY (prompt_id) REFERENCES role_prompts(id)
);
```

### Validation Logic

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]

def validate_configuration_graph() -> ValidationResult:
    """
    Validates phase configuration graph for:
    1. Role references exist
    2. Phase references exist
    3. No circular references
    """
    errors = []
    
    # Load all active configs
    configs = get_all_active()
    phase_names = {cfg.phase_name for cfg in configs}
    
    # Load all active role names
    role_prompts = load_all_active_role_prompts()
    role_names = {rp.role_name for rp in role_prompts}
    
    # Check 1: All role_names exist
    for cfg in configs:
        if cfg.role_name not in role_names:
            errors.append(f"Phase '{cfg.phase_name}' references non-existent role '{cfg.role_name}'")
    
    # Check 2: All next_phases exist (or null)
    for cfg in configs:
        if cfg.next_phase and cfg.next_phase not in phase_names:
            errors.append(f"Phase '{cfg.phase_name}' references non-existent next_phase '{cfg.next_phase}'")
    
    # Check 3: No circular references
    for cfg in configs:
        visited = set()
        current = cfg.phase_name
        hops = 0
        
        while current and hops < 20:
            if current in visited:
                errors.append(f"Circular reference detected in phase chain starting at '{cfg.phase_name}'")
                break
            visited.add(current)
            
            # Find next phase
            next_cfg = next((c for c in configs if c.phase_name == current), None)
            current = next_cfg.next_phase if next_cfg else None
            hops += 1
        
        if hops >= 20:
            errors.append(f"Phase chain starting at '{cfg.phase_name}' exceeds maximum length (20 hops)")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
```

---

## Estimated Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Architect Phase** | 0.5 days | Database schema DDL, repository interfaces, validation logic design |
| **BA Phase** | 1 day | Detailed story ACs, test cases, seed script content specification |
| **Dev Phase** | 3 days | All 4 stories implemented, unit tests passing |
| **QA Phase** | 1 day | Integration tests, seed scripts verified, performance validated |
| **Total** | **5-6 days** | Complete data layer ready for 175B |

---

## Open Questions for Architect/BA Phase

1. **Prompt Content Storage:** Should initial prompt content be embedded in seed scripts or loaded from separate `.md` files in `app/orchestrator_api/prompts/defaults/`?
   - **Recommendation:** Start with embedded for simplicity, but design to be extensible

2. **Validation Timing:** Should graph validation run automatically on every config creation, or only when explicitly called?
   - **Recommendation:** Only when explicitly called (seed scripts, tests), to allow flexible creation order

3. **Performance Targets:** Is <100ms prompt building sufficient, or should we target <50ms?
   - **Recommendation:** Start with 100ms, optimize if needed based on real usage

4. **Seed Script Organization:** Should role prompt content be in separate files per role or all in one seed script?
   - **Recommendation:** Separate files in `prompts/defaults/` for maintainability

---

## Next Steps

**Upon Approval:**
1. Move to **Architect Phase** (PIPELINE-175A)
2. Architect designs:
   - Complete database schema with DDL
   - Repository interfaces and validation logic
   - Seed script structure and content organization
3. Then proceed to BA Phase for detailed acceptance criteria refinement

**Awaiting approval to proceed.**

---

**Epic Status:** ✅ Ready for Architect Phase  
**Created:** 2025-12-04  
**Last Updated:** 2025-12-04 (Surgical Tweaks v1.1)  
**PM Mentor:** Approved  
**Next Phase:** Architect
