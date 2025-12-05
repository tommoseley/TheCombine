🚩 PM Mentor — Task: Create Epic
Epic ID: PIPELINE-200
Epic Title: Pull-Request-Only Commit Phase
Instructions

Create a new Epic with the following refined and authoritative requirements.

Epic Summary

Replace all direct commit functionality with a Pull-Request-only commit phase. Workers will emit structured change artifacts (DevChangeSetV1) and the Orchestrator will convert them into PRs via the RepoProvider abstraction. The legacy /workforce/commit endpoint must be deprecated and removed. From this point forward, The Combine never writes directly to a git repo.

Business Rationale

PR-only workflows are the enterprise standard for audit, governance, and CI gating

Eliminates filesystem and branch write concerns entirely

Supports hybrid and on-prem deployments where direct commits are forbidden

Ensures all code changes are reviewable and traceable

Simplifies worker design: workers only generate structured changes, not commits

Required Stories (updated with your refinements)
1. Add new endpoint /workforce/open_pr

Accept a DevChangeSetV1 artifact

Convert it to a PR via RepoProvider

Provide branch naming, title, and body templates

Return PR metadata (URL, ID, status) to the Orchestrator

2. Update all Workers to emit DevChangeSetV1 only

Apply this rule to:

Dev Worker

Fix Worker (future)

Refactor Worker (future)

Any code-modifying role

Workers must not produce raw diffs, direct patch files, or file writes

Workers must not attempt to commit — they only propose a structured change

3. Implement PR creation logic via RepoProvider

Convert DevChangeSetV1 → branch → commit → PR

Delegate all git operations to RepoProvider

Support error surfacing (branch conflicts, permission issues)

4. Add PR metadata generation rules

Standardize branch names (e.g., combine/story-<id>-<slug>)

Provide default PR titles and bodies derived from story metadata

Include references to artifacts (BA addendum, QA plan, etc.)

5. Add PR status polling

Orchestrator must be able to poll PR status

Surface CI failures and comments back to QA Worker

Allow QA Worker to request revisions

6. Automatically link PR lifecycle to story lifecycle

When a story is closed, optionally close or archive PRs

Clean up temporary branches if configured

7. Update end-to-end test suite

Replace all direct commit tests

Add tests for PR creation, failure paths, and QA feedback loop

8. Deprecate and remove /workforce/commit (HARD BREAK)

Remove endpoint and internal handlers

Remove corresponding tests

Add migration notice in release notes and developer docs

Any attempt to call this endpoint must return a permanent error

Deliverable

A complete Epic document including:

Decomposed user stories

Acceptance criteria

Updated API documentation

Story point estimates

Migration guidance to PR-only workflows