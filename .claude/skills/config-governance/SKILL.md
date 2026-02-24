---
name: config-governance
description: Govern seed configuration, prompt versioning, and LLM execution invariants. Use when modifying seed/, prompts, combine-config, or enforcing ADR-040/ADR-049 rules.
---

# Configuration Governance

## Seed Governance

`seed/` contains governed inputs. Prompts are:
- **Versioned** (filename includes version)
- **Certified** (auditor prompts validate structure)
- **Hashed** (`seed/manifest.json` contains SHA-256 checksums)
- **Logged** (prompt content recorded on every LLM execution per ADR-010)

Prompts are **not edited casually**. Changes require:
1. Explicit intent
2. Version bump
3. Re-certification
4. Manifest regeneration

## Stateless LLM Execution Invariant (ADR-040)

IMPORTANT: The Combine is NOT a chat system.

When developing or modifying The Combine, you MUST treat all LLM execution as stateless with respect to conversation transcripts.

**No transcript replay — even within the same execution.**

Raw transcripts carry contamination: tone leakage, accidental capability claims, "as I said earlier" references, role confusion. Replaying transcripts means debugging drift forever.

Each LLM invocation MUST receive:
- The canonical role prompt
- The task- or node-specific prompt
- The current user input (single turn only)
- **Structured context_state** (governed data derived from prior turns)

Each LLM invocation MUST NOT receive:
- Prior conversation history (even from same execution)
- Previous assistant responses
- Accumulated user messages
- Raw conversational transcripts

**Continuity comes from structured state, not transcripts.**

If continuity is required, use `context_state` with structured fields:
- `intake_summary`, `known_constraints[]`, `open_gaps[]`
- `questions_asked[]` (IDs, not prose), `answers{}`
- Never raw conversation text

**node_history is for audit. context_state is for memory. Keep them separate.**

**If you are about to load or replay conversation history, STOP — this is a violation.**

_See ADR-040 and session log 2026-01-17._

## No Black Boxes (ADR-049)

Every DCW (Document Creation Workflow) MUST be explicitly composed of gates, passes, and mechanical operations.

**"Generate" is deprecated as a step abstraction — it hides too much.**

DCWs are first-class workflows, not opaque steps inside POWs. If a step does something non-trivial, it must show its passes.

Composition patterns:
- **Full pattern**: PGC Gate (LLM → UI → MECH) → Generation (LLM) → QA Gate (LLM + remediation)
- **QA-only pattern**: Generation (LLM) → QA Gate (LLM + remediation)
- **Gate Profile pattern**: Multi-pass classification with internals

**If you are about to create a DCW with opaque "Generate" steps, STOP — decompose into explicit gates.**

_See ADR-049._
