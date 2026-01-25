# WS-PGC-UX-001: PGC Questions UI Integration

**Status:** Ready for Implementation  
**Created:** 2026-01-24  
**Scope:** Multi-commit (frontend + backend integration)

---

## Governing References

- **ADR-012**: Pre-Generation Clarification (PGC workflow)
- **ADR-039**: Document Interaction Workflows
- **WS-PGC-VALIDATION-001**: Code-based validation (completed)
- **Schema**: `seed/schemas/clarification_question_set.v2.json`

---

## Preconditions

- [ ] WS-PGC-VALIDATION-001 complete (code-based validation operational)
- [ ] `pending_user_input_payload` field available in workflow state
- [ ] `pgc_answers` table exists (migration applied)
- [ ] Document workflow API functional (`/api/v1/document-workflows/*`)

---

## Purpose

The document workflow system pauses at PGC nodes to collect user answers, but the UI currently doesn't handle this. The "Generate Document" button triggers a background task that fails when workflows pause for PGC.

This work statement implements the UX to:
1. Render PGC questions from `pending_user_input_payload`
2. Collect and submit user answers
3. Resume workflow after answers submitted
4. Show progress during generation
5. Redirect to document on completion

---

## Current Flow (Broken)

```
User clicks "Generate Project Discovery"
  → POST /projects/{id}/documents/project_discovery/build
  → run_workflow_build() starts
  → Workflow pauses at PGC node
  → Background task fails: "Workflow requires user input (unexpected)"
```

## Target Flow

```
User clicks "Generate Project Discovery"
  → POST /projects/{id}/workflows/project_discovery/start
  → Workflow starts, pauses at PGC
  → UI renders PGC questions form
  → User submits answers
  → POST /projects/{id}/workflows/{exec_id}/pgc-answers
  → Workflow resumes, runs to completion
  → UI shows success, links to document
```

---

## Implementation

### 1. New Routes

**File:** `app/web/routes/public/workflow_build_routes.py`

