# Claude Code Skills — The Combine

This directory contains 10 project-specific Claude Code Skills that provide on-demand operational knowledge for The Combine.

## Skill Catalog

| Skill | Triggers | Path |
|-------|----------|------|
| `ws-execution` | Execute WS, run phases, Do No Harm audit, planning discipline | `.claude/skills/ws-execution/SKILL.md` |
| `autonomous-bug-fix` | Fix bug, runtime error, exception, reproduce failure | `.claude/skills/autonomous-bug-fix/SKILL.md` |
| `subagent-dispatch` | Parallel WS, spawn subagent, worktree isolation | `.claude/skills/subagent-dispatch/SKILL.md` |
| `metrics-reporting` | Report metrics, WS duration, phase boundary, cost tracking | `.claude/skills/metrics-reporting/SKILL.md` |
| `session-management` | Start session, close session, session log, backfill | `.claude/skills/session-management/SKILL.md` |
| `config-governance` | Seed governance, prompt versioning, ADR-040, ADR-049 | `.claude/skills/config-governance/SKILL.md` |
| `ia-validation` | IA validation, render_as, coverage levels, package.yaml | `.claude/skills/ia-validation/SKILL.md` |
| `ia-golden-tests` | IA tests, golden contracts, coverage report, debug IA | `.claude/skills/ia-golden-tests/SKILL.md` |
| `tier0-verification` | Run Tier 0, tier0.sh, WS mode, scope validation | `.claude/skills/tier0-verification/SKILL.md` |
| `combine-governance` | ADR execution, WS structure, WP structure, ADR-045 taxonomy | `.claude/skills/combine-governance/SKILL.md` |

## How Skills Work

Skills are discovered automatically by Claude Code when their trigger phrases match the current task context. Each skill loads on-demand — only the relevant skill(s) are loaded for a given task.

## Governance

- Each rule lives in exactly one skill (no duplication)
- CLAUDE.md retains always-on identity, constraints, and structure
- Skills contain operational procedures loaded when relevant
- Modifying skills follows the same WS process as any code change
