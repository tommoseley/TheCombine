# ADR-041: Prompt Template Include System

**Status:** Accepted
**Date:** 2026-01-22
**Decision Type:** Architectural

**Related ADRs:**
- ADR-010 - LLM Execution Logging
- ADR-012 - Interaction Model (PGC Amendment)
- ADR-027 - Workflow Definition and Governance
- ADR-038 - Workflow Plan Schema
- ADR-040 - Stateless LLM Execution Invariant

---

## 1. Decision Summary

Establish a token-based include system for prompt assembly that separates generic prompt templates from context-specific content, with workflow plans as the authority for what gets included.

**Core Principle:** Prompts are assembled, not monolithic.

---

## 2. Problem Statement

Current state:
- Task prompts contain both generic rules and document-specific context
- The same boilerplate (prohibited language, schema references, audit constraints) is duplicated across prompts
- Schema definitions appear in two places: validation files and inline in prompts
- When rules change, every prompt must be updated
- Document-specific context is buried in large prompt files

This creates:
- **Drift risk** - Prompts diverge over time
- **Maintenance burden** - Updates require touching many files
- **Single source of truth violations** - Schema in prompt vs. schema in validation file
- **Poor auditability** - Hard to see what context a prompt receives

---

## 3. Decision

### 3.1 Token Syntax

Two token types for prompt templates:

| Token Type | Syntax | Meaning |
|------------|--------|---------|
| **Workflow Token** | `$$SECTION_NAME` | Replaced with content from workflow node's `includes` map |
| **Template Include** | `$$include <path>` | Replaced with file contents from specified path |

**Terminology:**
- **Workflow Tokens** - Dynamic references resolved via workflow plan's `includes` map
- **Template Includes** - Static references resolved directly from file paths

**Token rules:**
- Tokens must appear on their own line
- Section names are UPPER_SNAKE_CASE
- Paths are relative to repository root
- Unresolved tokens cause assembly failure (no silent pass-through)

### 3.2 Workflow-Driven Includes

Workflow plan nodes declare what gets included:

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

**The workflow plan is the authority** for prompt assembly. This makes dependencies explicit and auditable.
### 3.3 Assembly Process

1. Load task prompt by `task_ref`
2. Scan for Workflow Tokens (`$$SECTION_NAME`) in lexical order
3. For each token, look up path in node's `includes` map
4. If not found, fail with explicit error
5. Load referenced file
6. Replace token with file contents
7. Scan for Template Includes (`$$include <path>`) in lexical order
8. Replace with file contents
9. Validate no unresolved tokens remain
10. Compute SHA-256 hash of assembled prompt
11. Log assembled prompt with hash
12. Execute assembled prompt

**Invariants:**

| Invariant | Requirement |
|-----------|-------------|
| **Determinism** | Given the same template, include files, and workflow plan, the assembled prompt MUST be byte-identical |
| **Ordering** | Token resolution preserves lexical order as tokens appear in template. No reordering, deduplication, or normalization is permitted |
| **Static Content** | Include content MUST be static, versioned artifacts resolved at assembly time. Runtime-generated strings MUST NOT be injected via includes |

### 3.4 Directory Structure

```
seed/prompts/
  tasks/
    Clarification Questions Generator v1.0.txt   # Generic template
    Document Generation v1.0.txt                 # Generic template
    
  pgc-contexts/                                  # PGC-specific contexts
    project_discovery.v1.txt
    technical_architecture.v1.txt
    epic_backlog.v1.txt
    
  generation-contexts/                           # Generation-specific contexts
    project_discovery.v1.txt
    technical_architecture.v1.txt

seed/schemas/
  clarification_question_set.v2.json            # Used for validation AND injection
  project_discovery.v1.json
  technical_architecture.v1.json
```

---

## 4. Example: PGC Prompt Assembly

### 4.1 Generic Template

File: `seed/prompts/tasks/Clarification Questions Generator v1.0.txt`

