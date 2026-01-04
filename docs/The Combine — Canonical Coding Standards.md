The Combine — Canonical Coding Standards (Developer Mentor)
Status: Canonical
Scope: All code produced, reviewed, or modified by the Developer Mentor
Precedence: Overrides personal preference, prior habits, or external style guides where conflicts exist
––––––––––––––––––––––––––––––––––

Canonical Intent

You are building code for The Combine, not a generic software project.

The goals of these standards are to preserve intent across time, minimize cognitive load for future maintainers, enforce architectural boundaries, make failure explicit and observable, and maintain a strict separation between thinking and execution.

If a choice improves cleverness but harms clarity, clarity wins.

Philosophy

Code is read more than written. Optimize for the maintainer who inherits this in six months. That maintainer is you.

Clean code is not aesthetic. It is operational empathy.

Naming (Non-Negotiable)

Names must reveal intent without explanation. If a name requires a comment, the name is wrong.

Rules:

Functions use verb phrases describing action (calculate_token_cost, not cost)

Booleans are questions that answer themselves (is_valid, has_permission, should_retry)

Collections are plural nouns (artifacts, not artifact_list)

Classes are nouns describing what they are, not what they do (ArtifactRepository, not ArtifactManager)

Abbreviation Rule:

Do not use abbreviations for domain concepts, roles, entities, or variables

If you choose a term, you must use that exact term consistently everywhere
Example: choose “developer” OR “development”, not dev / developer / dev_role interchangeably

Mixing abbreviated and full forms of the same concept is prohibited

Exceptions:

Widely accepted standard abbreviations are allowed where unambiguous
Examples include ID, OK, HTTP, API, UUID, JSON

Prohibited:

Generic names such as data, info, temp, result

Ad-hoc or informal abbreviations

Hungarian notation

Functions

Functions must be small, focused, and operate at one level of abstraction.

Rules:

If a function description includes “and,” split it

Functions exceeding roughly 20 lines must be questioned

More than three parameters requires a Pydantic model

A function must be either a command or a query, never both

Line count is a smell, not a law. Readability beats code golfing.

Comments

Code explains what. Comments explain why.

Rules:

Do not comment obvious code

Do not leave commented-out code in the codebase; Git is the archive

Comments that restate the code are prohibited.

Error Handling

Fail fast. Fail loud. Fail with context.

Rules:

Raise exceptions; never return error codes

Never swallow exceptions silently

Every error must communicate what failed, what was expected, and what was received

Four-tier error model:

HTTPException for API boundaries only

Domain exceptions for business logic failures

Validation errors for Pydantic schema violations

Database errors for persistence and SQLAlchemy failures

Errors are part of the system contract.

Logging

Logs are part of the product experience.

Rules:

Use structured logs only

Log events, not prose

Never log secrets or raw prompt bodies by default

Every log entry must include a correlation ID

If behavior cannot be reconstructed from logs, the system is broken.

Correlation IDs (Mandatory)

Every request must be traceable end-to-end.

Rules:

Accept X-Correlation-Id on all inbound requests

Generate one if missing

Propagate it to logs, database audit records, LLM calls, and outbound HTTP requests

Include the correlation ID in all exception context

Code without correlation ID propagation is non-compliant.

Architecture Constraints (Absolute)

These rules are not negotiable.

No hard-coded prompts. Prompts may exist only in the role_prompts table or versioned JSON files

QueryOptions must be Pydantic models; raw dicts are prohibited

Creative vs mechanical separation is mandatory. LLMs reason and synthesize; code executes deterministic work

Correlation IDs are required at every layer

Artifact identity is path-based, using project_id/epic_id/story_id. Relational keys may exist internally for indexing and constraints, but identity and retrieval are path-based

Layering and Boundaries

Dependency rules:

API layers may depend on the domain

The domain must never depend on API or persistence layers

Persistence implementations live outside the domain

Domain logic depends on repository interfaces, not implementations

Boundary violations are architectural defects.

SOLID Principles (Applied)

Single Responsibility: Each class has one reason to change.
Open/Closed: Extend behavior without modifying existing code.
Liskov Substitution: Subtypes must be interchangeable with their base types.
Interface Segregation: Prefer small, focused interfaces.
Dependency Inversion: High-level modules depend on abstractions, not concretions.

SOLID is a discipline, not a slogan.

DRY With Discipline

Duplication is cheaper than the wrong abstraction.

Rules:

Duplicate until the pattern is obvious (rule of three)

Extract abstractions only when they are stable

Prefer explicit code over clever code

Premature abstraction is deferred pain.

Testing

Tests are documentation that executes.

Rules:

Test behavior, not implementation

One assertion per test when practical

Mock external systems such as LLMs and databases

Code that is difficult to test is poorly designed

Required test pyramid:

Unit tests for domain logic

Contract tests for API schemas and invariants

Minimal end-to-end smoke tests for happy paths only

Formatting and Tooling

Formatting is automated and enforced.

Black for formatting

Ruff for linting

Pre-commit hooks for enforcement

Formatting debates are noise.

Public API Shape

APIs are contracts, not conversations.

Rules:

All API responses must follow a consistent envelope including correlation_id, data, and errors

Errors must include a stable error_code and a human-readable message

Pre-Commit Standard

Before submitting code, verify:

You would understand this code in six months

Names eliminate the need for comments

Terminology is consistent and non-abbreviated

Architectural boundaries are respected

Failures are explicit and contextual

Correlation IDs are propagated

The solution is as simple as possible

Tests prove behavior

If any answer is no, revise.

Canonical Closing

Clean code is not about rules. It is about respect for future maintainers, system integrity, and the difference between thinking and doing.

This document is canonical. Deviations require explicit architectural justification.