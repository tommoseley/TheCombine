# WS-PGC-VALIDATION-001: Code-Based Validation and PGC Answer Persistence

**Status:** Complete
**Created:** 2026-01-24
**Completed:** 2026-01-24
**Scope:** Multi-commit (two phases)

---

## Governing References

- **ADR-012**: Pre-Generation Clarification (PGC as mandatory readiness gate)
- **ADR-010**: LLM Execution Logging (audit trail requirements)
- **Schema**: `seed/schemas/clarification_question_set.v2.json`
- **Workflow**: `seed/workflows/project_discovery.v1.json` (v1.7.0)

---

## Preconditions

Before starting this work:

- [x] ADR-041 Phases 1-7 complete (prompt template includes operational)
- [x] Schema v2 migration complete (`clarification_question_set.v2.json` in use)
- [x] QA node executor exists at `app/domain/workflow/nodes/qa.py`
- [x] Document workflow end-to-end functional (start → PGC → input → generation → QA → persist)
- [x] Database has `pending_user_input_payload` and `pending_user_input_schema_ref` columns

---

## Purpose

The document workflow system runs end-to-end but has two gaps:

1. **Semantic QA is non-deterministic** - LLM-based QA v1.1 doesn't reliably catch promotion violations (e.g., "should" priority answers becoming hard constraints)

2. **PGC answers lack provenance** - Answers stored only in `context_state["pgc_answers"]`, not as auditable first-class documents

This work statement addresses both with deterministic code-based solutions.

---

## Phase 1: Code-Based Promotion Validation

### Objective

Create a deterministic validation layer that runs BEFORE LLM-based QA to catch promotion violations and internal contradictions.

### Location

```
app/domain/workflow/validation/
â”œâ”€â”€ __init__.py
â”œâ”€â”€ promotion_validator.py
â”œâ”€â”€ validation_result.py
â””â”€â”€ rules.py
```

### Input Contract

```python
@dataclass
class PromotionValidationInput:
    pgc_questions: List[Dict[str, Any]]  # From PGC node output
    pgc_answers: Dict[str, Any]          # User's answers
    generated_document: Dict[str, Any]   # The document to validate
    intake: Optional[Dict[str, Any]] = None  # Concierge intake (for grounding check)
```

### Output Contract

```python
@dataclass
class ValidationIssue:
    severity: Literal["error", "warning"]
    check_type: Literal["promotion", "contradiction", "policy", "grounding"]
    section: str
    field_id: Optional[str]
    message: str
    evidence: Dict[str, Any]  # Source data that triggered the issue

@dataclass
class PromotionValidationResult:
    passed: bool              # True if no errors (warnings OK)
    issues: List[ValidationIssue]
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]
```

### Validation Rules

#### Rule 1: Promotion Validity (WARNING)

A `known_constraints` entry is valid ONLY if:
- It traces to a PGC question with `priority: "must"` AND user provided a specific answer

OR:
- It is explicitly stated in the intake brief

**Matching Algorithm:**
- Extract keywords from constraint text (nouns, verbs - exclude stopwords)
- Extract keywords from PGC question text and answer value/label
- Match if keyword overlap >= 50% of constraint keywords
- Case-insensitive comparison
- Use simple word tokenization (split on whitespace/punctuation)

```python
def check_promotion_validity(
    constraints: List[Dict],
    pgc_questions: List[Dict],
    pgc_answers: Dict,
    intake: Optional[Dict]
) -> List[ValidationIssue]:
    """
    For each constraint, verify it has valid grounding.
    
    Warning if:
    - Constraint appears to derive from should/could answer
    - Constraint has no traceable source (< 50% keyword match)
    """
```

#### Rule 2: Internal Contradiction (ERROR)

The same semantic item CANNOT appear in both `assumptions` and `known_constraints`.

**Matching Algorithm:**
- Extract keywords from both texts
- Calculate Jaccard similarity: |intersection| / |union|
- Match if similarity > 0.5 (50% keyword overlap)
- Case-insensitive comparison

```python
def check_internal_contradictions(
    constraints: List[Dict],
    assumptions: List[Dict]
) -> List[ValidationIssue]:
    """
    Error if same concept appears in both sections.
    """
```

#### Rule 3: Policy Conformance (WARNING)

No section may contain questions about prohibited topics.

