# PIPELINE-175B: Data-Driven Pipeline Execution

**Epic Type:** Infrastructure/Refactoring  
**Priority:** P0 - Critical Foundation  
**Estimated Effort:** 5-6 days  
**Depends On:** PIPELINE-175A Complete  
**Status:** Approved for Architect Phase (after 175A)  
**Version:** 1.1 (Surgical Tweaks Applied)

---

## Epic Summary

Refactor pipeline orchestration to use data-driven configuration from 175A. Replace all hardcoded role-specific execution methods with a generic `PhaseExecutorService` that executes any phase using configuration data. This completes the transformation to fully configuration-controlled pipeline execution.

**Key Deliverable:** `PipelineService.advance_phase()` uses `PhaseConfiguration` to determine flow and `PhaseExecutorService` to execute phases generically. Feature flag allows gradual rollout with instant rollback capability.

---

## Business Rationale

### Problem Statement

With 175A complete, we have configuration data but execution still uses hardcoded logic. Each role has dedicated execution methods creating:
- Engineering bottleneck for new roles
- Code duplication across similar execution patterns
- No ability to customize pipeline flows per customer
- Maintenance burden with 5+ role-specific code paths

### Business Value

Switching execution to use configuration data enables:
- **Enterprise Ready:** Customers customize pipelines via configuration
- **Rapid Innovation:** Try new roles/phases in hours, not weeks
- **Reduced Maintenance:** Single execution path replaces per-role methods
- **Future-Proof:** Foundation for REPO-200, LLM-300, CONNECTOR-100

### Risk Management

Feature flag provides:
- Testing in staging before production rollout
- Gradual rollout to users (percentage-based if needed)
- Instant rollback if issues discovered
- Parallel validation (compare old vs new execution)

---

## User Stories

### Story 0: Implement LLMResponseParser

**As a** PhaseExecutor  
**I want** reliable JSON extraction from LLM responses  
**So that** artifacts can be submitted even with chatty or formatted responses

#### Implementation Requirements

**Parser Interface:**

```python
class LLMResponseParser:
    @staticmethod
    def extract_json(response: str, expected_type: str) -> dict:
        """
        Extract JSON from LLM response handling:
        - Direct clean JSON
        - Markdown code fences (```json ... ```)
        - Surrounding explanatory text
        - Multiple JSON blocks (take first valid)
        - Whitespace variations
        
        Args:
            response: Raw LLM response text
            expected_type: Expected artifact type (for error messages)
        
        Returns:
            Parsed JSON as dict
            
        Raises:
            ParseError with response snippet (1000 chars) for debugging
        """
```

**Parsing Strategy (try in order):**
1. **Direct parse:** `json.loads(response.strip())`
2. **Markdown fence stripping:** Remove ` ```json ` and ` ``` `, then parse
3. **Regex extraction:** Find `{...}` substring using regex, then parse
4. **Array extraction:** Find `[...]` if object extraction failed
5. **Failure:** Log full response (truncated), raise `ParseError`

**Error Structure:**

```python
class ParseError(Exception):
    def __init__(self, message: str, response_snippet: str):
        super().__init__(message)
        self.response_snippet = response_snippet
```

#### Acceptance Criteria

**AC-0.1: Clean JSON Parsing**
- Input: `{"epic_id": "TEST-001", "title": "Test"}` → Successfully parsed
- Input with leading/trailing whitespace → Successfully parsed
- Invalid JSON syntax: `{epic_id: "TEST"}` (missing quotes) → ParseError raised with clear message

**AC-0.2: Markdown Fence Handling**
- Input: ` ```json\n{"epic_id": "TEST-001"}\n``` ` → Successfully parsed, fences removed
- Input: ` ```\n{"epic_id": "TEST-001"}\n``` ` (no language tag) → Successfully parsed
- Multiple fenced blocks in response → First valid JSON block extracted and parsed

**AC-0.3: Chatty Response Handling**
- Input: `Here's the epic:\n{"epic_id": "TEST-001"}\nLet me know if you need changes` → JSON extracted successfully
- Input: `Sure! {"epic_id": "TEST-001"} Hope this helps!` → JSON extracted successfully
- Multiple JSON objects in text → First complete object extracted

**AC-0.4: Error Handling & Context (REVISED)**
- Parse failure raises `ParseError` with response snippet (truncated to 1000 chars)
- `ParseError` includes `response_snippet` attribute for debugging
- Parser itself does **not** include pipeline_id or phase (stays pure/reusable)
- `PhaseExecutorService` (Story 1) wraps parse errors with pipeline context in logs
- Error message includes `expected_type` to help debugging

**AC-0.5: Edge Cases**
- Empty response: `""` → ParseError immediately with message "Empty response"
- Only text, no JSON: `"This is just text"` → ParseError after all strategies tried
- Malformed JSON: `{"key": "value"` (unclosed) → ParseError with snippet showing malformed section
- Array when object expected: `[{...}]` → Attempts to use first array element as object

---

### Story 1: Implement PhaseExecutorService

**As a** Pipeline Orchestrator  
**I want** generic phase execution for any role  
**So that** adding roles requires zero code changes

#### Implementation Requirements

**Service Interface:**

