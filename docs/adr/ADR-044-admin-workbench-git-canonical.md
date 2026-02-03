# ADR-044: Admin Workbench with Git-Canonical Document Configuration

**Status:** Accepted
**Decision Owner:** Product Owner
**Date:** 2026-02-02

**Related ADRs:**
- ADR-030 — Backend-for-Frontends
- ADR-031 — Canonical Schema Registry
- ADR-032 — Fragment & Rendering Model
- ADR-034 — Execution Thread & Governance
- ADR-035 — Durable Work Item Queue

---

## Context

The Combine treats documents as governed production artifacts, not conversational output.

Document behavior is defined by a coordinated set of configuration artifacts:
- Prompts (role, task, QA, PGC, questions)
- Schemas
- Workflow steps and production modes
- Document definitions (full document + sidecar)
- Gating rules and lifecycle constraints

These artifacts:
- Directly influence production behavior
- Propagate constraints downstream
- Must be auditable, reviewable, diffable, and reversible

Today, these artifacts are distributed across seed files and registries, with no unified editing surface, release discipline, or governance boundary.

---

## Decision

**Git SHALL be the canonical source of truth for all document configuration artifacts.**

An **Admin Workbench** SHALL be introduced as a controlled Git workspace with domain-specific tooling—not an editor that happens to write to Git.

### Canonical Rules

1. **If a document configuration is not committed to Git, it does not exist.**
2. **All configuration changes exist only as Git changesets.** There is no "saved but uncommitted" state that matters to the system.
3. **Runtime systems MUST NOT mutate configuration artifacts.**

### Core Principle

The Admin Workbench is not just a "Machine Shop."
It is a **controlled Git workspace with governance semantics**.

Think of it as: VS Code + Git, but:
- Constrained to Document Type Packages
- With production semantics instead of developer semantics

---

## Scope of Canonical Artifacts

Git-canonical artifacts include:

| Artifact Type | Description |
|---------------|-------------|
| Document Type Packages | Atomic unit containing all artifacts for one document type |
| Prompt artifacts | Role, task, QA, PGC, questions |
| Schema artifacts | JSON Schema definitions |
| Workflow definitions | Steps, production modes, entity creation |
| Document definitions | Full view + sidecar rendering |
| Gating rules | Lifecycle definitions and constraints |
| Test fixtures | Golden traces for validation |

---

## Architecture Implications

### Source of Truth

- Git repository stores immutable, versioned Document Type Packages
- Each release corresponds to a Git commit (or tag)
- `_active/active_releases.json` provides active pointer indirection

### Runtime Read Path

Runtime reads from **DB-cached materializations** keyed by `(doc_type_id, version)` for performance and stability.

DB-cached entries are generated from Git packages by an explicit **Sync** operation.

### Release Change / Cache Invalidation

When `_active/active_releases.json` changes:
1. System invalidates caches for affected document types
2. Materializes new active versions to DB
3. Production Line resolves via: active pointer → semver → DB cache

If cache miss occurs, runtime triggers materialization before proceeding.

### Trigger Mechanism

- **MVP:** Push-based via Admin Workbench on Promote/Activate
- **Future:** Webhook-triggered sync from Git provider

No Git polling in MVP.

### Database Role

Database stores:
- Active release pointers (cached from Git)
- Cached materializations (derived from Git packages)
- Production audit records

Database does NOT store canonical configuration. Git is canonical.

### Release Model

| State | Description | Git State |
|-------|-------------|-----------|
| **Draft** | Editable working state | Uncommitted changes on branch |
| **Staged** | Frozen, validated candidate | Committed, awaiting activation |
| **Released** | Immutable, active version | Tagged commit + active pointer |

Rollback is achieved by switching the active release pointer—a single commit to `active_releases.json`.

---

## Admin Workbench UX Model

### Every Editing Session is a Git Workspace

When opening a Document Type in the Admin Workbench:
- User is placed on a branch derived from the current active release
- UI shows: branch name, base commit, dirty state

**This must be visible. Hidden Git is how drift sneaks in.**

### Git is a First-Class Panel

A dedicated "Changes" panel is always accessible, showing:
- Modified files (grouped by artifact type)
- Added/removed artifacts
- Semantic diff viewer

Example grouping:
```
Prompts (2 changed)
Schema (1 changed – ⚠ breaking)
DocDef (1 changed)
package.yaml (auto-updated)
```