```python
PROHIBITED_TERMS = {
    "budget": ["budget", "funding", "financial", "cost", "price", "expense", "money"],
    "authority": ["authority", "approval", "sign-off", "permission", "authorized", "approve"]
}

def check_policy_conformance(document: Dict) -> List[ValidationIssue]:
    """
    Scan unknowns, stakeholder_questions for prohibited terms.
    Case-insensitive substring match.
    """
```

#### Rule 4: Grounding Validation (WARNING)

`mvp_guardrails` entries must trace to explicit input (intake or must-answer).

Uses same keyword matching as Rule 1.

```python
def check_grounding(
    guardrails: List[Dict],
    pgc_questions: List[Dict],
    pgc_answers: Dict,
    intake: Optional[Dict]
) -> List[ValidationIssue]:
    """
    Warning if guardrail appears to be inferred rather than stated.
    """
```

### Integration Point

**File:** `app/domain/workflow/nodes/qa.py`

Add validation call BEFORE LLM-based QA:

```python
async def execute(self, node_id: str, node_config: Dict, context: DocumentWorkflowContext, state_snapshot) -> NodeResult:
    # ... existing setup code ...
    
    # NEW: Run code-based validation first
    from app.domain.workflow.validation import PromotionValidator, PromotionValidationInput
    
    validator = PromotionValidator()
    validation_input = PromotionValidationInput(
        pgc_questions=context.get("pgc_questions", []),
        pgc_answers=context.get("pgc_answers", {}),
        generated_document=document,
        intake=context.get("concierge_intake")
    )
    validation_result = validator.validate(validation_input)
    
    # Fail immediately on errors
    if not validation_result.passed:
        return NodeResult(
            outcome="failed",
            metadata={
                "validation_errors": [asdict(e) for e in validation_result.errors],
                "validation_warnings": [asdict(w) for w in validation_result.warnings],
                "validation_source": "code_based"
            }
        )
    
    # Continue to LLM-based QA, include warnings in final metadata
    # ... existing LLM QA code ...
    
    # Merge warnings into final result metadata
    if validation_result.warnings:
        result_metadata["code_validation_warnings"] = [asdict(w) for w in validation_result.warnings]
```

### Test Location

Create directory: `tests/tier1/workflow/validation/`

**File:** `tests/tier1/workflow/validation/test_promotion_validator.py`

```python
import pytest
from app.domain.workflow.validation import PromotionValidator, PromotionValidationInput

class TestPromotionValidity:
    def test_must_answer_creates_valid_constraint(self):
        """Constraint from must-answer with 50%+ keyword match should not warn."""
        
    def test_should_answer_as_constraint_warns(self):
        """Constraint derived from should-answer emits warning."""
        
    def test_could_answer_as_constraint_warns(self):
        """Constraint derived from could-answer emits warning."""
        
    def test_intake_stated_constraint_valid(self):
        """Constraint explicitly in intake is valid."""
        
    def test_no_match_warns(self):
        """Constraint with < 50% keyword match to any source warns."""

class TestInternalContradictions:
    def test_same_item_in_both_sections_errors(self):
        """Same concept (> 50% Jaccard) in assumptions and constraints is error."""
        
    def test_similar_but_different_items_ok(self):
        """Items with < 50% Jaccard similarity should not error."""

class TestPolicyConformance:
    def test_budget_question_warns(self):
        """Questions containing 'budget' emit warning."""
        
    def test_timeline_question_ok(self):
        """Questions about timeline are acceptable."""
        
    def test_case_insensitive(self):
        """'BUDGET' and 'Budget' both trigger warning."""

class TestGrounding:
    def test_stated_guardrail_valid(self):
        """Guardrail matching intake keyword doesn't warn."""
        
    def test_inferred_guardrail_warns(self):
        """Guardrail not traceable to input warns."""
```

### Phase 1 Acceptance Criteria

- [x] `PromotionValidator` class exists with `validate()` method
- [x] All four rule checks implemented with specified algorithms
- [x] Keyword extraction function with stopword removal
- [x] Jaccard similarity function for text comparison
- [x] Validation runs before LLM-based QA in `app/domain/workflow/nodes/qa.py`
- [x] Errors cause QA node to fail with structured error metadata
- [x] Warnings passed through to final QA result
- [x] All tests pass (minimum 10 test cases)
- [x] No new external dependencies (use stdlib only)