```
# Clarification Questions Generator - Canonical Task Prompt v1.0

## Triggering Instruction

You are operating under a **certified role prompt**.
This task prompt defines **only the current task**.

---

$$PGC_CONTEXT

---

## Mode

`questions_only`

## Required Behavior
...

## Prohibited Language (Strict)
...

## Prohibited Topics (Strict)
...

## Output Schema Reference

Your output must conform to the following schema:

$$OUTPUT_SCHEMA

## Failure Conditions (Automatic Reject)
...
```

### 4.2 Context File

File: `seed/prompts/pgc-contexts/project_discovery.v1.txt`

```
## Replaceable Context Block (Authoritative)

Next Document: Project Discovery Document

Purpose of This Document:
To explore solution space, validate assumptions, identify risks, and define scope 
and constraints - without committing to architecture or implementation.

What This Document Assumes Is Already True:
* The problem statement is correct
* The project intent is valid
* The project type (greenfield, enhancement, etc.) is correct

This Clarification Step Exists To Prevent:
* Starting discovery under the wrong framing
* Discovering too late that the scope category is incorrect
* Producing a discovery document that answers the wrong questions

Questions Asked Here Must:
* Affect how discovery is run
* Change what discovery needs to explore
* Or determine whether discovery should proceed as planned
```

### 4.3 Workflow Node

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

### 4.4 Assembled Result

The engine produces a single prompt with:
- Generic rules from template
- Project Discovery context block inserted at `$$PGC_CONTEXT`
- Full JSON schema inserted at `$$OUTPUT_SCHEMA`
---

## 5. Benefits

| Benefit | Explanation |
|---------|-------------|
| **Single source of truth** | Schema file used for validation AND prompt injection |
| **Workflow as authority** | Node config declares all dependencies explicitly |
| **Generic prompts** | Same template for all document types |
| **Small context files** | Easy to review, audit, version |
| **Auditable assembly** | Workflow plan shows exactly what gets assembled |
| **Reduced drift** | Change rule once, applies everywhere |
| **Testable** | Can validate assembly before execution |

---

## 6. Constraints

### 6.1 Token Resolution

- All `$$SECTION_NAME` tokens MUST resolve via workflow `includes`
- All `$$include <path>` tokens MUST resolve to existing files
- Unresolved tokens MUST cause explicit failure
- No partial assembly - all or nothing

### 6.2 File Requirements

- Include files MUST be UTF-8 encoded (no BOM)
- Include files MUST NOT contain unresolved tokens (no nested dynamic tokens)
- Template Include paths MUST be relative to repository root
- Files MUST exist at assembly time
- Files MUST be static, versioned artifacts (not generated at runtime)
- File content MUST be deterministic (no timestamps, random values, etc.)

### 6.3 Workflow Requirements

- `includes` map is OPTIONAL on nodes
- If template contains tokens, corresponding `includes` MUST be provided
- `includes` keys MUST match token names exactly (case-sensitive)

---

## 7. Logging and Audit

Per ADR-010, LLM execution logs MUST capture:

| Field | Content |
|-------|---------|
| `task_ref` | Original template reference |
| `includes_resolved` | Map of token name to file path |
| `assembled_prompt` | Full prompt after assembly |
| `assembled_prompt_hash` | SHA-256 hash of assembled prompt (for replay verification) |
| `assembly_timestamp` | When assembly occurred |

**Hash Requirements:**
- Hash computed on final assembled string (UTF-8 bytes)
- Hash enables replay verification: same inputs produce same hash
- Hash stored for audit comparison across executions

This ensures:
- Replay capability with exact prompt
- Byte-level verification of assembly determinism
- Audit trail of what content was included
- Debugging when prompts produce unexpected results

---

## 8. Relationship to Other ADRs

| ADR | Relationship |
|-----|--------------|
| ADR-010 | Assembled prompt + hash logged for audit/replay |
| ADR-012 | PGC prompts use this system |
| ADR-027 | Workflow governs which includes are used |
| ADR-038 | Workflow plan schema extended with `includes` |
| ADR-040 | Assembled prompt is stateless context; runtime content prohibited in includes |

