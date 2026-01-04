# The Combine: Architectural Restructure Proposal v3

## Scope

Enforce clean layer boundaries **within the existing `app/` package**. Renaming `app/` to `src/` is out of scope and may be considered as a follow-on change.

---

## 1. Layer Philosophy

| Layer | Responsibility | Contains |
|-------|----------------|----------|
| `app/domain/` | Core business logic | Mentors, LLM services, prompt building, response parsing |
| `app/api/` | Data + API | Models, repositories, services, REST endpoints |
| `app/web/` | Pure presentation | Routes, templates, static assets — **no persistence** |
| `app/infrastructure/` | Cross-cutting | Config, database connection |

**Key principles**:

1. **`app/domain/`** — The AI/mentor pipeline. No FastAPI, no Jinja, no SQLAlchemy models. Just the "thinking" logic.

2. **`app/api/`** — All data persistence lives here. Models, repositories, services. Also REST API endpoints. Web layer calls into this.

3. **`app/web/`** — Pure presentation. Routes are thin: parse request → call `app/api/` service → render template. **No repositories, no models, no business logic.**

4. **`app/infrastructure/`** — Config and database setup. Shared by all layers.

---

## 2. Structural Violations in Current Codebase

### 2.1 Parallel Ownership

| Concept | Location 1 | Location 2 | Location 3 |
|---------|-----------|------------|------------|
| Repositories | `app/combine/repositories/` | `app/artifact_repository_fastapi.py` | — |
| Routers | `app/api/routers/` | `app/combine/routers/` | `app/web/routes/` |
| Services | `app/api/services/` | `app/combine/services/` | `app/web/services/` |
| Schemas | `app/api/schemas/` | `app/combine/schemas/` | — |
| Models | `app/combine/models/` | — | — |

### 2.2 Domain Contamination

- `app/combine/routers/artifacts.py` — FastAPI router inside domain
- `app/combine/mentors/routes.py` — Another router hidden in mentors
- `app/combine/templates/` — Jinja templates in domain layer (dead code from old sidebar)
- `app/combine/models/` — SQLAlchemy models mixed with mentor logic

### 2.3 Web Layer Has Services

- `app/web/services/project_service.py` — Persistence logic in presentation layer
- `app/web/services/epic_service.py` — Same violation
- `app/web/services/story_service.py` — Same violation
- `app/web/services/search_service.py` — Same violation

### 2.4 Orphaned Files

| File | Problem |
|------|---------|
| `app/artifact_repository_fastapi.py` | Unclear relationship to other repos |
| `app/dependencies.py` | Duplicate purpose |
| `app/web/routes.py` (28KB) | Monolith alongside `app/web/routes/` directory |
| `app/combine/templates/metrics/` | Dead code from old sidebar |
| `database.py`, `config.py` (root) | Infrastructure at project root |

---

## 3. Target Structure

```
app/
├── __init__.py
│
├── domain/                          # Core AI/mentor logic (NO FastAPI, NO SQLAlchemy models)
│   ├── __init__.py
│   ├── mentors/                     # AI mentor pipeline
│   │   ├── __init__.py
│   │   ├── base_mentor.py
│   │   ├── pm_mentor.py
│   │   ├── architect_mentor.py
│   │   ├── ba_mentor.py
│   │   └── dev_mentor.py
│   ├── services/                    # LLM interaction, prompt building
│   │   ├── __init__.py
│   │   ├── llm_caller.py
│   │   ├── llm_response_parser.py
│   │   ├── role_prompt_builder.py
│   │   └── token_metrics_types.py
│   ├── schemas/                     # Domain Pydantic models (NOT API schemas)
│   │   ├── __init__.py
│   │   ├── artifacts.py
│   │   └── metrics.py
│   └── utils/
│       ├── __init__.py
│       ├── id_generators.py
│       └── pricing.py
│
├── api/                             # Data layer + REST endpoints
│   ├── __init__.py
│   ├── main.py                      # FastAPI app
│   ├── dependencies.py
│   ├── models/                      # ALL SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── artifact.py
│   │   ├── artifact_version.py
│   │   ├── project.py
│   │   ├── role_prompt.py
│   │   └── workflow.py
│   ├── repositories/                # ALL data access
│   │   ├── __init__.py
│   │   ├── artifact_repository.py
│   │   ├── project_repository.py
│   │   └── role_prompt_repository.py
│   ├── services/                    # Data services (called by web + API)
│   │   ├── __init__.py
│   │   ├── artifact_service.py
│   │   ├── project_service.py       # ← moved from web
│   │   ├── epic_service.py          # ← moved from web
│   │   ├── story_service.py         # ← moved from web
│   │   ├── search_service.py        # ← moved from web
│   │   ├── role_prompt_service.py
│   │   ├── token_metrics_service.py
│   │   ├── usage_recorder.py
│   │   └── email_service.py
│   ├── routers/                     # REST API endpoints
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── artifacts.py
│   │   ├── auth.py
│   │   └── mentors.py               # ← moved from domain
│   ├── schemas/                     # API request/response shapes
│   │   ├── __init__.py
│   │   ├── requests.py
│   │   └── responses.py
│   └── middleware/
│       ├── __init__.py
│       ├── error_handling.py
│       ├── logging.py
│       └── request_id.py
│
├── web/                             # Pure presentation (NO persistence logic)
│   ├── __init__.py
│   ├── routes/                      # Thin route handlers
│   │   ├── __init__.py
│   │   ├── shared.py
│   │   ├── home_routes.py
│   │   ├── project_routes.py
│   │   ├── epic_routes.py
│   │   ├── story_routes.py
│   │   ├── architecture_routes.py
│   │   ├── mentor_routes.py
│   │   ├── search_routes.py
│   │   └── debug_routes.py
│   ├── templates/
│   │   ├── layout/
│   │   ├── components/
│   │   └── pages/
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
│
└── infrastructure/                  # Cross-cutting concerns
    ├── __init__.py
    ├── config.py                    # ← moved from root
    └── database.py                  # ← moved from root
```

