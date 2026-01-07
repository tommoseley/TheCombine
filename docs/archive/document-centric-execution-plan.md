# The Combine — Document-Centric Refactoring Execution Plan

**Document Type:** Execution Plan  
**Status:** Ready for Execution  
**Date:** December 16, 2025  
**Target:** Pre-MVP Completion  
**Scope:** Python monolith refactoring (C#/Lambda migration deferred)

---

## Executive Summary

This plan converts The Combine from worker-centric to document-centric architecture within the existing Python codebase. The goal is to establish the correct abstractions now, making the future C#/Lambda split straightforward rather than a second refactoring.

**Timeline:** 4-5 days of focused work  
**Risk:** Low — incremental, testable changes  
**Dependencies:** None — self-contained refactoring

---

## Current State Assessment

### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `BaseMentor` | Working | Has `PromptServiceProtocol`, `ArtifactServiceProtocol` |
| `PreliminaryArchitectMentor` | Working | Hardcoded document type knowledge |
| `DetailedArchitectMentor` | Working | Hardcoded document type knowledge |
| Prompt templates | In DB | Already versioned and stored |
| JSON schemas | Partial | Some inline, some missing |
| Artifact storage | Working | Generic, document-agnostic |
| UI routes | Working | Worker-centric (`/mentors/architect/...`) |
| Tree navigation | Working | Mixes workers and documents |

### What's Wrong

1. **Mentors know too much** — Each mentor class embeds document structure, rendering hints, validation
2. **Routes are worker-centric** — `/mentors/preliminary-architect/execute` instead of `/documents/discovery-architecture/build`
3. **No document registry** — Document types scattered across code
4. **No document handlers** — Parsing/validation/rendering mixed into mentors and templates
5. **UI exposes workers** — "Create Preliminary Architecture" button, not "Build Discovery Architecture"

---

## Target State

### The Document Registry

A single source of truth for all document types:

```python
# app/domain/registry/document_types.py

DOCUMENT_REGISTRY = {
    "discovery_architecture": {
        "name": "Discovery Architecture",
        "description": "Early constraints, unknowns, and architectural direction",
        "schema": "schemas/discovery_architecture.json",
        "builder": {
            "system_prompt": "architect/discovery_system",
            "user_prompt": "architect/discovery_user",
        },
        "requires": [],  # No dependencies
        "handler": "discovery_architecture",
        "icon": "search",
        "category": "architecture",
    },
    "architecture_spec": {
        "name": "Architecture Specification",
        "description": "Components, interfaces, data models, and workflows",
        "schema": "schemas/architecture_spec.json",
        "builder": {
            "system_prompt": "architect/spec_system",
            "user_prompt": "architect/spec_user",
        },
        "requires": ["discovery_architecture"],
        "handler": "architecture_spec",
        "icon": "landmark",
        "category": "architecture",
    },
    "epic_set": {
        "name": "Epic Set",
        "description": "Project epics derived from architecture",
        "schema": "schemas/epic_set.json",
        "builder": {
            "system_prompt": "pm/epic_generation_system",
            "user_prompt": "pm/epic_generation_user",
        },
        "requires": ["discovery_architecture"],
        "handler": "epic_set",
        "icon": "layers",
        "category": "planning",
    },
    # ... more document types
}
```

### The Document Builder

One class that builds any document:

```python
# app/domain/services/document_builder.py

class DocumentBuilder:
    """Builds any document type from the registry."""
    
    async def build(
        self,
        doc_type: str,
        project_id: str,
        epic_id: Optional[str] = None
    ) -> Artifact:
        # 1. Load registry entry
        config = get_document_config(doc_type)
        
        # 2. Check dependencies
        await self._verify_dependencies(config, project_id)
        
        # 3. Gather inputs
        inputs = await self._gather_inputs(config, project_id, epic_id)
        
        # 4. Load and render prompts
        system_prompt = await self._load_prompt(config["builder"]["system_prompt"])
        user_prompt = await self._render_prompt(config["builder"]["user_prompt"], inputs)
        
        # 5. Call LLM
        raw_response = await self._call_llm(system_prompt, user_prompt)
        
        # 6. Hand off to handler
        handler = get_handler(config["handler"])
        return await handler.process(raw_response, project_id, epic_id)
```

### Document Handlers

Per-document-type processing:

```python
# app/domain/handlers/base_handler.py

class BaseDocumentHandler(ABC):
    """Base class for document handlers."""
    
    @property
    @abstractmethod
    def doc_type(self) -> str: ...
    
    @property
    @abstractmethod
    def schema_path(self) -> str: ...
    
    def parse(self, raw_response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response. Override if custom parsing needed."""
        return LLMResponseParser().parse(raw_response)
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate against schema."""
        schema = load_schema(self.schema_path)
        return validate_against_schema(data, schema)
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize/enrich. Override for custom transformation."""
        return data
    
    @abstractmethod
    def render(self, data: Dict[str, Any], project: Dict) -> str:
        """Return HTML for full view."""
        ...
    
    @abstractmethod
    def render_summary(self, data: Dict[str, Any]) -> str:
        """Return HTML for card/list view."""
        ...
    
    async def process(
        self,
        raw_response: str,
        project_id: str,
        epic_id: Optional[str] = None
    ) -> Artifact:
        """Full processing pipeline."""
        # Parse
        data = self.parse(raw_response)
        
        # Validate
        is_valid, errors = self.validate(data)
        if not is_valid:
            raise DocumentValidationError(self.doc_type, errors)
        
        # Transform
        data = self.transform(data)
        
        # Persist
        artifact = await self._save_artifact(data, project_id, epic_id)
        
        return artifact
```

---

## Execution Plan

### Day 1: Foundation

**Morning: Document Registry**

1. Create `app/domain/registry/__init__.py`
2. Create `app/domain/registry/document_types.py` with registry dict
3. Create `app/domain/registry/loader.py` with helper functions:
   - `get_document_config(doc_type: str) -> Dict`
   - `list_document_types() -> List[str]`
   - `list_by_category(category: str) -> List[str]`
   - `get_dependencies(doc_type: str) -> List[str]`
4. Populate registry with existing document types:
   - `discovery_architecture` (from PreliminaryArchitectMentor)
   - `architecture_spec` (from DetailedArchitectMentor)
   - `epic_set` (from PM mentor)

**Afternoon: Handler Base Class**

1. Create `app/domain/handlers/__init__.py`
2. Create `app/domain/handlers/base_handler.py` with `BaseDocumentHandler`
3. Create `app/domain/handlers/exceptions.py`:
   - `DocumentValidationError`
   - `DocumentParseError`
   - `DependencyMissingError`
4. Move `LLMResponseParser` usage into base handler

**Deliverable:** Registry exists, base handler exists, no behavior change yet.

---

### Day 2: First Handler Migration

**Target:** `discovery_architecture`

**Morning: Handler Implementation**

1. Create `app/domain/handlers/discovery_architecture_handler.py`
2. Implement:
   - `doc_type = "discovery_architecture"`
   - `schema_path = "schemas/discovery_architecture.json"`
   - `transform()` — any enrichment currently in mentor
   - `render()` — move logic from `_preliminary_architecture.html` template
   - `render_summary()` — compact version for cards
3. Create/formalize JSON schema at `app/schemas/discovery_architecture.json`

**Afternoon: Handler Registration**

1. Create `app/domain/handlers/registry.py`:
   ```python
   HANDLERS = {
       "discovery_architecture": DiscoveryArchitectureHandler(),
   }
   
   def get_handler(handler_id: str) -> BaseDocumentHandler:
       return HANDLERS[handler_id]
   ```
2. Update templates to call `handler.render()` instead of inline logic
3. Test: existing PreliminaryArchitectMentor still works, but handler does rendering

**Deliverable:** Discovery Architecture uses handler for render. Mentor unchanged.

---

### Day 3: Document Builder

**Morning: Builder Implementation**

1. Create `app/domain/services/document_builder.py`
2. Implement `DocumentBuilder` class:
   - `build(doc_type, project_id, epic_id)` — main entry point
   - `build_stream(doc_type, project_id, epic_id)` — SSE version
   - `_verify_dependencies()` — check required docs exist
   - `_gather_inputs()` — collect input documents
   - `_load_prompt()` — load from prompt service
   - `_render_prompt()` — template substitution
   - `_call_llm()` — Anthropic call (extract from BaseMentor)
3. Builder uses registry to configure itself, handler to process output

**Afternoon: Wire Up Discovery Architecture**

1. Create new route: `POST /api/documents/build`
   ```python
   @router.post("/build")
   async def build_document(
       doc_type: str,
       project_id: str,
       epic_id: Optional[str] = None,
       db: AsyncSession = Depends(get_db)
   ):
       builder = DocumentBuilder(db)
       artifact = await builder.build(doc_type, project_id, epic_id)
       return {"artifact_id": str(artifact.id)}
   ```
2. Create streaming route: `POST /api/documents/build-stream`
3. Test: Can build discovery_architecture via new route
4. Old mentor route still works (parallel paths)

**Deliverable:** New document-centric API works for discovery_architecture.

---

### Day 4: Migrate Remaining Document Types

**Morning: Architecture Spec Handler**

1. Create `app/domain/handlers/architecture_spec_handler.py`
2. Create `app/schemas/architecture_spec.json`
3. Register handler
4. Add to document registry with dependency on discovery_architecture
5. Test via new API

**Afternoon: Epic Set Handler**

1. Create `app/domain/handlers/epic_set_handler.py`
2. Create `app/schemas/epic_set.json`
3. Register handler
4. Add to document registry
5. Test via new API

**Evening: Any Additional Document Types**

- Story backlog
- BA breakdown
- Whatever else exists

**Deliverable:** All existing document types work through new system.

---

### Day 5: UI Migration & Cleanup

**Morning: Update UI Routes**

1. Create `app/web/routes/document_routes.py`:
   ```python
   @router.get("/projects/{project_id}/documents/{doc_type}")
   async def view_document(...)
   
   @router.post("/projects/{project_id}/documents/{doc_type}/build")
   async def build_document_ui(...)
   ```
2. Update tree templates to use document-centric URLs
3. Update project detail page:
   - Replace "Create Preliminary Architecture" → "Build Discovery Architecture"
   - Replace mentor-specific buttons with generic document buttons
   - Use registry to show available document types

**Afternoon: Template Cleanup**

1. Update `_project_detail_content.html`:
   - Loop over document types from registry
   - Show status (exists/missing/building)
   - Generic "Build" button per document type
2. Ensure all document views use handler.render()
3. Remove hardcoded document knowledge from templates

**Evening: Deprecation**

1. Mark old mentor routes as deprecated (don't remove yet)
2. Add redirect from old routes to new routes
3. Update any remaining UI references
4. Document migration in README

**Deliverable:** UI is document-centric. Old routes deprecated but functional.

---

## File Structure After Refactoring

```
app/
├── domain/
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── document_types.py      # The registry
│   │   └── loader.py              # Helper functions
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base_handler.py        # BaseDocumentHandler
│   │   ├── registry.py            # Handler lookup
│   │   ├── exceptions.py
│   │   ├── discovery_architecture_handler.py
│   │   ├── architecture_spec_handler.py
│   │   └── epic_set_handler.py
│   ├── services/
│   │   ├── document_builder.py    # The one builder
│   │   └── llm_response_parser.py # Existing, unchanged
│   └── mentors/
│       └── base_mentor.py         # Deprecated, still functional
├── schemas/
│   ├── discovery_architecture.json
│   ├── architecture_spec.json
│   └── epic_set.json
├── api/
│   └── routes/
│       ├── document_routes.py     # New API routes
│       └── mentor_routes.py       # Deprecated
└── web/
    └── routes/
        ├── document_routes.py     # New UI routes
        └── project_routes.py      # Updated
```

---

## Migration Checklist

### Day 1
- [ ] Create `app/domain/registry/` directory
- [ ] Create `document_types.py` with initial registry
- [ ] Create `loader.py` with helper functions
- [ ] Create `app/domain/handlers/` directory
- [ ] Create `base_handler.py`
- [ ] Create `exceptions.py`

### Day 2
- [ ] Create `discovery_architecture_handler.py`
- [ ] Create `app/schemas/discovery_architecture.json`
- [ ] Create `handlers/registry.py`
- [ ] Update discovery architecture templates to use handler
- [ ] Test existing flow still works

### Day 3
- [ ] Create `document_builder.py`
- [ ] Create `POST /api/documents/build` route
- [ ] Create `POST /api/documents/build-stream` route
- [ ] Test discovery_architecture via new API
- [ ] Verify old mentor route still works

### Day 4
- [ ] Create `architecture_spec_handler.py`
- [ ] Create `app/schemas/architecture_spec.json`
- [ ] Create `epic_set_handler.py`
- [ ] Create `app/schemas/epic_set.json`
- [ ] Register all handlers
- [ ] Test all document types via new API

### Day 5
- [ ] Create `app/web/routes/document_routes.py`
- [ ] Update tree templates for document-centric URLs
- [ ] Update project detail with generic document buttons
- [ ] Remove hardcoded document knowledge from templates
- [ ] Mark old routes deprecated
- [ ] Update README

---

## Risk Mitigation

### Risk: Breaking Existing Functionality

**Mitigation:** Parallel paths. Old mentor routes continue to work throughout migration. Only deprecated after new routes proven.

### Risk: Template Complexity

**Mitigation:** Handlers own rendering. Templates become thin wrappers that call `handler.render(data)`. Logic moves to Python where it's testable.

### Risk: Schema Mismatch

**Mitigation:** Extract schemas from current working outputs. Validate against real data before enforcing.

### Risk: Scope Creep

**Mitigation:** This plan is document-centric refactoring only. No new features. No C# migration. No Lambda deployment. Those are separate efforts.

---

## Success Criteria

1. **All document creation goes through `DocumentBuilder`**
   - No direct mentor instantiation from routes

2. **All document rendering goes through handlers**
   - No document-specific logic in templates

3. **Adding a new document type requires:**
   - One registry entry
   - One handler class
   - One schema file
   - Zero route changes
   - Zero template changes (beyond including the rendered output)

4. **UI shows document types, not workers**
   - "Build Discovery Architecture" not "Run Preliminary Architect"
   - Document status visible in project view
   - Dependencies visible

5. **Old mentor routes deprecated but functional**
   - No immediate breakage for any existing integrations

---

## What This Enables (Post-MVP)

Once document-centric architecture is in place:

1. **C# Core Application** — Handlers, registry, and domain logic port cleanly to a typed language

2. **Python Lambda Layer** — `DocumentBuilder._call_llm()` extracts to serverless functions

3. **New Document Types** — Data changes only, as promised

4. **A/B Prompt Testing** — Registry points to prompt versions; swap without code changes

5. **Human Upload** — Handler.process() works regardless of source

6. **Multi-Worker Documents** — Builder can call multiple LLMs, handler reconciles

The refactoring is not the goal. The refactoring creates the foundation.

---

## Starting Tomorrow

**First commit:** Create the registry directory and `document_types.py` with the three known document types. That's the seed. Everything else grows from there.

Let's build a document factory.
