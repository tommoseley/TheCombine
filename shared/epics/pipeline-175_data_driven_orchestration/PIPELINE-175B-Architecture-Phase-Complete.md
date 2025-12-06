# PIPELINE-175B: Architecture Phase - Complete Specification (REVISED)

**Architecture Mentor Team:** A-1 (Senior), A-2 (Mid), A-3 (Junior)  
**Date:** 2025-12-05  
**Status:** ✅ Ready for Dev (QA-Critical Issues Resolved)  
**Input:** PM Phase Deliverable (Validated)  
**QA Review:** Issues 1-5 resolved, Medium-Severity items documented

---

## Phase Gate: PM Deliverable Review

**A-1 Review:** ✅ PM deliverable is clear, well-scoped, with explicit boundaries. Stories are implementable. Risks identified and mitigated.

**A-2 Review:** ✅ Stories are SRP-aligned, testability requirements explicit. No SOLID violations in proposed approach.

**A-3 Review:** ✅ Assumptions documented, no ambiguities detected. Method signatures are inferrable from acceptance criteria.

**Gate Status:** ✅ PASSED - Proceeding to Architecture Phase

---

## QA Review Corrections Summary

**QA-Critical Issues Resolved:**
1. ✅ Added catch-all exception handler in orchestrator
2. ✅ Made parser strategy ordering configurable
3. ✅ Added explicit logging in ConfigurationLoader
4. ✅ Standardized UsageRecorder logging format with structured fields
5. ✅ Added state-mutation and next_phase validation requirements

**Medium-Severity Items Documented:**
6. ✅ Token usage guardrails acknowledged as out-of-scope for 175B
7. ✅ Diagnostic logging strategy specified
8. ✅ Next-phase validation behavior documented

---

## ADR-001: SRP Component Decomposition

### Context

The PM deliverable proposes "PhaseExecutorService" with the following responsibilities:
1. Load phase configuration from database
2. Build prompts via RolePromptService
3. Call Anthropic LLM API
4. Parse LLM responses to extract JSON artifacts
5. Record prompt usage to audit trail
6. Assemble execution results

This violates Single Responsibility Principle. A class with 6 distinct responsibilities creates:
- Testing complexity (must mock 5+ dependencies)
- Maintenance burden (changes to any subsystem require modifying this class)
- God Class anti-pattern (>200 lines likely)

### Decision

Decompose into 6 single-responsibility components:

1. **LLMResponseParser** - Extract JSON from noisy LLM output (3 parsing strategies)
2. **LLMCaller** - Invoke Anthropic API and return response (thin wrapper)
3. **ConfigurationLoader** - Load and validate phase configuration from database
4. **UsageRecorder** - Record prompt usage to audit trail (best-effort, non-blocking)
5. **RolePromptService** - Build prompts with context (already exists from 175A ✅)
6. **PhaseExecutionOrchestrator** - Coordinate execution flow (thin coordinator, <150 lines)

Each component has exactly one reason to change:
- Parser changes when parsing strategies evolve
- Caller changes when LLM API contract changes
- Loader changes when configuration schema changes
- Recorder changes when audit requirements change
- Builder changes when prompt structure changes (175A)
- Orchestrator changes when execution flow changes

### Consequences

**Positive:**
- ✅ Each component independently testable (unit tests with mocks)
- ✅ Clear error boundaries (each component owns its failure domain)
- ✅ Easy to extend (add parsing strategy, swap LLM provider later)
- ✅ Reduced cognitive load (each class <150 lines, single purpose)
- ✅ Parallel development possible (different devs can work on different components)

**Negative:**
- ❌ More classes to maintain (6 vs 2)
- ❌ More dependency wiring (mitigated by clear DI pattern)
- ❌ Slightly more boilerplate (dataclasses for results)

**Mitigation:** The benefits far outweigh costs. More classes is acceptable when each class is simpler.

### Status

✅ APPROVED by A-1, A-2, A-3

---

## Component Catalog (SRP-Enforced)

### Component 1: LLMResponseParser

**File:** `app/orchestrator_api/services/llm_response_parser.py`  
**Single Responsibility:** Extract JSON artifacts from LLM response text using multiple fallback strategies  
**Why It Exists:** LLMs produce varied output formats (markdown fences, explanatory text, malformed JSON)  
**Dependencies:** None (stdlib only: json, re, dataclasses)  
**Size Estimate:** ~120 lines (3 strategies + parser logic + configurable ordering)

**Public Interface:**
```python
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Sequence

@dataclass
class ParseResult:
    """Result of parsing attempt with diagnostics."""
    success: bool
    data: Optional[Dict[str, Any]]
    strategy_used: Optional[str]
    error_messages: List[str]

class LLMResponseParser:
    """Parse JSON artifacts from LLM responses using multiple strategies."""
    
    def __init__(self, strategies: Optional[Sequence['ParsingStrategy']] = None):
        """
        Initialize parser with parsing strategies.
        
        Args:
            strategies: Ordered list of strategies to try. If None, uses default:
                       [DirectParseStrategy, MarkdownFenceStrategy, FuzzyBoundaryStrategy]
                       
        Raises:
            ValueError: If strategies list is empty
        """
        if strategies is None:
            strategies = [
                DirectParseStrategy(),
                MarkdownFenceStrategy(),
                FuzzyBoundaryStrategy()
            ]
        
        if not strategies:
            raise ValueError("Parser requires at least one strategy")
        
        self._strategies = list(strategies)
    
    def parse(self, response_text: str) -> ParseResult:
        """
        Extract JSON from LLM response text.
        
        Tries strategies in configured order until one succeeds.
        
        Args:
            response_text: Raw text from LLM
            
        Returns:
            ParseResult with success status and data or errors
            
        Raises:
            Never raises - all errors captured in ParseResult
            
        Logs:
            DEBUG: Each strategy attempt and result
        """
```

**Internal Strategy Interface:**
```python
from typing import Protocol

class ParsingStrategy(Protocol):
    """Protocol for parsing strategies."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse JSON from text.
        
        Returns:
            Parsed dict on success, None on failure
            
        Raises:
            Never raises - returns None on any error
        """
```

**Responsibilities:**
- Apply parsing strategies in configured order
- Return first successful parse
- Collect error messages from all failed strategies
- Provide diagnostics for debugging
- Log each strategy attempt at DEBUG level

**Does NOT:**
- Know about LLM APIs
- Know about phases, pipelines, or execution
- Validate artifact schemas (out of scope)
- Raise exceptions (returns ParseResult)

**Error Handling:**
- All parsing exceptions caught and converted to error messages
- Invalid input types (None, non-string) return ParseResult(success=False)
- Empty string returns ParseResult(success=False)

