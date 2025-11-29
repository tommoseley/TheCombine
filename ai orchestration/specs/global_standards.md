📘 Purpose

These rules apply to every role, every agent, every orchestrator, and every artifact.
They define the Constitution of the system. Nothing overrides them.

1. Canonical Document Shape — Required Structure

All canonical documents must follow this JSON structure:

{
  "type": "<canonical_type>",
  "version": <integer>,
  "sections": {
    "<section_key>": {
      "blocks": [
        { "id": "...", "type": "<block_type>", ... }
      ]
    }
  }
}

Allowed Canonical Types
    canonical_program_charter
    canonical_epic
    canonical_architecture
    canonical_backlog
    canonical_pm_questions
    canonical_feature_tree (future)
    canonical_code_spec (future)
Allowed Block Types

Every block MUST be one of:
    paragraph
    heading
    list_item
    code
    component
    entity
    decision
    risk
    table
    key_value
No other block types permitted.

2. Strict Validation Requirements
2.1 No Extra Keys

All JSON must use:

extra = "forbid"

No additional fields allowed anywhere in:
    root
    sections
    blocks
    component data
    entity data
    risk objects
    table definitions

2.2 ID Rules

    Every block requires an "id".
    All IDs must be unique within the same section.
    IDs may repeat across different sections only if not semantically confusing.

3. Rewrite Cycle Requirement

Any document that fails validation must be:

    1. Returned to the Domain Mentor
    2. Mentor receives validation errors
    3. Mentor rewrites until passing validation (max 3 attempts)
    4. If still failing → escalate to user

4. Consistency Requirements
4.1 Upstream → Downstream Consistency

Downstream documents MUST reflect upstream intent:
    Charter → Epic → Architecture → Backlog → Code Spec (future)
    No document may contradict upstream definitions.
    BAs may refine but NOT reinterpret business intent.
    Architects may design but NOT alter functional value.
    PMs may contextualize but NOT alter technical feasibility.

4.2 Grounded Reasoning

All agents must:
    Cite the specific upstream section used
    Adapt to clarified Q&A
    Avoid hallucinations
    Avoid unstated assumptions

5. Mentors’ Responsibilities

Every Mentor must:
    Enforce global standards
    Enforce role-specific standards
    Ensure artifact clarity
    Eliminate redundancy
    Correct misalignment with user intent
    Normalize tone, structure, and formatting

6. Orchestrator Responsibilities

Orchestrators must:
    Load all relevant standards at runtime
    Enforce stage order
    Ensure only canonical documents feed downstream phases
    Store all approved documents in canonical store
    Provide consistent user Q&A pipeline

7. Human-in-the-Loop Rules

    All clarifying questions must be consolidated by Mentors, NOT workers.
    Answers provided by user must be broadcast to all workers AND mentors.
    Users must explicitly approve all canonical artifacts before advancing.

8. Creative Constraints

    Zero creativity outside role boundaries.
    No speculative architecture or features.
    No reinterpreting business value or constraints.
    No contradictions with standards or upstream artifacts.