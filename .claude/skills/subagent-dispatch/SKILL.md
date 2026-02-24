---
name: subagent-dispatch
description: Dispatch and manage subagents for parallel WS execution, research tasks, and test isolation. Use when parallelizing work across Work Statements or running concurrent investigations.
---

# Subagent Dispatch

Use subagents to parallelize work and keep the main context window clean.

## Parallel WS Execution

When a Work Package defines multiple independent Work Statements:

- Read the WP dependency chain to determine what can parallelize
- If two WSs have no dependency relationship AND non-overlapping `allowed_paths`, they are safe to run in parallel
- Spawn one subagent per independent WS
- **Mandatory:** Use `isolation: "worktree"` for parallel WS subagents to prevent git conflicts and silent overwrites

**Subagent responsibilities:**
- Run Do No Harm audit for its WS
- Execute all phases (failing tests -> implement -> verify)
- Report results (pass/fail, tests written, files changed, issues found)
- Do NOT modify files outside its WS `allowed_paths`

**Main agent responsibilities:**
- Determine parallelism from WP dependency chain
- Spawn subagents for independent WSs
- Wait for completion before spawning dependent WSs
- Run Tier 0 after all WSs complete
- Aggregate and report results

## Other Subagent Uses

Also use subagents for:

- **Research tasks**: Reading multiple files to assess impact before a Do No Harm audit
- **Parallel grep/audit**: Searching across different directory trees simultaneously
- **Test isolation**: Running different test suites in parallel
- **Impact analysis**: Assessing what a proposed change would affect

One task per subagent. Keep them focused.