---

## 4. Data Flow

### Web Request Flow
```
┌─────────────────────────────────────────────────────────────────────┐
│ app/web/routes/project_routes.py                                    │
│                                                                     │
│   @router.get("/projects/{id}")                                     │
│   async def get_project(id, db):                                    │
│       project = await project_service.get_project(db, id)           │
│       return templates.TemplateResponse("...", {"project": project})│
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ app/api/services/project_service.py                                 │
│                                                                     │
│   async def get_project(db, id):                                    │
│       return await project_repo.get_by_id(db, id)                   │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ app/api/repositories/project_repository.py                          │
│                                                                     │
│   async def get_by_id(db, id):                                      │
│       return db.query(Project).filter(...).first()                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Mentor Execution Flow
```
┌─────────────────────────────────────────────────────────────────────┐
│ app/web/routes/architecture_routes.py                               │
│                                                                     │
│   @router.post("/projects/{id}/architecture")                       │
│   async def generate_architecture(id, db):                          │
│       project = await project_service.get_project(db, id)           │
│       result = await architect_mentor.execute(project)              │
│       await artifact_service.save(db, result)                       │
│       return RedirectResponse(...)                                  │
└─────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────┐
         ▼                              ▼
┌─────────────────────────┐   ┌─────────────────────────────────────┐
│ app/api/services/       │   │ app/domain/mentors/architect_mentor │
│ project_service.py      │   │                                     │
│                         │   │   async def execute(project):       │
│ (data access)           │   │       prompt = build_prompt(...)    │
│                         │   │       response = llm_caller.call()  │
└─────────────────────────┘   │       return parse_response(...)    │
                              └─────────────────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────────────────────┐
                              │ app/domain/services/llm_caller.py   │
                              │                                     │
                              │   def call(prompt, model):          │
                              │       return anthropic.messages()   │
                              └─────────────────────────────────────┘
