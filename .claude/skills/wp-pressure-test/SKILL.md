---
name: wp-pressure-test
description: Pre-flight validate a Work Package (WP) + its Work Statements (WS) against the codebase, active releases, schema registry, and governance invariants before execution begins. Phase 1 is fully mechanical (PASS/FAIL). Phase 2 is LLM-assisted architectural pressure testing with evidence and resolution options. Output is a structured report with verdict READY / READY_WITH_CONDITIONS / NOT_READY.
---

# WP/WS Pressure Test (Pre-Flight)

This skill prevents mid-execution stops by validating a drafted WP/WS set against:
- the actual repository (files, paths, modules)
- combine-config registry (active_releases.json, schema/task locations)
- governance invariants (no dual shapes for same concept, no missing prerequisites, auditable mutations)

**Read-only only.** Never modify code, schemas, configs, or documents while running this skill.

---

## When to Use

Use this skill when:
- A WP/WS set is drafted and about to be accepted for execution
- Any WS touches schemas, persistence, doc registry, APIs, or workflows
- Any WP has 3+ WSs
- Any WP introduces or modifies doc types, handlers, registry, prompts, or IA
- Before handing a WP to Claude Code for implementation

---

## Inputs Required

1) WP document path (markdown)
2) All associated WS document paths (markdown)
3) Any schema bundle paths referenced (json files)
4) Repo access (read-only)

If WS docs are not explicitly listed, infer WS set by scanning links/references from the WP.

---

## Output Location

Write report to: `docs/audits/YYYY-MM-DD-wp-pressure-test-{WP-ID}.md`
---

# Phase 0 -- Build Inventory (Mechanical)

Before any validation, build a normalized inventory from WP + WS text.

Extract:
- WP id, title
- WS ids, titles
- WS dependency edges (depends_on)
- referenced doc_type_ids / schema ids / prompt ids / workflow ids
- file paths mentioned, grouped by action if stated (create/modify/delete/unknown)
- allowed_paths (if present) per WS
- ADR refs + policy refs

This inventory is the evidence base for every later check.
Include it (briefly) in the report.

If the WP/WS lacks enough structure to extract inventory reliably, flag as a **Phase 0 FAIL**:
- "WP/WS not pressure-testable: insufficient concrete references"

---

# Phase 1 -- Structural Validation (Mechanical PASS/FAIL)

These checks are binary. No judgment calls.

## 1.1 File Reference Validation

For every file path mentioned in WS execution steps:
- If WS implies "modify" or "delete": file must exist.
- If WS implies "create": parent directory must exist and file must not already exist.
- If action is unknown: verify parent directory exists; mark as CONDITION (not FAIL).

FAIL if any required existing file is missing, or any "create" collides with an existing file.

## 1.2 Registry Path Existence (Config Directories)

If WP/WS references global config paths, verify directories exist (or are explicitly created by the WP):
- `combine-config/schemas/...`
- `combine-config/prompts/tasks/...`
- `combine-config/document_types/...`
- `combine-config/_active/active_releases.json`

FAIL if a referenced registry root path is missing and not planned as a created artifact.

## 1.3 Active Releases Consistency

If WP/WS references doc types, schemas, tasks, workflows:
- referenced doc_type_ids must exist in active_releases.json (unless WP explicitly creates them)
- new doc_type_ids must not already exist (collision)
- new schema/task releases must conform to repo conventions used elsewhere
- referenced releases must exist on disk if claimed as already present

FAIL on collisions or missing required dependencies.

## 1.4 Dependency Chain Validation

For WS dependencies:
- every referenced WS id must exist
- dependency graph must be acyclic
- optional: produce a topological order preview

FAIL on cycles or dangling references.

## 1.5 Allowed Paths Coverage

If WS defines allowed_paths:
- every file path referenced by that WS must fall under allowed_paths

FAIL if any file referenced is out-of-scope.

## 1.6 ADR / Policy Reference Validation

For each ADR/policy referenced:
- referenced files must exist in docs/adr/ and docs/policies/ (or equivalent canonical locations)

FAIL if referenced governance docs do not exist.

## 1.7 Schema Identity Conflicts

If WP introduces schemas:
- Duplicate `$id` vs any existing schema => FAIL
- Same doc_type_id mapping to different schema `$id` in active config => FAIL unless WP contains an explicit migration WS in-scope

FAIL on provable identity collisions.

## 1.8 Handler / Registry Consistency

If WP adds/modifies document types:
- ensure there is a handler strategy (existing handler verified or new handler WS present)
- ensure handler registry is updated in-scope when required by current architecture

