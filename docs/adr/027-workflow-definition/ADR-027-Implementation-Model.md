# ADR-027 Implementation Model

_Version: 1.0_  
_Date: 2026-01-02_

This document provides the reference implementation model for ADR-027 (Workflow Definition & Governance).

---

## 1. Core Concepts

### Workflow = Hierarchy + Sequence

A workflow defines:

1. **Document Types** — What documents exist in this workflow
2. **Entity Types** — Collection items that are not standalone documents (e.g., epics, stories)
3. **Steps** — Who produces what, in what order, with what inputs
4. **Iteration** — How to loop over collections

### Separation of Concerns

| Concern | Governed By | Implemented By |
|---------|-------------|----------------|
| Documents can own documents | ADR-011 | Workflow validator |
| Step execution loop | ADR-012 | `StepExecutor` |
| Clarification format | ADR-024 | Schema validation |
| Workflow definition | ADR-027 | `workflow.v1.json` files |
| Intake gate | ADR-025 | Pre-workflow step |
| Concierge role | ADR-026 | Role prompt |

---

## 2. Workflow Definition Schema

### 2.1 Top-Level Structure

```json
{
  "schema_version": "workflow.v1",
  "workflow_id": "software_product_development",
  "revision": "wfrev_2026_01_02_a",
  "effective_date": "2026-01-02",
  "name": "Software Product Development",
  "description": "End-to-end workflow for software product creation",
  
  "document_types": { },
  "entity_types": { },
  "steps": [ ]
}
```

**Note:** Semantic versioning (`1.0.0`) is NOT used in workflows. The `revision` is opaque, and `manifest.json` is the authoritative version binding.

### 2.2 Document Types

Document types are standalone, governed artifacts that are persisted and auditable.

```json
"document_types": {
  "project_discovery": {
    "name": "Project Discovery",
    "scope": "project",
    "may_own": [],
    "acceptance_required": false
  },
  "epic_backlog": {
    "name": "Epic Backlog",
    "scope": "project",
    "may_own": ["epic"],
    "collection_field": "epics",
    "acceptance_required": true,
    "accepted_by": ["pm"]
  },
  "project_architecture": {
    "name": "Project Technical Architecture",
    "scope": "project",
    "may_own": [],
    "acceptance_required": true,
    "accepted_by": ["architect"]
  },
  "epic_architecture": {
    "name": "Epic Technical Architecture",
    "scope": "epic",
    "may_own": [],
    "acceptance_required": false
  },
  "story_backlog": {
    "name": "Story Backlog",
    "scope": "epic",
    "may_own": ["story"],
    "collection_field": "stories",
    "acceptance_required": true,
    "accepted_by": ["pm", "ba"]
  }
}
```

**Key fields:**

| Field | Purpose |
|-------|---------|
| `scope` | Where this document lives (project, epic, story) |
| `may_own` | Entity types this document can contain |
| `collection_field` | Field name containing owned entities |
| `acceptance_required` | Whether human sign-off is needed |
| `accepted_by` | List of roles that may accept (allows flexibility) |

### 2.3 Entity Types

Entity types are collection items inside documents. They are NOT standalone documents.

```json
"entity_types": {
  "epic": {
    "name": "Epic",
    "parent_doc_type": "epic_backlog",
    "creates_scope": "epic"
  },
  "story": {
    "name": "Story",
    "parent_doc_type": "story_backlog",
    "creates_scope": "story"
  }
}
```

**Key distinction:**

- `document_types` → Stored as standalone artifacts, versioned, auditable
- `entity_types` → Items within a document's collection, create child scopes for iteration

### 2.4 Steps

Steps define the production line — who produces what, in what order.

