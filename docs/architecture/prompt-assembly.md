# Prompt Assembly System

_Architecture reference for ADR-041_

---

## The Problem It Solves

Today, prompts are **monolithic files** - a single 200-line prompt contains:
- Generic rules (same for all document types)
- Document-specific context (unique per type)
- Schema definitions (duplicated from validation files)

When you change a rule, you touch 10 files. When schemas drift, you get validation/prompt mismatches.

---

## The Solution: Assembled Prompts

Instead of one big file, you have:

```
Template (generic)     +    Context (specific)    +    Schema (authoritative)
         |                        |                          |
    $$PGC_CONTEXT    ->    project_discovery.v1.txt
    $$OUTPUT_SCHEMA  ->    clarification_question_set.v2.json
```

The **workflow plan** says which pieces go together.

---

## Concrete Example

**1. Generic Template** (`seed/prompts/tasks/Clarification Questions Generator v1.0.txt`)

```
# Clarification Questions Generator

You are operating under a certified role prompt.

---

$$PGC_CONTEXT

---

## Output Schema

$$OUTPUT_SCHEMA

## Prohibited Language
- Never say "I recommend"
- Never ask about budget
...
```

**2. Context File** (`seed/prompts/pgc-contexts/project_discovery.v1.txt`)

```
## Context Block

Next Document: Project Discovery Document

Purpose: Explore solution space, validate assumptions...

Questions Asked Here Must:
- Affect how discovery is run
- Change what discovery needs to explore
```

**3. Workflow Node** (`seed/workflows/pm_discovery.v1.json`)

```json
{
  "node_id": "pgc",
  "type": "pgc",
  "task_ref": "Clarification Questions Generator v1.0",
  "includes": {
    "PGC_CONTEXT": "seed/prompts/pgc-contexts/project_discovery.v1.txt",
    "OUTPUT_SCHEMA": "seed/schemas/clarification_question_set.v2.json"
  }
}
```

**4. Assembly** (what `PromptAssembler.assemble()` does)

```python
# 1. Load template
template = load("Clarification Questions Generator v1.0.txt")

# 2. Find $$PGC_CONTEXT, look up in includes map
#    includes["PGC_CONTEXT"] = "seed/prompts/pgc-contexts/project_discovery.v1.txt"
#    Load that file, replace the token

# 3. Find $$OUTPUT_SCHEMA, look up in includes map
#    includes["OUTPUT_SCHEMA"] = "seed/schemas/clarification_question_set.v2.json"
#    Load that file, replace the token

# 4. Compute SHA-256 hash of final assembled prompt

# 5. Return AssembledPrompt with content + hash + metadata
```

**5. Result** (what gets sent to LLM)

```
# Clarification Questions Generator

You are operating under a certified role prompt.

---

## Context Block

Next Document: Project Discovery Document

Purpose: Explore solution space, validate assumptions...

Questions Asked Here Must:
- Affect how discovery is run
- Change what discovery needs to explore

---

## Output Schema

{"$schema": "...", "type": "object", "properties": {...}}

## Prohibited Language
- Never say "I recommend"
- Never ask about budget
...
```

---

## The Two Token Types

| Type | Syntax | Resolved From | Use Case |
|------|--------|---------------|----------|
| **Workflow Token** | `$$PGC_CONTEXT` | Workflow's `includes` map | Context that varies by workflow |
| **Template Include** | `$$include seed/shared/rules.txt` | File path directly | Shared content across all workflows |

Workflow Tokens let the same template serve different document types:
- `pm_discovery.v1.json` uses `project_discovery.v1.txt`
- `technical_arch.v1.json` uses `technical_architecture.v1.txt`

Same template, different contexts.

---

## Why the Invariants Matter

**Determinism** (same inputs -> byte-identical output):
- Enables replay: re-run with same inputs, get same prompt
- Hash verification: if hashes match, prompts are identical

**Ordering** (lexical order preserved):
- `$$TOKEN_A` before `$$TOKEN_B` in template -> resolved in that order
- No surprises, no "optimization"

**Static Content** (no runtime generation):
- Includes come from versioned files on disk
- Not from database, not from LLM, not from user input
- This keeps assembly auditable and replayable

---

## The Encoding Rule

All files loaded as UTF-8. All `\r\n` converted to `\n`. Hash computed on normalized bytes.

Without this, the same prompt on Windows vs Linux produces different hashes.

---

## What Gets Logged (per ADR-010)

```json
{
  "task_ref": "Clarification Questions Generator v1.0",
  "includes_resolved": {
    "PGC_CONTEXT": "seed/prompts/pgc-contexts/project_discovery.v1.txt",
    "OUTPUT_SCHEMA": "seed/schemas/clarification_question_set.v2.json"
  },
  "assembled_prompt": "# Clarification Questions Generator\n\nYou are...",
  "assembled_prompt_hash": "a1b2c3d4e5f6...",
  "assembly_timestamp": "2026-01-22T15:30:00Z",
  "correlation_id": "uuid-here"
}
```

You can reconstruct exactly what prompt was sent, verify the hash, replay if needed.

---

## The CI Guardrail

On every push to `seed/prompts/**` or `seed/workflows/**`:

```
CI runs compile_prompts.py
    |
For each workflow node with task_ref:
    - Load template
    - Resolve all tokens from includes
    - If any fail -> BUILD BREAKS
    |
Output compiled prompts to build/prompts/ (artifact, not committed)
```

Drift becomes a build failure, not a production surprise.

---

## What This Does Not Do

- **No conditional logic**: Cannot do `$$if CONDITION then X else Y`. Use workflow routing instead.
- **No parameters**: Cannot do `$$CONTEXT(param=value)`. Make separate context files.
- **No recursion**: Includes cannot contain tokens. Single-pass assembly only.
- **No runtime content**: Cannot inject LLM output or database results via includes. Use the standard context input mechanism for that.

---

## References

- [ADR-041: Prompt Template Include System](../adr/041-prompt-template-includes/ADR-041-Prompt-Template-Includes.md)
- [ADR-010: LLM Execution Logging](../adr/010-llm-execution-logging/)
- [WS-ADR-041-001: Implementation Work Statement](../work-statements/WS-ADR-041-001.md)

---

_Last updated: 2026-01-22_