FAIL if new doc types are introduced with no handler plan where a handler is required.
---

# Phase 2 -- Architectural Pressure Test (LLM-assisted)

These are judgment checks. Each produces a finding with:
- severity: HIGH / MEDIUM / LOW
- evidence: specific files/paths/lines/schema paths
- why it matters: execution risk
- resolution options: Quick Fix / Correct Fix / Eject

Guidance:
- HIGH means "likely to cause a mid-execution stop, runtime bomb, or governance violation"
- MEDIUM means "will work but accumulates debt or introduces coupling risk"
- LOW means "style/consistency or minor future friction"

## 2.1 Persistence Strategy

Determine where new data lives:
- existing document store (preferred)
- new persistence plane (requires migrations, repos, audit surface)

HIGH if WP creates a parallel persistence path without explicit decision + rollback plan.

## 2.2 Dual Shape / Duplicate Concept Risk

Check whether WP introduces a second "shape" for a concept that already exists in:
- combine-config schemas
- document_type package schemas
- API request/response models
- domain models

HIGH if two active shapes would coexist for the same doc_type_id without migration.

## 2.3 Missing Prerequisite Decisions

Identify assumptions not decided yet:
- "pending" architecture references
- relying on WPs/WSs not yet executed
- TBDs in execution steps

HIGH if the WP requires an undecided prerequisite to proceed.

## 2.4 Governance Gaps for Mutations

For each write operation (API endpoint, mutation, promotion, state change):
- is provenance captured?
- is there an auditable trail?
- is there idempotency or replay strategy?
- does it respect existing Tier-0/Tier-1 constraints?

HIGH if mutation exists without audit/provenance plan.

## 2.5 Invariant Contradictions

Check whether schemas allow contradictory states that violate stated invariants.
Example: "TA is prerequisite" but schema permits empty ta_ref or bindings without TA pin.

HIGH if contradiction can occur in valid schema state.

## 2.6 Blast Radius

Estimate the change surface:
- number of existing files touched
- subsystems touched
- test coverage context (if available)

MEDIUM/HIGH if large surface + low testability + no staged WS boundaries.

## 2.7 API Surface Consistency

Evaluate new endpoints for consistency with existing patterns:
- routing conventions
- response envelopes
- auth expectations
- error format

MEDIUM unless it breaks auth or invariants (then HIGH).

## 2.8 Migration & Rollback Reality

Assess whether changes can be rolled back:
- active_releases changes
- schema changes
- file deletions
- migrations (if any)

HIGH if irreversible change is introduced without explicit rollback strategy.
---

# Phase 3 -- Resolution Options (Required for every finding)

Each finding must include three options:

**A. Quick Fix** -- smallest change that unblocks (may add debt)
**B. Correct Fix** -- architecturally sound fix (may require extra WS/ADR)
**C. Eject** -- defer/remove scope, with tracking location

Rules:
- Quick Fix must be real and implementable (no "TODO later")
- Correct Fix must name concrete file(s)/WS(s)/ADR(s)
- Eject must specify where it will be tracked (WP id / debt register / ADR stub)

The skill may recommend an option, but must clearly label it as a recommendation.
The skill does not decide. The user (or a governed decision step) decides.

---

# Verdict Rules

- **READY**: Phase 1 all PASS + no HIGH findings in Phase 2
- **READY_WITH_CONDITIONS**: Phase 1 PASS + HIGH findings exist BUT there is an in-scope Correct Fix represented as WS/ADR, and execution can proceed by ordering
- **NOT_READY**: Any Phase 1 FAIL OR any HIGH finding without a chosen in-scope resolution
---

# Report Format (Required)

Produce:

1) Header: WP id, date, repo branch, inputs
2) Inventory summary (Phase 0 output)
3) Phase 1 table (PASS/FAIL)
4) Phase 2 table (severity + one-line finding)
5) Findings section (each with evidence + A/B/C options)
6) Summary: Verdict + Blocking Issues + Conditions + Accepted Risks

Use this template:

```markdown
# WP Pressure Test -- {WP-ID}: {WP Title}

**Date:** YYYY-MM-DD
**WP Location:** {file path}
**WS Count:** {N}
**Codebase Branch:** {branch name}

---

## Phase 0: Inventory

{Brief structured summary of extracted inventory}

---

## Phase 1: Structural Validation

| Check | Result | Details |
|-------|--------|---------|
| 1.1 File References | PASS/FAIL | {summary} |
| 1.2 Registry Paths | PASS/FAIL | {summary} |
| 1.3 Active Releases | PASS/FAIL | {summary} |
| 1.4 Dependency Chain | PASS/FAIL | {summary} |
| 1.5 Allowed Paths | PASS/FAIL | {summary} |
| 1.6 ADR/Policy Refs | PASS/FAIL | {summary} |
| 1.7 Schema Conflicts | PASS/FAIL | {summary} |
| 1.8 Handler/Registry | PASS/FAIL | {summary} |

**Structural Result:** {PASS | FAIL -- N issues}

---

## Phase 2: Architectural Pressure Test

| Check | Severity | Finding |
|-------|----------|---------|
| 2.1 Persistence | -- / HIGH / MEDIUM / LOW | {one-line summary} |
| 2.2 Dual Schema | -- / HIGH / MEDIUM / LOW | {one-line summary} |
| 2.3 Prerequisites | -- / HIGH / MEDIUM / LOW | {one-line summary} |
| 2.4 Governance Gaps | -- / HIGH / MEDIUM / LOW | {one-line summary} |
| 2.5 Invariant Contradictions | -- / HIGH / MEDIUM / LOW | {one-line summary} |
| 2.6 Blast Radius | -- / HIGH / MEDIUM / LOW | {one-line summary} |
| 2.7 API Consistency | -- / HIGH / MEDIUM / LOW | {one-line summary} |
| 2.8 Migration/Rollback | -- / HIGH / MEDIUM / LOW | {one-line summary} |

**Architectural Result:** {N HIGH, N MEDIUM, N LOW findings}

---

## Findings & Resolutions

### Finding {N}: {Title}

**Severity:** HIGH | MEDIUM | LOW
**Phase:** 1.{check} or 2.{check}
**Description:** {What was found}
**Evidence:** {File paths, line numbers, schema excerpts}

**Resolution Options:**

**A. Quick Fix** -- {Smallest change to unblock}
- Action: {Concrete steps}
- Tradeoff: {What debt this creates}
- Effort: {Minimal | Small | Medium}

**B. Correct Fix** -- {Architecturally sound resolution}
- Action: {Concrete steps, may include new WS or ADR}
- Tradeoff: {Additional scope/time}
- Effort: {Small | Medium | Large}

**C. Eject** -- {Remove from scope}
- Action: {What to defer and where to track it}
- Tradeoff: {What capability is lost or delayed}
- Effort: {Minimal}

**Recommendation:** {A, B, or C with brief rationale}

---

## Summary

**Verdict:** READY | READY WITH CONDITIONS | NOT READY

**Blocking issues (must resolve before execution):**
- {List of HIGH findings that block execution}

**Conditions (resolve during execution or before affected WS):**
- {List of MEDIUM findings with chosen resolution}

**Accepted risks (tracked as debt):**
- {List of LOW findings and ejected items}
```
---

# Quick Commands (Optional Helpers)

Use repo-safe commands for evidence gathering (read-only):

```bash
# Find schema $id values
find combine-config/schemas -name "*.json" -print0 | xargs -0 grep -H '"$id"'

# Show doc types in active releases
python3 -c "
import json
p='combine-config/_active/active_releases.json'
d=json.load(open(p))
print('\n'.join(sorted(d.get('document_types', {}).keys())))
"

# Find router declarations
grep -RIn 'router\.\(get\|post\|put\|patch\|delete\)' app/api | head -50

# Check handler registry
grep -n 'Handler' app/domain/handlers/registry.py

# Check existing API routes for a path pattern
grep -rn 'work.binder\|work_binder\|work-binder' app/
```

Do not perform mutations, formatting, or auto-fixes during the pressure test.

---

# Rules

1. **Read-only.** Never modify code, schemas, or documents during a pressure test.
2. **Evidence required.** Every finding must cite specific files, line numbers, or schema paths.
3. **No invented problems.** Only report issues supported by codebase evidence or logical contradiction.
4. **Resolutions must be actionable.** "Consider refactoring" is not a resolution. Name the file, the change, and the effort.
5. **Run from repo root.** All paths relative to project root.
6. **Respect existing governance.** Check against ADRs, policies, and active_releases -- not against opinions about how things should be.
7. **Severity must be justified.** HIGH = blocks execution or causes runtime failure. MEDIUM = creates tech debt or merge conflicts. LOW = cosmetic or minor consistency issue.
8. **Don't duplicate the codebase-auditor.** This skill checks a specific WP against the codebase. It does not audit the entire codebase. If a finding is about pre-existing codebase issues unrelated to the WP, note it as context but don't report it as a WP finding.
9. **Recommend but don't decide.** The skill labels resolution recommendations clearly. Decisions belong to the user or a governed decision step.