```json
"steps": [
  {
    "step_id": "discovery",
    "role": "architect",
    "task_prompt": "Project Discovery v1.0",
    "produces": "project_discovery",
    "scope": "project",
    "inputs": [
      { "doc_type": "intake", "scope": "project" }
    ]
  },
  {
    "step_id": "epic_backlog",
    "role": "pm",
    "task_prompt": "Epic Backlog v1.0",
    "produces": "epic_backlog",
    "scope": "project",
    "inputs": [
      { "doc_type": "project_discovery", "scope": "project" }
    ]
  },
  {
    "step_id": "project_architecture",
    "role": "architect",
    "task_prompt": "Technical Architecture v1.0",
    "produces": "project_architecture",
    "scope": "project",
    "inputs": [
      { "doc_type": "project_discovery", "scope": "project" },
      { "doc_type": "epic_backlog", "scope": "project" }
    ]
  },
  {
    "step_id": "per_epic",
    "iterate_over": {
      "doc_type": "epic_backlog",
      "collection_field": "epics",
      "entity_type": "epic"
    },
    "scope": "epic",
    "steps": [
      {
        "step_id": "epic_architecture",
        "role": "architect",
        "task_prompt": "Epic Architecture v1.0",
        "produces": "epic_architecture",
        "scope": "epic",
        "inputs": [
          { "doc_type": "project_architecture", "scope": "project" },
          { "entity_type": "epic", "scope": "epic", "context": true }
        ]
      },
      {
        "step_id": "story_backlog",
        "role": "ba",
        "task_prompt": "Story Backlog v1.0",
        "produces": "story_backlog",
        "scope": "epic",
        "inputs": [
          { "entity_type": "epic", "scope": "epic", "context": true },
          { "doc_type": "epic_architecture", "scope": "epic" },
          { "doc_type": "project_architecture", "scope": "project", "required": false }
        ]
      },
      {
        "step_id": "per_story",
        "iterate_over": {
          "doc_type": "story_backlog",
          "collection_field": "stories",
          "entity_type": "story"
        },
        "scope": "story",
        "steps": [
          {
            "step_id": "implementation",
            "role": "developer",
            "task_prompt": "Story Implementation v1.0",
            "produces": "implementation",
            "scope": "story",
            "inputs": [
              { "entity_type": "story", "scope": "story", "context": true },
              { "doc_type": "epic_architecture", "scope": "epic" }
            ]
          }
        ]
      }
    ]
  }
]
```

**Input reference structure:**

```json
{
  "doc_type": "project_discovery",
  "scope": "project",
  "required": true,
  "context": false
}
```

- `doc_type` OR `entity_type` — What to reference
- `scope` — Where to find it
- `required` — Default: true
- `context` — If true, this is the iteration context item

---

## 3. Step State Machine

Every step follows a state machine for resumability:

```
                    +----------+
                    | pending  |
                    +----+-----+
                         |
                         v
+------------------------+------------------------+
| awaiting_clarification |<-- Clarification needed|
+------------+-----------+------------------------+
             | (user answers)
             v
+------------------------+
|      executing         |
+------------+-----------+
             |
     +-------+-------+
     |               |
     v               v
+---------+   +---------------------+
| failed  |   | awaiting_acceptance |
+---------+   +----------+----------+
                         | (human accepts)
                         v
                   +-----------+
                   | completed |
                   +-----------+
```

**States:**

| State | Meaning | Resumes When |
|-------|---------|--------------|
| `pending` | Not yet started | Workflow reaches this step |
| `awaiting_clarification` | Questions sent to user | User provides answers |
| `executing` | LLM processing | N/A (transient) |
| `awaiting_acceptance` | Output needs human approval | Human accepts/rejects |
| `completed` | Done, output stored | N/A (terminal) |
| `failed` | Unrecoverable error | Manual intervention |

---

## 4. Execution Engine

### 4.1 WorkflowExecutor

