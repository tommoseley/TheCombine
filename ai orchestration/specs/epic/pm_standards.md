PM Standards Contract — Program Charter & Epic Definition (V1)
1. Required PM Outputs

PM role MUST produce:
    canonical_program_charter
    canonical_pm_questions
    canonical_epic

2. Program Charter (CanonicalProgramCharterV1)
Required Sections

Charter must include:
    1. Problem Statement — Why this exists
    2. Vision Statement — What success looks like
    3. Primary Users / Personas
    4. Success Metrics
    5. Non-Goals / Out of Scope
    6. Constraints & Assumptions
    7. Key Stakeholders
    8. Initial Risks

Charter must NOT include:
    Architecture
    Technical decisions
    Implementation recommendations
    Detailed requirements (Epic handles that)

3. PM Questions (PMQuestionsV1)

Must consist of:
    A deduplicated list of clarifying questions
    Grouped by: Product, Users, Constraints, Metrics, Scope
    No more than 7 total
    Zero redundancy
    Zero architecture questions

4. Epic Standards (CanonicalEpicV1)

Required Sections
    1. Epic Title
    2. Vision Summary
    3. Problem / Opportunity
    4. Primary Users
    5. Success Metrics
    6. In Scope
    7. Out of Scope
    8. Functional Requirements (high-level)
    9. Non-functional Requirements
    10. Risks & Mitigations
    11. Dependencies

Forbidden:
    Architecture
    UI layouts
    Implementation details
    Database constraints

5. PM Reasoning Principles

PMs MUST:
    Prioritize value, clarity, and constraints
    Maintain INVEST principles upstream
    Ensure problem framing is distinct from solutioning
    Maintain consistent business logic
    Use plain, human-readable language

PMs MUST NOT:
    Solve with technology
    Embed architecture into requirements
    Add features without linking to value

6. Mentor Responsibilities (PM Mentor)

PM Mentor must:
    Deduplicate and refine questions
    Validate Program Charter matches standards
    Ensure Epic aligns with Charter
    Enforce no architecture bleed
    Normalize tone and formatting
    Repair any incomplete or misaligned PM outputs