# WS-PGC-VALIDATION-001: Code-Based Validation and PGC Answer Persistence

**Status:** Ready for Implementation
**Created:** 2026-01-24
**Scope:** Multi-commit (two phases)

---

## Context

The document workflow system now runs end-to-end:
```
Start → PGC (questions) → User Input (JSON) → Generation → QA → Persist → Complete
```

Two gaps remain:

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
├── __init__.py
├── promotion_validator.py
├── validation_result.py
└── rules.py
```

### Input Contract

The validator receives:

```python
@dataclass
class PromotionValidationInput:
    pgc_questions: List[Dict[str, Any]]  # From PGC node output
    pgc_answers: Dict[str, Any]          # User's answers
    generated_document: Dict[str, Any]   # The document to validate
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
- It traces to a PGC question with `priority: "must"` AND
- The user provided a specific answer (not null/empty/undecided)

OR:
- It is explicitly stated in the intake brief (check `context_state["concierge_intake"]`)

```python
def check_promotion_validity(
    constraints: List[Dict],
    pgc_questions: List[Dict],
    pgc_answers: Dict,
    intake: Dict
) -> List[ValidationIssue]:
    """
    For each constraint, verify it has valid grounding.
    
    Warning if:
    - Constraint appears to derive from should/could answer
    - Constraint has no traceable source
    """
```

Implementation approach:
- Build a set of "valid constraint sources" from must-answers and intake
- For each constraint, attempt to match against valid sources (fuzzy text matching OK)
- If no match found, emit warning

#### Rule 2: Internal Contradiction (ERROR)

The same semantic item CANNOT appear in both `assumptions` and `known_constraints`.

```python
def check_internal_contradictions(
    constraints: List[Dict],
    assumptions: List[Dict]
) -> List[ValidationIssue]:
    """
    Error if same concept appears in both sections.
    
    Match by:
    - Exact text similarity (>80% match)
    - Same topic keywords
    """
```

#### Rule 3: Policy Conformance (WARNING)

No section may contain questions about:
- Budget, funding, financial constraints
- Authority, approval, sign-off (unless compliance-related)

```python
PROHIBITED_TERMS = [
    "budget", "funding", "financial", "cost", "price", "expense",
    "authority", "approval", "sign-off", "permission", "authorized"
]

def check_policy_conformance(document: Dict) -> List[ValidationIssue]:
    """
    Scan unknowns, stakeholder_questions for prohibited terms.
    """
```

#### Rule 4: Grounding Validation (WARNING)

`mvp_guardrails` entries must trace to:
- Explicit intake statement, OR
- Must-priority PGC answer

```python
def check_grounding(
    guardrails: List[Dict],
    pgc_questions: List[Dict],
    pgc_answers: Dict,
    intake: Dict
) -> List[ValidationIssue]:
    """
    Warning if guardrail appears to be inferred rather than stated.
    """
```

### Integration Point

In `app/domain/workflow/nodes/qa.py`, add validation call BEFORE LLM-based QA:

```python
async def execute(self, node_id: str, node_config: Dict, context: DocumentWorkflowContext, state_snapshot) -> NodeResult:
    # ... existing code ...
    
    # NEW: Run code-based validation first
    from app.domain.workflow.validation import PromotionValidator
    
    validator = PromotionValidator()
    validation_input = PromotionValidationInput(
        pgc_questions=context.get("pgc_questions", []),
        pgc_answers=context.get("pgc_answers", {}),
        generated_document=document
    )
    validation_result = validator.validate(validation_input)
    
    # Fail immediately on errors
    if not validation_result.passed:
        return NodeResult(
            outcome="failed",
            metadata={
                "validation_errors": [asdict(e) for e in validation_result.errors],
                "validation_warnings": [asdict(w) for w in validation_result.warnings]
            }
        )
    
    # Continue to LLM-based QA, but include warnings in metadata
    # ... existing LLM QA code ...
```