```python
class WorkflowExecutor:
    """
    Executes a workflow definition.
    Each step runs through ADR-012's loop.
    Handles iteration and state persistence.
    """
    
    def __init__(
        self,
        workflow: dict,
        step_executor: StepExecutor,
        state_store: WorkflowStateStore
    ):
        self.workflow = workflow
        self.step_executor = step_executor
        self.state_store = state_store
    
    async def execute(self, context: WorkflowContext) -> WorkflowResult:
        """
        Execute workflow from current state.
        Resumes from last incomplete step if paused.
        """
        for step in self.workflow["steps"]:
            result = await self._execute_step(step, context)
            
            # Step is paused (clarification or acceptance)
            if result.status in ("awaiting_clarification", "awaiting_acceptance"):
                await self.state_store.save(context, step, result)
                return WorkflowResult(
                    status=result.status,
                    paused_at=step["step_id"],
                    context=context
                )
            
            # Step failed
            if result.status == "failed":
                await self.state_store.save(context, step, result)
                return WorkflowResult(
                    status="failed",
                    failed_at=step["step_id"],
                    error=result.error,
                    context=context
                )
        
        return WorkflowResult(status="completed", context=context)
    
    async def _execute_step(
        self,
        step: dict,
        context: WorkflowContext
    ) -> StepResult:
        """Execute a single step or iteration block."""
        
        # Check for existing state (resume)
        existing_state = await self.state_store.get_step_state(
            context, step["step_id"]
        )
        if existing_state and existing_state.status == "completed":
            return existing_state
        
        # Iteration step
        if "iterate_over" in step:
            return await self._execute_iteration(step, context)
        
        # Regular step
        return await self._execute_single_step(step, context)
    
    async def _execute_iteration(
        self,
        step: dict,
        context: WorkflowContext
    ) -> StepResult:
        """Execute iteration block over a collection."""
        
        iter_config = step["iterate_over"]
        collection = context.resolve_collection(
            doc_type=iter_config["doc_type"],
            collection_field=iter_config["collection_field"]
        )
        
        for item in collection:
            child_context = context.create_child(
                scope=step["scope"],
                entity_type=iter_config["entity_type"],
                item=item
            )
            
            for substep in step["steps"]:
                result = await self._execute_step(substep, child_context)
                
                if result.status != "completed":
                    return result
        
        return StepResult(status="completed")
    
    async def _execute_single_step(
        self,
        step: dict,
        context: WorkflowContext
    ) -> StepResult:
        """Execute a single production step via ADR-012."""
        
        # Gather inputs
        inputs = context.gather_inputs(step["inputs"])
        
        # Get acceptance config from document_types
        doc_type_config = self.workflow["document_types"].get(step["produces"], {})
        acceptance_required = doc_type_config.get("acceptance_required", False)
        accepted_by = doc_type_config.get("accepted_by", [])
        
        # Execute via StepExecutor (ADR-012)
        result = await self.step_executor.execute(
            role=step["role"],
            task_prompt=step["task_prompt"],
            inputs=inputs,
            scope=step["scope"],
            acceptance_required=acceptance_required,
            accepted_by=accepted_by
        )
        
        # Store output if complete
        if result.status == "completed":
            context.store_document(
                doc_type=step["produces"],
                content=result.output,
                scope=step["scope"]
            )
        
        return result
```

### 4.2 StepExecutor (ADR-012 Loop)

```python
class StepExecutor:
    """
    Executes a single step per ADR-012.
    This is the mechanical heart of the system.
    """
    
    async def execute(
        self,
        role: str,
        task_prompt: str,
        inputs: List[InputDocument],
        scope: str,
        acceptance_required: bool = False,
        accepted_by: List[str] = None
    ) -> StepResult:
        
        # 1. Load prompts
        role_prompt = self.prompt_registry.get_role(role)
        task = self.prompt_registry.get_task(task_prompt)
        
        # 2. Build request
        request = self._build_request(role_prompt, task, inputs)
        
        # 3. Clarification gate (ADR-024)
        clarification_result = await self._clarification_gate(request)
        if clarification_result.has_questions:
            return StepResult(
                status="awaiting_clarification",
                questions=clarification_result.questions
            )
        
        # 4. Execute task
        output = await self._execute_llm(request)
        
        # 5. QA gate (ADR-012)
        qa_result = await self._qa_gate(output, task.qa_criteria)
        
        if not qa_result.passed:
            # 6. Remediation loop
            output = await self._remediation_loop(
                request=request,
                output=output,
                qa_findings=qa_result,
                max_attempts=3
            )
            
            if output is None:
                return StepResult(
                    status="failed",
                    error="QA remediation exhausted"
                )
        
        # 7. Acceptance gate (if required)
        if acceptance_required:
            return StepResult(
                status="awaiting_acceptance",
                output=output,
                accepted_by=accepted_by
            )
        
        return StepResult(status="completed", output=output)
    
    async def _clarification_gate(self, request: Request) -> ClarificationResult:
        """
        Execute clarification check per ADR-024.
        Output must conform to clarification_question_set.v1 schema.
        """
        ...
    
    async def _qa_gate(self, output: dict, criteria: QACriteria) -> QAResult:
        """
        Execute QA evaluation per ADR-012.
        QA is a veto, not an advisor.
        """
        ...
    
    async def _remediation_loop(
        self,
        request: Request,
        output: dict,
        qa_findings: QAResult,
        max_attempts: int
    ) -> Optional[dict]:
        """
        Attempt to fix QA failures per ADR-012.
        Returns None if remediation exhausted.
        """
        ...
```

