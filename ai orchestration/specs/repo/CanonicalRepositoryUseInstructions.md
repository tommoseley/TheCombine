🧭 Canonical Repository Use Instructions
for Workforce workers, mentors, and Lead Dev
1. Branches & Sources of Truth
main
    Single source of truth for production-quality code.
    Human and CI-protected. No direct pushes from workers.
workforce-sandbox
    The Workforce’s working branch.
    All AI-originated changes land here via the Workbench’s /workforce/commit endpoint.
    From here, changes are reviewed and merged into main by you or CI.
Rule: Workers and mentors never talk to GitHub directly. All repo writes go through the Workbench Workforce module.

2. Roles & Responsibilities
🧱 Workers
Operate only on text: Python modules, HTML templates, tests, docs, etc.
Never call git, never assume branch structure, never manage commits.
Always:
    Start from a file snapshot provided by the Lead Dev.
    Produce full-file replacements, not partial patches, unless explicitly asked otherwise.
    Preserve unrelated code and semantics.

🧭 Lead Dev (AI)
Owns technical coherence of the codebase.
Responsibilities:
    Fetches current versions of files based on main.
    Distributes those file snapshots + instructions to workers.
    Receives worker proposals and chooses / synthesizes the canonical version.
    Ensures style, tests, and architecture principles are respected.
    Calls the Workbench /workforce/commit endpoint to push changes to workforce-sandbox.
Rule: The Lead Dev is the only agent that decides what actually gets committed.

🎓 Mentors
Review and guidance only.
Responsibilities:
    Comment on worker proposals.
    Suggest improved designs, patterns, and simplifications.
    Identify missing tests or edge cases.
Do not:
    Directly modify the repo.
    Bypass the Lead Dev or Workforce commit flow.

3. Allowed Paths & Scope

(You can tweak this to match your repo layout.)

Workers and mentors may modify:
    app/** – application code and routes
    app/workforce/** – Workforce integration code
    tests/** – test suites
    templates/** – HTML/Jinja templates (if present)
    docs/** – documentation

Workers and mentors must not modify (unless explicitly asked):
    infra/**, deploy/**, k8s/** – deployment/infrastructure
    .github/** – CI/CD workflows
    Dockerfile, docker-compose.yml
    pyproject.toml, requirements.txt (or equivalent) without explicit instruction
Rule: If in doubt, assume infra/CI is off-limits unless the ticket explicitly calls for it.

4. Standard Workflow for a Task (e.g., AUTH-100)
1. Lead Dev sets the context
    Reads the ticket (e.g., AUTH-100) and defines:
        Problem statement
        Affected files / modules
        Acceptance criteria
    Fetches file snapshots based on the current main commit.
    Shares with workers something like:
“Here is the current content of app/auth/routes.py from main@<hash>. Implement AUTH-100 based on this.”

2. Workers propose changes

Each worker:
    Reads the provided file(s) and instructions.
    Produces complete updated versions of the relevant files:
    path: the file path
    content: full file content after their changes
Workers must not:
    Rebase, merge, or think about branches.
    Assume their version is the winner; they’re proposing, not committing.

3. Mentors review proposals

Mentors:

Compare worker proposals against:

Design goals

Readability

Test coverage

Provide comments and suggested adjustments to the workers and Lead Dev.

No git operations. No commits.

4. Lead Dev integrates and commits

Lead Dev:

Reviews all worker proposals and mentor feedback.

Chooses or synthesizes the canonical version of each file.

Ensures:

Consistent style

Test coverage for new behavior

No regressions vs the main baseline

Calls Workbench’s /workforce/commit with something like:

{
  "message": "AUTH-100: implement login + session validation",
  "changes": [
    { "path": "app/auth/routes.py", "content": "..." },
    { "path": "tests/test_auth_routes.py", "content": "..." }
  ]
}


Those changes are committed to workforce-sandbox, not main.

5. Human / CI merges into main

GitHub Actions (or similar) run tests on workforce-sandbox.

On green, either:

Auto-PR to main, or

You manually review and merge.

5. Commit Message Guidelines

When the Lead Dev calls /workforce/commit, use messages like:

AUTH-100: add login endpoint and tests

AUTH-101: session cookie validation

BUG-123: fix 500 on missing workspace

Pattern:

[TICKET-ID]: short description of the change

This keeps the history coherent whether the author was AI or human.

6. Things Workers and Mentors Must NOT Do

Do not:

Run git clone, git pull, git push, or any git commands.

Assume they are working on main directly.

Modify infra/CI unless the task explicitly says so.

Silently drop existing behaviors or endpoints.

Do not:

Merge multiple unrelated tasks into one commit.

Change global patterns (e.g. auth model, routing style) without a clearly-scoped ticket.