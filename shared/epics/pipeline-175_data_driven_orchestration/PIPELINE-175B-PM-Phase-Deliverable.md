# PIPELINE-175B: PM Phase Deliverable

**Epic:** Execution Layer — PhaseExecutorService & LLMResponseParser  
**PM Mentor Team:** PM-A (Senior), PM-B (Mid), PM-C (Junior)  
**Date:** 2025-12-05  
**Status:** Ready for Architecture Review

---

## Executive Summary

PIPELINE-175B delivers the execution engine that transforms our data infrastructure (175A) into a working orchestration system. This epic introduces two core components that enable generic, configuration-driven phase execution while maintaining strict backward compatibility through feature-flag isolation.

**Key Insight:** This is the "make it work" epic. 175A built the data layer; 175B makes pipelines actually use it. Success means a PM→Architect flow executing end-to-end with zero hardcoded prompts.

**Epic Scope:** Tightly focused on execution mechanics. Multi-artifact support, LLM abstraction, and admin tooling are explicitly deferred to future epics.

---

## Story List (5 Stories)

1. **LLMResponseParser - Core Parsing Engine** (Medium, 3-5 days)
2. **PhaseExecutorService - Generic Execution Engine** (High, 5-8 days)
3. **Feature Flag Integration into PipelineService** (Medium, 2-3 days)
4. **End-to-End Integration Testing** (Medium, 3-4 days)
5. **Documentation & Deployment Preparation** (Low, 2 days)

**Total Estimated Duration:** 15-22 days  
**Recommended Parallelization:** Story 1 can start immediately; Story 2 depends on Story 1; Stories 3-5 sequential after Story 2

---

## Story 1: LLMResponseParser - Core Parsing Engine

**Owner:** PM-A (Senior) → Architecture → Dev  
**Complexity:** Medium  
**Estimated Effort:** 3-5 days  
**Dependencies:** None (pure utility component)

### User Story

As a PhaseExecutorService, I need to reliably extract JSON artifacts from LLM responses that may contain markdown fences, explanatory text, or malformed JSON, so that I can capture work products regardless of LLM output format variations.

### Context

