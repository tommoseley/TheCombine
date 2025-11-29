## 0. Scope

These standards apply to **all code** in the Document Machine MVP:

* Language: **Python 3.11+**
* Backend: **FastAPI**
* Templates/UI: **Jinja2 + HTMX + vanilla JS**
* DB: **SQLite in Phase 1, PostgreSQL in Phase 2+**
* Agents: Anthropic client via a dedicated Agent Service

Where a rule uses **MUST / SHOULD / MAY**, treat it as RFC-style.

---

## 1. Project & Module Structure

**C-STR-001** – Top-level layout:

```text
app/
  core/          # settings, security, base deps
  models/        # SQLAlchemy models & Pydantic schemas
  services/      # business logic & integrations
  orchestrator/  # agent orchestration, pipelines
  api/           # FastAPI routers (HTTP endpoints)
  templates/     # Jinja2 templates
  static/        # CSS, JS, images
  db/            # migrations, seed scripts
tests/
pyproject.toml or requirements.txt
README.md
```

**C-STR-002** – Module boundaries:

* **Routers** call **services**, not DB directly.
* **Services** call **models/DB**, **Agent Service**, or other services.
* **Orchestrator** coordinates agents and writes **canonical documents**, not UI.

**C-STR-003** – File naming:

* Python: `snake_case.py`
* Templates: `kebab-case.html`
* Tests mirror code: `tests/test_<module>.py`

---

## 2. Python Style & Type Hints

**C-PY-001** – Style:

* Follow **PEP8**.
* Line length target **100 chars** (soft, not religious).

**C-PY-002** – Type hints:

* **All** public functions and class methods MUST be fully typed.
* No `Any` unless there is a very good reason and a comment: `# type: ignore[reason]`.

**C-PY-003** – Imports:

* Standard library → third-party → local imports, with blank lines between.
* No wildcard imports (`from x import *` is forbidden).

**C-PY-004** – Docstrings:

* Public modules/classes/functions SHOULD use short, focused docstrings.
* Use the “one-line summary + optional detail” style.

---

## 3. Configuration & Secrets

**C-CONF-001** – Config via environment:

* All secrets and environment-dependent config **MUST** come from environment variables.
* Use a single `Settings` class (Pydantic BaseSettings or similar) in `app/core/config.py`.

**C-CONF-002** – No hard-coded secrets:

* API keys, DB passwords, tokens, etc. MUST NOT appear in source files, tests, or templates.

**C-CONF-003** – Mode flags:

* At minimum: `ENVIRONMENT` in `{local, dev, prod}`.
* Branch behavior (logging level, debug, etc.) on this flag.

---

## 4. FastAPI Conventions

**C-API-001** – Routers:

* Routers live in `app/api/`.
* Each domain gets its own router: `workspaces.py`, `auth.py`, `orchestrator.py`, `repo_view.py`.

**C-API-002** – Path & verb usage:

* **GET** – read, list, render pages.
* **POST** – create / trigger actions.
* **PATCH** – partial updates (status, archive).
* **DELETE** – soft-delete operations.

**C-API-003** – Request/response models:

* Use **Pydantic models** for input and output, except for trivial forms rendered in HTML.
* Route signatures SHOULD reference Pydantic models, not raw dicts.

**C-API-004** – Dependencies:

* Use FastAPI `Depends` for:

  * DB sessions
  * Current user/session (once auth exists)
  * Shared services (e.g., `AgentService`, `ExportService`)

**C-API-005** – Error handling:

* Raise `HTTPException` with meaningful messages.
* Never leak raw stack traces or secrets to the client.
* Map known domain errors → 4xx responses, not 500.

---

## 5. Database & Models

**C-DB-001** – ORM:

* Use **SQLAlchemy ORM** for DB access.
* One central `Base` in `app/models/base.py`.

**C-DB-002** – Soft deletes:

* Soft-delete via a `status` field or `deleted_at` timestamp, NEVER hard-delete user-facing entities.
* Queries MUST exclude soft-deleted by default.

**C-DB-003** – Migrations:

* Use Alembic or equivalent for schema evolution (Phase 1 OK to start minimal, but no manual SQL scattered across code).
* No destructive schema changes without explicit migration scripts.

**C-DB-004** – JSON fields:

* Canonical documents stored as JSON fields (`content`).
* Validation MUST occur in a **schema layer** (Pydantic) before persisting.

---

## 6. Orchestrator & Agents

**C-ORCH-001** – Separation:

* Orchestrator logic MUST live under `app/orchestrator/`.
* Agent-specific code MUST live under `app/services/agents.py` (or submodules).

**C-ORCH-002** – Async execution:

* Orchestrator uses `asyncio.gather` for parallel agent calls.
* No blocking I/O inside async code; if necessary, push to a thread (`anyio.to_thread.run_sync` or similar).

**C-ORCH-003** – Deterministic pipelines:

* Pipeline stages must be explicit state transitions (e.g., `pm_questions` → `epic_generation` → `architecture_approval`).
* State changes go through a single pipeline-state update function, not ad hoc updates scattered in code.

**C-ORCH-004** – Validation before save:

* All agent outputs MUST:

  1. Be parsed into a matching Pydantic model (`CanonicalEpicV1`, `CanonicalArchitectureV1`, `CanonicalBacklogV1`, etc.).
  2. Fail fast on validation errors.
  3. Log errors and optionally re-ask the Mentor agent.

---

## 7. Templates, HTMX, and Frontend

**C-UI-001** – Templates:

* Jinja2 templates in `app/templates/`.
* Layout inheritance: base templates (`base.html`) with `block` inheritance.

**C-UI-002** – HTMX usage:

* HTMX for partial updates: forms, list refreshes, approval actions.
* Prefer **server-rendered fragments** over heavy client-side JS.

**C-UI-003** – No SPA:

* No React, no SPA frameworks, no client-side routing in MVP.

**C-UI-004** – Progressive enhancement:

* Core flows SHOULD still function without JS/HTMX where feasible (graceful degradation).

---

## 8. Logging & Observability

**C-LOG-001** – Logging:

* Use Python `logging` with a single centralized config.
* Log levels: DEBUG (local), INFO (dev), WARNING/ERROR (prod).

**C-LOG-002** – Structured logs:

* Log structured messages for key operations (orchestrator steps, agent retries, export, auth).
* At minimum: `event`, `workspace_id`, `stage`, and any relevant IDs.

**C-LOG-003** – No PII in logs:

* Do not log secrets, full user emails, or raw LLM prompts/responses if they contain sensitive info.

---

## 9. Testing

**C-TEST-001** – Framework:

* Use **pytest**.

**C-TEST-002** – Coverage expectations:

* New services and orchestration functions SHOULD come with tests.
* Auth, pipeline transitions, and canonical validations are **must-have** for tests.

**C-TEST-003** – Test structure:

```text
tests/
  api/          # endpoint tests
  services/     # business logic
  orchestrator/ # pipeline tests
  models/       # model + validation tests
```

**C-TEST-004** – Fast tests:

* Tests must be able to run with **SQLite in memory** and no external integrations (LLM calls mocked).

---

## 10. Safety & AI-Agent Constraints

These are the “do not burn down the repo” rules for AI devs.

**C-AI-001** – No destructive operations:

* AI-generated code MUST NOT:

  * Delete or rewrite unrelated modules.
  * Drop DB tables.
  * Modify `.git` config, `.env`, or secrets.

**C-AI-002** – Locality of change:

* Changes SHOULD be localized to the files and modules needed to implement a specific story.
* When touching shared infrastructure (config, models, router wiring), changes MUST be minimal and intentional.

**C-AI-003** – Idempotent migrations:

* DB migrations generated by AI MUST be additive or safely reversible.

**C-AI-004** – Standards obedience:

* If code conflicts with these standards, the **Dev Mentor** MUST instruct agents to refactor.
* Dev agents MUST not introduce alternative stacks (Django, Flask, TS/Nest, React, etc.) in this repo.

---