```python
class PhaseExecutorService:
    """
    Generic phase executor - works for ANY role/phase combination.
    
    This is the only execution method needed. Adding new roles requires
    NO code changes - just database configuration.
    """
    
    def __init__(self, anthropic_api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize with direct Anthropic API client (MVP).
        
        Designed for future LLM-300 provider swap:
        - LLM calls isolated in separate method
        - API key and model parameterized
        - No Anthropic-specific logic outside LLM call method
        """
        self.api_key = anthropic_api_key
        self.model = model
        self.role_prompt_service = RolePromptService()
        self.artifact_service = ArtifactService()
        self.pipeline_repo = PipelineRepository()
        self.artifact_repo = ArtifactRepository()
        self.usage_repo = PipelinePromptUsageRepository()
        
    async def execute_phase(
        self,
        pipeline_id: str,
        role: str,
        phase: str,
        expected_artifact_type: str
    ) -> Dict[str, Any]:
        """
        Execute any phase with any role.
        
        Returns:
            {
                "artifact_id": str,
                "artifact_type": str,
                "prompt_id": str,
                "payload": dict
            }
        """
```

**Execution Flow:**
1. **Fetch context:** Load pipeline + existing artifacts from repositories
2. **Build prompt:** Call `RolePromptService.build_prompt()` with full context
3. **Execute LLM:** Call Anthropic API with system (prompt) + user (request) messages
4. **Parse response:** Use `LLMResponseParser.extract_json()` to get artifact data
5. **Submit artifact:** Call `ArtifactService.submit_artifact()` for validation
6. **Record usage:** Call `PipelinePromptUsageRepository.record_usage()` for audit
7. **Return result:** Structured dict with artifact_id, type, prompt_id, payload

**Error Handling Strategy:**
- Missing config → raise `ConfigurationError` with helpful message
- LLM timeout → retry once after 5s, then fail with error state
- Parse failure → retry LLM call once with clarifying prompt, then fail
- Validation failure → let `ArtifactService` raise, include context in logs

#### Acceptance Criteria

**AC-1.1: Generic Execution Interface**
- `execute_phase(pipeline_id, "pm", "pm_phase", "epic")` successfully executes PM phase
- `execute_phase(pipeline_id, "architect", "arch_phase", "arch_notes")` successfully executes Architect phase
- `execute_phase(pipeline_id, "ba", "ba_phase", "ba_spec")` successfully executes BA phase
- Method signature accepts any role/phase/artifact_type combination
- No role-specific code paths in implementation (no `if role == "pm"` checks)

**AC-1.2: Context Injection**
- Prompt includes pipeline metadata: `pipeline_id`, `epic_id`, `current_phase`
- Prompt includes all existing artifacts as structured context
- Prompt built via `RolePromptService.build_prompt()` (uses database prompts)
- Context formatted as structured JSON for clarity

**AC-1.3: LLM Integration**
- Anthropic API called with correct model parameter (`claude-sonnet-4-20250514`)
- System message contains full prompt from `RolePromptService`
- User message requests artifact production: `"Execute {phase} and produce {artifact_type}"`
- API errors handled gracefully:
  - Timeout: Retry once after 5s
  - Rate limit: Exponential backoff (5s, 10s)
  - Invalid response: Parse error handling
  - Network error: Clear error message

**AC-1.4: Observability & Structured Logging**
- **Phase start log:**
  - Level: INFO
  - Fields: `pipeline_id`, `phase`, `role`, `prompt_id`, `timestamp`
  
- **LLM call log:**
  - Level: DEBUG
  - Fields: `pipeline_id`, `model`, `input_tokens`, `output_tokens`, `latency_ms`
  
- **Phase complete log:**
  - Level: INFO
  - Fields: `pipeline_id`, `phase`, `artifact_id`, `duration_ms`, `timestamp`
  
- **Error log:**
  - Level: ERROR
  - Fields: `pipeline_id`, `phase`, `role`, `error_type`, `error_message`, `retry_count`

**AC-1.5: Error Handling Strategy**
- **Missing PhaseConfiguration:**
  - Raises: `ConfigurationError("No configuration found for phase 'X'")`
  - Includes: `phase_name` in error message
  
- **Missing RolePrompt:**
  - Raises: `ConfigurationError("No active prompt found for role 'X'")`
  - Includes: `role_name` in error message
  
- **LLM Timeout:**
  - First occurrence: Log warning, retry after 5s
  - Second timeout: Raise error, mark pipeline failed
  - Log includes: `pipeline_id`, retry count, timeout duration
  
- **Parse Failure:**
  - First occurrence: Log full response (truncated), retry LLM with clarifying prompt
  - Clarifying prompt: `"Please return ONLY valid JSON with no surrounding text"`
  - Second failure: Raise `ParseError`, mark pipeline failed
  - PhaseExecutor wraps `ParseError` with pipeline context before logging
  
- **Validation Failure:**
  - `ArtifactService` raises validation error
  - PhaseExecutor logs with pipeline context but doesn't catch (let it propagate)