### Tests

Create `tests/tier1/workflow/validation/test_promotion_validator.py`:

```python
class TestPromotionValidity:
    def test_must_answer_creates_valid_constraint(self):
        """Constraint from must-answer should not warn."""
        
    def test_should_answer_as_constraint_warns(self):
        """Constraint derived from should-answer emits warning."""
        
    def test_could_answer_as_constraint_warns(self):
        """Constraint derived from could-answer emits warning."""
        
    def test_intake_stated_constraint_valid(self):
        """Constraint explicitly in intake is valid."""

class TestInternalContradictions:
    def test_same_item_in_both_sections_errors(self):
        """Same concept in assumptions and constraints is error."""
        
    def test_similar_but_different_items_ok(self):
        """Related but distinct items should not error."""

class TestPolicyConformance:
    def test_budget_question_warns(self):
        """Questions about budget emit warning."""
        
    def test_timeline_question_ok(self):
        """Questions about timeline are acceptable."""

class TestGrounding:
    def test_stated_guardrail_valid(self):
        """Guardrail from intake doesn't warn."""
        
    def test_inferred_guardrail_warns(self):
        """Guardrail not traceable to input warns."""
```

### Acceptance Criteria

- [ ] `PromotionValidator` class exists with `validate()` method
- [ ] All four rule checks implemented
- [ ] Validation runs before LLM-based QA in qa.py
- [ ] Errors cause QA node to fail with structured error metadata
- [ ] Warnings passed through to final QA result
- [ ] All tests pass
- [ ] No new dependencies required

---

## Phase 2: PGC Answer Persistence

### Objective

Store PGC answers as first-class documents with full provenance, enabling:
- Audit trail of what was answered
- QA validation against source answers
- Future analytics on question effectiveness

### Database Model

Add to `app/api/models/pgc_answer.py`:

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

Create `alembic/versions/create_pgc_answers_table.py`:

```python
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
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
def downgrade():
    op.drop_table('pgc_answers')
```

### Repository

Create `app/domain/repositories/pgc_answer_repository.py`:

```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.models.pgc_answer import PGCAnswer

class PGCAnswerRepository:
    def __init__(self, db: AsyncSession):
        self._db = db
    
    async def save(self, answer: PGCAnswer) -> PGCAnswer:
        self._db.add(answer)
        await self._db.commit()
        await self._db.refresh(answer)
        return answer
    
    async def get_by_execution(self, execution_id: str) -> Optional[PGCAnswer]:
        result = await self._db.execute(
            select(PGCAnswer).where(PGCAnswer.execution_id == execution_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_project(self, project_id: str) -> List[PGCAnswer]:
        result = await self._db.execute(
            select(PGCAnswer)
            .where(PGCAnswer.project_id == project_id)
            .order_by(PGCAnswer.created_at.desc())
        )
        return list(result.scalars().all())
```

### Integration Points

#### 1. Save answers when user submits input

In `app/api/v1/routers/document_workflows.py`, update `submit_user_input`:

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
        from uuid import UUID
        
        pgc_answer = PGCAnswer(
            execution_id=execution_id,
            workflow_id=state.workflow_id,
            project_id=UUID(state.project_id),
            pgc_node_id=state.current_node_id,
            schema_ref=state.pending_user_input_schema_ref or "unknown",
            questions=state.pending_user_input_payload.get("questions", []),
            answers=request.user_input
        )
        db.add(pgc_answer)
        await db.commit()
    
    # ... rest of existing code ...
```

#### 2. Load answers for validation

In `app/domain/workflow/plan_executor.py`, when preparing context for QA:

```python
# Before executing QA node, load PGC answers from database
if node_type == "qa":
    from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
    
    repo = PGCAnswerRepository(self._db_session)
    pgc_answer = await repo.get_by_execution(state.execution_id)
    
    if pgc_answer:
        context["pgc_questions"] = pgc_answer.questions
        context["pgc_answers"] = pgc_answer.answers