### Commit is a UX Action, Not a Side Effect

| Action | Behavior |
|--------|----------|
| **Commit Draft** | Requires message, updates semver suggestion, runs validations |
| **Stage Release** | Freezes commit, locks edits |
| **Activate Release** | Updates `_active/active_releases.json`, triggers runtime sync |

**No "Save" button exists.** No commit = nothing happened.

### package.yaml is Partially System-Owned

The UX auto-updates:
- Version
- Artifact references
- Checksums (optional)

Manual edits that break invariants are prevented.

### Git Operations (MVP)

**Required:**
- Clone/fetch repository
- List branches/tags
- Load a specific release commit
- Create branch (per editing session)
- Modify files in-place
- Commit with message
- Tag release
- Update active pointer file
- Diff vs base
- Diff vs previous release
- History for this document type only

**Not required (block instead):**
- Rebase UI
- Merge conflict resolution UI
- Arbitrary branch switching

**Principle: Fail fast > clever Git UX.**

### Git Credential Model

**MVP:** Service account with audit metadata

```
Author: Combine Config Bot <config-bot@thecombine.ai>
Co-Authored-By: tom.moseley <tom@example.com>
```

This provides:
- Consistent commit authorship
- Full traceability via metadata
- No credential delegation complexity

Per-user Git identity is a future enhancement.

---

## Repository Layout

```
/combine-config/
  /README.md

  /_conventions/
    ids.md
    versioning.md
    promotion.md

  /_active/
    active_releases.json

  /document_types/
    /project_discovery/
      /releases/
        /1.4.0/
          package.yaml
          prompts/
            task.prompt.txt
            qa.prompt.txt
            pgc_context.prompt.txt
            questions.prompt.txt
          schemas/
            output.schema.json
          workflows/
            workflow.fragment.json
          docdefs/
            full.docdef.json
            sidecar.docdef.json
          rules/
            gating.rules.json
          tests/
            fixtures/
            golden_traces/

    /primary_implementation_plan/
      /releases/
        /1.0.0/
          ...same shape...

  /prompts/
    /roles/
      /technical_architect/
        /releases/
          /1.0.0/
            role.prompt.txt
      /project_manager/
        /releases/
          /1.0.0/
            role.prompt.txt
    /templates/
      /document_generator/
        /releases/
          /1.0.0/
            template.txt
    /shared/
      /releases/
        /1.0.0/
          untrusted_context_clause.txt
          output_format_contract.txt

  /workflows/
    /software_product_development/
      /releases/
        /1.0.0/
          workflow.json

  /components/
    /SummaryBlockV1/
      /releases/
        /1.0.0/
          component.json

  /schemas/
    /registry/
      schema_registry.json
```

### Shared vs Packaged Artifacts

| Artifact Type | Ownership | Location |
|---------------|-----------|----------|
| Role prompts | **Shared** | `/prompts/roles/{role_id}/releases/{semver}/` |
| Templates | **Shared** | `/prompts/templates/{template_id}/releases/{semver}/` |
| Boilerplate includes | **Shared** | `/prompts/shared/releases/{semver}/` |
| Task prompts | Packaged | `/document_types/{doc_type}/releases/{semver}/prompts/` |
| QA prompts | Packaged | (same) |
| PGC context | Packaged | (same) |
| Question prompts | Packaged | (same) |
| Schemas | Packaged | (same) |
| DocDefs | Packaged | (same) |

### Referencing Shared Artifacts

In `package.yaml`:
```yaml
role_prompt_ref: "prompt:role:technical_architect:1.0.0"
template_ref: "prompt:template:document_generator:1.0.0"
```

Shared artifacts are version-locked per package to ensure reproducibility.

---

## Naming Conventions

### IDs (Canonical)

- `doc_type_id`: snake_case (e.g., `primary_implementation_plan`)
- Artifact ID prefixes:
  - `prompt:{doc_type_id}:{kind}:{semver}`
  - `prompt:role:{role_id}:{semver}`
  - `prompt:template:{template_id}:{semver}`
  - `schema:{doc_type_id}:{semver}`
  - `docdef:{doc_type_id}:{surface}:{semver}` where surface ∈ {full, sidecar}
  - `rules:{doc_type_id}:{semver}`
  - `workflow:{workflow_id}:{semver}`

### Filenames (Stable, Diff-Friendly)