---

## Phase 2: PGC Answer Persistence

### Objective

Store PGC answers as first-class documents with full provenance.

### Database Model

**File:** `app/api/models/pgc_answer.py`

```python
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base
import uuid
from datetime import datetime

class PGCAnswer(Base):
    __tablename__ = "pgc_answers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Links to workflow execution
    execution_id = Column(String(36), nullable=False, index=True)
    workflow_id = Column(String(100), nullable=False)
    
    # Links to project
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # The node that generated the questions
    pgc_node_id = Column(String(100), nullable=False)
    
    # Schema reference for validation
    schema_ref = Column(String(255), nullable=False)
    
    # The questions that were asked (snapshot)
    questions = Column(JSONB, nullable=False)
    
    # The answers provided
    answers = Column(JSONB, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "project_id": str(self.project_id),
            "pgc_node_id": self.pgc_node_id,
            "schema_ref": self.schema_ref,
            "questions": self.questions,
            "answers": self.answers,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
```

### Migration

**File:** `alembic/versions/create_pgc_answers_table.py`

```python
"""create pgc_answers table

Revision ID: create_pgc_answers
Create Date: 2026-01-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'create_pgc_answers'
down_revision = 'add_pgc_payload_fields'  # Chain after previous migration
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'pgc_answers',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('execution_id', sa.String(36), nullable=False, index=True),
        sa.Column('workflow_id', sa.String(100), nullable=False),
        sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('pgc_node_id', sa.String(100), nullable=False),
        sa.Column('schema_ref', sa.String(255), nullable=False),
        sa.Column('questions', postgresql.JSONB(), nullable=False),
        sa.Column('answers', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
def downgrade():
    op.drop_table('pgc_answers')
```

### Repository

**File:** `app/domain/repositories/pgc_answer_repository.py`

**IMPORTANT:** Follow existing pattern - repository does NOT commit. Caller owns transaction.

```python
"""
PGC Answer Repository.

IMPORTANT: Does NOT commit. Caller owns transaction.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.api.models.pgc_answer import PGCAnswer

logger = logging.getLogger(__name__)


class PGCAnswerRepository:
    """PostgreSQL repository for PGC answers. Does NOT commit internally."""
    
    def __init__(self, db: AsyncSession):
        self._db = db
    
    async def add(self, answer: PGCAnswer) -> None:
        """Add answer to session. Caller must commit."""
        self._db.add(answer)
        logger.info(f"Added PGC answer for execution {answer.execution_id}")
    
    async def get_by_execution(self, execution_id: str) -> Optional[PGCAnswer]:
        """Get PGC answer by execution ID."""
        result = await self._db.execute(
            select(PGCAnswer).where(PGCAnswer.execution_id == execution_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_project(self, project_id: UUID) -> List[PGCAnswer]:
        """Get all PGC answers for a project, newest first."""
        result = await self._db.execute(
            select(PGCAnswer)
            .where(PGCAnswer.project_id == project_id)
            .order_by(PGCAnswer.created_at.desc())
        )
        return list(result.scalars().all())
```

### Integration Points

#### 1. Save answers when user submits input

**File:** `app/api/v1/routers/document_workflows.py`

In `submit_user_input` endpoint:

```python
@router.post("/executions/{execution_id}/input")
async def submit_user_input(
    execution_id: str,
    request: UserInputRequest,
    db: AsyncSession = Depends(get_db)
):
    # ... existing code to load state ...
    
    # NEW: Persist PGC answers if this is a PGC node
    if state.current_node_id == "pgc" and state.pending_user_input_payload:
        from app.api.models.pgc_answer import PGCAnswer
        from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
        from uuid import UUID
        
        repo = PGCAnswerRepository(db)
        pgc_answer = PGCAnswer(
            execution_id=execution_id,
            workflow_id=state.workflow_id,
            project_id=UUID(state.project_id),
            pgc_node_id=state.current_node_id,
            schema_ref=state.pending_user_input_schema_ref or "unknown",
            questions=state.pending_user_input_payload.get("questions", []),
            answers=request.user_input
        )
        await repo.add(pgc_answer)
        # Note: commit happens later with state save
    
    # ... rest of existing code (which commits) ...
```

#### 2. Load answers for QA validation

**File:** `app/domain/workflow/plan_executor.py`

