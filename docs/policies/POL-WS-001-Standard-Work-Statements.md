# POL-WS-001: Standard Work Statements

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-01-06 |
| **Applies To** | All human and AI contributors executing governed work in The Combine |
| **Related Artifacts** | ADRs, Governance Policies, Schemas, Work Statements |

---

## 1. Purpose

Standard Work Statements (WS) define how governed work is executed repeatedly, correctly, and without drift.

They translate architectural decisions (ADRs) and governance policies into explicit, mechanical execution procedures suitable for both human contributors and AI agents.

Work Statements exist to:

- Prevent interpretive or "creative" compliance
- Enable safe and repeatable delegation to AI
- Preserve architectural integrity during change
- Ensure auditability and consistent outcomes

---

## 2. When a Work Statement Is Required

A Work Statement **MUST** be used when any of the following apply:

- An ADR or policy is being applied to existing code or systems
- An ADR or policy is being applied to multiple surfaces or instances
- Execution is delegated to an AI agent
- Deviation would introduce architectural drift
- The work establishes or propagates a new architectural pattern

A Work Statement **MAY** be used for:

- Complex one-off changes
- High-risk or irreversible work
- Coordination across multiple components

A Work Statement is **NOT** required for:

- Pure analysis or exploration
- Drafting ADRs or policies
- Non-durable discussion

---

## 3. Relationship to ADRs and Policies

- **ADRs** define *what must be true*
- **Policies** define *how governance operates*
- **Work Statements** define *how work is executed*

Work Statements:

- **MUST** reference the governing ADRs, policies, and schemas
- **MUST NOT** reinterpret, extend, or override ADRs
- **MUST NOT** introduce new architectural decisions

If a governing ADR or policy is unclear, contradictory, or incomplete:

1. **STOP**
2. Escalate for clarification
3. Do not proceed until corrected

---

## 4. Required Structure of a Work Statement

Every Work Statement **MUST** include the following sections:

### Purpose
What work is being executed and why

### Governing References
ADRs, policies, schemas, and standards that control the work

### Verification Mode
`A` (all criteria verified) or `B` (declared exceptions)

### Allowed Paths
A list of file-path prefixes that define the containment boundary for this Work Statement. These prefixes are passed to Tier 0 as `--scope` arguments during WS execution (see Section 6).

Example:
```
## Allowed Paths
- ops/scripts/
- tests/infrastructure/
- docs/policies/
- CLAUDE.md
```

### Scope
Explicit statement of what is included and excluded

### Preconditions
Required artifacts, system state, approvals, or inputs

### Procedure
Step-by-step execution instructions

- Written to be followed mechanically
- No assumed knowledge
- No skipped or implicit steps

### Prohibited Actions
Actions that must not be taken (see Section 5)

### Verification Checklist
Objective checks to confirm correct execution

### Definition of Done
Conditions under which the work is considered complete

---

## 5. Prohibited Actions (Authoritative)

A Work Statement **MUST** explicitly list known prohibited actions relevant to the task.

In addition, **all prohibitions and constraints defined in governing ADRs, policies, schemas, and architectural rules are implicitly in force**, whether or not they are restated in the Work Statement.

Lack of explicit prohibition in a Work Statement does **not** grant permission to:

- Violate ADRs
- Violate governance policies
- Breach architectural boundaries
- Circumvent quality gates
- Introduce implicit behavior, shortcuts, or assumptions

If a contributor believes an action is permitted due to omission:

1. **STOP**
2. Escalate for clarification
3. Do not proceed on assumption

---

## 6. Execution Rules

- Work Statements are executed **exactly as written**
- Steps must not be skipped, reordered, merged, optimized, or reinterpreted

If a step cannot be completed as written:

1. **STOP**
2. Escalate for revision or clarification

### Tier 0 Verification in WS Mode

When executing a Work Statement, Tier 0 **MUST** be invoked in WS mode with `--scope` prefixes derived from the Work Statement's `allowed_paths[]` field:

```bash
ops/scripts/tier0.sh --ws --scope <each allowed_paths prefix>
```

If Tier 0 is run in WS mode without `--scope`, it will **FAIL by design**. This prevents "false green" runs where scope was never validated.

### AI-Specific Rules

AI agents:

- Must treat Work Statements as authoritative instructions
- Must not infer missing steps
- Must not generalize beyond stated scope
- Must refuse execution if a required Work Statement is missing

---

## 7. Modification and Versioning

Work Statements are versioned artifacts.

Changes require:

- Explicit revision
- Documented rationale

Silent or informal edits are **prohibited**.

Superseded Work Statements must be clearly marked as such.

---

## 8. Acceptance and Closure

A Work Statement is considered complete only when:

- All procedural steps are executed
- All verification checklist items pass
- The Definition of Done is satisfied
- The outcome conforms to all governing ADRs and policies

Partial completion is **not acceptable** unless explicitly defined in the Work Statement.

---

## 9. Enforcement

Failure to use or comply with a required Work Statement constitutes:

- A governance violation
- Grounds for rejection of the work output

All contributors—human and AI—are held to the same standard.

---

## 10. Inclusion in AI Bootstrap

This policy is a **mandatory reference** in all AI bootstrap prompts.

AI agents must be instructed to:

- Request a Work Statement when required
- Refuse execution in its absence
- Halt execution upon ambiguity, contradiction, or missing governance

---

*End of Policy*