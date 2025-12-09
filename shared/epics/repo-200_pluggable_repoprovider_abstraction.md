🚩 PM Mentor — Task: Create Epic
Epic ID: REPO-200
Epic Title: Pluggable RepoProvider Abstraction
Instructions

Create a new Epic with the following requirements.

Epic Summary

Introduce a RepoProvider abstraction that fully decouples The Combine from any specific Git hosting platform. This architecture enables seamless support for GitHub.com, GitHub Enterprise, GitLab, and Azure DevOps—without modifying worker prompts, canon, or orchestration pipelines. All code read/write operations must flow through this provider, ensuring compatibility with SaaS, hybrid, and fully on-prem deployments.

Business Rationale

Enterprise customers use a diverse mix of Git platforms

Workers must never access local filesystems or receive raw credentials

All code changes must go through Pull Requests for auditability and CI gating

Required foundation for air-gapped and hybrid customer deployments

Establishes a durable integration boundary for future enterprise expansion

Required Stories (decompose further as needed)
1. Define the RepoProvider interface in Python

Specify all required methods (get_file, list_files, create_branch, apply_changeset, open_pr, get_pr_status, etc.)

Require consistent error handling and return types

Add comprehensive docstrings describing contract expectations

2. Implement GitHubCloudProvider (GitHub.com)

Fully implement the RepoProvider interface for GitHub.com

Use GitHub REST or GraphQL API for all repo interactions

Support authentication via GitHub App or PAT

Include robust error-handling, logging, and rate-limit awareness

3. Implement GitHubEnterpriseProvider

Mirror GitHubCloudProvider but configurable for GH Enterprise endpoints

Support self-hosted certificates and custom base URLs

Validate compatibility with enterprise security constraints

4. Create stub provider classes for future expansion

Implement placeholder provider classes that inherit from RepoProvider and raise NotImplementedError for all methods.

Requirements:

Add GitLabProvider(RepoProvider)

Add AzureDevOpsProvider(RepoProvider)

Each method must explicitly raise NotImplementedError

Add class-level comments:

“Future implementation — intentionally unimplemented. Serves as template for new providers.”

Register these stubs in the provider registry/config (disabled by default)

Purpose:

Makes extensibility explicit

Prevents accidental GitHub-specific assumptions

Creates a clear architectural contract for future workers and developers

5. Replace /workforce/commit with PR creation via RepoProvider

Refactor commit flow to always create a Pull Request instead of writing to disk

Accept a DevChangeSetV1 artifact and convert it into PR content

Enforce a standard branch naming schema

Surface PR URL and status to QA Worker and Orchestrator

6. Add RepoProvider selection to tenant/project configuration

Support selecting the active provider per tenant or per project

Validate configuration on load

Ensure workflows fail gracefully if an unsupported provider is selected

7. Update all orchestrator repo operations to use injected RepoProvider

Replace direct GitHub API or filesystem logic

Ensure all reads and writes flow through the abstraction

Update tests to mock RepoProvider behavior

Deliverable

A complete Epic document including:

Decomposed user stories

Acceptance criteria for each

Story point estimates

Clear definition of done for the entire Epic