Before executing QA node, ensure context has PGC data:

```python
# When preparing to execute QA node
if current_node.get("type") == "qa" and self._db_session:
    from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
    
    repo = PGCAnswerRepository(self._db_session)
    pgc_answer = await repo.get_by_execution(state.execution_id)
    
    if pgc_answer:
        # Add to context for validation
        context["pgc_questions"] = pgc_answer.questions
        context["pgc_answers"] = pgc_answer.answers
        logger.info(f"Loaded PGC answers for QA validation: {len(pgc_answer.questions)} questions")
```

#### 3. API endpoint to retrieve answers

**File:** `app/api/v1/routers/document_workflows.py`

```python
@router.get("/executions/{execution_id}/pgc-answers")
async def get_pgc_answers(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get PGC questions and answers for an execution."""
    from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
    
    repo = PGCAnswerRepository(db)
    answer = await repo.get_by_execution(execution_id)
    
    if not answer:
        raise HTTPException(status_code=404, detail="PGC answers not found for this execution")
    
    return answer.to_dict()
```

### Test Location

**File:** `tests/tier1/repositories/test_pgc_answer_repository.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
from app.api.models.pgc_answer import PGCAnswer

class TestPGCAnswerRepository:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def repo(self, mock_db):
        return PGCAnswerRepository(mock_db)
    
    async def test_add_does_not_commit(self, repo, mock_db):
        """Repository add should not commit - caller owns transaction."""
        answer = PGCAnswer(
            execution_id="exec-123",
            workflow_id="test",
            project_id=uuid4(),
            pgc_node_id="pgc",
            schema_ref="schema://test",
            questions=[],
            answers={}
        )
        await repo.add(answer)
        mock_db.add.assert_called_once_with(answer)
        mock_db.commit.assert_not_called()
    
    async def test_get_by_execution_returns_none_when_missing(self, repo, mock_db):
        """Getting nonexistent answer returns None."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        result = await repo.get_by_execution("nonexistent")
        assert result is None
```

### Phase 2 Acceptance Criteria

- [x] `PGCAnswer` model exists with all fields
- [x] Migration file creates `pgc_answers` table with correct schema
- [x] `PGCAnswerRepository` follows project pattern (does NOT commit)
- [x] Answers persisted when user submits input at PGC node
- [x] Answers loaded into context before QA node execution
- [x] API endpoint `GET /executions/{id}/pgc-answers` returns answers
- [x] API endpoint returns 404 if no answers exist
- [x] All tests pass (minimum 5 test cases)
- [x] Export `PGCAnswer` from `app/api/models/__init__.py`

---

## Definition of Done

This work statement is complete when:

1. **Phase 1 Complete:**
   - All validation rules implemented and tested
   - Integration in qa.py verified with manual test
   - Promotion violations produce warnings
   - Internal contradictions produce errors

2. **Phase 2 Complete:**
   - PGC answers persist to database
   - Answers retrievable via API
   - QA node receives PGC data in context

3. **Integration Verified:**
   - End-to-end test: start workflow → answer PGC → generate → QA uses persisted answers
   - Validation warnings appear in QA result metadata

4. **Documentation:**
   - Session summary written to `docs/session_logs/`
   - `PROJECT_STATE.md` updated

---

## Execution Order

1. **Phase 1 first** - Validation logic is self-contained, no DB changes
2. **Phase 2 second** - Builds on Phase 1 by providing source data for validation

---

## Prohibited Actions

- Do NOT modify existing prompt files (*.txt in seed/prompts/)
- Do NOT change the workflow JSON structure
- Do NOT run database migrations (provide the migration file only)
- Do NOT modify LLM-based QA logic (only add code-based validation BEFORE it)
- Do NOT add external dependencies (use stdlib only)
- Do NOT commit in repository methods (caller owns transaction)

---

## Files to Create

### Phase 1
- `app/domain/workflow/validation/__init__.py`
- `app/domain/workflow/validation/promotion_validator.py`
- `app/domain/workflow/validation/validation_result.py`
- `app/domain/workflow/validation/rules.py`
- `tests/tier1/workflow/__init__.py`
- `tests/tier1/workflow/validation/__init__.py`
- `tests/tier1/workflow/validation/test_promotion_validator.py`