```python
"""
Workflow-based document build routes.

For document types with PGC workflows (e.g., project_discovery),
provides interactive build flow with question/answer UI.
"""

router = APIRouter(tags=["workflow-build"])

# Document types that use workflow builds (have PGC)
WORKFLOW_BUILD_TYPES = {"project_discovery"}


@router.post("/projects/{project_id}/workflows/{doc_type_id}/start")
async def start_workflow_build(
    request: Request,
    project_id: str,
    doc_type_id: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    Start workflow-based document build.
    
    Returns:
    - PGC questions partial if workflow pauses
    - Generating partial if workflow runs without pause
    - Complete partial if workflow finishes immediately
    """
    # Validate doc_type uses workflow
    if doc_type_id not in WORKFLOW_BUILD_TYPES:
        raise HTTPException(400, f"{doc_type_id} does not use workflow builds")
    
    # Load project
    project = await _get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Load intake document (required input)
    intake = await _get_intake_document(db, project["id"])
    if not intake:
        raise HTTPException(400, "Concierge Intake required before generating Project Discovery")
    
    # Create executor and start workflow
    executor = await _get_executor(db)
    
    document_id = f"{doc_type_id}-{uuid4().hex[:12]}"
    state = await executor.start_execution(
        document_id=document_id,
        document_type=doc_type_id,
        initial_context={
            "concierge_intake": intake.content,
            "project_id": str(project["id"]),
        },
    )
    
    # Run to first pause or completion
    state = await executor.run_to_completion_or_pause(state.execution_id)
    
    # Return appropriate partial based on state
    return _render_workflow_state(request, state, project, doc_type_id)


@router.post("/projects/{project_id}/workflows/{execution_id}/pgc-answers")
async def submit_pgc_answers(
    request: Request,
    project_id: str,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    Submit PGC answers and resume workflow.
    
    Form data: answers[QUESTION_ID] = value
    """
    # Parse form data
    form = await request.form()
    answers = _parse_pgc_form(form)
    
    # Load project for context
    project = await _get_project(db, project_id)
    
    # Submit answers to workflow
    executor = await _get_executor(db)
    state = await executor.submit_user_input(
        execution_id=execution_id,
        user_input=answers,  # Dict[str, Any]
    )
    
    # Run to next pause or completion
    state = await executor.run_to_completion_or_pause(execution_id)
    
    # Return appropriate partial
    return _render_workflow_state(request, state, project, state.document_type)


@router.get("/projects/{project_id}/workflows/{execution_id}/status")
async def get_workflow_status(
    request: Request,
    project_id: str,
    execution_id: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    Poll endpoint for workflow status during generation.
    
    Used by HTMX to check progress and update UI.
    """
    project = await _get_project(db, project_id)
    executor = await _get_executor(db)
    state = await executor._persistence.load(execution_id)
    
    if not state:
        raise HTTPException(404, "Workflow not found")
    
    return _render_workflow_state(request, state, project, state.document_type)


def _render_workflow_state(
    request: Request,
    state,
    project: dict,
    doc_type_id: str,
) -> HTMLResponse:
    """Render appropriate partial based on workflow state."""
    
    doc_type_config = {
        "project_discovery": {
            "name": "Project Discovery",
            "icon": "compass",
        }
    }
    config = doc_type_config.get(doc_type_id, {"name": doc_type_id, "icon": "file-text"})
    
    context = {
        "request": request,
        "project": project,
        "project_id": project["id"],
        "execution_id": state.execution_id,
        "doc_type_id": doc_type_id,
        "doc_type_name": config["name"],
        "doc_type_icon": config["icon"],
    }
    
    if state.status == DocumentWorkflowStatus.COMPLETED:
        context["workflow_state"] = "complete"
        return templates.TemplateResponse(
            "public/pages/partials/_workflow_build_container.html",
            context,
        )
    
    if state.status == DocumentWorkflowStatus.FAILED:
        context["workflow_state"] = "failed"
        context["error_message"] = state.terminal_outcome or "Unknown error"
        return templates.TemplateResponse(
            "public/pages/partials/_workflow_build_container.html",
            context,
        )
    
    if state.pending_user_input and state.pending_user_input_payload:
        # PGC questions
        questions = state.pending_user_input_payload.get("questions", [])
        context["workflow_state"] = "paused_pgc"
        context["questions"] = questions
        context["pending_user_input_payload"] = state.pending_user_input_payload
        return templates.TemplateResponse(
            "public/pages/partials/_workflow_build_container.html",
            context,
        )
    
    # Running state
    context["workflow_state"] = "running"
    context["progress"] = _estimate_progress(state)
    context["status_message"] = _get_status_message(state)
    return templates.TemplateResponse(
        "public/pages/partials/_workflow_build_container.html",
        context,
    )


def _parse_pgc_form(form) -> Dict[str, Any]:
    """Parse form data into answers dict.
    
    Handles:
    - answers[QUESTION_ID] = "value" (single value)
    - answers[QUESTION_ID][] = ["a", "b"] (multi-select)
    - answers[QUESTION_ID] = "true"/"false" (yes/no)
    """
    answers = {}
    multi_values = {}
    
    for key, value in form.multi_items():
        # Parse answers[QUESTION_ID] or answers[QUESTION_ID][]
        if key.startswith("answers["):
            # Extract question ID
            if key.endswith("[]"):
                q_id = key[8:-2]  # answers[X][] -> X
                if q_id not in multi_values:
                    multi_values[q_id] = []
                multi_values[q_id].append(value)
            else:
                q_id = key[8:-1]  # answers[X] -> X
                # Convert yes/no to boolean
                if value == "true":
                    answers[q_id] = True
                elif value == "false":
                    answers[q_id] = False
                else:
                    answers[q_id] = value
    
    # Merge multi-values
    answers.update(multi_values)
    
    return answers


def _estimate_progress(state) -> int:
    """Estimate progress percentage based on workflow state."""
    node_progress = {
        "pgc": 10,
        "generation": 50,
        "qa": 80,
        "persist": 95,
        "end": 100,
    }
    return node_progress.get(state.current_node_id, 30)


def _get_status_message(state) -> str:
    """Get human-readable status message."""
    node_messages = {
        "pgc": "Preparing questions...",
        "generation": "Generating document...",
        "qa": "Validating quality...",
        "persist": "Saving document...",
        "end": "Completing...",
    }
    return node_messages.get(state.current_node_id, "Processing...")
```

### 2. Templates

**File:** `app/web/templates/public/pages/partials/_workflow_build_container.html`

