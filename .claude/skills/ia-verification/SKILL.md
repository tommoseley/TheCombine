---
name: ia-verification
description: Post-execution verification that implementation artifacts conform to their authoritative sources (WS specs, schema bundles, design system, governance policies). Mechanically checks structural compliance — not quality, not opinion. Output is a structured report with verdict COMPLIANT / NON-COMPLIANT / PARTIAL.
---

# IA Verification (Implementation-Authority Conformance)

This skill answers one question: **does what was built match what was specified?**

It runs after execution (WS completion, schema change, artifact modification) and mechanically verifies that implementation artifacts conform to their governing authoritative sources.

**Read-only only.** Never modify code, schemas, configs, or documents while running this skill.

---

## When to Use

Use this skill when:
- A WS has been executed and CC reports "done"
- An authoritative source has changed (schema version bump, ADR revision, design system update)
- Before accepting a WP as complete
- When verifying that existing artifacts still conform after upstream changes
- Before any promotion gate (WS -> done, WP -> done)

---

## Inputs Required

1) **Artifact(s)** to verify -- file paths of what was built/modified
2) **Authoritative source(s)** -- the WS, schema bundle, ADR, policy, or design system spec that governs the artifact
3) Repo access (read-only)

If artifacts are not explicitly listed, infer from the WS `allowed_paths` and execution steps.

---

## Output Location

Write report to:

`docs/audits/YYYY-MM-DD-ia-verification-{WS-ID or WP-ID}.md`
---

# Phase 0 -- Build Conformance Map (Mechanical)

Before any verification, build a map of artifact -> authority relationships.

Extract from the WS/WP:
- File paths created or modified (the artifacts)
- Schema bundle referenced (the shape authority)
- WS execution steps (the behavior authority)
- ADR/policy refs (the governance authority)
- Design system refs (the UX authority, if applicable)
- Verification criteria stated in the WS

Produce a conformance map:

```
artifact: app/domain/services/wp_promotion_service.py
authorities:
  - WS-WB-004 (execution steps, acceptance criteria)
  - WP-WB-001-schemas.json (work_package_v1_1_0 schema)
  - ADR-010 (audit logging requirement)
```

If the WS lacks enough structure to build this map, flag as **Phase 0 FAIL**:
- "Cannot verify: insufficient authority references in WS"

---

# Phase 1 -- Schema Conformance (Mechanical PASS/FAIL)

These checks are binary. No judgment calls.

## 1.1 Schema Shape Compliance

For every schema governing a verified artifact:

1. **Load the schema JSON.** Extract `required[]` and all `properties{}` keys at every nesting level. Also note `additionalProperties`, `enum`, `const`, `type`, and conditional (`if/then`) constraints. Resolve all `$ref` references to their `definitions` entries.
2. **Load the artifact JSON** (the actual persisted document or document content).
3. **Verify schema version/`$id`** — does the implementation reference the correct schema version?
4. **Perform a bidirectional field diff:**

   **a) REQUIRED FIELD CHECK:**
   For each field in schema `required[]`:
   - Is the field present in the document? If NO → **FAIL** (missing required field)
   - Is the field non-null and non-empty? If null/empty and schema does not allow null → **FAIL**
   - Is the field the correct type per schema `type`? If NO → **FAIL**
   - If schema specifies `enum` or `const`, is the value in the allowed set? If NO → **FAIL**

   **b) OPTIONAL FIELD CHECK:**
   For each field in schema `properties{}` that is NOT in `required[]`:
   - Is the field present in the document? If NO → **finding** (LOW: optional field absent)
   - If present, is the type correct? If NO → **FAIL**

   **c) UNDECLARED FIELD CHECK:**
   For each field in the document at this nesting level:
   - Is the field declared in schema `properties{}`? If NO → **finding** (MEDIUM: undeclared field — potential `additionalProperties` violation)
   - If schema has `"additionalProperties": false` and field is undeclared → **FAIL**

   **d) NESTED OBJECT CHECK:**
   For each field that is type `"object"` with its own `properties{}` and/or `required[]`:
   - Recurse steps a-c into the nested schema definition
   For each field that is type `"array"` with `items` containing `properties{}` (or `items` with `$ref`):
   - Verify at least one array element exists (if schema has `minItems >= 1`)
   - Recurse steps a-c into the items schema for each element (sample first element if array is large)
   For `$ref` references:
   - Resolve the `$ref` to its `definitions` entry and recurse

   **e) CONDITIONAL CHECK:**
   If schema has `if/then/else` blocks:
   - Identify which condition branch applies to the document
   - Verify the corresponding `then` or `else` constraints are satisfied

