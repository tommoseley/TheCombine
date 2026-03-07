# POL-CODE-001: Code Construction Standard

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-03-06 |
| **Applies To** | All human and AI contributors writing or modifying code in The Combine |
| **Related Artifacts** | CLAUDE.md (Reuse-First Rule, Execution Constraints), ADR-045 (System Ontology), ADR-057 (Ontology) |

---

## 1. Purpose

This policy formalizes the code construction rules that govern how code is written, extended, and maintained in The Combine. These rules ensure consistency, reuse, testability, and terminological precision across the codebase.

---

## 2. Reuse-First Rule

Before creating anything new (file, module, schema, service, prompt):

1. **Search** the codebase and existing docs/ADRs.
2. **Prefer** extending or refactoring over creating.
3. **Create new** only when reuse is not viable.

### Constraints

- If you create something new, you MUST be able to justify why reuse was not appropriate.
- Creating something new when a suitable existing artifact exists is a defect.

*Source: CLAUDE.md "Reuse-First Rule"*

---

## 3. Complexity Management

### CRAP Score Thresholds

- Functions exceeding CRAP score > 30 are flagged as critical and require remediation.
- Remediation path: decompose into focused sub-methods (cyclomatic complexity reduction), add test coverage (coverage increase), or both.

### Structural Rules

- No god functions: business logic MUST be modular and testable.
- Mechanical/deterministic checks are preferred over LLM-based validation wherever possible.
- Make every change as simple as possible. Find root causes, not symptoms.
- No temporary fixes. No "we'll clean this up later" without a tech debt entry.
- Changes should only touch what is necessary.

*Source: WP-CRAP-001/002 practices, CLAUDE.md "Planning Discipline - Simplicity First"*

---

## 4. Ontology Compliance

Per ADR-045 and ADR-057, terminological precision is mandatory:

- **One meaning per term, system-wide.** No synonyms in code.
- **Registration before use:** Check the ontology before naming columns, fields, classes, or parameters.
- **Use registered terms:** Code identifiers MUST use registered terms, not alternatives.
- Prose documentation may use natural language; code MUST NOT.

### ADR-045 Taxonomy

| Category | Examples |
|----------|----------|
| **Primitives** | Prompt Fragment, Schema |
| **Composites** | Role, Task, DCW, POW |
| **Ontological terms** | Interaction Pass |

Core principle: Prompt Fragments shape behavior; Schemas define acceptability; Interaction Passes bind and execute both.

*Source: CLAUDE.md "ADR-045 Taxonomy Reference", ADR-057*

---

## 5. Code Style

- **Explicit dependencies:** All imports and dependencies MUST be declared.
- **Readability over cleverness:** Favor clarity and maintainability.
- **No silent failures:** Errors MUST be surfaced, not swallowed.
- **No black boxes:** If a step does something non-trivial, it must show its passes (ADR-049). "Generate" is deprecated as a step abstraction.

*Source: CLAUDE.md "Execution Constraints" (ADR-049), "Non-Negotiables"*

---

## 6. Prompt and Seed Governance

Prompts are governed inputs, not documentation:

- Prompts live in `seed/prompts/` and are versioned, certified, hashed, and logged.
- Do NOT merge role logic into task prompts.
- Do NOT edit prompts without a version bump.
- Prompt changes require: explicit intent, version bump, re-certification, manifest regeneration.

*Source: CLAUDE.md "Seed Governance", "Non-Negotiables"*

---

## 7. Governance Boundary

This policy formalizes rules already enforced through CLAUDE.md, ADR-045, ADR-049, ADR-057, and established CRAP score audit practices. It does not introduce new rules or enforcement mechanisms. Mechanical enforcement is out of scope and deferred to future quality gate work.

---

*End of Policy*