```

**Key insight**: Domain mentors have no knowledge of HTTP or databases. They receive data and return results. Persistence is handled by `app/api/`.

---

## 5. Incremental Migration Plan

Each step results in a **building, working codebase**. Run tests after each step.

---

### Step 1: Create `app/infrastructure/` and Move Config

**Goal**: Centralize infrastructure concerns.

**Actions**:
```bash
mkdir -p app/infrastructure
touch app/infrastructure/__init__.py
```

Create `app/infrastructure/config.py`:
```python
# Re-export from original location for backward compatibility
from config import *
```

Create `app/infrastructure/database.py`:
```python
# Re-export from original location for backward compatibility
from database import *
```

**Verification**:
```bash
python -c "from app.infrastructure.config import settings; print('OK')"
python -c "from app.infrastructure.database import get_db; print('OK')"
pytest
```

**Result**: Code builds. Old imports still work. New imports available.

---

### Step 2: Create `app/domain/` with Re-exports (Mentors + LLM Only)

**Goal**: Establish domain layer for AI/mentor logic only.

**Actions**:
```bash
mkdir -p app/domain/{mentors,services,schemas,utils}
touch app/domain/__init__.py
touch app/domain/{mentors,services,schemas,utils}/__init__.py
```

Create re-export files:

`app/domain/mentors/__init__.py`:
```python
# Canonical location for mentor logic
from app.combine.mentors.base_mentor import BaseMentor
from app.combine.mentors.pm_mentor import PMMentor
from app.combine.mentors.architect_mentor import ArchitectMentor
from app.combine.mentors.ba_mentor import BAMentor
from app.combine.mentors.dev_mentor import DevMentor
# NOTE: routes.py is NOT re-exported - belongs in app/api/
```

`app/domain/services/__init__.py`:
```python
# LLM-related services only
from app.combine.services.llm_caller import *
from app.combine.services.llm_response_parser import *
from app.combine.services.role_prompt_builder import *
from app.combine.services.token_metrics_types import *
```

`app/domain/schemas/__init__.py`:
```python
from app.combine.schemas.artifacts import *
from app.combine.schemas.metrics import *
```

`app/domain/utils/__init__.py`:
```python
from app.combine.utils.id_generators import *
from app.combine.utils.pricing import *
```

**Verification**:
```bash
python -c "from app.domain.mentors import ArchitectMentor; print('OK')"
python -c "from app.domain.services import LLMCaller; print('OK')"
pytest
```

**Result**: Code builds. Domain layer established for AI logic.

---

### Step 3: Move Models to `app/api/models/`

**Goal**: Consolidate all SQLAlchemy models in API layer.

**Actions**:
```bash
mkdir -p app/api/models
touch app/api/models/__init__.py
```

Create `app/api/models/__init__.py`:
```python
# Re-export during migration
from app.combine.models import *
```

**Verification**:
```bash
python -c "from app.api.models import Artifact, Project; print('OK')"
pytest
```

**Result**: Code builds. Models accessible from new location.

---

### Step 4: Move Repositories to `app/api/repositories/`

**Goal**: Consolidate all repositories in API layer.

**Actions**:
```bash
mkdir -p app/api/repositories
touch app/api/repositories/__init__.py
```

Create `app/api/repositories/__init__.py`:
```python
# Re-export during migration
from app.combine.repositories.artifact_repository import ArtifactRepository
from app.combine.repositories.project_repository import ProjectRepository
from app.combine.repositories.role_prompt_repository import RolePromptRepository
```

**Verification**:
```bash
python -c "from app.api.repositories import ArtifactRepository; print('OK')"
pytest
```

**Result**: Code builds. Repositories accessible from new location.

---

### Step 5: Move Web Services to `app/api/services/`

**Goal**: Remove persistence logic from web layer.

**Actions**:

1. Copy services from `app/web/services/` to `app/api/services/`:
```bash
cp app/web/services/project_service.py app/api/services/
cp app/web/services/epic_service.py app/api/services/
cp app/web/services/story_service.py app/api/services/
cp app/web/services/search_service.py app/api/services/
```

2. Update imports in copied files to use new locations:
```python
# OLD
from app.combine.repositories import ProjectRepository