LLMs frequently wrap JSON in markdown fences (```json), add explanatory text before/after the artifact, or produce slightly malformed JSON. We need robust parsing that attempts multiple strategies and provides clear diagnostics on failure.

### Acceptance Criteria

**AC1.1 - Strategy Pattern Implementation**
- LLMResponseParser implements strategy pattern with ordered list of parsing strategies
- Strategies execute in sequence: DirectParse → MarkdownFence → FuzzyBoundary
- First successful parse returns immediately; subsequent strategies skipped
- Returns ParseResult dataclass with:
  - `success: bool`
  - `data: Optional[Dict[str, Any]]`
  - `strategy_used: Optional[str]`
  - `error_messages: List[str]` (from all failed strategies)
- All strategies return None on failure (no exceptions raised)

**AC1.2 - Direct Parse Strategy**
- Attempts `json.loads()` on entire response string
- Pre-processing: strips leading/trailing whitespace
- Pre-processing: removes common prefixes like "Here is the JSON:", "Result:", etc.
- Returns parsed dict on success, None on JSONDecodeError
- Logs reason for failure to error_messages

**AC1.3 - Markdown Fence Strategy**
- Detects code fences with regex: ` ```json`, ` ```JSON`, ` ``` ` (backticks with optional language)
- Extracts content between opening and closing fence
- If multiple fences exist, extracts the largest JSON block
- Attempts json.loads() on extracted content
- Returns parsed dict on success, None if no fences or parse fails
- Logs reason for failure to error_messages

**AC1.4 - Fuzzy Boundary Strategy**
- Finds first `{` and last `}` in response text
- Extracts substring from first `{` to last `}` inclusive
- Attempts json.loads() on extracted content
- Returns parsed dict on success, None if boundaries not found or parse fails
- Logs reason for failure to error_messages

**AC1.5 - Error Handling & Diagnostics**
- All parsing exceptions caught and converted to error messages
- ParseResult with success=False includes all attempted strategies
- Error messages are developer-friendly (include snippet of problematic text)
- Invalid input types (None, non-string) return ParseResult(success=False, error="Invalid input type")

**AC1.6 - Test Coverage**
- Clean JSON response (direct parse succeeds)
- JSON in triple-backtick markdown fence
- JSON in fence with language specifier (```json)
- JSON with explanatory text before and after
- Multiple JSON blocks (largest extracted)
- Malformed JSON (all strategies fail gracefully)
- Empty string input
- None input
- Non-string input (int, dict, etc.)
- Nested JSON objects
- JSON arrays (should work)
- Edge case: text with `{` and `}` but not valid JSON

**AC1.7 - Performance**
- Parsing completes in <100ms for responses up to 10KB
- No regex catastrophic backtracking on malicious input

### Definition of Done

- [ ] `LLMResponseParser` class implemented in `app/orchestrator_api/services/llm_response_parser.py`
- [ ] `ParseResult` dataclass defined with all fields
- [ ] All three strategies implemented and tested independently
- [ ] 15+ unit tests covering all acceptance criteria
- [ ] All tests passing
- [ ] Docstrings on all public methods
- [ ] No external dependencies beyond standard library (json, re)

### Edge Cases & Risks

**Edge Case 1:** Response contains multiple valid JSON blocks  
**Mitigation:** Markdown strategy extracts largest; document this behavior

**Edge Case 2:** Response is valid JSON but not an object (e.g., JSON array)  
**Decision:** Support arrays; artifact validation happens in PhaseExecutorService

**Risk 1:** LLM returns 50KB response with JSON buried in middle  
**Mitigation:** FuzzyBoundary strategy handles this; may be slow but acceptable for 175B

---

## Story 2: PhaseExecutorService - Generic Execution Engine

**Owner:** PM-A (Senior) → Architecture → Dev  
**Complexity:** High  
**Estimated Effort:** 5-8 days  
**Dependencies:** Story 1 (LLMResponseParser)

### User Story

As a PipelineService, I need a generic phase executor that can run any configured phase using database-defined prompts and configurations, so that I can eliminate hardcoded execution methods and support dynamic workflow changes.

### Context

This is the core execution engine. It orchestrates: config loading → prompt building → LLM invocation → response parsing → artifact validation → usage recording. This replaces all `execute_pm_phase()`, `execute_architect_phase()`, etc. methods.

### Acceptance Criteria

**AC2.1 - Service Initialization**
- PhaseExecutorService accepts dependencies via constructor:
  - `role_prompt_service: RolePromptService`
  - `phase_config_repo: PhaseConfigurationRepository`
  - `usage_repo: PipelinePromptUsageRepository`
  - `parser: LLMResponseParser`
  - `anthropic_client: anthropic.Anthropic`
- All dependencies injected (no hard instantiation inside service)
- Service is stateless (no instance variables beyond dependencies)
- Supports mock injection for testing

**AC2.2 - execute_phase Method Signature**
```python
def execute_phase(
    self,
    pipeline_id: str,
    phase_name: str,
    epic_context: str,
    pipeline_state: Dict[str, Any],
    artifacts: Dict[str, Any]
) -> PhaseExecutionResult
```

**AC2.3 - Phase Configuration Loading**
- Calls `phase_config_repo.get_by_phase(phase_name)`
- Raises `ExecutionError` if phase config not found
- Raises `ExecutionError` if phase config not active
- Extracts: `role_name`, `artifact_type`, `next_phase` from config
- Logs: "Executing phase {phase_name} with role {role_name}"

**AC2.4 - Prompt Building**
- Calls `role_prompt_service.build_prompt()` with full context:
  - role_name (from config)
  - pipeline_id
  - phase_name
  - epic_context
  - pipeline_state
  - artifacts
- Receives: `(prompt_text, prompt_id)`
- Raises `ExecutionError` if prompt building fails (e.g., no active prompt)
- Logs prompt_id for audit trail

**AC2.5 - LLM Invocation (Direct Anthropic)**
- Creates message via Anthropic client:
  ```python
  response = anthropic_client.messages.create(
      model="claude-sonnet-4-20250514",
      max_tokens=4096,
      temperature=0.7,
      system=prompt_text,
      messages=[{"role": "user", "content": "Please proceed with this phase."}]
  )
  ```
- Extracts response text from `response.content[0].text`
- Raises `ExecutionError` on API errors with full error context
- Logs: LLM invocation time, token usage (if available)

**AC2.6 - Response Parsing**
- Passes LLM response text to `parser.parse(response_text)`
- Checks `ParseResult.success`
- If parse fails: raises `ExecutionError` with parser diagnostics
- Validates artifact is a dict (not array, string, etc.)
- Does NOT validate artifact schema (that's future work)

**AC2.7 - Usage Recording**
- Calls `usage_repo.record_usage()` with:
  - pipeline_id
  - prompt_id (from step 2.4)
  - role_name (from config)
  - phase_name
- Recording happens AFTER successful parse (on success path only)
- If usage recording fails: log warning but don't fail execution
- Rationale: Audit trail failure shouldn't block pipeline progress

**AC2.8 - Result Assembly**
- Returns `PhaseExecutionResult` dataclass containing:
  - `success: bool` (always True if method completes; exceptions on failure)
  - `artifact: Dict[str, Any]` (parsed artifact)
  - `artifact_type: str` (from config)
  - `next_phase: Optional[str]` (from config)
  - `prompt_id: str` (for audit)
  - `llm_response_raw: str` (full LLM response for debugging)
  - `execution_time_ms: int` (time spent in LLM call)

**AC2.9 - Error Handling**
- All errors raise `ExecutionError` (custom exception class)
- Error messages include:
  - pipeline_id
  - phase_name
  - Specific failure reason (config missing, prompt build failed, LLM error, parse error)
  - Relevant context (e.g., parser error messages)
- Errors do NOT partially update any state
- Errors are logged with full context before raising

**AC2.10 - Logging**
- Log at start: "Executing phase {phase_name} for pipeline {pipeline_id}"
- Log after prompt build: "Built prompt using {prompt_id}"
- Log after LLM call: "LLM responded in {time}ms with {tokens} tokens"
- Log after parse: "Parsed artifact type {artifact_type}"
- Log after usage record: "Recorded usage {usage_id}"
- Log on error: Full error context

### Definition of Done

- [ ] `PhaseExecutorService` class implemented in `app/orchestrator_api/services/phase_executor_service.py`
- [ ] `PhaseExecutionResult` dataclass defined
- [ ] `ExecutionError` exception class created
- [ ] All steps (AC2.3-2.8) implemented
- [ ] 12+ unit tests with mocked dependencies (no real LLM calls)
- [ ] 2+ integration tests with real database, mocked LLM
- [ ] All tests passing
- [ ] Comprehensive error handling for every step
- [ ] Logging at every major step
- [ ] Docstrings on all public methods

### Edge Cases & Risks

**Edge Case 1:** LLM returns valid JSON but not the expected artifact type  
**Decision:** For 175B, accept any JSON dict; schema validation is future work  
**Action:** Document this limitation clearly

**Edge Case 2:** LLM call takes 60+ seconds  
**Mitigation:** Anthropic client has default timeout; document expected behavior  
**Future:** Add configurable timeout in 175C

**Risk 1:** Anthropic API rate limits or failures  
**Mitigation:** Let ExecutionError propagate; retry logic is future work (PIPELINE-200)  
**Acceptance:** 175B assumes happy-path LLM availability

**Risk 2:** Prompt too large (>100K tokens)  
**Mitigation:** Document max prompt size; monitoring in future epic  
**Acceptance:** Current prompts are <5K tokens; not an immediate concern

---

## Story 3: Feature Flag Integration into PipelineService

**Owner:** PM-B (Mid) → Architecture → Dev  
**Complexity:** Medium  
**Estimated Effort:** 2-3 days  
**Dependencies:** Story 2 (PhaseExecutorService)

### User Story

As a system operator, I need a feature flag to control whether pipelines use the new PhaseExecutorService or legacy hardcoded methods, so that I can safely deploy 175B with instant rollback capability and gradual rollout control.

### Context

This is critical for safe deployment. Feature flag allows us to deploy code without immediately changing behavior. Operators can enable data-driven execution per-environment (dev → staging → prod) or even per-pipeline.

### Acceptance Criteria

**AC3.1 - Feature Flag Definition**
- Environment variable: `DATA_DRIVEN_ORCHESTRATION`
- Accepts: `"true"`, `"false"` (case-insensitive, default: `"false"`)
- Loaded in `app/orchestrator_api/config.py` or settings module
- Accessible via Settings class or config function
- Flag value logged at application startup

**AC3.2 - PipelineService.advance_phase() Modification**
- Check feature flag at START of `advance_phase()` method
- If flag=false: use existing legacy execution methods (no changes to current behavior)
- If flag=true: call PhaseExecutorService.execute_phase()
- Flag checked on EVERY execution (runtime, not startup)
- Log which execution path is taken: "Using data-driven execution" or "Using legacy execution"

**AC3.3 - PhaseExecutorService Integration**
- When flag=true, `advance_phase()` instantiates PhaseExecutorService with dependencies:
  - RolePromptService (instantiated)
  - PhaseConfigurationRepository (instantiated)
  - PipelinePromptUsageRepository (instantiated)
  - LLMResponseParser (instantiated)
  - Anthropic client (from existing Anthropic() instantiation)
- Calls `executor.execute_phase()` with pipeline context
- Receives PhaseExecutionResult
- Updates pipeline state with returned artifact
- Advances to next_phase from result
- Handles ExecutionError with same error reporting as legacy methods

**AC3.4 - Backward Compatibility**
- With flag=false: ZERO changes to existing behavior
- All PIPELINE-150 tests must pass with flag=false
- All existing pipelines work identically with flag=false
- No new dependencies introduced when flag=false

**AC3.5 - Error Handling Parity**
- ExecutionError from PhaseExecutorService handled same as legacy method exceptions
- Error messages maintain same format for API consumers
- Pipeline state transitions remain atomic (success or no change)

**AC3.6 - Configuration Documentation**
- README.md updated with feature flag documentation
- Example: `export DATA_DRIVEN_ORCHESTRATION=true`
- Deployment guide includes flag rollout strategy
- Monitoring recommendations (flag state, execution path metrics)

### Definition of Done

- [ ] Feature flag defined in config module
- [ ] `advance_phase()` modified with conditional logic
- [ ] PhaseExecutorService integration complete
- [ ] All PIPELINE-150 tests pass with flag=false
- [ ] 5+ tests for flag=true execution path
- [ ] 3+ tests for flag toggle behavior
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Deployment guide created

### Edge Cases & Risks

**Edge Case 1:** Flag changes during pipeline execution  
**Decision:** Flag checked per phase; mid-pipeline toggle is acceptable  
**Rationale:** Each phase is atomic; no state corruption risk

**Edge Case 2:** Flag=true but missing phase configs  
**Behavior:** ExecutionError raised, pipeline fails fast with clear error  
**Acceptable:** Operators must seed database before enabling flag

**Risk 1:** Flag accidentally set to true in production before configs ready  
**Mitigation:** Deployment checklist includes "verify configs seeded"  
**Mitigation:** Fail fast with clear error message guides operator

**Risk 2:** Performance regression with new execution path  
**Mitigation:** Story 4 includes performance testing  
**Acceptance:** <200ms overhead is acceptable for 175B

---

## Story 4: End-to-End Integration Testing

**Owner:** PM-B (Mid) → QA Lead  
**Complexity:** Medium  
**Estimated Effort:** 3-4 days  
**Dependencies:** Story 3 (Feature Flag Integration)

### User Story

As a QA engineer, I need comprehensive end-to-end tests that validate the entire data-driven execution flow from PM phase through Architect phase, so that I can confirm the system works correctly with real database configs and mocked LLM responses.

### Context

Integration tests validate the full stack: database → repositories → services → execution → state updates. These tests prove that 175A infrastructure + 175B execution = working pipeline.

### Acceptance Criteria

**AC4.1 - Test Environment Setup**
- Integration test fixture that:
  - Initializes test database with schema
  - Seeds role prompts (PM, Architect minimally)
  - Seeds phase configurations (pm_phase → arch_phase)
  - Provides sample pipeline fixture
  - Mocks Anthropic API responses
- Fixture cleanup: drops all data after test
- Reusable across multiple test cases

**AC4.2 - PM Phase Execution Test**
- Given: Pipeline in "initialized" state, feature flag=true
- When: `advance_phase()` called for pm_phase
- Then:
  - PhaseConfigurationRepository loads pm_phase config
  - RolePromptService builds PM prompt with context
  - Mocked LLM returns valid PM artifact (epic JSON)
  - LLMResponseParser extracts artifact successfully
  - PipelinePromptUsageRepository records usage
  - Pipeline state updated with epic artifact
  - Pipeline advances to arch_phase
  - All steps logged correctly

**AC4.3 - Architect Phase Execution Test**
- Given: Pipeline completed pm_phase, now in arch_phase, feature flag=true
- When: `advance_phase()` called for arch_phase
- Then:
  - PhaseConfigurationRepository loads arch_phase config
  - RolePromptService builds Architect prompt with PM artifact in context
  - Mocked LLM returns valid Architect artifact (arch_notes JSON)
  - LLMResponseParser extracts artifact successfully
  - PipelinePromptUsageRepository records usage
  - Pipeline state updated with arch_notes artifact
  - Pipeline advances to ba_phase
  - All steps logged correctly

**AC4.4 - Legacy vs Data-Driven Parity Test**
- Given: Same pipeline, same inputs
- When: Run with flag=false (legacy), capture result
- When: Run with flag=true (data-driven), capture result
- Then:
  - Both produce equivalent artifacts (same structure)
  - Both advance to same next phase
  - Both have same error handling behavior
  - Execution time within 20% of each other

**AC4.5 - Error Handling Integration Tests**
- Test: Missing phase config → ExecutionError with clear message
- Test: Missing active prompt → ExecutionError with clear message
- Test: LLM API failure → ExecutionError with API error details
- Test: Unparseable LLM response → ExecutionError with parse diagnostics
- Test: Usage recording failure → Warning logged, execution continues
- All errors: Pipeline state unchanged

**AC4.6 - Audit Trail Verification**
- Given: PM and Architect phases executed
- When: Query PipelinePromptUsageRepository
- Then:
  - 2 usage records exist
  - Records include correct pipeline_id, prompt_ids, role_names, phase_names
  - Timestamps are accurate
  - Can trace which prompt versions were used

**AC4.7 - Performance Benchmarks**
- Measure end-to-end execution time for PM → Architect flow
- Baseline: <500ms per phase (excluding LLM call time)
- Overhead from data-driven approach: <200ms vs legacy
- Log metrics: config load time, prompt build time, parse time

### Definition of Done

- [ ] Integration test suite created in `tests/integration/test_data_driven_execution.py`
- [ ] All 7 acceptance criteria covered with tests
- [ ] 12+ integration tests total
- [ ] All tests passing with flag=true
- [ ] All PIPELINE-150 tests passing with flag=false
- [ ] Performance benchmarks documented
- [ ] Test documentation includes setup instructions

### Edge Cases & Risks

**Edge Case 1:** Tests flaky due to database state  
**Mitigation:** Each test uses isolated database session with full cleanup

**Edge Case 2:** Mocked LLM responses too simplistic  
**Mitigation:** Use real-world response samples from actual LLM calls

**Risk 1:** Integration tests are slow (>30s suite)  
**Mitigation:** Use in-memory SQLite, optimize fixture setup  
**Acceptance:** 15-20s for full integration suite is acceptable

---

## Story 5: Documentation & Deployment Preparation

**Owner:** PM-C (Junior) → Tech Writer  
**Complexity:** Low  
**Estimated Effort:** 2 days  
**Dependencies:** Stories 1-4 complete

### User Story

As a developer or operator, I need clear documentation on how the data-driven execution system works, how to deploy it, and how to troubleshoot common issues, so that I can confidently use and maintain the new system.

### Context

This epic introduces significant new architecture. Documentation ensures knowledge transfer, reduces support burden, and enables safe deployment.

### Acceptance Criteria

**AC5.1 - Architecture Documentation**
- Create `docs/PIPELINE-175B-Architecture.md` covering:
  - System overview diagram (component interaction)
  - Data flow: Config → Prompt Build → LLM → Parse → Result
  - Component responsibilities (PhaseExecutorService, LLMResponseParser, etc.)
  - Sequence diagram for typical phase execution
  - Error handling flow
  - Audit trail mechanism

**AC5.2 - Deployment Guide**
- Create `docs/PIPELINE-175B-Deployment.md` covering:
  - Prerequisites: Database seeded (175A)
  - Feature flag configuration
  - Rollout strategy (dev → staging → prod)
  - Verification steps (how to confirm it's working)
  - Rollback procedure (disable flag)
  - Monitoring recommendations

**AC5.3 - API Documentation**
- Docstrings on all public methods updated
- `PhaseExecutorService.execute_phase()` fully documented
- `LLMResponseParser.parse()` fully documented
- `PhaseExecutionResult` dataclass fields explained
- Code examples for common usage patterns

**AC5.4 - Troubleshooting Guide**
- Create `docs/PIPELINE-175B-Troubleshooting.md` covering:
  - Common errors and solutions:
    - "No active prompt found for role X" → Check role_prompts table
    - "Phase configuration not found" → Check phase_configurations table
    - "LLM response parsing failed" → Check llm_response_raw in logs
  - Debugging tips: Enable verbose logging, check audit trail
  - How to validate database seeding
  - How to test with feature flag locally

**AC5.5 - Migration Notes**
- Document differences between legacy and data-driven execution
- Breaking changes: None (flag defaults to false)
- New capabilities: Dynamic prompt updates, audit trail
- Future deprecation plan: Legacy methods removed in PIPELINE-200

**AC5.6 - README Updates**
- Update main README.md with 175B overview
- Add feature flag to configuration section
- Link to detailed documentation

### Definition of Done

- [ ] All 4 documentation files created and complete
- [ ] All public API docstrings reviewed and updated
- [ ] README.md updated
- [ ] Documentation reviewed by at least one other developer
- [ ] Code examples tested and verified working
- [ ] Troubleshooting guide includes real error messages from testing

### Edge Cases & Risks

**Risk 1:** Documentation becomes stale as code evolves  
**Mitigation:** Add "Last Updated" dates, link to code for source of truth

**Risk 2:** Documentation too technical for operators  
**Mitigation:** Separate operator guide (deployment/troubleshooting) from developer guide (architecture/API)

---

## Epic-Level Risks & Mitigation

### Risk 1: Anthropic API Changes Breaking Integration
**Likelihood:** Low  
**Impact:** High  
**Mitigation:**
- Pin anthropic SDK version in requirements.txt
- Monitor Anthropic SDK release notes
- Integration tests catch API contract changes early
**Acceptance:** For 175B, direct Anthropic dependency is acceptable; abstraction layer is future work (LLM-300)

### Risk 2: LLM Response Format Drift Over Time
**Likelihood:** Medium  
**Impact:** Medium  
**Mitigation:**
- LLMResponseParser has multiple fallback strategies
- Log all parse failures for monitoring
- Parser diagnostics help identify new patterns
**Future:** Prompt engineering improvements in PIPELINE-200

### Risk 3: Performance Regression vs Legacy Methods
**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:**
- Performance benchmarks in Story 4 establish baseline
- Database queries optimized (proper indexes from 175A)
- Accept <200ms overhead for flexibility gains
**Acceptance:** Slight overhead acceptable for maintainability

### Risk 4: Database Configs Not Seeded in Production
**Likelihood:** Medium  
**Impact:** High (system won't work)  
**Mitigation:**
- Deployment checklist includes "verify database seeded"
- Feature flag defaults to false (safe)
- Clear error messages guide operators
- Health check endpoint includes config validation
**Action:** Add health check in deployment preparation

### Risk 5: Mid-Epic Scope Creep
**Likelihood:** Medium  
**Impact:** Medium  
**Mitigation:**
- Explicit exclusions documented (multi-artifact, LLM abstraction, admin UI)
- PM-A reviews all feature requests against scope
- "Future epic" parking lot for deferred features
**Discipline:** Architects and developers must honor scope boundaries

---

## Assumptions for Downstream Roles

### Assumptions for Architecture Phase

1. **Anthropic SDK Direct Usage:** Architecture should design for direct anthropic.Anthropic client usage. LLM provider abstraction is explicitly deferred to LLM-300.

2. **Single Artifact Per Phase:** Each phase produces exactly one artifact (dict). Multi-artifact support is explicitly deferred to PIPELINE-200.

3. **No Schema Validation:** PhaseExecutorService accepts any valid JSON dict as artifact. Schema validation against expected artifact structure is explicitly deferred.

4. **No Retry Logic:** LLM failures result in ExecutionError. Retry/circuit-breaker patterns are explicitly deferred to PIPELINE-200.

5. **Synchronous Execution:** All execution is synchronous/blocking. Async/queue-based execution is explicitly deferred.

6. **In-Process Components:** All services instantiated in-process. No microservices, no RPC. Future: PIPELINE-300 may introduce service boundaries.

7. **Logging to stdout:** All logging via Python logging module to stdout. Structured logging, log aggregation deferred to OPS-100.

### Assumptions for BA Phase

1. **Test Strategy:** Unit tests with mocked dependencies + integration tests with mocked LLM. No tests with real Anthropic API calls (cost/speed).

2. **Error Message Format:** ExecutionError messages should be developer-friendly (include context, pipeline_id, phase_name). User-friendly error messages are future work (UI-100).

3. **Artifact Storage:** Artifacts stored in pipeline state JSON blob (existing pattern). Dedicated artifact storage is future work (STORAGE-100).

4. **Audit Trail Queries:** Basic audit queries supported (get by pipeline, get by prompt). Advanced analytics deferred to ANALYTICS-100.

5. **Performance Targets:** <500ms per phase overhead acceptable for 175B. Aggressive optimization deferred until performance issues observed.

### Assumptions for Development Phase

1. **Test Database:** Use in-memory SQLite for tests. Production uses persistent SQLite (for now) or PostgreSQL (future).

2. **Mocking Strategy:** Use unittest.mock for all external dependencies (Anthropic client, repositories in unit tests). pytest-mock is acceptable alternative.

3. **Code Location:** 
   - `app/orchestrator_api/services/llm_response_parser.py`
   - `app/orchestrator_api/services/phase_executor_service.py`
   - `app/orchestrator_api/config.py` (feature flag)
   - `app/orchestrator_api/exceptions.py` (ExecutionError)

4. **Dependencies:** May need to add anthropic SDK to requirements.txt if not already present.

5. **Logging Level:** Default to INFO level. DEBUG level for detailed execution tracing.

### Assumptions for QA Phase

1. **Regression Testing:** All PIPELINE-150 tests must pass with flag=false. This is gate condition for release.

2. **Integration Test Environment:** Dedicated test database, seeded with 175A data, mocked LLM responses.

3. **Performance Testing:** Simple time measurements acceptable. Load testing deferred to PERF-100.

4. **Manual Testing:** QA should manually verify PM → Architect flow with real LLM (Claude Sonnet 4) at least once to validate prompt quality.

5. **Edge Case Coverage:** Focus on error paths (missing configs, parse failures, API errors). Happy path well-covered by integration tests.

---

## Recommended Story Order

### Phase 1: Foundation (Stories 1-2)
**Week 1-2:** 
- Story 1 (LLMResponseParser) - Start immediately
- Story 2 (PhaseExecutorService) - Start as soon as Story 1 complete

**Rationale:** These are core components. Everything else depends on them. No parallelization possible.

### Phase 2: Integration (Story 3)
**Week 3:** 
- Story 3 (Feature Flag Integration) - Requires Story 2 complete

**Rationale:** Clean integration point. Can't integrate until executor exists.

### Phase 3: Validation & Documentation (Stories 4-5)
**Week 3-4:** 
- Story 4 (Integration Testing) - Can start as soon as Story 3 code-complete
- Story 5 (Documentation) - Can parallel with Story 4, finalize last

**Rationale:** These can partially overlap. Documentation can start while integration tests being written.

### Critical Path
Story 1 → Story 2 → Story 3 → Story 4 → Story 5  
**No parallelization opportunities due to tight dependencies.**

---

## Out of Scope (Explicitly Deferred)

### Deferred to Future Epics

**LLM-300: Provider Abstraction Layer**
- Abstract LLM interface (supports Anthropic, OpenAI, etc.)
- Provider-agnostic LLMClient
- Configuration-driven provider selection

**PIPELINE-200: Advanced Execution Features**
- Multi-artifact support (phases producing >1 artifact)
- Retry logic with exponential backoff
- Circuit breaker patterns
- Artifact schema validation
- Async/queue-based execution

**ANALYTICS-100: Audit & Analytics**
- Advanced audit trail queries
- Prompt usage analytics
- Performance metrics dashboard
- Cost tracking per pipeline

**UI-100: Admin Interface**
- Web UI for managing prompts
- Visual phase configuration editor
- Pipeline monitoring dashboard

**STORAGE-100: Artifact Storage**
- Dedicated artifact storage (S3, blob storage)
- Artifact versioning
- Large artifact support (>1MB)

**REPO-200: Repository Integration**
- Commit phase PR creation
- GitHub/GitLab integration
- Automatic changeset commits

---

## Success Criteria (Epic Level)

### Must Have (Launch Blockers)

1. **Functional Completeness**
   - ✅ LLMResponseParser handles all common LLM response formats
   - ✅ PhaseExecutorService executes PM → Architect flow end-to-end
   - ✅ Feature flag controls execution path correctly
   - ✅ Audit trail records all prompt usage

2. **Quality Gates**
   - ✅ All PIPELINE-150 tests pass with flag=false (zero regression)
   - ✅ All 175B tests pass (50+ tests total)
   - ✅ Integration tests prove end-to-end functionality
   - ✅ No critical bugs in error handling

3. **Deployment Readiness**
   - ✅ Feature flag documented and configurable
   - ✅ Deployment guide complete
   - ✅ Rollback procedure documented and tested
   - ✅ Database seeding verified

### Nice to Have (Not Blockers)

4. **Performance**
   - 🎯 <500ms overhead per phase (measured in Story 4)
   - 🎯 <200ms delta vs legacy execution

5. **Documentation**
   - 🎯 Architecture diagram clear and accurate
   - 🎯 Troubleshooting guide covers 80% of common issues
   - 🎯 API documentation complete

### Won't Have (Explicitly Punted)

6. **Advanced Features**
   - ❌ LLM provider abstraction
   - ❌ Multi-artifact support
   - ❌ Retry logic
   - ❌ Schema validation
   - ❌ Admin UI

---

## Handoff to Architecture

### Context Package for Architect Mentor

**What We Defined:**
- 5 stories with clear boundaries and acceptance criteria
- Dependencies and sequencing
- Scope boundaries (what's in, what's deferred)
- Key assumptions about implementation approach
- Risk register with mitigations

**What Architecture Must Define:**
- Class structure and interfaces for LLMResponseParser
- Component interaction patterns for PhaseExecutorService
- Dependency injection strategy
- Error handling patterns (ExecutionError hierarchy)
- Logging strategy and structured log format
- Test architecture (mocking strategy, fixture design)
- Feature flag implementation pattern

**What Architecture Must Validate:**
- Story decomposition is technically feasible
- No hidden dependencies or circular references
- Proposed approach aligns with existing codebase patterns
- Performance targets are achievable
- Test strategy is sufficient

**Open Questions for Architecture:**
1. Should ExecutionError be in exceptions.py or new execution_exceptions.py?
2. Should PhaseExecutorService be a class or module with functions?
3. How should we handle Anthropic client instantiation (singleton, per-call, dependency injection)?
4. Should ParseResult be a dataclass or TypedDict?
5. Should feature flag be in config.py or dedicated feature_flags.py?

**Success Criteria for Architecture Phase:**
- Architecture notes address all 5 stories
- Component diagrams show clear boundaries
- Interface contracts defined (method signatures, return types)
- Test architecture specified
- Architecture is reviewable by senior developers

---

## PM Mentor Sign-Off

**Prepared by:** PM Mentor Team (PM-A, PM-B, PM-C)  
**Reviewed by:** PM-A (Senior Lead)  
**Status:** ✅ Ready for Architecture Phase  
**Confidence Level:** High (scope is tight, stories are clear, risks identified)

**PM-A Notes:**  
"This is a well-scoped epic. The tight focus on execution mechanics (no LLM abstraction, no multi-artifact, no UI) keeps complexity manageable. Feature flag is critical for safe deployment. Story 1 is low-risk; Story 2 is the heart of the epic; Stories 3-5 are integration and polish. Architecture should validate that our proposed approach aligns with existing codebase patterns before dev starts."

**PM-B Notes:**  
"Feature flag strategy is sound. Deployment guide in Story 5 will be critical for ops team. Integration tests in Story 4 give us confidence. Main risk is scope creep - we must hold the line on 'no schema validation' and 'no retry logic' or this epic balloons."

**PM-C Notes:**  
"Documentation in Story 5 covers the bases. Troubleshooting guide should include actual error messages from test failures. Recommend we capture screenshots of successful PM → Architect flow for documentation during QA phase."

**Ready for Orchestrator handoff to Architecture Mentor.**