### 4.3 WorkflowContext

```python
@dataclass
class WorkflowContext:
    """
    Tracks execution state across a workflow.
    Documents are stored by scope.
    """
    
    project_id: UUID
    workflow_id: str
    correlation_id: UUID
    
    # Document storage by scope
    project_documents: Dict[str, Document] = field(default_factory=dict)
    epic_documents: Dict[UUID, Dict[str, Document]] = field(default_factory=dict)
    story_documents: Dict[UUID, Dict[str, Document]] = field(default_factory=dict)
    
    # Entity storage (collection items)
    epics: Dict[UUID, dict] = field(default_factory=dict)
    stories: Dict[UUID, dict] = field(default_factory=dict)
    
    # Current position
    current_scope: str = "project"
    current_epic_id: Optional[UUID] = None
    current_story_id: Optional[UUID] = None
    
    def gather_inputs(self, input_refs: List[dict]) -> List[InputDocument]:
        """
        Resolve input references to actual documents/entities.
        Respects scope hierarchy and required flags.
        """
        results = []
        
        for ref in input_refs:
            if "doc_type" in ref:
                doc = self._resolve_document(ref)
            else:
                doc = self._resolve_entity(ref)
            
            if doc is None and ref.get("required", True):
                raise MissingInputError(ref)
            
            if doc is not None:
                results.append(doc)
        
        return results
    
    def _resolve_document(self, ref: dict) -> Optional[Document]:
        """Resolve document reference by scope."""
        scope = ref["scope"]
        doc_type = ref["doc_type"]
        
        if scope == "project":
            return self.project_documents.get(doc_type)
        elif scope == "epic":
            epic_docs = self.epic_documents.get(self.current_epic_id, {})
            return epic_docs.get(doc_type)
        elif scope == "story":
            story_docs = self.story_documents.get(self.current_story_id, {})
            return story_docs.get(doc_type)
        
        return None
    
    def _resolve_entity(self, ref: dict) -> Optional[dict]:
        """Resolve entity (collection item) reference."""
        entity_type = ref["entity_type"]
        
        if entity_type == "epic":
            return self.epics.get(self.current_epic_id)
        elif entity_type == "story":
            return self.stories.get(self.current_story_id)
        
        return None
    
    def store_document(self, doc_type: str, content: dict, scope: str):
        """Store document at appropriate scope level."""
        if scope == "project":
            self.project_documents[doc_type] = content
        elif scope == "epic":
            if self.current_epic_id not in self.epic_documents:
                self.epic_documents[self.current_epic_id] = {}
            self.epic_documents[self.current_epic_id][doc_type] = content
        elif scope == "story":
            if self.current_story_id not in self.story_documents:
                self.story_documents[self.current_story_id] = {}
            self.story_documents[self.current_story_id][doc_type] = content
    
    def resolve_collection(self, doc_type: str, collection_field: str) -> List[dict]:
        """Get collection items from a document."""
        doc = self._resolve_document({
            "doc_type": doc_type, 
            "scope": self._infer_scope(doc_type)
        })
        if doc is None:
            return []
        return doc.get(collection_field, [])
    
    def create_child(
        self, 
        scope: str, 
        entity_type: str, 
        item: dict
    ) -> "WorkflowContext":
        """Create child context for iteration."""
        child = WorkflowContext(
            project_id=self.project_id,
            workflow_id=self.workflow_id,
            correlation_id=self.correlation_id,
            project_documents=self.project_documents,
            epic_documents=self.epic_documents,
            story_documents=self.story_documents,
            epics=self.epics,
            stories=self.stories,
            current_scope=scope
        )
        
        # Generate ID for the entity if needed
        item_id = item.get("id") or uuid4()
        
        if entity_type == "epic":
            child.current_epic_id = item_id
            child.epics[item_id] = item
        elif entity_type == "story":
            child.current_epic_id = self.current_epic_id
            child.current_story_id = item_id
            child.stories[item_id] = item
        
        return child
```

---

## 5. Workflow Validator

The validator enforces ADR-011 (ownership rules) and schema integrity.