**AC-1.6: LLM-300 Future Compatibility**
- LLM calls isolated in private method: `_call_llm(messages: List[dict]) -> str`
- Constructor accepts `api_key` and `model` as parameters (not hardcoded)
- No Anthropic-specific logic outside `_call_llm` method
- Interface designed to accept future `LLMProvider` abstraction
- Comments indicate LLM-300 swap points

---

### Story 2: Refactor PipelineService.advance_phase

**As a** Pipeline Orchestrator  
**I want** phase advancement driven by configuration  
**So that** pipeline flow is data-controlled and role-agnostic

#### Implementation Requirements

**Updated PipelineService Method:**

```python
class PipelineService:
    def __init__(self, orchestrator, llm_provider):
        self.phase_config_repo = PhaseConfigurationRepository()
        self.phase_executor = PhaseExecutorService(llm_provider)
        self.pipeline_repo = PipelineRepository()
        self.transition_repo = PhaseTransitionRepository()
    
    async def advance_phase(self, pipeline_id: str) -> PhaseAdvancedResponse:
        """
        Generic phase advancement using PhaseConfiguration.
        
        Replaces all role-specific execution methods.
        """
        # 1. Load current phase config
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        current_config = self.phase_config_repo.get_by_phase(pipeline.current_phase)
        
        # 2. Validate next phase exists
        if not current_config.next_phase:
            raise ValueError(f"Phase {pipeline.current_phase} is terminal")
        
        next_config = self.phase_config_repo.get_by_phase(current_config.next_phase)
        if not next_config:
            raise ConfigurationError(f"Next phase not found: {current_config.next_phase}")
        
        # 3. Update pipeline state
        previous_phase = pipeline.current_phase
        updated_pipeline = self.pipeline_repo.update_state(
            pipeline_id=pipeline_id,
            new_state=next_config.phase_name,
            new_phase=next_config.phase_name
        )
        
        # 4. Record phase transition
        self.transition_repo.create(
            pipeline_id=pipeline_id,
            from_state=previous_phase,
            to_state=next_config.phase_name,
            reason="Phase advancement"
        )
        
        # 5. Execute next phase with configured role
        await self.phase_executor.execute_phase(
            pipeline_id=pipeline_id,
            role=next_config.role_name,
            phase=next_config.phase_name,
            expected_artifact_type=next_config.artifact_type
        )
        
        # 6. Return response
        return PhaseAdvancedResponse(
            pipeline_id=updated_pipeline.pipeline_id,
            previous_phase=previous_phase,
            current_phase=updated_pipeline.current_phase,
            state=updated_pipeline.state,
            updated_at=updated_pipeline.updated_at
        )
```

**Code Removal:**
- Delete `execute_pm_phase()` method
- Delete `execute_architect_phase()` method
- Delete `execute_ba_phase()` method
- Delete `execute_dev_phase()` method
- Delete `execute_qa_phase()` method
- Remove all phase-specific conditional logic
- Remove all role-specific imports

#### Acceptance Criteria

**AC-2.1: Generic Phase Advancement**
- `advance_phase(pipeline_id)` works for any phase without role-specific code
- Method loads `PhaseConfiguration` to determine next phase and role
- Method calls generic `PhaseExecutor.execute_phase()` with configured parameters
- No hardcoded role checks (zero occurrences of `if phase == "pm_phase"` or similar)
- No hardcoded artifact type mappings

**AC-2.2: State Machine Logic**
- Current phase configuration loaded successfully from database
- `next_phase` validated to exist before state transition
- Pipeline `state` and `current_phase` updated atomically (single transaction)
- Phase transition recorded in `phase_transitions` table with timestamp
- Terminal phases (next_phase=null) handled correctly:
  - Attempting to advance from terminal phase raises clear error
  - Error message: `"Phase X is terminal - cannot advance"`

**AC-2.3: Error Handling**
- Missing current phase config → raises `ConfigurationError("No config for phase 'X'")`
- Missing next phase config → raises `ConfigurationError("Next phase 'Y' not found")`
- Inactive phase config → raises `ConfigurationError("Phase 'X' is not active")`
- Terminal phase advancement → raises `ValueError("Phase 'X' is terminal")`
- All errors include full context: `pipeline_id`, `current_phase`, expected `next_phase`

**AC-2.4: Code Cleanup Complete**
- All role-specific execution methods deleted from codebase
- All phase-specific conditionals removed from orchestration logic
- Phase advancement logic <50 lines (excluding error handling and logging)
- No imports of role-specific modules in `PipelineService`
- Grep for `execute_pm_phase` → 0 results (except legacy/ and tests)
- Grep for `if.*phase.*==.*"pm_phase"` in services/ → 0 results

**AC-2.5: Behavior Preservation**
- API endpoint responses maintain identical format (no breaking changes)
- Phase sequence remains same: PM → Arch → BA → Dev → QA → Commit
- Artifact validation rules unchanged (still enforced by `ArtifactService`)
- Performance within 10% of PIPELINE-150 baseline
- All timing/latency characteristics similar

---

### Story 3: Feature Flag & Migration Strategy

**As a** System Administrator  
**I want** controlled rollout of new execution logic  
**So that** risk is minimized and instant rollback is possible

#### Implementation Requirements

**Feature Flag Implementation:**