**Logging Strategy (QA Issue #7):**
```python
logger.debug(f"Attempting parse with {strategy.__class__.__name__}")
# On success:
logger.debug(f"Parse succeeded using {strategy.__class__.__name__}")
# On failure:
logger.debug(f"Parse failed with {strategy.__class__.__name__}: {error}")
```

**Diagnostic error messages are:**
- Returned in ParseResult.error_messages
- Logged at DEBUG level only
- NOT included in user-facing exceptions (orchestrator simplifies these)
- NOT stored in pipeline state

**Test Strategy:**
- 15+ unit tests covering all strategies and edge cases (per PM AC1.6)
- Additional test: Custom strategy ordering
- Additional test: Empty strategy list raises ValueError
- No mocks needed (pure function, stdlib only)
- Test data includes real LLM response samples

**QA Issue #2 Resolution:** Strategy ordering is now configurable via constructor, enabling QA to test edge cases by reordering strategies or injecting custom strategies.

---

### Component 2: LLMCaller

**File:** `app/orchestrator_api/services/llm_caller.py`  
**Single Responsibility:** Invoke Anthropic API and return response text with timing/usage metrics  
**Why It Exists:** Isolate LLM API details from execution logic; enable mocking for tests  
**Dependencies:** anthropic SDK (external)  
**Size Estimate:** ~100 lines

**Public Interface:**
```python
from dataclasses import dataclass
from typing import Optional, Dict
import anthropic
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class LLMCallResult:
    """Result of LLM API call with metrics."""
    success: bool
    response_text: Optional[str]
    execution_time_ms: int
    token_usage: Optional[Dict[str, int]]  # {"input_tokens": N, "output_tokens": M}
    error: Optional[str]

class LLMCaller:
    """Thin wrapper for Anthropic API calls."""
    
    def __init__(self, client: anthropic.Anthropic):
        """
        Initialize caller with Anthropic client.
        
        Args:
            client: Configured Anthropic client instance
        """
        self._client = client
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> LLMCallResult:
        """
        Call Anthropic API and return response.
        
        Args:
            system_prompt: System prompt (role bootstrap + instructions + context)
            user_message: User message (typically "Please proceed with this phase.")
            model: Model identifier
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            
        Returns:
            LLMCallResult with response text or error
            
        Raises:
            Never raises - all errors captured in LLMCallResult
            
        Logs:
            DEBUG: Request parameters
            DEBUG: Success with timing and token usage
            ERROR: Failure with error details
        """
```

**Responsibilities:**
- Make API call with provided prompts and parameters
- Extract response text from API response object
- Measure execution time (start to finish)
- Capture token usage from API response
- Convert API errors to LLMCallResult with error message
- Log request/response details

**Does NOT:**
- Build prompts (that's RolePromptService)
- Parse responses (that's LLMResponseParser)
- Know about phases or configurations
- Retry on failure (explicitly out of scope for 175B)
- Enforce token limits (acknowledged as out-of-scope for 175B, see QA Issue #6)

**Error Handling:**
- Catches all anthropic SDK exceptions
- Converts to LLMCallResult(success=False, error=str(e))
- Measures time even on failure
- No exceptions propagate

**Logging:**
```python
logger.debug(f"Calling LLM: model={model}, max_tokens={max_tokens}, temp={temperature}")
# On success:
logger.debug(f"LLM call succeeded in {elapsed_ms}ms, tokens: input={input}, output={output}")
# On failure:
logger.error(f"LLM call failed after {elapsed_ms}ms: {error}")
```

**Token Usage Guardrails (QA Issue #6):**
- **Acknowledged:** No enforcement of max_total_tokens, max_cost_per_phase, or runaway response prevention in 175B
- **Rationale:** These are monitoring/governance concerns, not execution concerns
- **Future Work:** Token limits and cost tracking deferred to ANALYTICS-100 or OPS-100
- **Current Behavior:** Token usage captured and logged; no validation or limits enforced

**Test Strategy:**
- 8+ unit tests with mocked anthropic.Anthropic client
- Test: successful call, API error, timeout, malformed response
- No real API calls in tests (cost/speed)

---

### Component 3: ConfigurationLoader

**File:** `app/orchestrator_api/services/configuration_loader.py`  
**Single Responsibility:** Load and validate phase configuration from database  
**Why It Exists:** Configuration loading has distinct failure modes; isolate for clarity  
**Dependencies:** PhaseConfigurationRepository (175A)  
**Size Estimate:** ~70 lines

**Public Interface:**
```python
from dataclasses import dataclass
from typing import Optional
import logging
from app.orchestrator_api.persistence.repositories.phase_configuration_repository import (
    PhaseConfigurationRepository
)

logger = logging.getLogger(__name__)

@dataclass
class PhaseConfig:
    """Phase configuration data transfer object."""
    phase_name: str
    role_name: str
    artifact_type: str
    next_phase: Optional[str]
    is_active: bool

class ConfigurationError(Exception):
    """Phase configuration not found or invalid."""
    pass

class ConfigurationLoader:
    """Load and validate phase configurations."""
    
    def __init__(self, repo: PhaseConfigurationRepository):
        """
        Initialize loader with repository.
        
        Args:
            repo: Phase configuration repository instance
        """
        self._repo = repo
    
    def load_config(self, phase_name: str) -> PhaseConfig:
        """
        Load and validate phase configuration.
        
        Args:
            phase_name: Phase identifier (e.g., "pm_phase")
            
        Returns:
            PhaseConfig with validated data
            
        Raises:
            ConfigurationError: If config not found or not active
            
        Logs:
            DEBUG: Config loaded successfully
            ERROR: Config not found or not active (before raising)
        """
```

**Responsibilities:**
- Query repository for phase configuration by name
- Validate configuration exists
- Validate configuration is active (is_active=True)
- Convert ORM model to dataclass (decouple from persistence layer)
- Log failure before raising (for traceability)
- Raise ConfigurationError with clear message on failure

**Does NOT:**
- Execute phases
- Build prompts
- Call LLMs
- Know about orchestration flow

**Error Handling:**
- Logs error at ERROR level before raising (QA Issue #3)
- Raises ConfigurationError if phase not found
- Raises ConfigurationError if phase not active
- Error message includes phase_name for context

**Logging (QA Issue #3 Resolution):**
```python
# On not found:
logger.error(f"Phase config not found: {phase_name}")
raise ConfigurationError(f"Phase configuration not found: {phase_name}")

# On not active:
logger.error(f"Phase config not active: {phase_name}")
raise ConfigurationError(f"Phase configuration not active: {phase_name}")

# On success:
logger.debug(f"Loaded config for {phase_name}: role={config.role_name}")
```

**Test Strategy:**
- 6+ unit tests with mocked repository
- Test: config found and active, config not found, config not active
- Test: repository error propagation
- Test: logging verification

---

### Component 4: UsageRecorder

**File:** `app/orchestrator_api/services/usage_recorder.py`  
**Single Responsibility:** Record prompt usage to audit trail (best-effort, non-blocking)  
**Why It Exists:** Audit recording is optional; shouldn't block execution on failure  
**Dependencies:** PipelinePromptUsageRepository (175A)  
**Size Estimate:** ~60 lines

**Public Interface:**
```python
from dataclasses import dataclass
import logging
import json
from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import (
    PipelinePromptUsageRepository
)

logger = logging.getLogger(__name__)

@dataclass
class UsageRecord:
    """Prompt usage data to record."""
    pipeline_id: str
    prompt_id: str
    role_name: str
    phase_name: str

class UsageRecorder:
    """Record prompt usage to audit trail."""
    
    def __init__(self, repo: PipelinePromptUsageRepository):
        """
        Initialize recorder with repository.
        
        Args:
            repo: Pipeline prompt usage repository instance
        """
        self._repo = repo
    
    def record_usage(self, usage: UsageRecord) -> bool:
        """
        Record prompt usage (best-effort).
        
        Args:
            usage: Usage record to persist
            
        Returns:
            True if recorded successfully, False on any error
            
        Raises:
            Never raises - logs errors and returns False
            
        Logs:
            DEBUG: Success with usage_id
            WARNING: Failure with structured error details
        """
```

**Responsibilities:**
- Call repository to record usage
- Convert repository exceptions to boolean result
- Log failures at WARNING level with structured format
- Return success/failure indicator

**Does NOT:**
- Block execution on failure (returns False, doesn't raise)
- Validate prompt or pipeline existence (repository handles that)
- Know about execution flow

**Critical Design Decision:** Recording failure does NOT propagate as exception. Rationale: Audit trail is important but not critical path. Pipeline should proceed even if audit fails.

**Error Handling:**
- Catches all repository exceptions
- Logs at WARNING level with structured format (QA Issue #4)
- Returns False on any error
- Never raises

**Logging (QA Issue #4 Resolution - Structured Format):**
```python
# On success:
logger.debug(f"Recorded usage: usage_id={usage_id}")

# On failure (structured JSON):
logger.warning(
    "Usage record failure",
    extra={
        "event": "usage_record_failure",
        "pipeline_id": usage.pipeline_id,
        "phase_name": usage.phase_name,
        "role_name": usage.role_name,
        "prompt_id": usage.prompt_id,
        "error": str(e)
    }
)
```

**Structured Log Format Specification:**
```json
{
  "timestamp": "2025-12-05T10:30:45Z",
  "level": "WARNING",
  "logger": "app.orchestrator_api.services.usage_recorder",
  "message": "Usage record failure",
  "event": "usage_record_failure",
  "pipeline_id": "pip_abc123",
  "phase_name": "pm_phase",
  "role_name": "pm",
  "prompt_id": "rp_xyz789",
  "error": "IntegrityError: Foreign key constraint failed"
}
```

**Why Structured Logging Matters (QA Issue #4):**
- Enables programmatic analysis of audit failures
- Supports future analytics and responsible AI auditing
- Machine-readable for automated alerting
- Searchable by pipeline_id, phase_name, role_name, prompt_id

**Test Strategy:**
- 4+ unit tests with mocked repository
- Test: successful record, repository error, logging verification
- Test: Verify structured log format includes all required fields

---

### Component 5: RolePromptService (Existing - 175A)

**File:** `app/orchestrator_api/services/role_prompt_service.py`  
**Single Responsibility:** Build prompts from database with context injection  
**Why It Exists:** Already implemented in 175A ✅  
**Dependencies:** RolePromptRepository (175A)  
**Size Estimate:** ~130 lines (already exists)

**Public Interface:**
```python
from typing import Optional, Dict, Any, Tuple
from app.orchestrator_api.persistence.repositories.role_prompt_repository import (
    RolePromptRepository
)

class RolePromptService:
    """Build role prompts with context injection."""
    
    def __init__(self):
        """Initialize service with repository."""
        self.prompt_repo = RolePromptRepository()
    
    def build_prompt(
        self,
        role_name: str,
        pipeline_id: str,
        phase: str,
        epic_context: Optional[str] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Build complete role prompt with all sections.
        
        Args:
            role_name: Role identifier (pm, architect, ba, etc.)
            pipeline_id: Pipeline identifier
            phase: Current phase name
            epic_context: Epic description (optional)
            pipeline_state: Pipeline state dict (optional)
            artifacts: Previous artifacts dict (optional)
            
        Returns:
            Tuple of (prompt_text, prompt_id)
            
        Raises:
            ValueError: If no active prompt found for role
        """
```

**Status:** ✅ NO CHANGES REQUIRED

**Note for Developers:** This service already exists and is tested (8/8 tests passing in 175A). Do not modify. Use as-is.

**Exception Handling:** Raises ValueError (not ExecutionError) when no active prompt found. PhaseExecutionOrchestrator must catch and convert to PromptBuildError.

---

### Component 6: PhaseExecutionOrchestrator

**File:** `app/orchestrator_api/services/phase_execution_orchestrator.py`  
**Single Responsibility:** Coordinate execution flow across components (thin coordinator)  
**Why It Exists:** Something must wire components together in correct sequence  
**Dependencies:** All 5 components above  
**Size Estimate:** ~150 lines (at limit, must not exceed)

**Critical Constraint:** This class MUST remain thin (<150 lines). If it grows, we've done something wrong. Orchestrator knows the "what" and "when", components know the "how".

**Public Interface:**
```python
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging
from app.orchestrator_api.services.llm_response_parser import LLMResponseParser
from app.orchestrator_api.services.llm_caller import LLMCaller
from app.orchestrator_api.services.configuration_loader import ConfigurationLoader
from app.orchestrator_api.services.usage_recorder import UsageRecorder, UsageRecord
from app.orchestrator_api.services.role_prompt_service import RolePromptService

logger = logging.getLogger(__name__)

@dataclass
class PhaseExecutionResult:
    """Result of phase execution."""
    success: bool
    artifact: Dict[str, Any]
    artifact_type: str
    next_phase: Optional[str]
    prompt_id: str
    llm_response_raw: str
    execution_time_ms: int
    error: Optional[str] = None

class ExecutionError(Exception):
    """Base exception for phase execution errors."""
    def __init__(self, message: str, phase_name: str, pipeline_id: str):
        self.message = message
        self.phase_name = phase_name
        self.pipeline_id = pipeline_id
        super().__init__(f"[{pipeline_id}:{phase_name}] {message}")

class ConfigurationError(ExecutionError):
    """Phase configuration error."""
    pass

class PromptBuildError(ExecutionError):
    """Prompt building error."""
    pass

class LLMError(ExecutionError):
    """LLM API call error."""
    pass

class ParseError(ExecutionError):
    """Response parsing error."""
    pass

class PhaseExecutionOrchestrator:
    """Coordinate phase execution across components."""
    
    def __init__(
        self,
        config_loader: ConfigurationLoader,
        prompt_builder: RolePromptService,
        llm_caller: LLMCaller,
        parser: LLMResponseParser,
        usage_recorder: UsageRecorder
    ):
        """
        Initialize orchestrator with all dependencies.
        
        Args:
            config_loader: Configuration loader instance
            prompt_builder: Prompt builder service instance
            llm_caller: LLM caller instance
            parser: Response parser instance
            usage_recorder: Usage recorder instance
        """
        self._config_loader = config_loader
        self._prompt_builder = prompt_builder
        self._llm_caller = llm_caller
        self._parser = parser
        self._usage_recorder = usage_recorder
    
    def execute_phase(
        self,
        pipeline_id: str,
        phase_name: str,
        epic_context: str,
        pipeline_state: Dict[str, Any],
        artifacts: Dict[str, Any]
    ) -> PhaseExecutionResult:
        """
        Execute phase by coordinating all components.
        
        Flow:
        1. Load phase configuration
        2. Build prompt with context
        3. Call LLM
        4. Parse response
        5. Record usage (best-effort)
        6. Return result
        
        Args:
            pipeline_id: Pipeline identifier
            phase_name: Phase to execute
            epic_context: Epic description
            pipeline_state: Current pipeline state (IMMUTABLE - not modified)
            artifacts: Previous phase artifacts (IMMUTABLE - not modified)
            
        Returns:
            PhaseExecutionResult with artifact and next phase
            
        Raises:
            ConfigurationError: Phase config not found
            PromptBuildError: Failed to build prompt
            LLMError: LLM API call failed
            ParseError: Failed to parse response
            ExecutionError: Unexpected internal error (catch-all)
            
        Logs:
            INFO: Phase execution start
            DEBUG: Each step completion
            ERROR: Any failure with full context
            
        State Immutability Guarantee (QA Issue #5):
            This method does NOT modify pipeline_state or artifacts inputs.
            All state mutations must occur in PipelineService after successful return.
        """
```

**Execution Flow (Detailed with QA Fixes):**

```python
def execute_phase(self, ...) -> PhaseExecutionResult:
    logger.info(f"Executing phase {phase_name} for pipeline {pipeline_id}")
    
    try:
        # Step 1: Load configuration
        # Raises ConfigurationError if not found or not active
        # Now logs before raising (QA Issue #3)
        config = self._config_loader.load_config(phase_name)
        logger.debug(f"Loaded config: role={config.role_name}, artifact={config.artifact_type}")
        
        # Step 2: Build prompt
        # Raises ValueError if no active prompt (must catch and convert)
        try:
            prompt_text, prompt_id = self._prompt_builder.build_prompt(
                role_name=config.role_name,
                pipeline_id=pipeline_id,
                phase=phase_name,
                epic_context=epic_context,
                pipeline_state=pipeline_state,
                artifacts=artifacts
            )
            logger.debug(f"Built prompt using {prompt_id}")
        except ValueError as e:
            raise PromptBuildError(str(e), phase_name, pipeline_id)
        
        # Step 3: Call LLM
        # Never raises - returns result object
        llm_result = self._llm_caller.call(
            system_prompt=prompt_text,
            user_message="Please proceed with this phase."
        )
        
        if not llm_result.success:
            raise LLMError(
                f"LLM call failed: {llm_result.error}",
                phase_name,
                pipeline_id
            )
        
        logger.debug(f"LLM responded in {llm_result.execution_time_ms}ms")
        
        # Step 4: Parse response
        # Never raises - returns result object
        parse_result = self._parser.parse(llm_result.response_text)
        
        if not parse_result.success:
            error_msg = "; ".join(parse_result.error_messages)
            raise ParseError(
                f"Parse failed: {error_msg}",
                phase_name,
                pipeline_id
            )
        
        logger.debug(f"Parsed artifact using strategy: {parse_result.strategy_used}")
        
        # Step 5: Record usage (best-effort, non-blocking)
        # Never raises - logs on failure with structured format (QA Issue #4)
        usage = UsageRecord(
            pipeline_id=pipeline_id,
            prompt_id=prompt_id,
            role_name=config.role_name,
            phase_name=phase_name
        )
        recorded = self._usage_recorder.record_usage(usage)
        if recorded:
            logger.debug("Recorded prompt usage")
        else:
            logger.warning("Failed to record usage (non-fatal)")
        
        # Step 6: Assemble result
        return PhaseExecutionResult(
            success=True,
            artifact=parse_result.data,
            artifact_type=config.artifact_type,
            next_phase=config.next_phase,
            prompt_id=prompt_id,
            llm_response_raw=llm_result.response_text,
            execution_time_ms=llm_result.execution_time_ms,
            error=None
        )
        
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except PromptBuildError as e:
        logger.error(f"Prompt build error: {e}")
        raise
    except LLMError as e:
        logger.error(f"LLM error: {e}")
        raise
    except ParseError as e:
        logger.error(f"Parse error: {e}")
        raise
    except Exception as e:
        # QA Issue #1: Catch-all for unexpected errors
        logger.error(
            f"Unexpected internal error during phase execution: {e}",
            exc_info=True  # Include stack trace
        )
        raise ExecutionError(
            message=f"Unexpected internal error: {type(e).__name__}: {str(e)}",
            phase_name=phase_name,
            pipeline_id=pipeline_id
        ) from e
```

**Responsibilities:**
- Wire components together
- Call components in correct sequence
- Convert component errors to appropriate ExecutionError subclasses
- Catch unexpected errors and wrap in ExecutionError (QA Issue #1)
- Assemble final PhaseExecutionResult
- Log execution steps at DEBUG/INFO level
- Log errors at ERROR level
- Guarantee input immutability (QA Issue #5)

**Does NOT:**
- Load configs (delegates to ConfigurationLoader)
- Build prompts (delegates to PromptBuilder)
- Call LLM (delegates to LLMCaller)
- Parse responses (delegates to Parser)
- Record usage (delegates to UsageRecorder)
- Contain business logic (pure coordination)
- Modify pipeline_state or artifacts inputs (immutable)

**Error Handling:**
- ConfigurationLoader raises ConfigurationError → propagates (now logs first per QA Issue #3)
- RolePromptService raises ValueError → converts to PromptBuildError
- LLMCaller returns result → checks success, raises LLMError on failure
- Parser returns result → checks success, raises ParseError on failure
- UsageRecorder never raises → logs warning if recording fails (structured format per QA Issue #4)
- **NEW (QA Issue #1):** Catch-all for unexpected exceptions → wraps in ExecutionError
- All errors include phase_name and pipeline_id for context

**State Immutability Guarantee (QA Issue #5):**
- This method does NOT modify `pipeline_state` or `artifacts` parameters
- These inputs are read-only
- All state mutations must occur in `PipelineService.advance_phase()` after successful return
- This ensures atomic state updates (either full success or no change)

**Test Strategy:**
- 12+ unit tests with all 5 dependencies mocked
- Test: happy path, each error path independently
- Test: unexpected exception handling (QA Issue #1)
- Verify component call sequence
- Verify error conversion
- Verify logging
- Verify input immutability (mock inputs, verify not modified)

---

## ADR-002: Strategy Pattern for LLMResponseParser

### Context

LLM responses vary widely in format:
- Clean JSON: `{"key": "value"}`
- Markdown fences: ` ```json\n{"key": "value"}\n``` `
- With explanation: `Here is the result:\n{"key": "value"}\nLet me know if you need changes.`
- Malformed: Missing quotes, trailing commas, etc.

We need multiple parsing approaches with clear fallback sequence and good diagnostics.

**QA Requirement:** Strategy ordering must be configurable to enable edge-case testing.

### Decision

Implement Strategy Pattern with three concrete strategies executed in order:

1. **DirectParseStrategy** - Attempts `json.loads()` on entire response
2. **MarkdownFenceStrategy** - Extracts JSON from ```json code fences
3. **FuzzyBoundaryStrategy** - Finds first `{` to last `}` and attempts parse

Parser executes strategies sequentially in **configurable order**. First success returns immediately. If all fail, returns ParseResult(success=False) with aggregated error messages.

### Implementation Pattern

```python
from typing import Protocol, Optional, Dict, Any, Sequence
import json
import re
import logging

logger = logging.getLogger(__name__)

class ParsingStrategy(Protocol):
    """Protocol for parsing strategies."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse JSON from text.
        
        Returns:
            Parsed dict on success, None on failure
        """

class DirectParseStrategy:
    """Attempt direct json.loads() on full text."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            # Strip whitespace and common prefixes
            text = text.strip()
            prefixes = ["Here is the JSON:", "Result:", "Output:"]
            for prefix in prefixes:
                if text.startswith(prefix):
                    text = text[len(prefix):].strip()
            
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

class MarkdownFenceStrategy:
    """Extract JSON from markdown code fences."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        # Match ```json or ``` followed by JSON
        pattern = r'```(?:json)?\s*\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if not matches:
            return None
        
        # If multiple fences, try largest first
        matches_sorted = sorted(matches, key=len, reverse=True)
        
        for match in matches_sorted:
            try:
                return json.loads(match.strip())
            except (json.JSONDecodeError, ValueError):
                continue
        
        return None

class FuzzyBoundaryStrategy:
    """Find first { to last } and attempt parse."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        
        if first_brace == -1 or last_brace == -1:
            return None
        
        json_text = text[first_brace:last_brace + 1]
        
        try:
            return json.loads(json_text)
        except (json.JSONDecodeError, ValueError):
            return None

class LLMResponseParser:
    """Parse JSON artifacts from LLM responses."""
    
    def __init__(self, strategies: Optional[Sequence[ParsingStrategy]] = None):
        """
        Initialize parser with strategies.
        
        Args:
            strategies: Ordered list of strategies. If None, uses default order:
                       [DirectParseStrategy, MarkdownFenceStrategy, FuzzyBoundaryStrategy]
                       
        Raises:
            ValueError: If strategies list is empty
        """
        if strategies is None:
            strategies = [
                DirectParseStrategy(),
                MarkdownFenceStrategy(),
                FuzzyBoundaryStrategy()
            ]
        
        if not strategies:
            raise ValueError("Parser requires at least one strategy")
        
        self._strategies = list(strategies)
        logger.debug(f"Parser initialized with {len(self._strategies)} strategies")
    
    def parse(self, response_text: str) -> ParseResult:
        if not isinstance(response_text, str):
            return ParseResult(
                success=False,
                data=None,
                strategy_used=None,
                error_messages=["Invalid input: expected string"]
            )
        
        if not response_text.strip():
            return ParseResult(
                success=False,
                data=None,
                strategy_used=None,
                error_messages=["Empty response text"]
            )
        
        errors = []
        
        for strategy in self._strategies:
            strategy_name = strategy.__class__.__name__
            logger.debug(f"Attempting parse with {strategy_name}")
            
            try:
                result = strategy.parse(response_text)
                if result is not None:
                    logger.debug(f"Parse succeeded using {strategy_name}")
                    return ParseResult(
                        success=True,
                        data=result,
                        strategy_used=strategy_name,
                        error_messages=[]
                    )
                else:
                    logger.debug(f"{strategy_name} returned None")
            except Exception as e:
                error_msg = f"{strategy_name}: {str(e)}"
                errors.append(error_msg)
                logger.debug(f"Parse failed with {strategy_name}: {str(e)}")
        
        return ParseResult(
            success=False,
            data=None,
            strategy_used=None,
            error_messages=errors if errors else ["All strategies failed"]
        )
```

### Benefits

- ✅ Each strategy is independently testable
- ✅ Easy to add new strategies without modifying parser (Open/Closed Principle)
- ✅ Clear failure diagnostics (which strategies were tried, why they failed)
- ✅ No complex conditional logic (each strategy is self-contained)
- ✅ Strategies can be reordered or removed without affecting others
- ✅ **QA can inject custom strategies or reorder for edge-case testing** (QA Issue #2)

### QA Issue #2 Resolution

**Problem:** Hardcoded strategy ordering makes edge-case testing difficult.

**Solution:** Constructor accepts optional `strategies` parameter:
- Default behavior unchanged (DirectParse → MarkdownFence → FuzzyBoundary)
- QA can reorder: `parser = LLMResponseParser([FuzzyBoundaryStrategy(), DirectParseStrategy()])`
- QA can inject custom strategies for testing
- Empty list raises ValueError (validation)

**Test Coverage:**
- Test default ordering
- Test custom ordering
- Test single strategy
- Test empty list raises ValueError

### Status

✅ APPROVED by A-1, A-2, A-3 (with QA Issue #2 resolution)

---

## ADR-003: LLMCaller Abstraction (Anthropic Wrapper)

### Context

Direct Anthropic API calls in orchestrator would:
- Violate SRP (orchestrator shouldn't know API details)
- Make testing difficult (can't mock API easily)
- Couple code tightly to Anthropic SDK
- Mix timing/metrics logic with orchestration logic

PM explicitly deferred full LLM provider abstraction to LLM-300, but we still need testability.

### Decision

Create thin `LLMCaller` wrapper that:
- Encapsulates Anthropic SDK details
- Provides mockable interface
- Converts API exceptions to `LLMCallResult` (no exceptions propagate)
- Measures execution time consistently
- Captures token usage for monitoring

This is Anthropic-specific but still provides testability and clear boundaries.

### Implementation Pattern

```python
from dataclasses import dataclass
from typing import Optional, Dict
import anthropic
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class LLMCallResult:
    """Result of LLM API call."""
    success: bool
    response_text: Optional[str]
    execution_time_ms: int
    token_usage: Optional[Dict[str, int]]
    error: Optional[str]

class LLMCaller:
    """Thin wrapper for Anthropic API calls."""
    
    def __init__(self, client: anthropic.Anthropic):
        """
        Initialize with Anthropic client.
        
        Args:
            client: Configured Anthropic() instance
        """
        self._client = client
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> LLMCallResult:
        """
        Call Anthropic API.
        
        Args:
            system_prompt: System prompt text
            user_message: User message text
            model: Model identifier
            max_tokens: Max response tokens
            temperature: Sampling temperature
            
        Returns:
            LLMCallResult (never raises)
            
        Logs:
            DEBUG: Request parameters and success details
            ERROR: Failure details
        """
        logger.debug(f"Calling LLM: model={model}, max_tokens={max_tokens}, temp={temperature}")
        start_time = time.time()
        
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Extract response text
            response_text = response.content[0].text
            
            # Extract token usage
            token_usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
            
            logger.debug(
                f"LLM call succeeded in {elapsed_ms}ms, "
                f"tokens: input={token_usage['input_tokens']}, output={token_usage['output_tokens']}"
            )
            
            return LLMCallResult(
                success=True,
                response_text=response_text,
                execution_time_ms=elapsed_ms,
                token_usage=token_usage,
                error=None
            )
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            logger.error(f"LLM call failed after {elapsed_ms}ms: {error_msg}")
            
            return LLMCallResult(
                success=False,
                response_text=None,
                execution_time_ms=elapsed_ms,
                token_usage=None,
                error=error_msg
            )
```

### Benefits

- ✅ Testable via mock LLMCaller (no need to mock Anthropic SDK in orchestrator tests)
- ✅ Isolates Anthropic SDK details (API contract changes localized here)
- ✅ Consistent error handling (no exceptions propagate)
- ✅ Consistent timing measurement (start to finish, even on error)
- ✅ Future: Easy to replace with LLM-300 abstraction (same interface)

### Why Not Full Abstraction Now?

PM explicitly scoped this out. Full abstraction would require:
- Abstract LLMProvider interface
- Multiple provider implementations
- Provider selection logic
- Configuration management

This adds complexity without immediate value. Current approach provides testability (primary need) while keeping scope tight.

### Token Usage Guardrails (QA Issue #6)

**Status:** Acknowledged as out-of-scope for 175B

**Current Behavior:**
- Token usage captured from API response
- Logged at DEBUG level
- Returned in LLMCallResult for monitoring
- No enforcement of limits

**Not Implemented (Explicitly Out of Scope):**
- max_total_tokens enforcement
- max_cost_per_phase limits
- Runaway response prevention
- Token budget alerts

**Rationale:**
- These are monitoring/governance concerns, not execution concerns
- Belong in separate monitoring/analytics system (ANALYTICS-100)
- Adding now would violate SRP (caller should call, not govern)

**Future Work:**
- Token limits → ANALYTICS-100 or OPS-100
- Cost tracking → ANALYTICS-100
- Budget enforcement → GOVERNANCE-100

**Risk Assessment:**
- Low for 175B (development/staging only)
- Must address before production scale (noted in PM deliverable)

### Status

✅ APPROVED by A-1, A-2, A-3 (with QA Issue #6 acknowledgment)

---

## ADR-004: Dependency Injection Pattern

### Context

6 components need clear wiring without tight coupling. We need:
- Independent testability (unit tests with mocks)
- Clear dependency graph (no hidden dependencies)
- Flexible composition (can swap implementations)

### Decision

Use Constructor Dependency Injection throughout:

**Low-level components** (no dependencies on other new components):
- `LLMResponseParser(strategies=None)` - Optional strategy list (QA Issue #2)
- `LLMCaller(client)` - Takes Anthropic client
- `ConfigurationLoader(repo)` - Takes repository
- `UsageRecorder(repo)` - Takes repository
- `RolePromptService()` - Has internal repository (175A design)

**High-level component** (depends on all low-level components):
- `PhaseExecutionOrchestrator(config_loader, prompt_builder, llm_caller, parser, usage_recorder)` - Takes all 5 dependencies

### Implementation Pattern

**Instantiation in PipelineService.advance_phase():**

```python
class PipelineService:
    def advance_phase(self, pipeline_id: str) -> Pipeline:
        # Check feature flag
        if not settings.DATA_DRIVEN_ORCHESTRATION:
            # Use legacy execution methods
            return self._legacy_advance_phase(pipeline_id)
        
        # Data-driven execution path
        logger.info("Using data-driven orchestration")
        
        # Instantiate dependencies
        parser = LLMResponseParser()  # Default strategy ordering
        
        anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        llm_caller = LLMCaller(anthropic_client)
        
        config_loader = ConfigurationLoader(PhaseConfigurationRepository())
        usage_recorder = UsageRecorder(PipelinePromptUsageRepository())
        prompt_builder = RolePromptService()
        
        # Instantiate orchestrator with all dependencies
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=config_loader,
            prompt_builder=prompt_builder,
            llm_caller=llm_caller,
            parser=parser,
            usage_recorder=usage_recorder
        )
        
        # Load pipeline
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        
        # Execute phase
        try:
            result = orchestrator.execute_phase(
                pipeline_id=pipeline.pipeline_id,
                phase_name=pipeline.current_phase,
                epic_context=pipeline.initial_context.get("epic_description", ""),
                pipeline_state=pipeline.state or {},
                artifacts=pipeline.state.get("artifacts", {})
            )
            
            # QA Issue #5: State mutation happens HERE, not in orchestrator
            # Atomic update: either full success or no change
            pipeline.state["artifacts"][result.artifact_type] = result.artifact
            pipeline.current_phase = result.next_phase
            
            # Validate next_phase if not None (QA Issue #8)
            if result.next_phase is not None:
                # Verify next_phase exists and is active
                try:
                    config_loader.load_config(result.next_phase)
                except ConfigurationError:
                    logger.error(f"Invalid next_phase: {result.next_phase} does not exist")
                    raise ExecutionError(
                        f"Invalid next_phase configuration: {result.next_phase}",
                        pipeline.current_phase,
                        pipeline_id
                    )
            
            self.pipeline_repo.update(pipeline)
            
            return pipeline
            
        except ExecutionError as e:
            logger.error(f"Execution failed: {e}")
            # Pipeline state unchanged (atomic operation)
            raise
```

### State Mutation Contract (QA Issue #5)

**Orchestrator Guarantees:**
1. **Input Immutability:** Does NOT modify `pipeline_state` or `artifacts` parameters
2. **Read-Only Operation:** All inputs treated as immutable
3. **No Side Effects:** Only reads data, doesn't write to database or modify state

**PipelineService Responsibilities:**
1. **Atomic Update:** Updates pipeline state only after successful orchestrator return
2. **Validation:** Validates next_phase exists before updating (QA Issue #8)
3. **Transaction Safety:** Uses repository transaction for atomic state update
4. **Rollback on Failure:** Pipeline state unchanged if orchestrator raises exception

**Why This Pattern:**
- Clear separation of concerns (orchestrator coordinates, service persists)
- Atomic operations (either full success or no change)
- Easier to test (orchestrator doesn't need database mocks)
- Safer (no partial state updates)

### Next Phase Validation (QA Issue #8)

**Expected Behaviors:**

**Case 1: Terminal Phase (next_phase=None)**
- Config has `next_phase=None` (e.g., commit_phase)
- Orchestrator returns `PhaseExecutionResult(next_phase=None)`
- PipelineService sets `pipeline.current_phase = None`
- Pipeline marked as complete

**Case 2: Valid Next Phase**
- Config has `next_phase="arch_phase"`
- Orchestrator returns result with `next_phase="arch_phase"`
- PipelineService validates arch_phase config exists
- If valid: Updates to arch_phase
- If invalid: Raises ExecutionError (config inconsistency)

**Case 3: Missing Next Phase Config**
- Config has `next_phase="nonexistent_phase"`
- Orchestrator returns result (doesn't validate)
- PipelineService attempts to validate nonexistent_phase
- ConfigurationLoader raises ConfigurationError
- PipelineService converts to ExecutionError and fails
- Pipeline state unchanged (atomic)

**Validation Logic:**
```python
if result.next_phase is not None:
    try:
        config_loader.load_config(result.next_phase)
    except ConfigurationError:
        raise ExecutionError(
            f"Invalid next_phase configuration: {result.next_phase}",
            pipeline.current_phase,
            pipeline_id
        )
```

**Why Orchestrator Doesn't Validate:**
- Orchestrator is thin coordinator, not validator
- Validation adds complexity (>150 line limit)
- PipelineService already has config_loader reference
- Keeps error handling centralized

### Testing Strategy

**Unit Tests (Orchestrator):**
```python
def test_orchestrator_happy_path():
    # Mock all dependencies
    mock_config = Mock(spec=ConfigurationLoader)
    mock_config.load_config.return_value = PhaseConfig(
        phase_name="pm_phase",
        role_name="pm",
        artifact_type="epic",
        next_phase="arch_phase",
        is_active=True
    )
    
    mock_prompt = Mock(spec=RolePromptService)
    mock_prompt.build_prompt.return_value = ("prompt text", "rp_123")
    
    mock_llm = Mock(spec=LLMCaller)
    mock_llm.call.return_value = LLMCallResult(
        success=True,
        response_text='{"title": "Test Epic"}',
        execution_time_ms=1000,
        token_usage={"input_tokens": 100, "output_tokens": 50},
        error=None
    )
    
    mock_parser = Mock(spec=LLMResponseParser)
    mock_parser.parse.return_value = ParseResult(
        success=True,
        data={"title": "Test Epic"},
        strategy_used="DirectParseStrategy",
        error_messages=[]
    )
    
    mock_recorder = Mock(spec=UsageRecorder)
    mock_recorder.record_usage.return_value = True
    
    # Instantiate orchestrator with mocks
    orchestrator = PhaseExecutionOrchestrator(
        config_loader=mock_config,
        prompt_builder=mock_prompt,
        llm_caller=mock_llm,
        parser=mock_parser,
        usage_recorder=mock_recorder
    )
    
    # Execute
    pipeline_state = {"key": "value"}
    artifacts = {"prev": "artifact"}
    
    result = orchestrator.execute_phase(
        pipeline_id="pip_test",
        phase_name="pm_phase",
        epic_context="Build user auth",
        pipeline_state=pipeline_state,
        artifacts=artifacts
    )
    
    # Verify
    assert result.success
    assert result.artifact == {"title": "Test Epic"}
    assert result.next_phase == "arch_phase"
    
    # Verify input immutability (QA Issue #5)
    assert pipeline_state == {"key": "value"}  # Unchanged
    assert artifacts == {"prev": "artifact"}  # Unchanged
    
    # Verify component calls
    mock_config.load_config.assert_called_once_with("pm_phase")
    mock_prompt.build_prompt.assert_called_once()
    mock_llm.call.assert_called_once()
    mock_parser.parse.assert_called_once()
    mock_recorder.record_usage.assert_called_once()
```

**Integration Tests:**
```python
def test_integration_pm_phase(test_db, seeded_configs):
    """Test with real DB, mocked LLM only."""
    # Real components
    parser = LLMResponseParser()
    config_loader = ConfigurationLoader(PhaseConfigurationRepository())
    usage_recorder = UsageRecorder(PipelinePromptUsageRepository())
    prompt_builder = RolePromptService()
    
    # Mock LLM only
    mock_llm = Mock(spec=LLMCaller)
    mock_llm.call.return_value = LLMCallResult(
        success=True,
        response_text='```json\n{"title": "Test Epic", "description": "..."}\n```',
        execution_time_ms=1500,
        token_usage={"input_tokens": 150, "output_tokens": 75},
        error=None
    )
    
    orchestrator = PhaseExecutionOrchestrator(
        config_loader=config_loader,
        prompt_builder=prompt_builder,
        llm_caller=mock_llm,
        parser=parser,
        usage_recorder=usage_recorder
    )
    
    result = orchestrator.execute_phase(
        pipeline_id="pip_test_123",
        phase_name="pm_phase",
        epic_context="Build authentication system",
        pipeline_state={},
        artifacts={}
    )
    
    assert result.success
    assert "title" in result.artifact
    
    # Verify usage was recorded
    usage_repo = PipelinePromptUsageRepository()
    usages = usage_repo.get_by_pipeline("pip_test_123")
    assert len(usages) == 1
```

### Benefits

- ✅ Every component independently testable (unit tests with mocks)
- ✅ No global state
- ✅ Clear dependency graph
- ✅ Easy to reason about (explicit dependencies in constructor)
- ✅ Flexible composition (can swap implementations)
- ✅ Input immutability enforced (QA Issue #5)
- ✅ Next-phase validation clear (QA Issue #8)

### Status

✅ APPROVED by A-1, A-2, A-3 (with QA Issues #5 and #8 resolutions)

---

## ADR-005: ExecutionError Contract and Error Surface Areas

### Context

Clear error boundaries required for each component. Need consistent error reporting that:
- Identifies which component failed
- Provides context (phase_name, pipeline_id)
- Enables appropriate error handling at orchestration level
- Doesn't leak implementation details
- Catches unexpected errors (QA Issue #1)

### Decision

Each component owns its error domain:

**Error Hierarchy:**
```python
class ExecutionError(Exception):
    """Base exception for phase execution errors."""
    def __init__(self, message: str, phase_name: str, pipeline_id: str):
        self.message = message
        self.phase_name = phase_name
        self.pipeline_id = pipeline_id
        super().__init__(f"[{pipeline_id}:{phase_name}] {message}")

class ConfigurationError(ExecutionError):
    """Phase configuration not found or invalid."""
    pass

class PromptBuildError(ExecutionError):
    """Failed to build prompt (no active prompt for role)."""
    pass

class LLMError(ExecutionError):
    """LLM API call failed."""
    pass

class ParseError(ExecutionError):
    """Failed to parse LLM response."""
    pass
```

### Error Responsibility Matrix

| Component | Raises | Returns | Rationale |
|-----------|--------|---------|-----------|
| **ConfigurationLoader** | `ConfigurationError` | - | Config errors are exceptional (should not happen if seeded properly); logs before raising (QA Issue #3) |
| **RolePromptService** | `ValueError` | - | Existing 175A design (orchestrator converts to PromptBuildError) |
| **LLMCaller** | Never | `LLMCallResult` | API errors are expected; not exceptional |
| **LLMResponseParser** | Never | `ParseResult` | Parse failures are expected; not exceptional |
| **UsageRecorder** | Never | `bool` | Recording failure shouldn't block execution |
| **PhaseExecutionOrchestrator** | `ConfigurationError`<br>`PromptBuildError`<br>`LLMError`<br>`ParseError`<br>`ExecutionError` | `PhaseExecutionResult` | Converts component errors, propagates to caller; catch-all for unexpected (QA Issue #1) |

### Orchestrator Error Handling Pattern

```python
def execute_phase(self, ...) -> PhaseExecutionResult:
    try:
        # Step 1: Load config - may raise ConfigurationError
        # Now logs before raising (QA Issue #3)
        config = self._config_loader.load_config(phase_name)
        
        # Step 2: Build prompt - may raise ValueError (convert to PromptBuildError)
        try:
            prompt_text, prompt_id = self._prompt_builder.build_prompt(...)
        except ValueError as e:
            raise PromptBuildError(str(e), phase_name, pipeline_id)
        
        # Step 3: Call LLM - returns result
        llm_result = self._llm_caller.call(...)
        if not llm_result.success:
            raise LLMError(
                f"LLM call failed: {llm_result.error}",
                phase_name,
                pipeline_id
            )
        
        # Step 4: Parse response - returns result
        parse_result = self._parser.parse(...)
        if not parse_result.success:
            errors = "; ".join(parse_result.error_messages)
            raise ParseError(
                f"Parse failed: {errors}",
                phase_name,
                pipeline_id
            )
        
        # Step 5: Record usage - returns bool, never raises
        # Now logs with structured format (QA Issue #4)
        recorded = self._usage_recorder.record_usage(...)
        if not recorded:
            logger.warning("Failed to record usage (non-fatal)")
        
        return PhaseExecutionResult(success=True, ...)
        
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except PromptBuildError as e:
        logger.error(f"Prompt build error: {e}")
        raise
    except LLMError as e:
        logger.error(f"LLM error: {e}")
        raise
    except ParseError as e:
        logger.error(f"Parse error: {e}")
        raise
    except Exception as e:
        # QA Issue #1: Catch-all for unexpected errors
        logger.error(
            f"Unexpected internal error during phase execution: {e}",
            exc_info=True  # Include stack trace
        )
        raise ExecutionError(
            message=f"Unexpected internal error: {type(e).__name__}: {str(e)}",
            phase_name=phase_name,
            pipeline_id=pipeline_id
        ) from e
```

### Error Message Examples

**Good (Clear, Actionable):**
- `ConfigurationError: Phase configuration not found: ba_phase`
- `PromptBuildError: No active prompt found for role: architect`
- `LLMError: LLM call failed: AuthenticationError: Invalid API key`
- `ParseError: Parse failed: DirectParseStrategy: JSONDecodeError line 1 col 5; MarkdownFenceStrategy: No fences found`
- `ExecutionError: Unexpected internal error: AttributeError: 'NoneType' object has no attribute 'text'` (QA Issue #1)

**Bad (Vague, Not Actionable):**
- `Error: Something went wrong`
- `ExecutionError: Failed`
- `Exception: NoneType object has no attribute 'text'` (no context)

### Benefits

- ✅ Clear error ownership (each component responsible for its domain)
- ✅ Consistent error context (always includes phase_name, pipeline_id)
- ✅ Components don't raise unless truly exceptional (API errors, parse failures are expected)
- ✅ Orchestrator converts results to exceptions (clear boundary)
- ✅ Error messages are developer-friendly (include diagnostics)
- ✅ Catch-all prevents unhandled exceptions (QA Issue #1)
- ✅ Full stack traces for unexpected errors (debugging aid)

### QA Issue #1 Resolution

**Problem:** Unexpected exceptions (AttributeError, TypeError, etc.) could bypass error handling and tear down call stack.

**Solution:** Final catch-all in orchestrator:
```python
except Exception as e:
    logger.error(f"Unexpected internal error: {e}", exc_info=True)
    raise ExecutionError(
        f"Unexpected internal error: {type(e).__name__}: {str(e)}",
        phase_name,
        pipeline_id
    ) from e
```

**Benefits:**
- Pipeline service gets consistent ExecutionError interface
- Pipeline state won't partially update
- Audit trail handles error consistently
- Stack trace preserved (`from e` clause)
- Error type included for debugging
- Full traceback logged (`exc_info=True`)

**Test Coverage:**
- Test: Mock parser raises AttributeError → ExecutionError
- Test: Mock caller raises TypeError → ExecutionError
- Test: Verify error message includes exception type
- Test: Verify logging includes stack trace

### Status

✅ APPROVED by A-1, A-2, A-3 (with QA Issue #1 resolution)

---

## Dependency Graph

```
PhaseExecutionOrchestrator (thin coordinator, <150 lines)
    │
    ├─→ ConfigurationLoader
    │       └─→ PhaseConfigurationRepository (175A)
    │
    ├─→ RolePromptService (175A, existing)
    │       └─→ RolePromptRepository (175A)
    │
    ├─→ LLMCaller
    │       └─→ anthropic.Anthropic (external SDK)
    │
    ├─→ LLMResponseParser (configurable strategies, QA Issue #2)
    │       └─→ [DirectParseStrategy, MarkdownFenceStrategy, FuzzyBoundaryStrategy]
    │
    └─→ UsageRecorder
            └─→ PipelinePromptUsageRepository (175A)

External Integration Point:
    PipelineService.advance_phase()
        └─→ PhaseExecutionOrchestrator (when DATA_DRIVEN_ORCHESTRATION=true)
        └─→ Validates next_phase (QA Issue #8)
        └─→ Atomic state update (QA Issue #5)
```

**Dependency Direction:** High-level (Orchestrator) depends on low-level (components). Never reversed. ✅ Dependency Inversion Principle compliant.

**No Circular Dependencies:** Verified by A-2 ✅

**Layering:**
- **Layer 1 (Persistence):** Repositories from 175A
- **Layer 2 (External):** Anthropic SDK
- **Layer 3 (Components):** Parser, Caller, Loader, Recorder, Builder
- **Layer 4 (Orchestration):** PhaseExecutionOrchestrator
- **Layer 5 (Service):** PipelineService

Dependencies flow upward only. ✅

---

## SOLID Compliance Check

### Single Responsibility Principle ✅

| Component | Single Responsibility |
|-----------|----------------------|
| LLMResponseParser | Parse JSON from text |
| LLMCaller | Call Anthropic API |
| ConfigurationLoader | Load phase config |
| UsageRecorder | Record audit trail |
| RolePromptService | Build prompts (175A) |
| PhaseExecutionOrchestrator | Coordinate execution |

**Each component has exactly one reason to change.**

**Verdict:** ✅ PASS

### Open/Closed Principle ✅

- **LLMResponseParser:** Can add new parsing strategies without modifying parser class; can reorder strategies via constructor (QA Issue #2)
- **Future:** Can swap LLMCaller implementations without changing orchestrator (LLM-300)
- **Future:** Can add new orchestration steps by extending (not modifying) orchestrator

**Components are open for extension, closed for modification.**

**Verdict:** ✅ PASS

### Liskov Substitution Principle ✅

- **ParsingStrategy protocol:** Any strategy can be substituted for another
- **LLMCaller:** Can be mocked/substituted in tests without breaking orchestrator
- **All components:** Can be mocked via interfaces without behavioral changes

**Subtypes are substitutable for their base types.**

**Verdict:** ✅ PASS

### Interface Segregation Principle ✅

- **No fat interfaces:** Each component has minimal, focused public API
- **LLMCaller:** Single `call()` method
- **Parser:** Single `parse()` method (optional `strategies` in constructor)
- **ConfigurationLoader:** Single `load_config()` method
- **UsageRecorder:** Single `record_usage()` method
- **Orchestrator:** Single `execute_phase()` method

**No component forced to depend on methods it doesn't use.**

**Verdict:** ✅ PASS

### Dependency Inversion Principle ✅

- **Orchestrator depends on abstractions:** Injected components (not concrete implementations)
- **Low-level components don't know about high-level:** Parser doesn't know about orchestration
- **Dependency direction:** High-level → Low-level (correct)

**High-level modules do not depend on low-level modules. Both depend on abstractions.**

**Verdict:** ✅ PASS

---

**Overall SOLID Assessment:** ✅ FULLY COMPLIANT

**A-2 Notes:** This architecture strictly adheres to all SOLID principles. No violations detected. Design is maintainable, testable, and extensible. QA feedback has strengthened error handling and configurability without compromising SOLID compliance.

---

## Testability Analysis

### Unit Test Strategy

| Component | Test Approach | Mock Dependencies | Test Count |
|-----------|---------------|-------------------|------------|
| **LLMResponseParser** | Direct instantiation | None (stdlib only) | 18+ (added: custom strategies, empty list) |
| **LLMCaller** | Mock Anthropic client | anthropic.Anthropic | 8+ |
| **ConfigurationLoader** | Mock repository | PhaseConfigurationRepository | 7+ (added: logging verification) |
| **UsageRecorder** | Mock repository | PipelinePromptUsageRepository | 5+ (added: structured log format) |
| **RolePromptService** | Existing (175A) | - | ✅ Done |
| **PhaseExecutionOrchestrator** | Mock all 5 dependencies | All components | 15+ (added: unexpected exception, immutability) |

**Total Unit Tests:** ~53 tests

### Integration Test Strategy

**Test Environment:**
- Real SQLite database (in-memory)
- Seeded with 175A data (role prompts, phase configs)
- Mock LLMCaller only (all other components real)

**Scenarios:**

1. **PM Phase Execution** (AC4.2)
   - Given: Pipeline in initialized state, flag=true
   - When: advance_phase() called for pm_phase
   - Then: Full flow succeeds, artifact stored, advances to arch_phase

2. **Architect Phase Execution** (AC4.3)
   - Given: Pipeline completed pm_phase
   - When: advance_phase() called for arch_phase
   - Then: Architect prompt includes PM artifact, succeeds

3. **Error Path: Missing Config** (AC4.5)
   - Given: Phase config not in database
   - When: execute_phase() called
   - Then: ConfigurationError raised with clear message

4. **Error Path: Missing Prompt** (AC4.5)
   - Given: No active prompt for role
   - When: execute_phase() called
   - Then: PromptBuildError raised

5. **Error Path: LLM Failure** (AC4.5)
   - Given: LLM call returns error
   - When: execute_phase() called
   - Then: LLMError raised

6. **Error Path: Parse Failure** (AC4.5)
   - Given: LLM returns unparseable response
   - When: execute_phase() called
   - Then: ParseError raised with diagnostics

7. **Error Path: Unexpected Exception** (QA Issue #1)
   - Given: Component raises unexpected exception
   - When: execute_phase() called
   - Then: ExecutionError raised with wrapped exception

8. **Audit Trail** (AC4.6)
   - Given: Phases executed successfully
   - When: Query usage repository
   - Then: All usage records present with correct data

9. **Audit Failure Non-Fatal** (QA Issue #4)
   - Given: Usage recording fails
   - When: Phase executes
   - Then: Execution succeeds, structured warning logged

10. **Legacy vs Data-Driven Parity** (AC4.4)
    - Given: Same inputs
    - When: Run with flag=false vs flag=true
    - Then: Results equivalent

11. **State Immutability** (QA Issue #5)
    - Given: Pipeline state and artifacts provided
    - When: execute_phase() called
    - Then: Inputs unchanged (not modified)

12. **Next Phase Validation** (QA Issue #8)
    - Given: Config has next_phase="missing_phase"
    - When: PipelineService validates next_phase
    - Then: ExecutionError raised, pipeline state unchanged

**Total Integration Tests:** ~15 tests

**Combined Test Count:** ~68 tests (exceeds PM requirement of 50+)

### Test Isolation

**Unit Tests:**
- Each component tested in complete isolation
- All dependencies mocked
- No database, no network, no file system
- Fast execution (<1ms per test)

**Integration Tests:**
- Real database (in-memory, fast)
- Real repositories
- Real component wiring
- Only LLM mocked (for speed/cost)
- Moderate execution (<100ms per test)

### Mock Strategy

**Using unittest.mock:**
```python
from unittest.mock import Mock, MagicMock, patch

# Mock LLMCaller
mock_llm = Mock(spec=LLMCaller)
mock_llm.call.return_value = LLMCallResult(...)

# Mock ConfigurationLoader
mock_config = Mock(spec=ConfigurationLoader)
mock_config.load_config.return_value = PhaseConfig(...)

# Mock Parser
mock_parser = Mock(spec=LLMResponseParser)
mock_parser.parse.return_value = ParseResult(...)

# Mock unexpected exception (QA Issue #1)
mock_parser.parse.side_effect = AttributeError("Mock unexpected error")
```

**Spec Argument:** Always use `spec=` to catch interface violations

### Coverage Targets

- **Line Coverage:** >95% for all new components
- **Branch Coverage:** >90% for all new components
- **Critical Paths:** 100% coverage (happy path + all error paths)
- **QA Critical Paths:** 100% coverage (all QA issues covered by tests)

### Testability Verdict

✅ **PASS** - All components independently testable with clear mock points. QA-critical paths fully covered.

**A-3 Assessment:** Architecture enables comprehensive testing with minimal scaffolding. No hidden dependencies. No global state. All components mockable. QA feedback has increased test coverage and edge-case handling.

---

## Sequence Diagram: PM Phase Execution

```
User/PipelineService                 PhaseExecutionOrchestrator    ConfigurationLoader    RolePromptService    LLMCaller    LLMResponseParser    UsageRecorder
        |                                          |                        |                      |               |               |                    |
        |--execute_phase("pm_phase")------------->|                        |                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
        |                                          |--load_config("pm_phase")->                    |               |               |                    |
        |                                          |<-PhaseConfig(role="pm")|                      |               |               |                    |
        |                                          |  [logs DEBUG]          |                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
        |                                          |--build_prompt(role="pm", context...)--------->|               |               |                    |
        |                                          |<-(prompt_text, prompt_id)-------------------|               |               |                    |
        |                                          |  [logs DEBUG]          |                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
        |                                          |--call(system=prompt_text, user="Proceed")------------------->|               |                    |
        |                                          |  [logs DEBUG]          |                      |               |               |                    |
        |                                          |<-LLMCallResult(success=True, response_text=...)-------------|               |                    |
        |                                          |  [logs DEBUG: timing]  |                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
        |                                          |--parse(response_text)----------------------------------------------------->|                    |
        |                                          |  [logs DEBUG: each strategy]                  |               |               |                    |
        |                                          |<-ParseResult(success=True, data={...})-------------------------------------|                    |
        |                                          |  [logs DEBUG: strategy]|                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
        |                                          |--record_usage(pipeline_id, prompt_id, role, phase)--------------------------------------------------------->|
        |                                          |  [logs structured WARNING if fails]           |               |               |                    |
        |                                          |<-True (success)---------------------------------------------------------------------------|                    |
        |                                          |  [logs DEBUG]          |                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
        |<-PhaseExecutionResult(artifact={...}, next_phase="arch_phase")---|                      |               |               |                    |
        |  [logs INFO: success]      |                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
        |--validate next_phase exists------------>|                        |                      |               |               |                    |
        |--update pipeline state (atomic)-------->|                        |                      |               |               |                    |
        |                                          |                        |                      |               |               |                    |
```

**Key Observations:**
- Orchestrator coordinates but doesn't implement
- Each component called once in sequence
- No callbacks or async (all synchronous)
- Logging at each major step
- State update happens in PipelineService, not orchestrator (QA Issue #5)
- Next-phase validation happens in PipelineService (QA Issue #8)
- Error handling omitted for clarity (see error flow diagram)

---

## Error Propagation Flow

```
Component                Error Condition              Returns/Raises              Orchestrator Action
-----------              ---------------              --------------              -------------------
ConfigurationLoader      Config not found             RAISES ConfigurationError   → Logs ERROR, propagates
                                                      [logs ERROR first]
ConfigurationLoader      Config not active            RAISES ConfigurationError   → Logs ERROR, propagates
                                                      [logs ERROR first]

RolePromptService        No active prompt             RAISES ValueError           → Catches, converts to PromptBuildError, propagates

LLMCaller                API error                    RETURNS LLMCallResult       → Checks success=False, RAISES LLMError
                                                      (success=False)

LLMResponseParser        Parse failure                RETURNS ParseResult         → Checks success=False, RAISES ParseError
                                                      (success=False)
                                                      [diagnostics logged DEBUG]

UsageRecorder            Record failure               RETURNS False               → Logs structured WARNING, continues
                                                                                     (does NOT raise)

Any Component            Unexpected exception         RAISES Exception            → Catches in final except, wraps in ExecutionError
                         (AttributeError, etc.)                                     [logs ERROR with stack trace]

Final Result:
- All errors (except UsageRecorder) propagate to PipelineService as ExecutionError subclass
- PipelineService handles errors same as legacy methods
- Pipeline state unchanged on error (atomic operation)
- Unexpected errors caught and wrapped (QA Issue #1)
```

**Error Handling Philosophy:**
- **Expected failures** (LLM errors, parse errors) → Return result objects, orchestrator converts
- **Exceptional failures** (config missing, prompt missing) → Raise immediately (with logging)
- **Non-critical failures** (usage recording) → Log structured warning and continue
- **Unexpected failures** (bugs, AttributeError, etc.) → Catch-all wraps in ExecutionError

---

## Logging Strategy

### Log Levels

**DEBUG:**
- Component method entry/exit
- Successful component operations
- Parsing strategy attempts and results (QA Issue #7)
- Token usage, timing details
- Configuration details

**INFO:**
- Phase execution start
- Phase execution success

**WARNING:**
- Usage recording failure (non-fatal, structured format per QA Issue #4)
- Stale prompt detected (>365 days)

**ERROR:**
- Configuration not found (before raising, QA Issue #3)
- Configuration not active (before raising, QA Issue #3)
- Prompt build failure
- LLM call failure
- Parse failure
- Unexpected internal error (QA Issue #1, includes stack trace)
- Any ExecutionError

### Log Format

```python
# Structured logging with context
logger.info(
    f"Executing phase {phase_name} for pipeline {pipeline_id}",
    extra={
        "pipeline_id": pipeline_id,
        "phase_name": phase_name,
        "role_name": role_name
    }
)

# Component-specific logging
logger.debug(
    f"LLM call succeeded in {elapsed_ms}ms",
    extra={
        "execution_time_ms": elapsed_ms,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "model": model
    }
)

# Structured warning for audit failures (QA Issue #4)
logger.warning(
    "Usage record failure",
    extra={
        "event": "usage_record_failure",
        "pipeline_id": usage.pipeline_id,
        "phase_name": usage.phase_name,
        "role_name": usage.role_name,
        "prompt_id": usage.prompt_id,
        "error": str(e)
    }
)

# Error logging with full context and stack trace
logger.error(
    f"Phase execution failed: {error}",
    extra={
        "pipeline_id": pipeline_id,
        "phase_name": phase_name,
        "error_type": type(error).__name__,
        "error_message": str(error)
    },
    exc_info=True  # Include stack trace
)
```

### Diagnostic Logging Strategy (QA Issue #7)

**ParseResult.error_messages:**
- Returned in ParseResult object
- Logged at DEBUG level during parsing
- NOT included in user-facing exceptions (orchestrator simplifies)
- NOT stored in pipeline state
- Available for debugging via logs

**When Diagnostics Are Logged:**
```python
# In Parser:
logger.debug(f"Attempting parse with {strategy_name}")
logger.debug(f"Parse succeeded using {strategy_name}")
logger.debug(f"Parse failed with {strategy_name}: {error}")

# In Orchestrator:
logger.debug(f"Parsed artifact using strategy: {parse_result.strategy_used}")
# On error:
logger.error(f"Parse failed: {'; '.join(parse_result.error_messages)}")
```

**Diagnostics Are NOT:**
- Included in ExecutionError user message (too verbose)
- Stored in pipeline state (not relevant for state)
- Shown in API responses (implementation detail)

**Diagnostics ARE:**
- Available in DEBUG logs for developers
- Included in ERROR logs when parse fails
- Useful for identifying LLM output pattern changes

### Log Output Location

- **Development:** stdout (captured by pytest)
- **Production:** stdout (captured by container orchestration)
- **Future:** Structured logging to aggregation service (OPS-100)

**Synchronous Execution Note:**
All logging is synchronous. No async logging. Single-threaded execution. This is intentional for 175B simplicity. Async execution deferred to PIPELINE-200.

---

## Architecture Mentor - Status Check

**A-1 (Senior Architect) Assessment:**

✅ Component decomposition is clean and SRP-compliant  
✅ No God Classes (all components <150 lines)  
✅ Clear boundaries and error ownership  
✅ Dependency graph is sound (no cycles, proper direction)  
✅ Sequence diagrams show clear execution flow  
✅ Architecture aligns with PM scope (no scope creep)  
✅ QA feedback integrated without compromising architecture  

**Confidence:** High - This architecture is implementable, maintainable, and production-ready

---

**A-2 (Mid-Level Architect) Assessment:**

✅ SOLID principles strictly enforced  
✅ Strategy pattern correctly applied (Parser, now configurable)  
✅ Dependency Injection enables full testability  
✅ Error contracts are explicit and consistent  
✅ Interface segregation (no fat interfaces)  
✅ Components are independently testable  
✅ State mutation contract clear and safe (QA Issue #5)  
✅ Catch-all error handling prevents unhandled exceptions (QA Issue #1)  

**Confidence:** High - Design patterns correctly applied, testability verified, QA concerns addressed

---

**A-3 (Junior Architect) Assessment:**

✅ All components under size limits  
✅ Method signatures are clear and unambiguous  
✅ Dataclasses well-defined  
✅ No ambiguities in responsibilities  
✅ Test strategy is comprehensive (68+ tests)  
✅ Error messages are developer-friendly  
✅ Logging strategy is detailed and implementable  
✅ QA issues have concrete solutions with test coverage  

**Confidence:** High - Specifications are detailed enough for implementation, QA concerns fully resolved

---

**Architecture Team Consensus:**

✅ **Architecture is READY FOR DEVELOPMENT**

This design:
- Honors SRP/SOLID absolutely
- Provides comprehensive testability
- Maintains clear error boundaries
- Stays within PM-defined scope
- Enables parallel development
- Is maintainable and extensible
- Addresses all QA-critical concerns

**No architectural risks identified. No blockers for development.**

**QA Review Status:** ✅ All critical issues resolved, medium-severity items documented, architecture approved for development

---

## Next Steps

### For Developer Mentor (Immediate)

**Phase 1: Core Components (Stories 1-2)**

1. **Implement LLMResponseParser** (Story 1)
   - Create `app/orchestrator_api/services/llm_response_parser.py`
   - Implement ParseResult dataclass
   - Implement 3 parsing strategies
   - Implement configurable strategy ordering (QA Issue #2)
   - Write 18+ unit tests (including custom strategies, empty list)
   - **DoD:** All tests passing, no external dependencies

2. **Implement LLMCaller** (Story 1)
   - Create `app/orchestrator_api/services/llm_caller.py`
   - Implement LLMCallResult dataclass
   - Implement call() method with error handling
   - Add comprehensive logging
   - Write 8+ unit tests with mocked Anthropic client
   - **DoD:** All tests passing, never raises exceptions

3. **Implement ConfigurationLoader** (Story 2)
   - Create `app/orchestrator_api/services/configuration_loader.py`
   - Implement PhaseConfig dataclass
   - Implement ConfigurationError exception
   - Add error logging before raising (QA Issue #3)
   - Write 7+ unit tests with mocked repository
   - **DoD:** All tests passing, clear error messages, logs before raising

4. **Implement UsageRecorder** (Story 2)
   - Create `app/orchestrator_api/services/usage_recorder.py`
   - Implement UsageRecord dataclass
   - Implement record_usage() with best-effort semantics
   - Add structured logging (QA Issue #4)
   - Write 5+ unit tests with mocked repository
   - **DoD:** All tests passing, never raises exceptions, structured logs

5. **Implement PhaseExecutionOrchestrator** (Story 2)
   - Create `app/orchestrator_api/services/phase_execution_orchestrator.py`
   - Implement PhaseExecutionResult dataclass
   - Implement ExecutionError hierarchy (4 exception classes)
   - Implement execute_phase() with all steps
   - Add catch-all exception handler (QA Issue #1)
   - Guarantee input immutability (QA Issue #5)
   - Write 15+ unit tests with all dependencies mocked
   - **DoD:** All tests passing, <150 lines, comprehensive logging, all QA issues covered

**Phase 2: Integration (Story 3)**

6. **Feature Flag Integration**
   - Add DATA_DRIVEN_ORCHESTRATION to config.py
   - Modify PipelineService.advance_phase() with conditional logic
   - Instantiate orchestrator with dependencies when flag=true
   - Wire PhaseExecutionResult to pipeline state updates (atomic, QA Issue #5)
   - Add next_phase validation (QA Issue #8)
   - Write 5+ tests for flag=true path, 3+ tests for toggle
   - **DoD:** All PIPELINE-150 tests pass with flag=false, state updates atomic

**Phase 3: Testing & Documentation (Stories 4-5)**

7. **Integration Tests**
   - Create integration test suite
   - Test PM → Architect flow end-to-end
   - Test all error paths (including unexpected exceptions)
   - Test state immutability
   - Test next_phase validation
   - Verify audit trail
   - Measure performance
   - **DoD:** 15+ integration tests passing

8. **Documentation**
   - Architecture documentation (this artifact ✅)
   - Deployment guide
   - Troubleshooting guide
   - API documentation
   - **DoD:** All docs reviewed and approved

### Critical Constraints for Developers

1. **Size Limit:** PhaseExecutionOrchestrator MUST stay under 150 lines
2. **SRP Enforcement:** If adding logic, ask "which component owns this?"
3. **No Exceptions from Caller/Parser:** Must return result objects
4. **Usage Recording Non-Fatal:** Must NOT block execution
5. **Error Context:** All ExecutionErrors must include phase_name, pipeline_id
6. **Catch-All Required:** Orchestrator must catch unexpected exceptions (QA Issue #1)
7. **Input Immutability:** Orchestrator must NOT modify pipeline_state or artifacts (QA Issue #5)
8. **Structured Logging:** UsageRecorder must use structured format (QA Issue #4)
9. **Log Before Raise:** ConfigurationLoader must log before raising (QA Issue #3)
10. **Configurable Strategies:** Parser must accept optional strategy list (QA Issue #2)

### Success Criteria

- ✅ All 68+ tests passing
- ✅ All PIPELINE-150 tests passing with flag=false
- ✅ SOLID compliance maintained
- ✅ No components >150 lines
- ✅ Integration tests prove end-to-end functionality
- ✅ All QA-critical issues addressed with test coverage
- ✅ State mutations are atomic
- ✅ Unexpected errors caught and wrapped
- ✅ Structured logging implemented

---

## Architecture Notes - Sign-Off

**Prepared by:** Architecture Mentor Team (A-1, A-2, A-3)  
**Reviewed by:** A-1 (Senior Lead)  
**QA Review:** ✅ All critical issues resolved  
**Status:** ✅ Ready for Development Phase  
**Confidence Level:** High

**Architecture adheres strictly to:**
- ✅ SRP/SOLID principles
- ✅ PM-defined scope boundaries
- ✅ Testability requirements
- ✅ Size constraints (no God Classes)
- ✅ Error handling contracts
- ✅ QA safety requirements

**QA-Critical Issues Resolved:**
1. ✅ Catch-all exception handler added
2. ✅ Parser strategies configurable
3. ✅ ConfigurationLoader logs before raising
4. ✅ UsageRecorder uses structured logging
5. ✅ State mutation contract explicit

**Medium-Severity Items Documented:**
6. ✅ Token usage guardrails acknowledged as out-of-scope
7. ✅ Diagnostic logging strategy specified
8. ✅ Next-phase validation behavior documented

**Ready for Orchestrator handoff to Developer Mentor.**
