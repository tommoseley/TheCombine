# WS-RENDER-006: Add Project Governance Section to Binder Export

**Parent:** Rendering pipeline
**Depends on:** WS-GOV-001 (policy documents must exist before binder can include them)
**Blocks:** Portable governed binder export (complete blueprint with factory standards)

---

## Objective

Add a "Project Governance" section at the front of the binder export that includes the active governance policy documents. This makes the binder a complete portable blueprint — factory standards, product definition, architecture, and governed work orders in a single export.

---

## Context

The binder export currently assembles:

```
CI-001 — Concierge Intake
PD-001 — Project Discovery
IP-001 — Implementation Plan
TA-001 — Technical Architecture
WP-001 — Core Python Implementation
  WS-001 — Create Script File Structure
  WS-002 — Implement Main Function Logic
```

What's missing is the governance section — the "how to build well" context that tells an executing agent or human team the factory standards (tests-first, CRAP thresholds, reuse-first, ontology, architectural constraints).

Without governance in the binder, the plan tells you *what* to build but not *how to build well*. An agent receiving the binder can execute the WSs but has no awareness of quality standards that apply across all work.

**Architectural constraint:** The binder renderer (`binder_renderer.py`) is a pure function — no DB, no filesystem, deterministic output. This must be preserved. The renderer cannot read policy files from disk; they must be passed in as data by the endpoint.

**Deployment constraint:** The Docker image copies only `app/`, `alembic/`, `alembic.ini`. Files in `docs/` are not available at runtime. Policy files must live in a location that is either deployed or read at assembly time by the endpoint.

The target binder structure:

```
Project Governance
  POL-ADR-EXEC-001 — ADR Execution Authorization
  POL-ARCH-001 — Architectural Integrity Standard
  POL-CODE-001 — Code Construction Standard
  POL-QA-001 — Testing & Verification Standard
  POL-WS-001 — Work Statement Standard
CI-001 — Concierge Intake
PD-001 — Project Discovery
...
```

---

## Scope

**In scope:**

- Move policy files from `docs/policies/` to `combine-config/policies/` (governed inputs alongside schemas and prompts)
- Binder endpoint (`app/api/v1/routers/projects.py`) reads policy files from `combine-config/policies/`, parses title and content, passes as data to the renderer
- Add `policies` parameter to `render_project_binder()` — a list of `{title, content}` dicts
- Renderer formats the governance section from the passed-in data (stays pure — no filesystem access)
- Full policy text included in binder (binder is portable; recipient may not have access to The Combine)
- Add governance entries to the TOC before pipeline documents
- Handle gracefully: if no policy data passed (empty list), omit the governance section (no error)

**Out of scope:**

- Drafting the policy documents themselves (WS-GOV-001 — complete)
- Changes to WS nesting (already implemented)
- Changes to single-document rendering
- Changes to evidence mode or IA verification gate
- Adding non-policy artifacts (ADRs, session logs) to the governance section

---

## Prohibited

- Do not modify policy document content — include as-is
- Do not hardcode policy file names — discover from the policies directory
- Do not change the rendering of pipeline documents or WS nesting
- Do not add new API endpoints — this is a change to the existing binder assembly path
- Do not have the renderer read from the filesystem — it receives data, not paths
- Do not break the pure function contract of `binder_renderer.py`

---

## Steps

### Phase 1: Move policy files

**Step 1.1: Move policies to combine-config**

Move all `*.md` files from `docs/policies/` to `combine-config/policies/`:

```
combine-config/policies/POL-ADR-EXEC-001-ADR-Execution-Authorization.md
combine-config/policies/POL-ARCH-001.md
combine-config/policies/POL-CODE-001.md
combine-config/policies/POL-QA-001.md
combine-config/policies/POL-WS-001-Standard-Work-Statements.md
combine-config/policies/GOV-SEC-T0-002-Secrets-Handling.md
```

Update any references in CLAUDE.md and other docs that point to `docs/policies/`.

### Phase 2: Tests first (must fail before implementation)

**Step 2.1: Test governance section in renderer (pure function tests)**

File: `tests/tier1/services/test_binder_governance.py` (new)

Tests (all operate on the pure `render_project_binder` function with policies passed as data):