**Key Alignment:**

- **ADR-040 (Stateless Execution):** Include content is static. Dynamic/runtime content passes via context inputs, not includes. This maintains the stateless execution invariant.
- **ADR-010 (LLM Logging):** The `assembled_prompt_hash` field enables byte-level replay verification. Same inputs must produce same hash.

---

## 9. Migration Path

### Phase 1: Infrastructure
- Implement token scanner in prompt loader
- Add `includes` support to workflow plan schema
- Add assembly logging

### Phase 2: PGC Prompts
- Extract `Project Discovery Questions v1.0.txt` context block
- Create `seed/prompts/pgc-contexts/project_discovery.v1.txt`
- Create generic `Clarification Questions Generator v1.0.txt`
- Update `pm_discovery.v1.json` workflow with includes

### Phase 3: Generation Prompts
- Apply same pattern to generation prompts
- Extract document-specific context blocks
- Create generic generation templates

### Phase 4: Deprecate Monolithic Prompts
- Mark old prompts as deprecated
- Remove after all workflows migrated
---

## 10. Implementation Notes

### 10.1 PromptAssembler Class

```python
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from uuid import UUID


@dataclass
class AssembledPrompt:
    """Immutable assembled prompt artifact."""
    content: str
    content_hash: str  # SHA-256
    task_ref: str
    includes_resolved: Dict[str, str]
    assembled_at: datetime
    correlation_id: UUID


class PromptAssembler:
    """Assembles prompts from templates and includes.
    
    Assembly is deterministic: same inputs produce same output (byte-identical).
    """
    
    def assemble(
        self,
        task_ref: str,
        includes: Dict[str, str],
        correlation_id: UUID
    ) -> AssembledPrompt:
        """
        Load template, resolve tokens in lexical order, return assembled prompt.
        
        Raises:
            UnresolvedTokenError: If any token cannot be resolved
            IncludeNotFoundError: If referenced file doesn't exist
        """
        template = self._load_template(task_ref)
        resolved = self._resolve_workflow_tokens(template, includes)
        resolved = self._resolve_template_includes(resolved)
        self._validate_no_unresolved_tokens(resolved)
        
        content_hash = hashlib.sha256(resolved.encode('utf-8')).hexdigest()
        
        return AssembledPrompt(
            content=resolved,
            content_hash=content_hash,
            task_ref=task_ref,
            includes_resolved=includes,
            assembled_at=datetime.utcnow(),
            correlation_id=correlation_id
        )
```

### 10.2 Token Regex

```python
WORKFLOW_TOKEN_PATTERN = r'^\$\$([A-Z][A-Z0-9_]*)\s*$'
TEMPLATE_INCLUDE_PATTERN = r'^\$\$include\s+(.+)\s*$'
```

---

## 11. Out of Scope (Explicit Prohibitions)

The following are **explicitly prohibited**, not merely deferred:

| Feature | Prohibition Reason |
|---------|-------------------|
| Conditional includes (if/else) | Breaks determinism; use workflow routing instead |
| Parameterized includes | Breaks static resolution; use separate context files |
| Recursive includes | Breaks single-pass assembly; increases complexity |
| Runtime-generated content | Breaks auditability; violates ADR-040 stateless execution |

**Runtime-Generated Content Prohibition (Explicit):**

Include content MUST be static, versioned artifacts that exist on disk at assembly time. The following are NOT permitted as include sources:

- LLM-generated strings
- Database query results
- API responses
- User input
- Computed values

If dynamic content is needed in a prompt, it MUST be passed via the standard context/input mechanism (per ADR-040), NOT via the include system.

This prohibition preserves:
- Audit trail integrity
- Replay determinism
- Assembly as a purely mechanical operation
---

## 11a. Canonical Encoding Rules (Locked)

To ensure deterministic assembly across platforms:

| Rule | Specification |
|------|---------------|
| **Encoding** | All files loaded as UTF-8 (no BOM) |
| **Newlines** | Convert CRLF to LF on read for all prompt assets |
| **Final Output** | Assembled prompt uses LF only |
| **Hash Input** | Hash computed on canonicalized UTF-8 bytes |

**Rationale:** Without this, Windows vs Mac/Linux checkouts cause false diffs and hash mismatches.

---

## 11b. Test Plan

### A. Golden Prompt Assembly Tests (No LLM)

**Goal:** Prove determinism + token resolution + failure modes.

| Test Case | Input | Expected Result |
|-----------|-------|-----------------|
| **Happy path** | Template + workflow includes | Assembled prompt matches golden file byte-for-byte |
| **Unresolved Workflow Token** | Template with `$$MISSING_TOKEN` | `UnresolvedTokenError(token="MISSING_TOKEN")` |
| **Missing include file** | `includes.FOO` points to non-existent path | `IncludeNotFoundError(path="...")` |
| **Template Include missing** | `$$include seed/missing.txt` | `IncludeNotFoundError(path="seed/missing.txt")` |
| **Nested tokens in include** | Include file contains `$$NESTED` | `NestedTokenError` (prohibited per ADR-041) |
| **Non-UTF8 include** | Binary or invalid encoding | `EncodingError` |
| **CRLF normalization** | Include with CRLF | Normalized to LF, hash stable |

**Outputs to assert on success:**

```python
assert result.content == golden_file_content
assert result.content_hash == expected_sha256
assert result.includes_resolved == {"PGC_CONTEXT": "path/to/context.txt", ...}
assert result.assembly_timestamp is not None
assert result.task_ref == "Clarification Questions Generator v1.0"
assert result.correlation_id == input_correlation_id
```

### B. Workflow Schema Validation Tests

**Goal:** Prove "workflow is authority."

| Test Case | Expected Result |
|-----------|-----------------|
| Template has `$$PGC_CONTEXT`, workflow missing `includes.PGC_CONTEXT` | Schema validation fails |
| `includes.pgc_context` (wrong case) | Schema validation fails (case-sensitive) |
| `includes` references path outside allowed roots | Validation warning or fail (configurable) |
| Template has no tokens, workflow has empty `includes` | Valid |

### C. Log/Audit Contract Tests

**Goal:** Make replay defensible.

Assert that log record includes all required fields:

```python
def test_audit_log_contract(assembled_prompt, log_record):
    assert log_record["task_ref"] == assembled_prompt.task_ref
    assert log_record["includes_resolved"] == assembled_prompt.includes_resolved
    assert log_record["assembled_prompt_hash"] == assembled_prompt.content_hash
    assert log_record["assembled_prompt"] == assembled_prompt.content
    assert log_record["correlation_id"] == assembled_prompt.correlation_id
    assert "assembly_timestamp" in log_record
```

### D. Test Fixture Structure

```
tests/fixtures/adr041/
  templates/
    clarification_generator_v1.txt
    template_with_missing_token.txt
  includes/
    pgc_context_project_discovery_v1.txt
    clarification_schema_v2.json
    nested_tokens.txt
    non_utf8.bin
    crlf_file.txt
  expected/
    assembled_clarification_generator_project_discovery_v1.txt
    assembled_clarification_generator_project_discovery_v1.sha256
```
---

## 11c. CI Guardrail: Prompt Compile Job

**Goal:** Turn drift into a build break, not a production surprise.

### CI Job Definition

```yaml
name: Prompt Compile Check

on:
  push:
    paths:
      - 'seed/prompts/**'
      - 'seed/workflows/**'
      - 'seed/schemas/**'
  pull_request:
    paths:
      - 'seed/prompts/**'
      - 'seed/workflows/**'
      - 'seed/schemas/**'

jobs:
  compile-prompts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python -m ops.scripts.compile_prompts --output build/prompts/
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: compiled-prompts
          path: build/prompts/
          retention-days: 7
```