5. **Report format per field:**
   - Field path (dot notation, e.g., `plan_summary.overall_intent`)
   - Schema requirement (required/optional)
   - Document state (present/absent/null/wrong-type/wrong-value)
   - Verdict (PASS/FAIL/finding with severity)

**FAIL if any required field is missing, any type is wrong, any enum/const is violated, or any `additionalProperties: false` constraint is breached.**

## 1.2 Registry Alignment

If the WS modified active_releases.json or registry entries:
- Do registered doc_type_ids match what the WS specified?
- Do schema paths point to files that exist?
- Do handler references resolve to actual classes?
- Are version strings consistent between registry and schema `$id`?

FAIL if registry state doesn't match WS specification.

## 1.3 API Surface Compliance

If the WS specified API endpoints:
- Do the routes exist in the router?
- Are HTTP methods correct?
- Do request/response shapes match the schema?
- Are error codes as specified?
- Is route registration wired (included in `__init__.py` or equivalent)?

FAIL if any specified endpoint is missing, wrong method, or unregistered.

## 1.4 File Inventory Check

For every file the WS said should be created or modified:
- Does the file exist?
- Is it in the correct location (matches allowed_paths)?
- If created: was it not pre-existing before the WS executed?
- If modified: has it actually changed?

FAIL if files are missing or misplaced.

## 1.5 Test Coverage Compliance

If the WS specified test requirements:
- Do test files exist for the specified artifacts?
- Do test names/descriptions cover the acceptance criteria stated in the WS?
- Do tests actually import/exercise the artifact under test?

FAIL if specified test coverage is absent.

## 1.6 Governance Compliance

For each governance requirement stated in the WS or governing ADRs:
- Are audit events written for every mutation? (ADR-010)
- Is provenance captured on writes? (generated_by, source_inputs, actor)
- Are invariants mechanically enforced? (not just documented)
- Are prohibited actions actually prevented? (return 400/422, not just unchecked)

FAIL if a stated governance requirement has no mechanical enforcement.

---

# Phase 2 -- Behavioral Conformance (LLM-assisted)

These are judgment checks that require reading code and comparing to spec.

Each produces a finding with:
- severity: HIGH / MEDIUM / LOW
- evidence: specific files/lines/functions
- authority reference: which WS step or acceptance criterion

## 2.1 Acceptance Criteria Traceability

For each acceptance criterion in the WS:
- Is there a concrete implementation that satisfies it?
- Is there a test that verifies it?
- Is the criterion fully met, partially met, or unaddressed?

HIGH if any acceptance criterion has no implementation or test.

## 2.2 Prohibited Action Enforcement

For each item in the WS "Prohibited" section:
- Is the prohibition mechanically enforced?
- Or is it merely "not done" (absence != enforcement)?

MEDIUM if prohibition relies on convention rather than code.

## 2.3 Plane Separation (if applicable)

If the WS specifies separation boundaries (e.g., "WS endpoints cannot mutate WP fields"):
- Are boundaries enforced with explicit validation/rejection?
- Or could a malformed request cross the boundary?

HIGH if boundary exists in spec but not in code.

## 2.4 Design System Compliance (if applicable)

If the WS references design system specs:
- Are specified components/tokens/patterns used?
- Are prohibited UX patterns absent? (modals, animations, auto-save)
- Do component names match convention?

MEDIUM unless a prohibited pattern is present (then HIGH).

## 2.5 Specification Drift

Compare what was built to what was specified, looking for:
- Extra functionality not in the WS (scope creep)
- Missing functionality that was in the WS (incomplete)
- Renamed concepts (WS says "promote", code says "convert")
- Structural choices that diverge from the WS approach

MEDIUM for scope creep. HIGH for missing functionality.

---

# Phase 3 -- Findings (Required for every non-PASS)

Each finding must include:

**Evidence:** Specific file paths, line numbers, function names
**Authority:** The WS step, acceptance criterion, or governance rule that governs it
**Gap:** What the authority requires vs. what was implemented
**Severity:** HIGH (blocks acceptance) / MEDIUM (technical debt) / LOW (minor inconsistency)
**Fix:** Concrete action to bring into compliance (file, change, effort)

Rules:
- Every finding must cite both the artifact AND the authority
- "Looks wrong" is not a finding. Cite the specific requirement it violates.
- Scope creep is a finding, not a feature. If it wasn't in the WS, flag it.
- Do not invent requirements. Only verify what the WS/schema/ADR actually states.

