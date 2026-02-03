# ADR-044 — Addendum A: Git as a First-Class UX Primitive

**Status:** Accepted (Addendum)
**Applies To:** ADR-044 (Admin Workbench with Git-Canonical Configuration)
**Date:** 2026-02-02

---

## Context

ADR-044 establishes Git as the canonical source of truth for document configuration.

However, treating Git as an implementation detail creates a dangerous abstraction leak:
- Hidden state
- Silent drift
- Unclear authorship
- Ambiguous releases

To maintain industrial governance guarantees, Git must be surfaced explicitly in the Admin Workbench UX.

---

## Decision

**Git operations SHALL be first-class UX primitives in the Admin Workbench.**

The Admin Workbench is not merely an editor that persists to Git.
It is a **controlled Git working environment with domain-specific constraints**.

### Canonical Principle

> If a change is not a Git change, it does not exist.
> There is no meaningful "saved" state outside of Git.

---

## UX Implications (Normative)

### 1. Git Workspace Semantics

Every Admin Workbench editing session operates on:
- A Git branch or isolated workspace
- Derived from the currently active release

The UI MUST visibly display:
- Branch/workspace name
- Base commit
- Dirty / clean state

**Hidden Git state is prohibited.**

### 2. First-Class Change Visibility

The Admin Workbench MUST include a **Changes panel** showing:
- Modified files
- Added / removed artifacts
- Diffs (semantic where possible, raw otherwise)
- Grouping by artifact type (prompt, schema, docdef, workflow, etc.)

### 3. Commit as an Explicit Action

The UX MUST provide explicit actions:
- **Commit Draft**
- **Stage Release**
- **Activate Release**

There SHALL be no implicit save or auto-commit behavior.

### 4. Release Activation

Activating a release:
1. Updates `_active/active_releases.json`
2. Commits the change to Git
3. Triggers runtime synchronization

Rollback is achieved solely by reverting this pointer via commit.

---

## Non-Goals (Clarified)

- No free-form Git operations (rebase, squash, force-push)
- No hidden background commits
- No chat-style prompt editing without diffs
- No production mutation without Git history

---

## Consequences

Configuration changes become auditable by construction.

Drift becomes structurally impossible.

The system naturally supports:
- PR-based approvals
- AI-authored config with human review
- Signed or notarized releases (future)

---

## WS-044-11: Git-Integrated Admin UX

**Status:** Proposed
**Scope:** Required for ADR-044 compliance
**Depends On:** ADR-044, ADR-044 Addendum A, WS-044-01

### Objective

Implement Git operations as explicit, visible UX actions within the Admin Workbench, ensuring that all configuration edits exist solely as Git changesets.

### In Scope

**Git Workspace Management:**
- Branch/workspace creation per editing session
- Base commit selection (default: active release)
- Read-only view of historical releases

**Change Visibility:**
- File-level change tracking
- Artifact-aware grouping
- Inline diff viewer (JSON / text)

**Commit & Release Actions:**
- Commit Draft (with message)
- Stage Release (freeze + validate)
- Activate Release (pointer update)

**Audit Metadata:**

Capture:
- Acting user (logical identity)
- Timestamp
- Rationale (commit message)

Persist metadata in commit message or structured trailer.

### UX Requirements (Normative)

#### Git Status Panel

The Admin Workbench MUST display:
- Current branch/workspace
- Base commit hash (short)
- Modified file count
- Staged vs unstaged changes

#### Commit Flow

A commit action MUST:
1. Run validations (schema, refs, governance rules)
2. Present failures inline
3. Block commit if violations exist
4. Require a commit message

**No validation → no commit.**

#### Release Flow

**Stage Release:**
- Freezes current commit
- Prevents further edits
- Runs full validation suite

**Activate Release:**
- Updates active pointer
- Commits pointer change
- Triggers runtime sync

### Permissions Model (MVP)

- Git operations executed via service account
- User identity recorded as:
  - Structured commit metadata
  - And/or DB audit log
- Per-user Git credentials explicitly out of scope for MVP

### Out of Scope

- Merge conflict resolution UI (block instead)
- Arbitrary branch manipulation
- PR workflow automation
- Signed commits (future enhancement)

### Acceptance Criteria

WS-044-11 is complete when:
- [ ] Admin users can edit configuration only within a visible Git workspace
- [ ] All changes appear as Git diffs before commit
- [ ] No configuration change affects runtime without a Git commit
- [ ] Releases are activated via committed pointer changes only
- [ ] Rollback is possible by reverting pointer commit
- [ ] Git state is always visible and never implicit

### Deliverables

- Git workspace abstraction (branch or working tree)
- Changes / Diff panel
- Commit / Stage / Activate UX flows
- Active pointer commit mechanism
- Minimal Git service integration layer
- Audit trail integration

---

*Last updated: 2026-02-02*