| Type | Filename |
|------|----------|
| Role prompt | `role.prompt.txt` |
| Task prompt | `task.prompt.txt` |
| QA prompt | `qa.prompt.txt` |
| PGC context | `pgc_context.prompt.txt` |
| Questions | `questions.prompt.txt` |
| Schema | `output.schema.json` |
| Full DocDef | `full.docdef.json` |
| Sidecar DocDef | `sidecar.docdef.json` |
| Gating rules | `gating.rules.json` |
| Workflow fragment | `workflow.fragment.json` |
| Manifest | `package.yaml` |

---

## Versioning Rules

### Semver Discipline

| Bump | When |
|------|------|
| **MAJOR** | Breaking change: fields removed/renamed/types changed; authority level change; production_mode change |
| **MINOR** | Additive backward-compatible: new optional fields; new docdef sections; prompt refinements |
| **PATCH** | Typo fixes, clarifications, non-functional edits |

### Compatibility Gates (Enforced by Tooling)

- Schema-breaking changes MUST force major bump
- DocDef pointers MUST resolve against schema for same release
- Prompts MUST reference schema ID for same release

---

## Active Pointer & Release Management

### active_releases.json Structure

```json
{
  "project_discovery": "1.4.0",
  "primary_implementation_plan": "1.0.0",
  "implementation_plan": "1.0.0",
  "technical_architecture": "1.0.0"
}
```

### Rules

- Rollback = single commit changing `active_releases.json`
- Runtime reads active pointer first, then resolves artifacts by convention
- Released artifacts are immutable (no in-place edits to released versions)

---

## Cross-Package Compatibility Validation

When activating a release, the system MUST validate the closure of dependencies:

- All `required_inputs` doc types have active releases
- All referenced shared prompts exist at specified versions
- All referenced components exist
- Schema/DocDef pointer integrity is intact for each package

**Activation MUST fail if any dependency is unresolved.**

---

## Governance Guardrails (MVP)

The following violations are **blocked, not warned**:

| Guardrail | Rule |
|-----------|------|
| PGC enforcement | No skipping mandatory PGC for Descriptive/Prescriptive documents |
| Creation mode integrity | No registering Extracted docs as document types |
| Release validation | No release without passing all validations |
| Cross-package integrity | No activation with unresolved dependencies |
| Schema compatibility | No breaking schema changes without major version bump |

---

## Consequences

### Positive

- Full diff, blame, and audit history
- Explicit release boundaries
- Fast, safe rollback via pointer change
- Strong alignment with industrial/regulated use cases
- Enables future PR-based and AI-assisted governance
- No configuration drift between environments

### Tradeoffs

- Higher MVP complexity
- Early Git integration required
- Admin UX must surface versioning explicitly
- Merge conflicts require governance resolution, not technical workarounds

These tradeoffs are intentional and aligned with The Combine's long-term positioning.

---

## Explicit Non-Goals

- No editing production documents from the Admin Workbench
- No live mutation of running production lines
- No implicit saves without commit
- No chat-style editing experience
- No merge conflict resolution UI (block instead)
- No Git polling (push-based sync only)

---

## Separation of Concerns

ADR-044 formally separates:

| Concern | System | Artifacts |
|---------|--------|-----------|
| **Machine Design** | Admin Workbench | Document Type Packages, prompts, schemas, workflows |
| **Machine Operation** | Production Line | Runtime execution, document production, audit logs |

Configuration flows one way: Git → Admin Workbench → DB Cache → Production Line

Production Line never writes back to configuration.

---

## Work Statements

### WS-044-01: Admin Workbench Core Architecture

**Objective:** Establish the Admin Workbench as a Git-canonical workspace and release manager.

**In Scope:**
- Admin-only "Machine Shop" UI
- Git read/write integration (clone, branch, commit, tag)
- Draft / Stage / Release lifecycle
- Active release pointer management
- Changes panel with semantic grouping

**Acceptance Criteria:**
- [ ] Configurations load from Git repository
- [ ] Edits require explicit commit (no "Save" action)
- [ ] Branch name, base commit, and dirty state visible
- [ ] Active release can be switched per document type
- [ ] Rollback completes without restart

---

### WS-044-02: Document Type Package Model

**Objective:** Define the Document Type Package as the atomic unit of configuration.

**Acceptance Criteria:**
- [ ] Package loads as a single unit from Git
- [ ] All internal references resolve
- [ ] Released versions are immutable
- [ ] Packages can be promoted independently
- [ ] `package.yaml` manifest validates against schema