```python
class WorkflowValidator:
    """
    Validates workflow definitions before execution.
    Enforces ADR-011 ownership rules and schema integrity.
    """
    
    def validate(self, workflow: dict) -> ValidationResult:
        """Run all validations. Fail fast."""
        
        errors = []
        
        # 1. Schema validation
        errors.extend(self._validate_schema(workflow))
        
        # 2. Document type consistency
        errors.extend(self._validate_document_types(workflow))
        
        # 3. Ownership graph is DAG (no cycles)
        errors.extend(self._validate_ownership_dag(workflow))
        
        # 4. Step references exist
        errors.extend(self._validate_step_references(workflow))
        
        # 5. Scope consistency
        errors.extend(self._validate_scope_consistency(workflow))
        
        # 6. Iteration paths exist
        errors.extend(self._validate_iteration_paths(workflow))
        
        # 7. Reference rules (ADR-011 §5)
        errors.extend(self._validate_reference_rules(workflow))
        
        # 7. Reference rules (ADR-011 §5)
        errors.extend(self._validate_reference_rules(workflow))
        
        return ValidationResult(
        errors.extend(self._validate_iteration_paths(workflow))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
    
    def _validate_ownership_dag(self, workflow: dict) -> List[str]:
        """Ensure may_own relationships form a tree-friendly DAG."""
        errors = []
        
        doc_types = workflow.get("document_types", {})
        
        # Build graph
        graph = {}
        for doc_id, doc_config in doc_types.items():
            graph[doc_id] = doc_config.get("may_own", [])
        
        # Check for cycles
        visited = set()
        path = set()
        
        def has_cycle(node):
            if node in path:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            path.add(node)
            
            for child in graph.get(node, []):
                if has_cycle(child):
                    return True
            
            path.remove(node)
            return False
        
        for doc_id in graph:
            if has_cycle(doc_id):
                errors.append(f"Ownership cycle detected involving '{doc_id}'")
        
        return errors
    
    def _validate_scope_consistency(self, workflow: dict) -> List[str]:
        """Ensure steps produce documents at appropriate scopes."""
        errors = []
        
        doc_types = workflow.get("document_types", {})
        
        def check_step(step, allowed_scope):
            if "iterate_over" in step:
                child_scope = step["scope"]
                for substep in step.get("steps", []):
                    check_step(substep, child_scope)
            else:
                produces = step.get("produces")
                step_scope = step.get("scope")
                
                if produces and produces in doc_types:
                    doc_scope = doc_types[produces].get("scope")
                    if doc_scope != step_scope:
                        errors.append(
                            f"Step '{step['step_id']}' has scope '{step_scope}' "
                            f"but produces '{produces}' which has scope '{doc_scope}'"
                        )
        
        for step in workflow.get("steps", []):
            check_step(step, "project")
        
        return errors
```

---

## 5.1 Reference Rule Validation (ADR-011 §5)

The validator enforces ADR-011's reference rules mechanically:

```python
def _validate_reference_rules(self, workflow: dict) -> List[str]:
    """
    Enforce ADR-011 §5 reference rules:
    - Child → Parent/Ancestor: Permitted
    - Same scope: Only iteration context item (context: true)
    - Sibling → Sibling: Forbidden
    - Cross-branch: Forbidden
    - Parent → Child (descendant): Forbidden
    """
    errors = []
    scope_hierarchy = self._build_scope_hierarchy(workflow)
    
    def validate_step_inputs(step: dict, current_scope: str):
        for input_ref in step.get("inputs", []):
            ref_scope = input_ref.get("scope")
            is_context = input_ref.get("context", False)
            ref_type = input_ref.get("doc_type") or input_ref.get("entity_type")
            
            # Rule 1: Ancestor scope - always permitted
            if scope_hierarchy.is_ancestor(ref_scope, current_scope):
                continue
            
            # Rule 2: Same scope - only if iteration context item
            if ref_scope == current_scope:
                if is_context:
                    continue  # Iteration item, allowed
                errors.append(
                    f"Step '{step['step_id']}': same-scope reference to "
                    f"'{ref_type}' forbidden (not iteration context)"
                )
                continue
            
            # Rule 3: Descendant scope - forbidden
            if scope_hierarchy.is_descendant(ref_scope, current_scope):
                errors.append(
                    f"Step '{step['step_id']}': descendant reference to "
                    f"'{ref_type}' at '{ref_scope}' forbidden"
                )
                continue
            
            # Rule 4: Cross-branch - forbidden
            errors.append(
                f"Step '{step['step_id']}': cross-branch reference to "
                f"'{ref_type}' at '{ref_scope}' forbidden"
            )
    
    def walk_steps(steps: List[dict], current_scope: str):
        for step in steps:
            if "iterate_over" in step:
                walk_steps(step.get("steps", []), step["scope"])
            else:
                validate_step_inputs(step, current_scope)
    
    walk_steps(workflow.get("steps", []), "project")
    return errors


class ScopeHierarchy:
    """Helper to check scope relationships."""
    
    def __init__(self, parent_map: dict):
        self.parent_map = parent_map
    
    def is_ancestor(self, maybe_ancestor: str, of_scope: str) -> bool:
        current = self.parent_map.get(of_scope)
        while current is not None:
            if current == maybe_ancestor:
                return True
            current = self.parent_map.get(current)
        return False
    
    def is_descendant(self, maybe_descendant: str, of_scope: str) -> bool:
        return self.is_ancestor(of_scope, maybe_descendant)
```