```python
# config.py or environment variable
DATA_DRIVEN_ORCHESTRATION = os.getenv("DATA_DRIVEN_ORCHESTRATION", "false").lower() == "true"

# In PipelineService
async def advance_phase(self, pipeline_id: str) -> PhaseAdvancedResponse:
    """Advance pipeline to next phase."""
    if DATA_DRIVEN_ORCHESTRATION:
        return await self._advance_phase_data_driven(pipeline_id)
    else:
        return await self._advance_phase_legacy(pipeline_id)

async def _advance_phase_data_driven(self, pipeline_id: str):
    """New data-driven implementation (Story 2)."""
    # ... new implementation from Story 2 ...

async def _advance_phase_legacy(self, pipeline_id: str):
    """Legacy hardcoded implementation (PIPELINE-150 preserved)."""
    # ... original PIPELINE-150 logic ...
```

**Code Organization:**

```
app/orchestrator_api/services/
├── pipeline_service.py             # Feature flag dispatch
├── phase_executor_service.py       # New generic executor
├── role_prompt_service.py          # Prompt building
├── legacy/                          # ⚠️ DEPRECATED - Removal scheduled
│   ├── README.md                   # "Scheduled for removal [DATE]"
│   └── pipeline_service_legacy.py  # Original PIPELINE-150 methods
```

**Runtime Warning When Legacy Active:**

```python
async def _advance_phase_legacy(self, pipeline_id: str):
    log_warning(
        "Legacy orchestration mode active - DEPRECATED",
        extra={
            "pipeline_id": pipeline_id,
            "deprecation_notice": "Legacy mode will be removed on 2025-01-15",
            "migration_guide": "https://docs.thecombine.ai/migration-175b.md"
        }
    )
    # ... legacy logic ...
```

**Migration Documentation:**

1. **Migration Guide (`docs/migration-175b.md`):**
   - How to enable data-driven mode
   - How to verify correct operation
   - Performance comparison checklist
   - Rollback procedure
   - Troubleshooting common issues

2. **Deprecation Timeline:**
   - **Data-driven mode:** Production-ready on 175B completion
   - **Legacy support period:** 2 weeks post-deployment (validation window)
   - **Migration deadline:** All pipelines on data-driven within 30 days
   - **Legacy code removal:** 30 days post-deployment (scheduled date in code comments)

#### Acceptance Criteria

**AC-3.1: Feature Flag Functional**
- Environment variable `DATA_DRIVEN_ORCHESTRATION` controls execution mode
- Default value is `"false"` (legacy mode) for safety during rollout
- Can be toggled via environment variable without code deployment
- Both execution modes functional and tested
- Feature flag value logged on service initialization

**AC-3.2: Migration Documentation & Deprecation Timeline (ENHANCED)**
- Migration guide documents:
  - Step-by-step enablement procedure
  - Validation steps to confirm correct operation
  - Performance comparison methodology
  - Rollback procedure if issues found
  
- **Deprecation timeline explicitly documented:**
  - **Data-driven mode:** Production-ready on 175B completion
  - **Legacy mode support:** 2 weeks post-deployment for validation
  - **Legacy code removal:** 30 days post-deployment (specific date documented in code)
  - **Migration deadline:** All production pipelines must use data-driven mode within 30 days

- **Code clearly marked:**
  - `services/legacy/README.md` contains: `"DEPRECATED - Removal scheduled 2025-01-15"`
  - Docstring on legacy methods: `"@deprecated Will be removed 2025-01-15"`
  - Runtime warning if legacy mode active (see implementation above)

**AC-3.3: Testing Both Modes**
- Test suite runs with both flag values (`true` and `false`)
- CI/CD pipeline tests both execution modes
- Integration test explicitly validates feature flag toggle
- Behavior comparison test validates outputs identical between modes
- Performance comparison: data-driven within 10% of legacy

**AC-3.4: Rollback Safety**
- Can disable data-driven mode by setting `DATA_DRIVEN_ORCHESTRATION=false`
- Rollback requires only environment variable change (no code deployment)
- No data loss when switching modes (database state compatible)
- Clear logging indicates active mode on every phase advancement
- Rollback procedure tested in staging environment

---

### Story 4: End-to-End & Regression Testing

**As a** Quality Engineer  
**I want** comprehensive test coverage of data-driven execution  
**So that** production rollout is safe and regressions caught early

#### Implementation Requirements

**Test Categories:**

1. **Unit Tests:**
   - `LLMResponseParser.extract_json()` with all edge cases
   - `PhaseExecutorService` methods (mocked LLM calls)
   - `PipelineService._advance_phase_data_driven()` logic
   - Feature flag dispatch logic

2. **Integration Tests:**
   - Full pipeline execution: PM → Architect phases using data config
   - Add new role via data configuration only
   - Custom pipeline flow with different phase order
   - Prompt versioning workflow

3. **Regression Tests:**
   - All PIPELINE-150 tests pass in legacy mode
   - API endpoints unchanged
   - Performance within tolerance

4. **Feature Flag Tests:**
   - Toggle validation (both modes work)
   - Output comparison (identical results)
   - Performance comparison

#### Acceptance Criteria