```html
{# Workflow Build Container - Handles workflow states for document generation #}
{# Expected: project, project_id, execution_id, doc_type_id, doc_type_name, doc_type_icon, workflow_state #}

<div id="workflow-container" class="p-6 max-w-5xl mx-auto">
    {% if workflow_state == 'paused_pgc' %}
        {% include "public/pages/partials/_pgc_questions.html" %}
    
    {% elif workflow_state == 'running' %}
        {# Generating State - with polling #}
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
            <div class="max-w-md mx-auto text-center">
                <div class="relative mx-auto mb-6 w-16 h-16">
                    <div class="absolute inset-0 rounded-full border-4 border-gray-200 dark:border-gray-700"></div>
                    <div class="absolute inset-0 rounded-full border-4 border-violet-600 border-t-transparent animate-spin"></div>
                </div>
                <h2 class="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Generating {{ doc_type_name }}</h2>
                <p class="text-gray-600 dark:text-gray-400 mb-4">{{ status_message }}</p>
                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                    <div class="bg-violet-600 h-2.5 rounded-full transition-all" style="width: {{ progress }}%"></div>
                </div>
            </div>
        </div>
        
        {# Poll for updates #}
        <div hx-get="/projects/{{ project_id }}/workflows/{{ execution_id }}/status"
             hx-trigger="every 2s"
             hx-target="#workflow-container"
             hx-swap="innerHTML"></div>
    
    {% elif workflow_state == 'complete' %}
        {# Success #}
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-800 p-8">
            <div class="max-w-md mx-auto text-center">
                <div class="mx-auto mb-6 w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                    <i data-lucide="check" class="w-8 h-8 text-green-600"></i>
                </div>
                <h2 class="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Document Created</h2>
                <p class="text-gray-600 dark:text-gray-400 mb-6">{{ doc_type_name }} generated successfully.</p>
                <a href="/projects/{{ project_id }}/documents/{{ doc_type_id }}"
                   hx-get="/projects/{{ project_id }}/documents/{{ doc_type_id }}"
                   hx-target="#main-content"
                   hx-push-url="true"
                   class="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-700 text-white rounded-lg font-medium">
                    <i data-lucide="file-text" class="w-5 h-5"></i>
                    View Document
                </a>
            </div>
        </div>
    
    {% elif workflow_state == 'failed' %}
        {# Error #}
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-800 p-8">
            <div class="max-w-md mx-auto text-center">
                <div class="mx-auto mb-6 w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                    <i data-lucide="alert-circle" class="w-8 h-8 text-red-600"></i>
                </div>
                <h2 class="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Generation Failed</h2>
                <p class="text-gray-600 dark:text-gray-400 mb-6">{{ error_message }}</p>
                <button onclick="window.location.reload()"
                        class="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium">
                    Try Again
                </button>
            </div>
        </div>
    {% endif %}
</div>

<script>if (typeof lucide !== 'undefined') lucide.createIcons();</script>
```

**File:** `app/web/templates/public/pages/partials/_pgc_questions.html`

```html
{# PGC Questions Form #}
{# Expected: execution_id, project_id, questions[], doc_type_name #}

<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
    <div class="flex items-center gap-3 mb-6">
        <div class="p-2 bg-violet-100 dark:bg-violet-900/30 rounded-lg">
            <i data-lucide="help-circle" class="w-6 h-6 text-violet-600"></i>
        </div>
        <div>
            <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Clarification Questions</h2>
            <p class="text-sm text-gray-500">Answer these questions to generate {{ doc_type_name }}</p>
        </div>
    </div>

    <form hx-post="/projects/{{ project_id }}/workflows/{{ execution_id }}/pgc-answers"
          hx-target="#workflow-container"
          hx-swap="innerHTML"
          class="space-y-6">
        
        {% for q in questions %}
        <div class="question-group border-l-4 
                    {% if q.priority == 'must' %}border-red-500
                    {% elif q.priority == 'should' %}border-amber-500
                    {% else %}border-gray-300{% endif %} 
                    bg-gray-50 dark:bg-gray-800/50 p-4 rounded-r-lg">
            
            {# Question header #}
            <div class="flex items-start justify-between mb-3">
                <label class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ q.text }}</label>
                <span class="ml-2 px-2 py-0.5 text-xs font-medium rounded
                       {% if q.priority == 'must' %}bg-red-100 text-red-800
                       {% elif q.priority == 'should' %}bg-amber-100 text-amber-800
                       {% else %}bg-gray-100 text-gray-600{% endif %}">
                    {% if q.priority == 'must' %}Required{% elif q.priority == 'should' %}Recommended{% else %}Optional{% endif %}
                </span>
            </div>
            
            {% if q.rationale %}
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">{{ q.rationale }}</p>
            {% endif %}
            
            {# Input based on answer_type #}
            {% if q.answer_type == 'single_choice' and q.choices %}
            <div class="space-y-2">
                {% for c in q.choices %}
                <label class="flex items-center gap-3 p-3 bg-white dark:bg-gray-700 rounded-lg border cursor-pointer hover:border-violet-300">
                    <input type="radio" name="answers[{{ q.id }}]" value="{{ c.id }}"
                           {% if q.required %}required{% endif %}
                           class="w-4 h-4 text-violet-600">
                    <span class="text-sm text-gray-900 dark:text-gray-100">{{ c.label }}</span>
                </label>
                {% endfor %}
            </div>
            
            {% elif q.answer_type == 'multi_choice' and q.choices %}
            <div class="space-y-2">
                {% for c in q.choices %}
                <label class="flex items-center gap-3 p-3 bg-white dark:bg-gray-700 rounded-lg border cursor-pointer hover:border-violet-300">
                    <input type="checkbox" name="answers[{{ q.id }}][]" value="{{ c.id }}"
                           class="w-4 h-4 text-violet-600 rounded">
                    <span class="text-sm text-gray-900 dark:text-gray-100">{{ c.label }}</span>
                </label>
                {% endfor %}
            </div>
            
            {% elif q.answer_type == 'yes_no' %}
            <div class="flex gap-4">
                <label class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-700 rounded-lg border cursor-pointer hover:border-violet-300">
                    <input type="radio" name="answers[{{ q.id }}]" value="true" {% if q.required %}required{% endif %} class="w-4 h-4 text-violet-600">
                    <span class="text-sm">Yes</span>
                </label>
                <label class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-700 rounded-lg border cursor-pointer hover:border-violet-300">
                    <input type="radio" name="answers[{{ q.id }}]" value="false" {% if q.required %}required{% endif %} class="w-4 h-4 text-violet-600">
                    <span class="text-sm">No</span>
                </label>
                {% if not q.required %}
                <label class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-700 rounded-lg border cursor-pointer hover:border-gray-300">
                    <input type="radio" name="answers[{{ q.id }}]" value="undecided" class="w-4 h-4 text-gray-400">
                    <span class="text-sm text-gray-500">Skip</span>
                </label>
                {% endif %}
            </div>
            
            {% else %}
            <textarea name="answers[{{ q.id }}]" rows="3"
                      {% if q.required %}required{% endif %}
                      placeholder="Enter your answer..."
                      class="w-full px-4 py-2 bg-white dark:bg-gray-700 border rounded-lg"></textarea>
            {% endif %}
        </div>
        {% endfor %}
        
        <div class="flex justify-end pt-4 border-t">
            <button type="submit" class="px-6 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg font-medium flex items-center gap-2">
                <i data-lucide="arrow-right" class="w-4 h-4"></i>
                Continue
            </button>
        </div>
    </form>
</div>
```