---

### WS-044-03: Prompt & Schema Editors

**Objective:** Provide structured editors with governance enforcement.

**Acceptance Criteria:**
- [ ] JSON Schema validation enforced on save
- [ ] Prompt linting enforced
- [ ] Authority-level → PGC/QA rules validated
- [ ] Breaking schema changes detected and flagged
- [ ] Shared prompt references resolve correctly

---

### WS-044-04: DocDef & Sidecar Editor

**Objective:** Configure full document and sidecar rendering behavior.

**Acceptance Criteria:**
- [ ] All source pointers resolve to schema fields
- [ ] Required fields are represented in DocDef
- [ ] Sidecar rules comply with authority level
- [ ] Preview matches production rendering

---

### WS-044-05: Workflow & Production Mode Configuration

**Objective:** Edit workflows with explicit production semantics.

**Acceptance Criteria:**
- [ ] Every step declares exactly one `production_mode`
- [ ] Illegal transitions are blocked
- [ ] Constructive steps explicitly define child creation via `creates_entities`
- [ ] Workflow fragment + master workflow composition works correctly

---

### WS-044-06: Preview & Dry-Run Engine

**Objective:** Preview document behavior as executed on the Production Line.

**Acceptance Criteria:**
- [ ] Preview uses staged artifacts only
- [ ] PGC / generation / QA run deterministically
- [ ] Diffs vs prior release are visible
- [ ] Failures block promotion to Released state

---

### WS-044-07: Release & Rollback Management

**Objective:** Make promotion and rollback explicit, fast, and safe.

**Acceptance Criteria:**
- [ ] Released artifacts are immutable (no edits to released versions)
- [ ] Rollback is instantaneous (pointer change only)
- [ ] Audit log captures who/when/why/what for every release change
- [ ] Cross-package compatibility validated before activation

---

### WS-044-08: Governance Guardrails (MVP)

**Objective:** Prevent known failure modes.

**Acceptance Criteria:**
- [ ] No skipping mandatory PGC (blocked, not warned)
- [ ] No extracted docs registered as document types
- [ ] No release without validation passing
- [ ] Violations are blocked with clear error messages
- [ ] Cross-package dependency closure validated on activation

---

### WS-044-09: Git Repository Layout & Naming Conventions

**Objective:** Define canonical Git repository structure for all Admin Workbench–managed configuration artifacts.

**In Scope:**
- Repository directory structure and file naming rules
- Artifact identity rules (IDs vs filenames)
- Versioning rules (semver + compatibility gates)
- Release tagging strategy and active pointer model
- Artifact reference scheme
- Import/export contract for Admin Workbench
- Shared vs packaged artifact ownership
- Package manifest requirements (`package.yaml`)
- Golden trace/fixture layout

**Acceptance Criteria:**
- [ ] Repository layout documented under `/_conventions/`
- [ ] At least one document type migrated to new structure
- [ ] Artifact resolution is deterministic
- [ ] Versioning gates specified (major/minor/patch rules)
- [ ] Active pointer mechanism supports rollback via commit
- [ ] Manifest format defined and validated
- [ ] Shared vs packaged ownership documented

**Deliverables:**
- `/_conventions/ids.md`
- `/_conventions/versioning.md`
- `/_conventions/promotion.md`
- Canonical repository skeleton
- Reference implementation (one migrated document type)
- Validator script/spec

---

### WS-044-10: Migration from seed/ to combine-config/

**Objective:** Migrate all document configuration artifacts from current `seed/`-based structure to Git-canonical `combine-config/` repository.

**In Scope:**
- Artifact mapping from `seed/` to `combine-config/`
- Registry transition (`seed/registry/document_types.py` elimination)
- Database seeding changes (single Importer/Materializer)
- Phased cutover plan
- Validation and parity checks

**Migration Mapping:**