# NEW
from app.api.repositories import ProjectRepository
```

3. Also copy/merge data services from `app/combine/services/`:
```bash
cp app/combine/services/artifact_service.py app/api/services/
cp app/combine/services/role_prompt_service.py app/api/services/
cp app/combine/services/token_metrics_service.py app/api/services/
cp app/combine/services/usage_recorder.py app/api/services/
cp app/combine/services/configuration_loader.py app/api/services/
```

4. Update `app/api/services/__init__.py`:
```python
from .project_service import *
from .epic_service import *
from .story_service import *
from .search_service import *
from .artifact_service import *
from .role_prompt_service import *
from .token_metrics_service import *
from .usage_recorder import *
from .email_service import *
```

**Verification**:
```bash
python -c "from app.api.services import project_service; print('OK')"
pytest
```

**Result**: Code builds. All data services in API layer.

---

### Step 6: Update Web Routes to Use `app.api.services`

**Goal**: Web layer now calls API services, not its own.

**Actions**:

Update imports in all `app/web/routes/*.py` files:
```python
# OLD
from ..services import project_service
from ..services.project_service import ProjectService

# NEW
from app.api.services import project_service
```

**Verification**:
```bash
pytest
# Manual: verify web pages still load
```

**Result**: Code builds. Web routes use API services.

---

### Step 7: Delete `app/web/services/`

**Goal**: Web layer has no more persistence logic.

**Actions**:

1. Verify no remaining imports:
```bash
grep -r "from app\.web\.services" app/
grep -r "from \.\.services" app/web/routes/
```

2. Delete:
```bash
rm -rf app/web/services/
```

**Verification**:
```bash
pytest
```

**Result**: Code builds. Web layer is pure presentation.

---

### Step 8: Move Mentor Routes to API Layer

**Goal**: Remove FastAPI dependency from domain.

**Actions**:

1. Copy `app/combine/mentors/routes.py` → `app/api/routers/mentors.py`

2. Update imports in the copied file:
```python
# OLD
from app.combine.mentors.pm_mentor import PMMentor

# NEW
from app.domain.mentors import PMMentor
```

3. Register in `app/api/routers/__init__.py`

4. Register in `app/api/main.py`

**Verification**:
```bash
python -c "from app.api.routers.mentors import router; print('OK')"
pytest
```

**Result**: Code builds. Mentor API in correct location.

---

### Step 9: Move `app/combine/routers/` to API Layer

**Goal**: Consolidate all API routers.

**Actions**:

1. For each file in `app/combine/routers/`:
   - Copy to `app/api/routers/`
   - Update imports to use `app.api.*` and `app.domain.*`
   - Register in `app/api/main.py`

**Verification**:
```bash
pytest
```

**Result**: Code builds. All API routers consolidated.

---

### Step 10: Delete Orphaned Files

**Goal**: Remove duplicates and dead code.

**Actions**:

```bash
# Orphaned repository at app root
rm app/artifact_repository_fastapi.py

# Monolithic routes file (superseded by routes/)
rm app/web/routes.py

# Dead templates from old sidebar
rm -rf app/combine/templates/
```

**Verification**:
```bash
pytest
```

**Result**: Code builds. No orphaned files.

---

### Step 11: Update All Imports to Canonical Paths

**Goal**: All code uses new import paths.

**Actions**:

```bash
# Models
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.models/from app.api.models/g' {} \;

# Repositories
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.repositories/from app.api.repositories/g' {} \;

# Data services (artifact, role_prompt, token, etc.)
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.services\.artifact_service/from app.api.services.artifact_service/g' {} \;
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.services\.role_prompt_service/from app.api.services.role_prompt_service/g' {} \;
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.services\.token_metrics_service/from app.api.services.token_metrics_service/g' {} \;
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.services\.usage_recorder/from app.api.services.usage_recorder/g' {} \;

# Domain services (LLM-related)
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.services\.llm_caller/from app.domain.services.llm_caller/g' {} \;
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.services\.llm_response_parser/from app.domain.services.llm_response_parser/g' {} \;

# Mentors
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.mentors/from app.domain.mentors/g' {} \;

# Schemas
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.schemas/from app.domain.schemas/g' {} \;

# Utils
find app tests -name "*.py" -exec sed -i 's/from app\.combine\.utils/from app.domain.utils/g' {} \;
```

**Verification**:
```bash
grep -r "from app\.combine\." app/ tests/
# Should return only __init__.py re-exports
pytest
```

**Result**: Code builds. Canonical imports throughout.

---

### Step 12: Move Physical Files

**Goal**: Complete migration by moving actual files.

**Actions**:

```bash
# Domain - mentors
mv app/combine/mentors/base_mentor.py app/domain/mentors/
mv app/combine/mentors/pm_mentor.py app/domain/mentors/
mv app/combine/mentors/architect_mentor.py app/domain/mentors/
mv app/combine/mentors/ba_mentor.py app/domain/mentors/
mv app/combine/mentors/dev_mentor.py app/domain/mentors/

# Domain - LLM services
mv app/combine/services/llm_caller.py app/domain/services/
mv app/combine/services/llm_response_parser.py app/domain/services/
mv app/combine/services/role_prompt_builder.py app/domain/services/
mv app/combine/services/token_metrics_types.py app/domain/services/

# Domain - schemas
mv app/combine/schemas/*.py app/domain/schemas/

# Domain - utils
mv app/combine/utils/*.py app/domain/utils/

# API - models
mv app/combine/models/*.py app/api/models/

# API - repositories
mv app/combine/repositories/*.py app/api/repositories/

# API - data services (already copied in step 5, now remove originals)
rm app/combine/services/artifact_service.py
rm app/combine/services/role_prompt_service.py
rm app/combine/services/token_metrics_service.py
rm app/combine/services/usage_recorder.py
rm app/combine/services/configuration_loader.py
```

Update `__init__.py` files to use direct imports instead of re-exports.

**Verification**:
```bash
pytest
```

**Result**: Code builds. Files in correct locations.

---

### Step 13: Delete `app/combine/`

**Goal**: Remove the old package entirely.

**Actions**:

1. Final verification:
```bash
grep -r "from app\.combine" app/ tests/
grep -r "import app\.combine" app/ tests/
# Should return nothing
```

2. Delete:
```bash
rm -rf app/combine/
```

**Verification**:
```bash
pytest
```

**Result**: Code builds. Clean structure achieved.

---

### Step 14: Move Root Infrastructure Files (Optional)

**Goal**: Complete infrastructure consolidation.

**Actions**:

1. Move actual files:
```bash
mv config.py app/infrastructure/config.py
mv database.py app/infrastructure/database.py
```

2. Create stubs at root for backward compatibility (optional):
```python
# config.py (root stub)
from app.infrastructure.config import *
```

3. Or update all imports:
```bash
find app tests -name "*.py" -exec sed -i 's/from config import/from app.infrastructure.config import/g' {} \;
find app tests -name "*.py" -exec sed -i 's/from database import/from app.infrastructure.database import/g' {} \;
```

**Verification**:
```bash
pytest
```

**Result**: Code builds. Infrastructure properly located.

---

## 6. Final Verification Checklist

After completing all steps:

- [ ] `app/domain/` has **zero** imports from `fastapi`, `starlette`, `jinja2`, `sqlalchemy`
  ```bash
  grep -rE "^from (fastapi|starlette|jinja|sqlalchemy)" app/domain/
  grep -rE "^import (fastapi|starlette|jinja|sqlalchemy)" app/domain/
  # Should return nothing
  ```

- [ ] `app/web/` has **zero** repository or model imports
  ```bash
  grep -r "repository" app/web/
  grep -r "from app.api.models" app/web/
  # Should return nothing (web calls services, not repos/models directly)
  ```

- [ ] All SQLAlchemy models are in `app/api/models/`
  ```bash
  grep -r "class.*Base\)" app/ --include="*.py"
  # Should only show files in app/api/models/
  ```

- [ ] All FastAPI routers are in `app/api/routers/`
  ```bash
  grep -r "APIRouter" app/ --include="*.py" -l
  # Should only show files in app/api/routers/
  ```

- [ ] `app/combine/` no longer exists
  ```bash
  ls app/combine/
  # Should error: No such file or directory
  ```

- [ ] All tests pass
  ```bash
  pytest
  ```

---

## 7. Summary: Before & After

### Before
```
app/
├── artifact_repository_fastapi.py   # Orphan
├── dependencies.py                  # Duplicate?
├── api/
│   ├── routers/                     # Some routers
│   ├── services/
│   │   └── email_service.py         # Only email here
│   └── schemas/
├── combine/                         # Mixed concerns
│   ├── mentors/
│   │   └── routes.py                # FastAPI in domain!
│   ├── models/                      # SQLAlchemy models
│   ├── repositories/                # Data access
│   ├── routers/                     # More routers!
│   ├── services/                    # Mixed services
│   └── templates/                   # Dead code
└── web/
    ├── routes.py                    # 28KB monolith
    ├── routes/                      # Proper routes
    ├── services/                    # Persistence in web!
    └── templates/
```

### After
```
app/
├── domain/                          # Pure AI/mentor logic
│   ├── mentors/                     # NO routes, NO models
│   ├── services/                    # LLM caller, parser only
│   ├── schemas/
│   └── utils/
├── api/                             # All data + REST
│   ├── models/                      # ALL SQLAlchemy models
│   ├── repositories/                # ALL data access
│   ├── services/                    # ALL data services
│   ├── routers/                     # ALL API endpoints
│   ├── schemas/
│   └── middleware/
├── web/                             # Pure presentation
│   ├── routes/                      # Thin handlers only
│   ├── templates/
│   └── static/
└── infrastructure/
    ├── config.py
    └── database.py
```

---

## 8. What Goes Where: Quick Reference

| Type of Code | Location |
|--------------|----------|
| SQLAlchemy model | `app/api/models/` |
| Repository class | `app/api/repositories/` |
| Data service (CRUD, queries) | `app/api/services/` |
| REST API endpoint | `app/api/routers/` |
| API request/response schema | `app/api/schemas/` |
| Mentor class | `app/domain/mentors/` |
| LLM caller/parser | `app/domain/services/` |
| Domain Pydantic model | `app/domain/schemas/` |
| Web route (HTMX) | `app/web/routes/` |
| Jinja template | `app/web/templates/` |
| Config/settings | `app/infrastructure/` |
| Database connection | `app/infrastructure/` |

---

## 9. Optional Follow-On: Rename `app/` to `src/`

If desired later, this is a simple global rename:

```bash
mv app src
find . -name "*.py" -exec sed -i 's/from app\./from src./g' {} \;
find . -name "*.py" -exec sed -i 's/import app\./import src./g' {} \;
```

This is **not required** to achieve clean boundaries and can be deferred indefinitely.

---

*Each step is independently committable and results in a working build.*