**AC-4.1: Parser Unit Tests**
- **Clean JSON cases:**
  - Valid JSON object parsed correctly
  - Valid JSON array parsed correctly
  - Whitespace variations handled
  - Unicode characters preserved

- **Markdown fence cases:**
  - ` ```json ` fences stripped correctly
  - ` ``` ` (no language) fences stripped correctly
  - Multiple fenced blocks (first taken)

- **Chatty response cases:**
  - JSON surrounded by explanatory text extracted
  - Multiple JSON objects (first taken)
  - JSON in middle of long response extracted

- **Error cases:**
  - Empty response raises `ParseError`
  - Only text raises `ParseError`
  - Malformed JSON raises `ParseError` with snippet
  - All errors include `response_snippet` attribute

- **Coverage:** 100% line and branch coverage for parser

**AC-4.2: Executor Unit Tests**
- Generic execution tested with mocked dependencies
- Context injection verified (pipeline, artifacts in prompt)
- Error handling for each failure mode (timeout, parse, validation)
- LLM integration isolated (mocked for unit tests)
- Logging output verified for all scenarios
- **Coverage:** 100% line coverage, >95% branch coverage

**AC-4.3: Integration Test - Standard Pipeline Execution**
- Test creates pipeline for epic "TEST-INTEGRATION-001"
- Advances through PM → Architect phases using data-driven execution
- Validates PM artifact (Epic) submitted correctly with proper schema
- Validates Architect artifact (ArchNotes) submitted correctly
- Verifies prompt usage recorded in `pipeline_prompt_usage` table (2 records)
- Confirms phase transitions recorded (2 transitions)
- **Total execution time:** <30 seconds for 2 phases

**AC-4.4: Integration Test - Custom Role Addition**
- Test adds new "security_reviewer" role via `RolePromptRepository.create()`
- Inserts new "security_phase" via `PhaseConfigurationRepository.create()`
- Updates QA phase config to point to security_phase (not commit_phase)
- Creates pipeline and advances to security phase
- Validates security artifact submitted correctly
- **Verification:** Zero code changes required (pure data configuration)
- Test demonstrates data-only role addition

**AC-4.5: Integration Test - Prompt Versioning**
- Test creates PM prompt version 1.0 (seeded)
- Executes pipeline using PM v1.0, records prompt_id
- Creates PM prompt version 2.0 with different content
- Sets v2.0 as active (deactivates v1.0)
- Executes second pipeline using PM v2.0
- Queries `pipeline_prompt_usage` table confirms:
  - Pipeline 1 used prompt v1.0 ID
  - Pipeline 2 used prompt v2.0 ID
- Demonstrates auditability of prompt versions

**AC-4.6: Regression Test - PIPELINE-150 Compatibility**
- All 20 existing tests in `tests/test_orchestrator_api/` pass with flag=false
- No test modifications required for legacy mode
- API response schemas identical to PIPELINE-150 format
- Response timing characteristics similar (within 10% variance)
- All endpoints behave identically from client perspective

**AC-4.7: Feature Flag Tests**
- Test toggles flag between `true` and `false`
- Verifies both modes execute successfully
- Compares outputs between modes (should be identical):
  - Same artifacts created
  - Same phase transitions
  - Same final pipeline state
- Performance comparison: <10% variance between modes
- Test validates rollback scenario (flag true → false mid-pipeline)

**AC-4.8: Test Organization**
- Unit tests in `tests/test_orchestrator_api/test_llm_parser.py`
- Unit tests in `tests/test_orchestrator_api/test_phase_executor.py`
- Integration tests in `tests/test_orchestrator_api/test_data_driven_execution.py`
- Regression tests reuse existing `tests/test_orchestrator_api/test_*.py` files
- Feature flag tests in `tests/test_orchestrator_api/test_feature_flag.py`
- Performance comparison in `tests/test_orchestrator_api/test_performance_comparison.py`

---

## Epic-Level Acceptance Criteria

### AC-E1: Fully Data-Driven Pipeline Execution

**Given** feature flag enabled (`DATA_DRIVEN_ORCHESTRATION=true`)  
**When** advancing any phase in any pipeline  
**Then** execution uses `PhaseExecutorService.execute_phase(pipeline_id, role, phase, artifact_type)` with all parameters loaded from `PhaseConfiguration`, and zero role-specific code paths exist in orchestration logic

**Verification:**
- Grep codebase for `"execute_pm_phase"`, `"execute_architect_phase"` → 0 results (except in `services/legacy/`)
- Grep orchestration code for `if.*phase.*==.*"pm_phase"` → 0 results (except legacy)
- Code review confirms generic execution method used exclusively
- All phase advancements logged with `"mode": "data_driven"` in structured logs

---

### AC-E2: Configuration-Only Role Addition

**Given** no code changes to application  
**When** inserting new role in `role_prompts` table and new phase in `phase_configurations` table via seed script or SQL  
**Then** pipeline executes new phase successfully with new role and produces valid artifact

**Verification:**
- Manual test: Add "security_reviewer" role via seed script or SQL insert
- Add "security_phase" config pointing to security_reviewer
- Update QA phase to transition to security_phase
- Execute pipeline end-to-end including security phase
- Validate security artifact submitted and stored correctly
- **Confirm:** Zero code changes, zero deployments required for role addition

