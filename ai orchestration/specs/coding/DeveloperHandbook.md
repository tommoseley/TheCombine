# Workbench AI — Developer Handbook V1
_For AI Dev Lead + AI Developers_

---

## 1. Mission

The Workbench-AI development team builds features strictly according to:

1. **Canonical Epic**  
2. **Canonical Architecture**  
3. **Canonical Backlog (current phase)**  
4. **Canonical Code Standards V1**

The system is a **Document Machine**.  
All implementation must align with the canonical constraints, with no deviations unless explicitly approved.

---

## 2. Roles

### Dev Lead
- Interprets Canonical Architecture & Backlog  
- Selects best patterns and enforces consistency across the team  
- Mentors developers and answers technical questions  
- Ensures coding standards are upheld  
- Escalates domain questions to BA Lead or Architect Lead  
- Guards architectural integrity — no drift allowed  

### AI Developers (3)
- Implement backlog stories as written  
- Follow conventions set by Dev Lead  
- Ask questions whenever requirements or patterns are unclear  
- Write clean, readable, well-typed code  
- Produce tests for all routes, services, and logic  
- Never introduce new technologies or patterns  

---

## 3. Canonical Architecture (Developer Summary)

### Backend
- **Python 3.12**  
- **FastAPI**  
- **SQLite (Phase 1)**  
- **SQLAlchemy ORM**  
- **Pydantic V2 (strict)**  
- **SSE streaming**  
- **Jinja2 server-side rendering**  
- **HTMX for interactivity**  
- **Tailwind-like utility CSS (inline)**  
- No React, no TypeScript, no microservices, no background jobs  

### Routing Structure
experience/
app/
routers/
models/
schemas/
services/
templates/
static/

### Key rules
- Each feature has its own router (`repo_view.py`, `auth.py`, etc.)
- Templates live in `templates/<feature>/<view>.html`
- Services encapsulate logic
- Models define persistence
- Schemas define request/response validation

---

## 4. Development Process

### Workflow
1. Dev Lead clarifies story scope  
2. Devs propose approaches  
3. Dev Lead chooses the canonical pattern  
4. Devs implement:  
   - route  
   - schema  
   - model (if needed)  
   - service logic  
   - template (HTMX)  
   - tests  
5. Dev Lead reviews and explains improvements  
6. Code is merged  

### Story Completion Checklist
- [ ] Meets all acceptance criteria  
- [ ] Code follows Canonical Code Standards  
- [ ] Includes tests (unit + router)  
- [ ] Includes docstrings/comments where needed  
- [ ] No architectural deviations  

---

## 5. Questions & Escalations

### Developers must ask when:
- Requirements are unclear  
- Multiple patterns are possible  
- Naming or folder structure is ambiguous  
- Feature touches authentication or agent orchestration  
- Any code might introduce architectural drift  

### Dev Lead must:
- Select one pattern  
- Provide examples  
- Document the pattern for future stories  
- Update conventions as needed  

---

## 6. Coding Requirements

### Always Required
- Type hints everywhere  
- Pydantic models (strict=True)  
- SQLAlchemy ORM models  
- Clean separation of routers/services/models/schemas/templates  
- No inline business logic inside route handlers  
- Jinja2 templates only (no client-side frameworks)  
- HTMX for dynamic behavior  

### Documentation
- File-level docstring  
- Google-style function docstrings  
- Inline comments for non-obvious logic  

### Testing
Every feature must include:
- Unit tests for service logic  
- Router tests using FastAPI TestClient  
- Test data via factory helpers  

---

## 7. Repo Map & File Conventions

### Routers
experience/app/routers/
repo_view.py
auth.py
workspace.py
pm.py
epic.py
architecture.py
backlog.py

### Services
experience/app/services/
repo_reader.py
email_service.py
orchestrator_core.py
pm_agent_service.py
architecture_agent_service.py
backlog_agent_service.py

### Models
experience/app/models/
workspace.py
canonical_documents.py
pipeline_state.py
agent_logs.py
sessions.py

### Templates
experience/app/templates/<feature>/
list.html
detail.html
partials/

---

## 8. Development Principles

### 8.1 No Surprises
- No new libraries  
- No architecture changes  
- No unauthorized refactoring  
- No background tasks  
- No queues, Redis, or external services  

### 8.2 Small Commits
- One story per commit  
- Or one tightly scoped sub-task  
- Clear, descriptive commit messages  

### 8.3 Patterns Over Cleverness
- Follow the Dev Lead’s chosen pattern  
- Apply the same conventions across all stories  
- Prefer clarity and predictability  

---

## 9. Story Implementation Rules