### 3. Modify Document Not Found Partial

**File:** `app/web/templates/public/pages/partials/_document_not_found.html`

Add conditional for workflow-based builds:

```html
{# In the Build Button section, replace the onclick with: #}

{% if doc_type_id in ['project_discovery'] %}
    {# Workflow-based build with PGC support #}
    <button 
        id="build-btn"
        {% if is_blocked %}disabled{% endif %}
        hx-post="/projects/{{ project.id }}/workflows/{{ doc_type_id }}/start"
        hx-target="#build-container"
        hx-swap="innerHTML"
        class="w-full px-4 py-3 {{ 'bg-gray-400 cursor-not-allowed' if is_blocked else 'bg-violet-600 hover:bg-violet-700' }} text-white rounded-lg flex items-center justify-center gap-2 font-medium">
        <i data-lucide="sparkles" class="w-5 h-5"></i>
        <span>Generate {{ doc_type_name }}</span>
    </button>
{% else %}
    {# Legacy background task build #}
    <button ... onclick="startDocumentBuild(...)">
{% endif %}
```

### 4. Register Routes

**File:** `app/web/routes/public/__init__.py`

```python
from .workflow_build_routes import router as workflow_build_router

# Add to router includes
public_router.include_router(workflow_build_router)
```

---

## Files to Create

- `app/web/routes/public/workflow_build_routes.py` - New routes
- `app/web/templates/public/pages/partials/_workflow_build_container.html` - Container partial
- `app/web/templates/public/pages/partials/_pgc_questions.html` - Questions form partial

## Files to Modify

- `app/web/templates/public/pages/partials/_document_not_found.html` - Conditional for workflow builds
- `app/web/routes/public/__init__.py` - Register new router

---

## Acceptance Criteria

- [ ] Clicking "Generate Project Discovery" shows PGC questions form
- [ ] Questions render correctly by type (single_choice, multi_choice, yes_no, free_text)
- [ ] Priority badges show (Required/Recommended/Optional)
- [ ] Form submits answers and resumes workflow
- [ ] Progress UI shows during generation
- [ ] Success redirects to document view
- [ ] Error state shows with retry option
- [ ] No JavaScript errors in browser console

---

## Definition of Done

1. User can generate Project Discovery from UI with PGC questions
2. All question types render and submit correctly
3. Workflow completes and document is created
4. Manual test: intake → PGC questions → answers → document generated

---

## Prohibited Actions

- Do NOT modify workflow engine code
- Do NOT modify validation code (WS-PGC-VALIDATION-001)
- Do NOT change database schema
- Do NOT add new Python dependencies

---

## Test Scenario

1. Create project via Concierge Intake
2. Navigate to Project Discovery (shows "Not Created")
3. Click "Generate Project Discovery"
4. See PGC questions form with 5-7 questions
5. Answer questions (mix of required/optional)
6. Click Continue
7. See progress indicator
8. See success message
9. Click "View Document"
10. See generated Project Discovery content

---

**End of Work Statement**