---

### AC-E3: Complete Prompt Auditability

**Given** any pipeline execution in data-driven mode  
**When** any phase completes  
**Then** `pipeline_prompt_usage` table contains record with complete metadata

**Verification:**
- Execute standard 6-phase pipeline
- Query `pipeline_prompt_usage` WHERE `pipeline_id` = X
- Confirm 6 records exist (one per phase: PM, Arch, BA, Dev, QA, Commit)
- Each record has correct:
  - `role_name` (pm, architect, ba, dev, qa, commit)
  - `phase_name` (pm_phase, arch_phase, etc.)
  - `prompt_id` (matches active prompt for that role)
  - `used_at` timestamp
- Timestamps chronologically ordered (PM first, Commit last)

---

### AC-E4: Standard Pipeline Runs End-to-End

**Given** feature flag enabled and freshly seeded database  
**When** creating pipeline and advancing through all phases  
**Then** pipeline progresses PM → Architect → BA → Dev → QA → Commit (stub) → Complete with all artifacts validated and stored correctly

**Verification:**
- Integration test executes full 6-phase pipeline
- Each phase produces expected artifact type:
  - PM: Epic
  - Architect: ArchNotes
  - BA: BASpec
  - Dev: ProposedChangeSet
  - QA: QAResult
  - Commit: CommitResult (stub)
- All artifacts pass Pydantic schema validation
- Final pipeline state is `"complete"`
- All 6 phase transitions recorded in `phase_transitions` table
- Total execution time: <5 minutes for full pipeline

---

### AC-E5: Backward Compatibility Maintained

**Given** PIPELINE-150 implementation complete and 175B deployed  
**When** feature flag disabled (`DATA_DRIVEN_ORCHESTRATION=false`)  
**Then** all PIPELINE-150 tests pass without modification, API endpoints behave identically, and existing pipelines complete successfully

**Verification:**
- Run full PIPELINE-150 test suite with flag=false → 20/20 tests pass
- No test file modifications required
- API integration tests show identical response schemas
- Manual verification: existing in-flight pipeline completes in legacy mode
- Performance metrics: within 10% of PIPELINE-150 baseline
- No breaking changes in API contracts (OpenAPI spec unchanged)

---

### AC-E6: Safe Rollout & Instant Rollback

**Given** feature flag deployed with data-driven mode enabled  
**When** toggling flag between `true` and `false`  
**Then** can enable/disable data-driven mode via environment variable without code deployment, with instant rollback capability

**Verification:**
- Set `DATA_DRIVEN_ORCHESTRATION=true` in environment
- Restart service, verify logs show `"orchestration_mode": "data_driven"`
- Execute test pipeline, confirm data-driven execution
- Set `DATA_DRIVEN_ORCHESTRATION=false` (simulated rollback)
- Restart service, verify logs show `"orchestration_mode": "legacy"`
- Execute test pipeline, confirm legacy execution
- Both modes produce identical outputs
- No data loss or corruption during mode switches
- Rollback procedure documented and tested in staging

---

### AC-E7: Legacy Code Removal Scheduled (NEW)

**Given** 175B deployed to production  
**When** 30 days elapsed since deployment  
**Then** legacy orchestration code deleted from codebase, only data-driven path remains

**Verification:**
- **On deployment day:** Cleanup ticket created: `"PIPELINE-175-CLEANUP: Remove legacy orchestration"`
- **Ticket scheduled for:** Deployment date + 30 days (specific date documented)
- **Ticket includes checklist:**
  - [ ] Verify all production pipelines confirmed on data-driven mode (monitoring dashboard)
  - [ ] Verify no legacy mode warnings in logs for 7 days
  - [ ] Delete `services/legacy/` directory entirely
  - [ ] Remove feature flag dispatch logic (make data-driven the only path)
  - [ ] Update documentation to remove legacy references
- **Ticket reviewed and merged on schedule**
- **Post-cleanup verification:**
  - Grep for `"_advance_phase_legacy"` → 0 results
  - Grep for `"DATA_DRIVEN_ORCHESTRATION"` → 0 results (flag removed)
  - Only data-driven execution path remains

---

## Dependencies

### Internal Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| **PIPELINE-175A Complete** | ⚠️ Prerequisite | Must be fully complete and deployed before 175B starts |
| **Anthropic API Key** | ⚠️ Required | Verify configured in deployment environment |
| **Artifact Schemas** | ✅ Ready | Pydantic models stable in `workforce/schemas/artifacts.py` |
| **Database Seeded** | ⚠️ Required | 175A seed scripts must have run successfully |

### Blocks These Epics

- ✋ **REPO-200** - RepoProvider abstraction (commit role becomes fully data-driven)
- ✋ **PIPELINE-200** - PR-only commit phase (uses generic executor from 175B)
- ✋ **LLM-300** - Pluggable LLM providers (executor designed for provider swap)

---

## Risks & Mitigation

### Risk 1: LLM Response Parsing Brittleness

**Risk Level:** 🟡 Medium  
**Likelihood:** High (LLMs vary response format unpredictably)  
**Impact:** Medium (blocks pipeline execution if parse fails)