---

# Verdict Rules

- **COMPLIANT**: Phase 1 all PASS + no HIGH findings in Phase 2
- **PARTIAL**: Phase 1 all PASS + HIGH findings exist but are isolated to specific acceptance criteria (core functionality works, gaps are enumerable)
- **NON-COMPLIANT**: Any Phase 1 FAIL OR systemic HIGH findings indicating the implementation doesn't match the specification

---

# Report Format (Required)

```markdown
# IA Verification -- {WS-ID or WP-ID}: {Title}

**Date:** YYYY-MM-DD
**Artifacts Verified:** {count}
**Authoritative Sources:** {list}
**Codebase Branch:** {branch name}

---

## Phase 0: Conformance Map

{Structured artifact -> authority mapping}

---

## Phase 1: Structural Conformance

| Check | Result | Details |
|-------|--------|---------|
| 1.1 Schema Shape | PASS/FAIL | {summary} |
| 1.2 Registry Alignment | PASS/FAIL | {summary} |
| 1.3 API Surface | PASS/FAIL | {summary} |
| 1.4 File Inventory | PASS/FAIL | {summary} |
| 1.5 Test Coverage | PASS/FAIL | {summary} |
| 1.6 Governance | PASS/FAIL | {summary} |

**Structural Result:** {PASS | FAIL -- N issues}

---

## Phase 2: Behavioral Conformance

| Check | Severity | Finding |
|-------|----------|---------|
| 2.1 Acceptance Criteria | -- / HIGH / MEDIUM / LOW | {summary} |
| 2.2 Prohibited Actions | -- / HIGH / MEDIUM / LOW | {summary} |
| 2.3 Plane Separation | -- / HIGH / MEDIUM / LOW | {summary} |
| 2.4 Design System | -- / HIGH / MEDIUM / LOW | {summary} |
| 2.5 Specification Drift | -- / HIGH / MEDIUM / LOW | {summary} |

**Behavioral Result:** {N HIGH, N MEDIUM, N LOW findings}

---

## Findings

### Finding {N}: {Title}

**Severity:** HIGH | MEDIUM | LOW
**Artifact:** {file path + line/function}
**Authority:** {WS step / acceptance criterion / ADR / schema path}
**Gap:** {What authority requires vs. what exists}
**Fix:** {Concrete action, file, effort}

---

## Summary

**Verdict:** COMPLIANT | PARTIAL | NON-COMPLIANT

**Blocking (must fix before acceptance):**
- {HIGH findings}

**Gaps (should fix, tracked as debt):**
- {MEDIUM findings}

**Minor (cosmetic/consistency):**
- {LOW findings}

**Acceptance Criteria Coverage:**
| Criterion | Status |
|-----------|--------|
| {AC from WS} | MET / PARTIAL / UNMET |
```

---

# Quick Commands (Optional Helpers)

```bash
# Find all files created/modified by a WS (compare git diff)
git diff --name-only HEAD~N

# Check schema $id in implementation
grep -rn '$id\|schema_id\|schema_version' app/domain/

# Find audit event writes
grep -rn 'audit_event\|write_audit\|log_event' app/

# Check route registration
grep -rn 'router\.\(get\|post\|put\|patch\|delete\)' app/api/

# Find test files for a module
find tests/ -name "*test*" | grep -i {module_name}

# Verify schema fields against implementation
python3 -c "
import json
schema = json.load(open('path/to/schema.json'))
props = schema.get('properties', {})
print('\n'.join(sorted(props.keys())))
"
```

Do not perform mutations, formatting, or auto-fixes during verification.

---

# Rules

1. **Read-only.** Never modify code, schemas, or documents during verification.
2. **Evidence required.** Every finding must cite specific artifacts AND specific authority references.
3. **No invented requirements.** Only verify what the WS/schema/ADR actually states. Do not add your own expectations.
4. **Verify both directions.** Check for missing implementation (under-build) AND extra implementation (over-build/scope creep).
5. **Run from repo root.** All paths relative to project root.
6. **Severity must be justified.** HIGH = blocks acceptance or violates governance. MEDIUM = debt or incomplete coverage. LOW = cosmetic or naming.
7. **Scope creep is a finding.** If code exists that no WS specified, flag it. Useful code that wasn't governed is still ungoverned code.
8. **Absence != enforcement.** A prohibition that isn't mechanically enforced is not met just because no one violated it yet.
9. **This is conformance, not review.** Do not evaluate code quality, performance, or style. Only evaluate: does it match what was specified?