### Reference Rules Summary

| Reference Direction | Permitted | Example |
|---------------------|-----------|---------|
| Child to Parent | Yes | Story step references epic_architecture |
| Child to Ancestor | Yes | Story step references project_architecture |
| Same scope (context) | Yes | Epic step references current epic entity |
| Same scope (other) | No | Epic step references another epic doc |
| Parent to Child | No | Project step references story doc |
| Cross-branch | No | One story references another story |

### Iteration Context Item

The `context: true` flag marks an input as "the current iteration item" — the only same-scope reference permitted:

```json
{
  "step_id": "per_epic",
  "iterate_over": { "entity_type": "epic" },
  "steps": [
    {
      "inputs": [
        { "entity_type": "epic", "context": true }
      ]
    }
  ]
}
```

---

## 6. Directory Structure

```
seed/
├── workflows/
│   ├── software_product_development.v1.json
│   ├── construction_project.v1.json
│   └── strategy_document.v1.json
├── prompts/
│   ├── roles/
│   │   ├── Architect 1.0.txt
│   │   ├── Project Manager 1.0.txt
│   │   ├── Business Analyst 1.0.txt
│   │   ├── Developer 1.0.txt
│   │   ├── Quality Assurance 1.0.txt
│   │   └── Concierge 1.0.txt
│   └── tasks/
│       ├── Concierge Intake v1.0.txt
│       ├── Project Discovery v1.0.txt
│       ├── Epic Backlog v1.0.txt
│       ├── Technical Architecture v1.0.txt
│       ├── Epic Architecture v1.0.txt
│       ├── Story Backlog v1.0.txt
│       └── Story Implementation v1.0.txt
├── schemas/
│   ├── workflow.v1.json
│   ├── clarification_question_set.v1.json
│   └── intake_gate_result.v1.json
└── manifest.json
```

---

## 7. Build Order

### Phase 0: Workflow Validator (Prerequisite)

- JSON schema for `workflow.v1`
- Semantic validation (DAG, scope consistency, reference existence)
- Fail fast before any execution exists

### Phase 1: Step Executor (ADR-012)

- Clarification gate with ADR-024 schema validation
- QA gate with veto authority
- Remediation loop
- Acceptance gate

### Phase 2: Workflow Executor

- Step sequencing
- Iteration blocks
- State persistence for resume

### Phase 3: Context & State

- Document storage by scope
- Entity (collection item) management
- Input resolution

### Phase 4: First Workflow

- `software_product_development.v1.json`
- Wire to existing handlers
- End-to-end test

### Phase 5: Intake Integration

- Concierge as pre-workflow gate
- Intake document feeds workflow selection
- Route to appropriate workflow

---

## 8. ADR Alignment

| ADR | How This Model Implements It |
|-----|------------------------------|
| **011** | `document_types.may_own` + validator enforces ownership |
| **012** | `StepExecutor` implements the canonical loop |
| **024** | Clarification gate validates against schema, referenced by 012 |
| **025** | Intake step produces document that informs workflow selection |
| **026** | Concierge role prompt governs intake behavior |
| **027** | Workflow JSON files are the governed capability maps |

---

## 9. Open Questions (Deferred)

1. **Parallel steps** — Can sibling steps execute concurrently? (Deferred to v2)
2. **Conditional steps** — Skip steps based on document content? (Deferred to v2)
3. **Cross-workflow references** — Can one workflow invoke another? (Deferred)
4. **Workflow migration** — Handling mid-execution workflow changes (per ADR-027 Section 9)