### Phase 2
- `app/api/models/pgc_answer.py`
- `app/domain/repositories/pgc_answer_repository.py`
- `alembic/versions/create_pgc_answers_table.py`
- `tests/tier1/repositories/test_pgc_answer_repository.py`

## Files to Modify

### Phase 1
- `app/domain/workflow/nodes/qa.py` - Add validation call before LLM QA

### Phase 2
- `app/api/v1/routers/document_workflows.py` - Save answers, add endpoint
- `app/domain/workflow/plan_executor.py` - Load answers for QA context
- `app/api/models/__init__.py` - Export PGCAnswer

---

## Verification Test

After implementation, this scenario should work:

```python
# Setup: PGC question with priority="should"
pgc_questions = [{"id": "TRACKING", "text": "progress tracking?", "priority": "should"}]
pgc_answers = {"TRACKING": True}

# Document incorrectly promotes to constraint
document = {
    "known_constraints": [
        {"id": "CNS-1", "constraint": "Must include progress tracking"}
    ],
    "assumptions": []
}

# Validation should catch this
from app.domain.workflow.validation import PromotionValidator, PromotionValidationInput

validator = PromotionValidator()
result = validator.validate(PromotionValidationInput(
    pgc_questions=pgc_questions,
    pgc_answers=pgc_answers,
    generated_document=document
))

assert result.passed == True  # Warnings don't fail
assert len(result.warnings) == 1
assert result.warnings[0].check_type == "promotion"
assert "should" in result.warnings[0].message.lower()
```

---

## Implementation Report

**Completed:** 2026-01-24
**Implementer:** Claude (Opus 4.5)

### Phase 1 Acceptance Criteria - ALL MET

- [x] `PromotionValidator` class exists with `validate()` method
- [x] All four rule checks implemented with specified algorithms
- [x] Keyword extraction function with stopword removal
- [x] Jaccard similarity function for text comparison
- [x] Validation runs before LLM-based QA in `app/domain/workflow/nodes/qa.py`
- [x] Errors cause QA node to fail with structured error metadata
- [x] Warnings passed through to final QA result
- [x] All tests pass (29 test cases - exceeds minimum of 10)
- [x] No new external dependencies (stdlib only)

### Phase 2 Acceptance Criteria - ALL MET

- [x] `PGCAnswer` model exists with all fields
- [x] Migration file creates `pgc_answers` table with correct schema
- [x] `PGCAnswerRepository` follows project pattern (does NOT commit)
- [x] Answers persisted when user submits input at PGC node
- [x] Answers loaded into context before QA node execution
- [x] API endpoint `GET /executions/{id}/pgc-answers` returns answers
- [x] API endpoint returns 404 if no answers exist
- [x] All tests pass (7 test cases - exceeds minimum of 5)
- [x] Export `PGCAnswer` from `app/api/models/__init__.py`

### Files Created

| File | Purpose |
|------|---------|
| `app/domain/workflow/validation/__init__.py` | Module exports |
| `app/domain/workflow/validation/validation_result.py` | Data classes |
| `app/domain/workflow/validation/rules.py` | Rule implementations |
| `app/domain/workflow/validation/promotion_validator.py` | PromotionValidator class |
| `app/api/models/pgc_answer.py` | SQLAlchemy model |
| `app/domain/repositories/pgc_answer_repository.py` | Repository (no commit) |
| `alembic/versions/20260124_001_create_pgc_answers_table.py` | Migration |
| `tests/tier1/workflow/__init__.py` | Test directory |
| `tests/tier1/workflow/validation/__init__.py` | Test directory |
| `tests/tier1/workflow/validation/test_promotion_validator.py` | 29 tests |
| `tests/tier1/repositories/__init__.py` | Test directory |
| `tests/tier1/repositories/test_pgc_answer_repository.py` | 7 tests |

### Files Modified

| File | Change |
|------|--------|
| `app/domain/workflow/nodes/qa.py` | Integrated code-based validation |
| `app/domain/workflow/plan_executor.py` | Load PGC answers for QA |
| `app/api/v1/routers/document_workflows.py` | Persist answers, new endpoint |
| `app/api/models/__init__.py` | Export PGCAnswer |

### Verification Test Result

```
Validation passed: True
Warnings: 1 (promotion from should-priority)
Errors: 0
WS verification scenario: PASSED
```

---

**End of Work Statement**