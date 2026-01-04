ADR-013 — Seed Governance

Status: Draft (Scaffold)
Date: 2026-01-02
Related ADRs: ADR-009 (Audit & Governance), ADR-010 (LLM Execution Logging)

1. Decision Summary

This ADR defines governance rules for seeded inputs that shape system behavior.

Seeded inputs are treated as governed artifacts, not configuration or documentation.

2. Problem Statement

Certain inputs:

Define system behavior

Must be versioned, certified, and auditable

Are consumed repeatedly across executions

Treating these as informal files or scripts introduces drift and risk.

3. Definitions

Seeded Input
A governed artifact used to initialize or constrain system behavior.

Certification
The process by which a seeded input is approved for use.

Replayability
The ability to reproduce behavior using a specific version of a seed.

4. Seed Categories

Seeded inputs may include (non-exhaustive):

Role prompts

Task prompts

Reference data

Canonical templates

This ADR defines governance rules, not taxonomy.

5. Governance Requirements

All seeded inputs must be:

Versioned

Immutable once certified

Identifiable by stable ID or hash

Loggable when used in execution

6. Change Control

Changes to seeded inputs must:

Produce a new version

Preserve historical versions

Be explicitly approved

Silent modification is prohibited.

7. Usage Constraints

Seeded inputs:

May be baked into runtime images, mounted, or injected

Must be referenced explicitly during execution

Must not be modified at runtime

8. Audit & Logging Alignment

Seed usage must align with:

ADR-009 (explicit governance)

ADR-010 (execution logging)

Every execution must record:

Which seeds were used

Their versions or hashes

9. Out of Scope

This ADR does not define:

Physical storage layout

Tooling for certification

CI/CD enforcement mechanisms

10. Drift Risks

Primary drift risks include:

Treating seeds as editable configuration

Allowing runtime mutation

Losing historical versions

Any relaxation of these constraints requires a new ADR.