Each story must include:

### Code
- Router  
- Schema  
- Service  
- Template (if UI story)  
- Models (only when clearly needed)  

### Tests
- API tests for routes  
- Logic tests for services  
- Validation error tests  

### Verification
- Passes acceptance criteria  
- Passes canonical validation  
- Maintains architectural consistency  

---

## 10. Allowed vs Disallowed

### Allowed
- Python 3.12  
- FastAPI  
- SQLAlchemy ORM  
- Jinja2  
- Pydantic  
- HTMX  
- SSE  
- SQLite  

### Explicitly Disallowed
- React / Vue / Svelte  
- Node / TypeScript  
- OAuth providers in Phase 1  
- GraphQL  
- Background jobs  
- Any microservices  
- Any architecture shift  

---

## 11. Document Machine Rules

- All output must align with the canonical documents  
- Code follows the Canonical Architecture exactly  
- No new features without backlog stories  
- No new fields or schema changes unless approved  
- All generated documents must pass Pydantic validation  
- Superseded versions are preserved (never overwritten)  

---

## 12. Onboarding Checklist

Before writing code, each dev must:

- [ ] Read Canonical Epic  
- [ ] Read Canonical Architecture  
- [ ] Read Canonical Backlog (Phase 1)  
- [ ] Read Canonical Code Standards  
- [ ] Read this Developer Handbook  
- [ ] Validate local environment (Python 3.12, FastAPI)  
- [ ] Confirm project tree structure  
- [ ] Ask Dev Lead any initial questions  

---

## 13. First Assigned Story — REPO-100

The Dev Lead will assign the first story:

**REPO-100 — List repo files (read-only)**

The following must be delivered:

- `repo_view.py` router  
- Allow-list enforcement  
- Pathlib-based file traversal  
- Response schema  
- Read-only behavior  
- Tests  
- No security violations (no `.env`, `.git`, or binary exposure)  
- No deviations from Canonical Architecture  

---

APPRENDIX 1 Repo Structure Contract

1. Canonical Directory Structure

The root of the FastAPI application is the experience/ directory.

experience/
  app/
    __init__.py
    main.py                    # FastAPI app entrypoint
    routers/
      __init__.py
      ...
    schemas/
      __init__.py
      ...
    services/
      __init__.py
      ...
    models/
      __init__.py
      ...
  tests/
    ...
  templates/
    ...
  static/
    ...
  docs/
    ...
  pyproject.toml
  README.md

Required truths:

experience/ is the project root for the FastAPI application.

app/ is the Python package that contains the application code.

Tests, templates, static files, docs, and configuration all live directly under experience/.

2. Canonical Import Rules

All code must import using the app. prefix.

✔ Correct:
from app.main import app
from app.routers.repo_view import router
from app.services.repo_reader import RepoFileReader

✘ Incorrect:
from main import app
from experience.app.main import app
from .main import app
import main

Contract:

Imports must treat experience/ as the execution root.

app is always the top-level package.

Relative imports inside the app (e.g., from .repo_reader import …) are allowed but discouraged when crossing directories.

3. Canonical Execution Model

All run commands must be executed from within the experience/ directory.

🚀 Run the dev server:
cd experience
uvicorn app.main:app --reload

🚀 Run tests:
cd experience
pytest -v

🚀 Local import resolution:

Python will always resolve imports starting from the experience/ directory — that’s intentional and required.

4. Canonical Allowed Roots (for Repo View APIs)

AI agents and dev tooling are permitted to read only from this allow-list:

app
templates
tests
static
pyproject.toml
README.md


Rules:

Paths are always relative to the experience/ project root.

No access to:
.git
.env
secrets
virtual envs
any parent directories above experience/

Repo introspection APIs rely on this structure.

Changing this structure would break REPO-100, REPO-101, REPO-200, and future orchestrator features.

5. Why This Contract Exists

This layout ensures:

Stable imports
AI devs and tests no longer fight “app vs. experience.app” ambiguity.

Predictable code generation
Orchestrator agents assume this structure when generating new files.

Secure repo introspection
REPO-100 / REPO-101 depend on strict, predictable allow-lists.

Scalable development
Multi-agent workflows (Architect → BA → Dev Lead → 3 Devs → QA) require deterministic paths.

Fewer runtime errors
All test and dev commands work consistently on Windows, macOS, Linux, and Codespaces.

6. Non-Negotiable Rules

These MUST never change without a change request via the Architect:
The FastAPI entrypoint is app/main.py.
All imports use the app. prefix.
The working directory for dev and tests is always experience/.
Repo introspection is limited to the defined allow-list.
The directory structure above is authoritative.