```

#### 3. API endpoint to retrieve answers

Add to `app/api/v1/routers/document_workflows.py`:

```python
@router.get("/executions/{execution_id}/pgc-answers")
async def get_pgc_answers(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
    
    repo = PGCAnswerRepository(db)
    answer = await repo.get_by_execution(execution_id)
    
    if not answer:
        raise HTTPException(404, "PGC answers not found")
    
    return answer.to_dict()
```

### Tests

Create `tests/tier1/repositories/test_pgc_answer_repository.py`:

```python
class TestPGCAnswerRepository:
    async def test_save_and_retrieve(self):
        """Save PGC answer and retrieve by execution_id."""
        
    async def test_get_by_project(self):
        """Retrieve all PGC answers for a project."""
        
    async def test_get_nonexistent_returns_none(self):
        """Getting nonexistent answer returns None."""
```

Create `tests/api/v1/test_pgc_answers_endpoint.py`:

```python
class TestPGCAnswersEndpoint:
    async def test_get_answers_after_submission(self):
        """After submitting answers, can retrieve them via API."""
        
    async def test_get_answers_404_before_submission(self):
        """Before submission, endpoint returns 404."""
```

### Acceptance Criteria

- [ ] `PGCAnswer` model exists with all fields
- [ ] Migration creates `pgc_answers` table
- [ ] Repository with save, get_by_execution, get_by_project
- [ ] Answers persisted when user submits input at PGC node
- [ ] Answers loaded into context for QA validation
- [ ] API endpoint to retrieve answers
- [ ] All tests pass

---

## Execution Order

1. **Phase 1 first** - Validation logic is self-contained, no DB changes
2. **Phase 2 second** - Builds on Phase 1 by providing source data for validation

## Prohibited Actions

- Do NOT modify existing prompt files
- Do NOT change the workflow JSON structure
- Do NOT run database migrations (provide the migration file only)
- Do NOT modify LLM-based QA logic (only add code-based validation before it)

## Verification

After implementation, the following test scenario should work:

```python
# Setup: PGC question with priority="should"
pgc_questions = [{"id": "TRACKING", "priority": "should", ...}]
pgc_answers = {"TRACKING": True}

# Document incorrectly promotes to constraint
document = {
    "known_constraints": [
        {"id": "CNS-1", "constraint": "Must include progress tracking"}
    ],
    "assumptions": []
}

# Validation should catch this
result = validator.validate(PromotionValidationInput(
    pgc_questions=pgc_questions,
    pgc_answers=pgc_answers,
    generated_document=document
))

assert len(result.warnings) == 1
assert result.warnings[0].check_type == "promotion"
assert "should" in result.warnings[0].message.lower()
```

---

## Files to Create

### Phase 1
- `app/domain/workflow/validation/__init__.py`
- `app/domain/workflow/validation/promotion_validator.py`
- `app/domain/workflow/validation/validation_result.py`
- `app/domain/workflow/validation/rules.py`
- `tests/tier1/workflow/validation/__init__.py`
- `tests/tier1/workflow/validation/test_promotion_validator.py`

### Phase 2
- `app/api/models/pgc_answer.py`
- `app/domain/repositories/pgc_answer_repository.py`
- `alembic/versions/create_pgc_answers_table.py`
- `tests/tier1/repositories/test_pgc_answer_repository.py`
- `tests/api/v1/test_pgc_answers_endpoint.py`

## Files to Modify

### Phase 1
- `app/domain/workflow/nodes/qa.py` - Add validation call before LLM QA

### Phase 2
- `app/api/v1/routers/document_workflows.py` - Save answers, add endpoint
- `app/domain/workflow/plan_executor.py` - Load answers for QA context
- `app/api/models/__init__.py` - Export PGCAnswer

---

**End of Work Statement**