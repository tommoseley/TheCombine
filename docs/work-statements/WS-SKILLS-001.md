# WS-SKILLS-001: Decompose CLAUDE.md into Claude Code Skills

## Status: Draft

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- POL-WS-001 -- Work Statement Standard

## Verification Mode: A

## Allowed Paths

- .claude/skills/
- CLAUDE.md

---

## Objective

Decompose the operational knowledge in CLAUDE.md into 10 focused Claude Code Skills that load on-demand, reducing CLAUDE.md from ~27K characters to ~13K while preserving all governance constraints. CLAUDE.md retains always-on identity, constraints, repo structure, and non-negotiables. Skills contain operational procedures loaded only when relevant to the current task.

---

## Preconditions

- CLAUDE.md exists and contains operational sections for WS execution, bug fixing, subagents, metrics, session management, seed governance, IA validation, Tier 0, and governance policies
- `.claude/` directory exists or can be created
- Claude Code Skills are discoverable from `.claude/skills/<name>/SKILL.md`

---

## Scope

### In Scope

- Create 10 project skills in `.claude/skills/`
- Create `.claude/skills/README.md` cataloging all skills
- Slim CLAUDE.md to always-on core with skill pointers
- Verify no governance content is lost in the migration

### Out of Scope

- Installing marketplace skills (that is operator action, not code)
- Modifying any application code
- Changing policies or ADRs
- Creating new governance rules (only moving existing ones)

---

## Skill Inventory

| # | Skill | Directory | Content Source (from CLAUDE.md) |
|---|-------|-----------|--------------------------------|
| 1 | `ws-execution` | `.claude/skills/ws-execution/` | POL-WS-001 enforcement, Do No Harm audit, phase execution, Planning Discipline section |
| 2 | `autonomous-bug-fix` | `.claude/skills/autonomous-bug-fix/` | Bug-First Testing Rule section, Autonomous Bug Fixing section |
| 3 | `subagent-dispatch` | `.claude/skills/subagent-dispatch/` | Subagent Usage section |
| 4 | `metrics-reporting` | `.claude/skills/metrics-reporting/` | Metrics Reporting section |
| 5 | `session-management` | `.claude/skills/session-management/` | Session Management section, Backfilling Session Logs section |
| 6 | `config-governance` | `.claude/skills/config-governance/` | Seed Governance section, ADR-040 Stateless LLM block, ADR-049 No Black Boxes block |
| 7 | `ia-validation` | `.claude/skills/ia-validation/` | ADR-054 coverage levels, render_as vocabulary, no-guessing rule |
| 8 | `ia-golden-tests` | `.claude/skills/ia-golden-tests/` | Golden contract test patterns, coverage report, debugging guide |
| 9 | `tier0-verification` | `.claude/skills/tier0-verification/` | Tier 0 commands, WS mode, interpreting results |
| 10 | `combine-governance` | `.claude/skills/combine-governance/` | POL-ADR-EXEC-001 enforcement, WS structure, WP structure, ADR-045 taxonomy |

---

## CLAUDE.md Retention Rules

### Sections That Stay (always-on)