**Mitigation:**
- Multiple parsing strategies in `LLMResponseParser` (direct, fence-stripped, regex)
- Retry logic: If parse fails, retry LLM with clarifying prompt once
- Comprehensive test coverage: 20+ edge cases in parser tests
- Fallback: Log full response for manual review if all strategies fail
- Monitoring: Alert on parse failure rate >5%

---

### Risk 2: Performance Regression from Database Lookups

**Risk Level:** 🟢 Low  
**Likelihood:** Low (database queries are fast with proper indexes)  
**Impact:** Low (slight latency increase, but likely <10ms)

**Mitigation:**
- Database indexes on all lookup fields (`role_name`, `phase_name`, `is_active`)
- Performance tests validate <10ms for config lookups
- Database connection pooling configured (avoid connection overhead)
- Query optimization if needed (already very simple queries)
- Monitoring: Track p95 latency for phase advancement

---

### Risk 3: Execution Logic Bugs in Refactoring

**Risk Level:** 🟡 Medium  
**Likelihood:** Medium (refactoring changes execution paths)  
**Impact:** High (could break pipeline execution)

**Mitigation:**
- Feature flag allows instant rollback to legacy code
- Extensive testing: unit, integration, regression, and E2E tests
- Gradual rollout: Enable for 10% of pipelines first, then increase
- Canary deployment: Test in staging for 1 week before production
- Monitoring: Compare success rates between legacy and data-driven modes
- Rollback procedure tested and documented

---

### Risk 4: Migration Breaking In-Flight Pipelines

**Risk Level:** 🟡 Medium  
**Likelihood:** Medium (pipelines may be mid-execution during deployment)  
**Impact:** High (user disruption if pipelines fail mid-flight)

**Mitigation:**
- Feature flag defaults to `false` (legacy mode) initially
- "Drain mode" option: Let existing pipelines complete in legacy, new ones use data-driven
- Backward compatibility tests ensure both modes work
- 2-week legacy support period allows safe migration
- Clear communication to users about migration timeline
- Ability to mark specific pipelines as "legacy-only" if needed

---

### Risk 5: Feature Flag Configuration Errors

**Risk Level:** 🟢 Low  
**Likelihood:** Low (simple boolean flag)  
**Impact:** Medium (wrong mode active if misconfigured)

**Mitigation:**
- Flag value logged on service initialization (visible in logs immediately)
- Health check endpoint reports current mode: `/health` includes `"orchestration_mode": "data_driven|legacy"`
- Monitoring alert if mode doesn't match expected value
- Configuration validation on startup (flag must be "true" or "false")
- Documentation clearly explains flag behavior

---

## Success Metrics

### Functional Metrics
- ✅ All 4 stories completed with ACs satisfied
- ✅ All 7 epic-level ACs verified
- ✅ Feature flag functional (both modes work)
- ✅ Zero code changes required to add new role (verified via security_reviewer test)
- ✅ All PIPELINE-150 tests pass in legacy mode

### Quality Metrics
- ✅ Code coverage >90% for new code
- ✅ All unit tests pass (parser, executor, service)
- ✅ All integration tests pass (E2E, custom role, versioning)
- ✅ All regression tests pass (PIPELINE-150 compatibility)
- ✅ Performance within 10% of PIPELINE-150 baseline
- ✅ Zero critical bugs in QA phase

### Business Metrics
- ✅ Time to add new role: <1 hour (vs weeks previously)
- ✅ Lines of orchestration code reduced by >50%
- ✅ Foundation ready for REPO-200, LLM-300, CONNECTOR-100
- ✅ Enterprise customer demos possible (custom pipeline flows via config)
- ✅ Complete audit trail available (compliance requirement met)

---

## Technical Notes

### Architecture Decisions

**ADR-001: Direct Anthropic API vs LLMProvider Abstraction**
- **Decision:** Use direct Anthropic API calls in PhaseExecutor (not abstracted LLMProvider yet)
- **Rationale:** LLM-300 not yet implemented; don't want to block 175B on it
- **Consequence:** PhaseExecutor designed for future swap but uses direct API calls initially
- **Swap Points:** Isolated in `_call_llm()` method, ready for LLM-300 provider injection
- **Future:** LLM-300 will replace direct API calls with pluggable provider abstraction

**ADR-002: Feature Flag Strategy**
- **Decision:** Use simple boolean environment variable, not percentage-based rollout
- **Rationale:** Simpler to reason about, easier to debug, sufficient for controlled rollout
- **Consequence:** All-or-nothing per deployment, but can control per environment (staging vs prod)
- **Alternative Considered:** Percentage-based rollout (10% → 50% → 100%) - deferred to operations team if needed
- **Future:** Could add percentage logic if needed, but boolean sufficient for MVP

**ADR-003: Legacy Code Retention Period**
- **Decision:** Keep legacy code for 30 days post-deployment, then remove
- **Rationale:** Gives time for validation and migration, but forces cleanup
- **Consequence:** Must actively monitor and plan removal, can't let "temporary" code linger
- **Cleanup Ticket:** Created on deployment day, scheduled for +30 days
- **Future:** If needed, can extend by updating ticket, but default is removal

---

### Error Handling Flow