| Current Location | New Location |
|------------------|--------------|
| `seed/prompts/roles/*.txt` | `combine-config/prompts/roles/{role_id}/releases/{semver}/role.prompt.txt` |
| `seed/prompts/tasks/{Doc} v{Ver}.txt` | `.../document_types/{doc_type}/releases/{semver}/prompts/task.prompt.txt` |
| `seed/prompts/tasks/{Doc} QA v{Ver}.txt` | `.../prompts/qa.prompt.txt` |
| `seed/prompts/tasks/{Doc} Questions v{Ver}.txt` | `.../prompts/questions.prompt.txt` |
| `seed/prompts/pgc-contexts/*.txt` | `.../prompts/pgc_context.prompt.txt` |
| `seed/prompts/templates/*.txt` | `combine-config/prompts/templates/{template_id}/releases/{semver}/template.txt` |
| `seed/schemas/*.json` | `.../schemas/output.schema.json` |
| `seed/workflows/*.json` | `.../workflows/{workflow_id}/releases/{semver}/workflow.json` |
| `seed/registry/component_artifacts.py` (docdefs) | `.../docdefs/*.docdef.json` |
| `seed/registry/document_types.py` | **Eliminated** (replaced by `package.yaml` manifests) |

**Registry Fate:**

`seed/registry/document_types.py` SHALL be eliminated. Its contents are replaced by:
- `package.yaml` manifests per Document Type Package
- `_active/active_releases.json` as the only activation control
- Runtime registry structures generated at import time from Git packages

**Database Seeding Changes:**

Before: Seed scripts load artifacts directly from filesystem.

After: Single Importer/Materializer:
- Input: `combine-config/` + active pointers
- Output: DB-cached artifacts by `(doc_type_id, version)`

**Rule:** Runtime MUST NOT read from `seed/` paths after cutover.

**Phased Cutover Plan:**

| Phase | Description |
|-------|-------------|
| **Phase 1** | Reference migration: Project Discovery + PIP to new structure, runtime still on `seed/` |
| **Phase 2** | Dual-read validation: Import migrated packages, run previews side-by-side, fix diffs |
| **Phase 3** | Authoritative switch: Runtime reads only from DB-cached Git materializations, freeze `seed/` |
| **Phase 4** | Cleanup: Remove unused seed loaders, archive `seed/` as historical reference |

**Validation & Parity Checks (must pass before Phase 3):**
- [ ] Artifact resolution parity (all refs resolve)
- [ ] Schema equality (or compatible superset)
- [ ] DocDef rendering parity
- [ ] PGC question equivalence
- [ ] QA outcomes equivalent for fixtures
- [ ] No runtime errors when active pointers switch

**Acceptance Criteria:**
- [ ] At least two reference document types fully migrated and released from `combine-config/`
- [ ] `seed/registry/document_types.py` no longer used by runtime
- [ ] Runtime reads only DB-cached artifacts imported from Git
- [ ] Active release switching works without restart
- [ ] No behavioral regression in previews or production runs
- [ ] Written cutover checklist exists and executed successfully

**Deliverables:**
- Migration mapping document
- Importer/Materializer implementation
- Migrated packages for reference doc types
- Cutover checklist
- Post-migration validation report

---

### WS-044-11: Golden Trace Runner & Regression Harness (Future)

**Status:** Deferred (not MVP)

**Objective:** Automated regression testing using golden traces.

**Scope:** Define runner that executes fixtures through preview engine and compares against golden traces.

---

## Package Manifest Requirements (package.yaml)

Minimum required fields:

```yaml
doc_type_id: project_discovery
display_name: Project Discovery
version: 1.4.0

authority_level: descriptive  # descriptive | prescriptive | constructive | elaborative
creation_mode: llm_generated  # llm_generated | constructed | extracted
production_mode: generate     # generate | authorize | construct
scope: project                # project | epic | feature

required_inputs: []
optional_inputs: []

# Shared artifact references
role_prompt_ref: "prompt:role:technical_architect:1.0.0"
template_ref: "prompt:template:document_generator:1.0.0"

# Packaged artifacts (relative paths)
artifacts:
  task_prompt: prompts/task.prompt.txt
  qa_prompt: prompts/qa.prompt.txt
  pgc_context: prompts/pgc_context.prompt.txt
  questions_prompt: prompts/questions.prompt.txt
  schema: schemas/output.schema.json
  full_docdef: docdefs/full.docdef.json
  sidecar_docdef: docdefs/sidecar.docdef.json
  gating_rules: rules/gating.rules.json

# Test artifacts
tests:
  fixtures:
    - tests/fixtures/fixture_minimal.json
    - tests/fixtures/fixture_realistic.json
  golden_traces:
    - tests/golden_traces/trace_001.json
```

---

## Decision Status

**Accepted** pending implementation via the work statements above.

---

*Last updated: 2026-02-02*