- Binder with policies passed → output includes a "Project Governance" section before the first pipeline document (CI-001)
- Governance section includes content from all passed policy dicts
- Policies are sorted alphabetically by title
- Governance section appears in the TOC as a group before pipeline documents
- Individual policies appear as indented TOC entries under governance
- Binder with empty policies list → governance section is omitted, no error, binder otherwise renders normally
- Binder with `policies=None` → governance section is omitted, no error
- Policy titles are used as-is from the passed-in data (renderer does not parse headings)

### Phase 3: Implementation

**Step 3.1: Add policies parameter to binder renderer**

File: `app/domain/services/binder_renderer.py`

Add `policies` parameter to `render_project_binder()`:

```python
def render_project_binder(
    project_id: str,
    project_title: str,
    documents: List[Dict[str, Any]],
    policies: Optional[List[Dict[str, str]]] = None,
    generated_at: Optional[str] = None,
) -> str:
```

Each policy dict: `{"title": "POL-QA-001 — Testing & Verification Standard", "content": "..."}`

Before the TOC and document sections, if policies is non-empty:

1. Sort policies alphabetically by title
2. Add governance TOC group (before pipeline documents)
3. Add governance body section (before first pipeline document)

Governance section format:

```markdown
---

# Project Governance

These standards apply to all work in this project.

---

## POL-ADR-EXEC-001 — ADR Execution Authorization

[policy content]

---

## POL-ARCH-001 — Architectural Integrity Standard

[policy content]

---
```

New helper functions: `_render_governance_toc(policies)`, `_render_governance_section(policies)`.

**Step 3.2: Read policies in binder endpoint**

File: `app/api/v1/routers/projects.py` (render_project_binder endpoint)

Before calling `_render_binder()`:

1. Scan `combine-config/policies/` for `*.md` files
2. For each file, read content and parse title from first `#` heading (fallback: filename without extension)
3. Build list of `{"title": title, "content": content}` dicts
4. Pass as `policies=policy_list` to `_render_binder()`

If `combine-config/policies/` doesn't exist or has no `.md` files, pass `policies=[]`.

**Step 3.3: Update TOC generation**

File: `app/domain/services/binder_renderer.py`

Update `_render_toc()` to accept an optional governance TOC block that renders before pipeline entries:

```markdown
## Table of Contents

### Project Governance
- [POL-ADR-EXEC-001 — ADR Execution Authorization](#pol-adr-exec-001)
- [POL-ARCH-001 — Architectural Integrity Standard](#pol-arch-001)
- [POL-CODE-001 — Code Construction Standard](#pol-code-001)
- [POL-QA-001 — Testing & Verification Standard](#pol-qa-001)
- [POL-WS-001 — Work Statement Standard](#pol-ws-001)

### Pipeline Documents
- [CI-001 — Concierge Intake](#ci-001)
...
```

### Phase 4: Verify

**Step 4.1:** Run all Phase 2 tests — all must pass.

**Step 4.2:** Run full Tier-1 suite — no regressions.

**Step 4.3:** Export a binder for a project with policy files in `combine-config/policies/`. Verify governance section appears first with all policies included.

---

## Allowed Paths

```
app/domain/services/binder_renderer.py       (renderer — add policies parameter)
app/api/v1/routers/projects.py               (endpoint — read policy files, pass as data)
combine-config/policies/                     (new location for policy files)
docs/policies/                               (remove after move)
tests/tier1/services/
CLAUDE.md                                    (update policy path references)
```

---

## Verification

- [ ] Policy files moved from `docs/policies/` to `combine-config/policies/`
- [ ] Binder export begins with a "Project Governance" section containing all active policies
- [ ] Governance section appears in the TOC before pipeline documents
- [ ] Policies are sorted alphabetically by title
- [ ] Policy content is included as-is (not modified by the renderer)
- [ ] Policy titles are parsed from file headings by the endpoint
- [ ] Binder with no policy files omits governance section gracefully (no error)
- [ ] Renderer remains a pure function (no filesystem access)
- [ ] Existing binder output (pipeline documents, WS nesting) is unchanged
- [ ] All existing Tier-1 tests pass (no regressions)

---

_Draft: 2026-03-06_