```
PhaseExecutorService.execute_phase()
    ↓
1. Load context from repositories
    ├─ Pipeline not found → ConfigurationError
    ├─ Phase config not found → ConfigurationError
    └─ Role prompt not found → ConfigurationError
    ↓
2. Build prompt via RolePromptService
    └─ Returns (prompt_text, prompt_id)
    ↓
3. Call LLM via Anthropic API
    ├─ Timeout → retry once (5s delay) → fail if second timeout
    ├─ Rate limit → exponential backoff (5s, 10s, 20s)
    └─ Network error → fail with clear message
    ↓
4. Parse response via LLMResponseParser
    ├─ Parse success → artifact_data (dict)
    ├─ Parse failure → log full response, retry LLM with clarifying prompt
    └─ Second parse failure → raise ParseError with context
    ↓
5. PhaseExecutor wraps ParseError with pipeline context
    └─ Logs: pipeline_id, phase, role, error, response_snippet
    ↓
6. Submit artifact via ArtifactService
    ├─ Validation success → artifact_id
    └─ Validation failure → raises ValidationError (let propagate)
    ↓
7. Record usage via PipelinePromptUsageRepository
    └─ Stores: pipeline_id, role_name, prompt_id, phase_name, timestamp
    ↓
8. Return result
    └─ {artifact_id, artifact_type, prompt_id, payload}
```

---

### Logging Strategy

**Log Levels:**
- **INFO:** Phase start, phase complete, mode switch
- **DEBUG:** LLM calls, prompt building, database queries
- **WARNING:** Legacy mode active (deprecation warning), retry attempts
- **ERROR:** Parse failures, validation failures, configuration errors

**Structured Log Fields:**
- Every log includes: `timestamp`, `pipeline_id`, `phase`, `role`
- LLM logs add: `model`, `input_tokens`, `output_tokens`, `latency_ms`
- Error logs add: `error_type`, `error_message`, `stack_trace` (if exception)

**Example Logs:**

```json
// Phase start
{
  "level": "INFO",
  "timestamp": "2025-01-15T10:30:45Z",
  "pipeline_id": "pip_abc123",
  "phase": "pm_phase",
  "role": "pm",
  "prompt_id": "rp_xyz789",
  "message": "Phase execution started",
  "mode": "data_driven"
}

// LLM call
{
  "level": "DEBUG",
  "timestamp": "2025-01-15T10:30:46Z",
  "pipeline_id": "pip_abc123",
  "model": "claude-sonnet-4-20250514",
  "input_tokens": 2450,
  "output_tokens": 850,
  "latency_ms": 3200,
  "message": "LLM call completed"
}

// Phase complete
{
  "level": "INFO",
  "timestamp": "2025-01-15T10:30:48Z",
  "pipeline_id": "pip_abc123",
  "phase": "pm_phase",
  "artifact_id": "art_def456",
  "duration_ms": 3500,
  "message": "Phase execution completed"
}
```

---

## Estimated Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Architect Phase** | 0.5 days | Service interfaces, error handling design, sequence diagrams |
| **BA Phase** | 1 day | Detailed story ACs, test case specifications, edge case documentation |
| **Dev Phase** | 4 days | All 4 stories implemented (parser, executor, refactor, flag), tests passing |
| **QA Phase** | 1.5 days | Integration tests, regression validation, performance comparison, rollback testing |
| **Total** | **7 days** | Complete data-driven execution with feature flag |

---

## Open Questions for Architect/BA Phase

1. **LLM Retry Strategy:** Should we retry on parse failure with a different prompt, or just fail immediately?
   - **Recommendation:** Retry once with clarifying prompt, then fail (gives LLM second chance)

2. **Performance Monitoring:** What latency threshold should trigger alerts?
   - **Recommendation:** p95 > 5 seconds for full phase execution

3. **Rollback Procedure:** Should rollback require service restart or should it be hot-reloadable?
   - **Recommendation:** Require restart for simplicity (environment variable changes need restart anyway)

4. **Legacy Code Location:** Should legacy code be in `services/legacy/` or just marked with `@deprecated`?
   - **Recommendation:** Separate directory (`services/legacy/`) for clear isolation and easy removal

5. **Feature Flag Granularity:** Should flag be per-deployment, per-pipeline, or per-user?
   - **Recommendation:** Per-deployment for MVP (simplest), can add per-pipeline if needed later

---

## Next Steps

**Upon Approval of 175B (after 175A complete):**
1. Move to **Architect Phase** (PIPELINE-175B)
2. Architect designs:
   - `PhaseExecutorService` detailed interface and flow
   - `LLMResponseParser` strategy and error handling
   - Feature flag implementation and rollback procedure
   - Logging and monitoring strategy
3. Then proceed to BA Phase for detailed acceptance criteria refinement

**Prerequisite:** PIPELINE-175A must be complete, deployed, and verified working before 175B starts

---

**Epic Status:** ✅ Ready for Architect Phase (after 175A)  
**Created:** 2025-12-04  
**Last Updated:** 2025-12-04 (Surgical Tweaks v1.1)  
**PM Mentor:** Approved  
**Depends On:** PIPELINE-175A Complete  
**Next Phase:** Architect (after 175A)
