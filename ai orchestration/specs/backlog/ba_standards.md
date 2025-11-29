BA Standards Contract — Backlog Definition (V1)

1. Required BA Outputs
BA Agents MUST produce:
    Feature Breakdown (optional intermediate)
    Backlog (CanonicalBacklogV1)
    Acceptance Criteria (Given/When/Then)
BA Mentor must:
    Refine
    Validate
    Produce final canonical backlog

2. Backlog Structure
Required Sections
    Feature Summary
    Feature → Story mapping
    Stories (INVEST-compliant)
    Acceptance Criteria
    Dependencies
    Non-functional requirements (mapped from Epic & Architecture)

3. Story Rules
Stories MUST:
    Follow INVEST
    Be user-focused
    Avoid implementation details
    Avoid architecture
    Map 1:1 to business value
Stories MUST include:
    Story ID
    Title
    Description
    Acceptance criteria
    Dependencies
    Traceability to Epic and Architecture

4. Acceptance Criteria Rules

AC must follow:
    Given <initial context>
    When <action>
    Then <outcome>

Must include:
    Happy path
    Edge case(s)
    User validation condition
Must NOT include:
    UI pixel specs
    Code-level detail
    System internals

5. BA Mentor Responsibilities
BA Mentor must:
    Validate all stories follow INVEST
    Ensure AC are testable and complete
    Ensure traceability to Epic and architecture
    Remove contradictions
    Repair unclear or ambiguous stories
    Enforce canonical backlog format
    Normalize tone and structure
    Rewrite until schema validation passes