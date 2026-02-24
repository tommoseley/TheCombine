---
name: combine-governance
description: Enforce governance policies for ADRs, Work Statements, and Work Packages. Use when creating WS/WP documents, checking ADR execution authorization, or applying ADR-045 taxonomy.
---

# Combine Governance

## POL-ADR-EXEC-001: ADR Execution Authorization

Per POL-ADR-EXEC-001, AI agents MUST:

1. **Recognize ADR states**: Architectural status (Draft/Accepted/Deprecated/Superseded) is independent of execution state (null/authorized/active/complete)
2. **Assess scope**: Determine if work is single-commit or multi-commit
3. **Follow the appropriate path**:
   - **Single-commit:** Work Statement -> Acceptance -> Execute
   - **Multi-commit:** Implementation Plan -> Acceptance -> Work Statement(s) -> Acceptance -> Execute
4. **Declare scope explicitly**: The expected scope MUST be stated in the Work Statement or Implementation Plan
5. **Escalate if scope grows**: If single-commit work expands, STOP and draft an Implementation Plan
6. **Refuse unauthorized execution**: Do NOT begin execution without explicit Work Statement acceptance

**Key principle:** ADR acceptance does NOT authorize execution. Execution requires completing the appropriate authorization path.

## Work Statement Structure (POL-WS-001)

Every WS document follows this structure:

```markdown
# WS-<ID>: Title

## Status: Draft | Accepted | Executing | Complete | Rejected

## Governing References
- List of ADRs, policies, parent WPs

## Verification Mode: A | B

## Allowed Paths
- List of filesystem paths this WS may modify

## Objective
## Preconditions
## Scope (In Scope / Out of Scope)
## Tier 1 Verification Criteria
## Procedure (Phase 1: Tests / Phase 2: Implement / Phase 3: Verify)
## Prohibited Actions
## Verification Checklist
```

## Work Package Structure

Work Packages group related Work Statements:

```markdown
# WP-<ID>: Title

## Work Statements
| WS | Title | Status | Dependencies |
|----|-------|--------|--------------|
| WS-001 | ... | Draft | None |
| WS-002 | ... | Draft | WS-001 |

## Dependency Chain
WS-001 -> WS-002 (sequential)
WS-003, WS-004 (parallel, no overlap)
```

## ADR-045 Taxonomy Reference

**Primitives** (authorable and governable in isolation):
- **Prompt Fragment**: Shapes behavior (role prompts, task prompts, QA prompts, PGC context)
- **Schema**: Defines acceptability (JSON Schema for output validation)

**Ontological term** (vocabulary, not configuration):
- **Interaction Pass**: Names what a DCW node is — the binding of prompt fragments + schema at execution time

**Composites** (assemble primitives for a purpose):
- **Role**: Identity + constraints (assembles prompt fragments)
- **Task**: Work unit within a DCW node (prompt fragment + schema reference)
- **DCW** (Document Creation Workflow): Graph of nodes producing one stabilized document
- **POW** (Project Orchestration Workflow): Sequence of steps, each invoking a DCW

**Core principle**: Prompt Fragments shape behavior; Schemas define acceptability; Interaction Passes bind and execute both.