- Purpose
- Project Root
- Read Order
- **Skills** (NEW -- pointer table to all 10 skills)
- **Governing Policies (Always-On Summaries)** (NEW -- one-line per policy with skill pointer)
- **Execution Constraints (Always-On)** (SLIMMED -- keep: no commit = nothing happened, reuse-first, don't invent file paths, Tier 0 is the bar, combine-config canonical)
- Knowledge Layers
- Repository Structure
- Deployment Reality
- Testing Strategy
- Execution Model
- Governing ADRs (add ADR-054 to table)
- ADR-045 Taxonomy Reference
- Project Knowledge vs Filesystem
- Non-Negotiables
- Quick Commands
- Remote DEV/TEST Databases

### Sections That Move to Skills

- Governing Policies (detail) -> `combine-governance` + `ws-execution`
- Seed Governance -> `config-governance`
- ADR-040 Stateless LLM Execution Invariant -> `config-governance`
- ADR-049 No Black Boxes -> `config-governance`
- Bug-First Testing Rule -> `autonomous-bug-fix`
- Autonomous Bug Fixing -> `autonomous-bug-fix`
- Subagent Usage -> `subagent-dispatch`
- Metrics Reporting -> `metrics-reporting`
- Planning Discipline -> `ws-execution`
- Session Management -> `session-management`
- Backfilling Session Logs -> `session-management`

### Always-On Policy Summary Format

Each policy gets a one-line summary in CLAUDE.md with a skill pointer:

```
- **POL-WS-001**: Work Statements define all implementation work. Follow steps in order. Stop on ambiguity.
  *(See: `.claude/skills/ws-execution/SKILL.md`)*
```

This prevents the "I didn't load the skill so I missed the rule" failure.

---

## SKILL.md Format

Each skill follows this structure:

```yaml
---
name: skill-name
description: What this skill does and when to use it. Include trigger phrases.
---

# Skill Title

## [Content organized by purpose]
```

The `description` field is critical -- it drives when Claude Code discovers and loads the skill. Include specific trigger phrases and action verbs.

---

## Tier 1 Verification Criteria

All new Tier-1 tests written for this WS must fail prior to implementation and pass after.

### Content Completeness

1. **All 10 skill directories exist**: `.claude/skills/<name>/SKILL.md` for each skill in inventory
2. **README exists**: `.claude/skills/README.md` catalogs all 10 skills with triggers and paths
3. **No content loss**: Every governance rule, procedure, and constraint from the original CLAUDE.md exists in either the new CLAUDE.md or exactly one skill (not duplicated, not dropped)
4. **Bug-First Rule preserved**: The complete Bug-First Testing Rule exists in `autonomous-bug-fix` skill
5. **ADR-040 preserved**: The complete stateless LLM execution invariant exists in `config-governance` skill
6. **ADR-049 preserved**: The complete No Black Boxes rule exists in `config-governance` skill
7. **Session template preserved**: The verbatim session log template exists in `session-management` skill

### CLAUDE.md Structure

8. **CLAUDE.md slimmed**: New CLAUDE.md is under 15K characters (was ~27K)
9. **Skills table present**: CLAUDE.md has a Skills section with table listing all 10 skills and triggers
10. **Policy summaries present**: CLAUDE.md has one-line summaries for each policy with skill pointers
11. **Always-on constraints present**: Reuse-first, no commit = nothing happened, don't invent file paths, Tier 0 is the bar, combine-config canonical
12. **Non-negotiables unchanged**: Non-Negotiables section is identical to original
13. **No moved sections remain**: CLAUDE.md does not contain Bug-First Testing Rule section, Subagent Usage section, Metrics Reporting section, Session Management section, Seed Governance section, or ADR-040/049 detail blocks

### Skill Quality

14. **Each skill has valid frontmatter**: name and description fields present in YAML frontmatter
15. **Each description includes trigger phrases**: description field contains action verbs and context phrases that enable discovery
16. **No cross-skill duplication**: No governance rule appears in full in more than one skill

---

## Procedure

### Phase 1: Write Failing Tests

Write tests asserting criteria 1-16. Verify all fail.

For criteria 1-3: filesystem checks (directories exist, files exist, content search).
For criteria 4-7: content assertions (specific text blocks exist in expected skill files).
For criteria 8-13: CLAUDE.md structure assertions (character count, section presence/absence).
For criteria 14-16: SKILL.md format validation (YAML parsing, field presence).

### Phase 2: Implement

1. Create `.claude/skills/` directory structure (10 subdirectories)
2. Write each SKILL.md with content migrated from CLAUDE.md:
   - `ws-execution`: POL-WS-001 enforcement, Do No Harm, phases, Planning Discipline
   - `autonomous-bug-fix`: Bug-First Rule, autonomous fix procedure, escalation criteria
   - `subagent-dispatch`: Parallelism rules, allowed_paths isolation, WP example
   - `metrics-reporting`: Endpoints, pinned enums, event_id, correlation ID, scoreboard
   - `session-management`: Start/close procedures, log template, PROJECT_STATE update
   - `config-governance`: Seed governance, ADR-040 stateless LLM, ADR-049 No Black Boxes
   - `ia-validation`: Coverage levels, no-guessing rule, render_as vocabulary, examples
   - `ia-golden-tests`: Contract test criteria, coverage report, debugging guide
   - `tier0-verification`: Commands, WS mode, interpreting results
   - `combine-governance`: POL-ADR-EXEC-001, WS structure, WP structure, ADR-045
3. Write `.claude/skills/README.md` with full catalog
4. Rewrite CLAUDE.md:
   - Keep all always-on sections per retention rules
   - Add Skills pointer table
   - Add Governing Policies (Always-On Summaries) with skill pointers
   - Slim Execution Constraints to always-on items only
   - Add ADR-054 to Governing ADRs table
   - Remove all sections that moved to skills
5. Verify no content was dropped by diffing original vs (new CLAUDE.md + all skills)

### Phase 3: Verify

1. All Tier 1 tests pass
2. CLAUDE.md under 15K characters
3. All 10 skills discoverable by Claude Code
4. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify any application code (app/, tests/, ops/, etc.)
- Do not modify policies, ADRs, or work statements
- Do not create new governance rules -- only move existing ones
- Do not duplicate content across skills (each rule lives in exactly one place)
- Do not remove the Non-Negotiables section from CLAUDE.md
- Do not remove Quick Commands or Database sections from CLAUDE.md

---

## Verification Checklist

- [ ] All Tier 1 tests fail before implementation
- [ ] 10 skill directories created with SKILL.md files
- [ ] README.md created in .claude/skills/
- [ ] CLAUDE.md rewritten with skills pointers
- [ ] CLAUDE.md under 15K characters
- [ ] All governance content preserved (nothing dropped)
- [ ] No content duplicated across skills
- [ ] Each SKILL.md has valid frontmatter with trigger description
- [ ] Policy summaries in CLAUDE.md point to correct skills
- [ ] Non-Negotiables section unchanged
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-SKILLS-001_