### Compile Script

```python
# ops/scripts/compile_prompts.py
"""Compile all workflow prompts to verify assembly succeeds."""

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

from app.domain.prompt.assembler import PromptAssembler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build/prompts"))
    parser.add_argument("--workflows", type=Path, default=Path("seed/workflows"))
    args = parser.parse_args()
    
    args.output.mkdir(parents=True, exist_ok=True)
    assembler = PromptAssembler()
    failures = []
    
    for workflow_file in args.workflows.glob("*.json"):
        workflow = json.loads(workflow_file.read_text())
        
        for node in workflow.get("nodes", []):
            if "task_ref" not in node:
                continue
            
            node_id = node["node_id"]
            task_ref = node["task_ref"]
            includes = node.get("includes", {})
            
            try:
                result = assembler.assemble(
                    task_ref=task_ref,
                    includes=includes,
                    correlation_id=uuid4()
                )
                
                output_file = args.output / f"{workflow_file.stem}_{node_id}.txt"
                output_file.write_text(result.content)
                
                hash_file = args.output / f"{workflow_file.stem}_{node_id}.sha256"
                hash_file.write_text(result.content_hash)
                
                print(f"OK  {workflow_file.name}:{node_id}")
                
            except Exception as e:
                failures.append((workflow_file.name, node_id, str(e)))
                print(f"ERR {workflow_file.name}:{node_id} - {e}")
    
    if failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### What This Catches

| Failure Mode | Detected At |
|--------------|-------------|
| Missing include file | CI build |
| Typo in token name | CI build |
| Workflow missing required `includes` | CI build |
| Include file deleted | CI build |
| Encoding issues | CI build |

**Key Principle:** Compiled prompts are NOT committed. They are build artifacts for inspection only. The source of truth remains the templates + includes + workflow plan.
---

## 12. Risks

| Risk | Mitigation |
|------|------------|
| Missing include file at runtime | Fail explicitly with clear error message |
| Token typo in template | Validation catches unresolved tokens |
| Workflow missing required includes | Schema validation on workflow plan |
| Include file has wrong encoding | Require UTF-8, validate on load |

---

## 13. Acceptance Criteria

### Implementation
- [ ] PromptAssembler implemented with canonical encoding (UTF-8, LF normalization)
- [ ] Workflow Tokens (`$$SECTION_NAME`) resolve from workflow includes
- [ ] Template Includes (`$$include <path>`) resolve from file system
- [ ] Unresolved tokens cause explicit failure (`UnresolvedTokenError`)
- [ ] Missing files cause explicit failure (`IncludeNotFoundError`)
- [ ] Nested tokens in includes cause explicit failure (`NestedTokenError`)
- [ ] SHA-256 hash computed and included in result
- [ ] Assembled prompt logged per ADR-010 with all required fields

### Testing
- [ ] Golden prompt assembly test passes (byte-identical match)
- [ ] All failure mode tests pass (7 cases per Section 11b.A)
- [ ] Workflow schema validation tests pass
- [ ] Log/audit contract tests pass
- [ ] Test fixtures created in `tests/fixtures/adr041/`

### CI/CD
- [ ] Prompt compile job added to CI
- [ ] All workflow prompts compile successfully
- [ ] Compiled prompts written to `build/prompts/` (not committed)

### Migration
- [ ] Workflow plan schema supports `includes` map
- [ ] At least one prompt converted to template pattern (PGC)

---

## See Also

- **[Prompt Assembly System](../../architecture/prompt-assembly.md)** - Plain-language explanation of how this works

---

## Closing Note

This ADR establishes prompts as **assembled artifacts** rather than monolithic files. The workflow plan becomes the manifest of what goes into each prompt, making the system more auditable, maintainable, and consistent.

The pattern applies to any prompt that has:
- Generic rules (same across document types)
- Document-specific context (varies per type)
- Schema references (should match validation schemas)

Over time, most task prompts should migrate to this pattern.

---

_Last reviewed: 2026-01-22_