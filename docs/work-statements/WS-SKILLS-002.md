# WS-SKILLS-002: Supplementary Claude Code Skills (Progressive Disclosure)

## Status: Draft

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- POL-WS-001 -- Work Statement Standard

## Verification Mode: A

## Allowed Paths

- .claude/skills/
- CLAUDE.md (READ ONLY -- do not modify)

## Supersedes

- WS-SKILLS-001 (incorrect approach: slimmed CLAUDE.md, caused CC to lose critical context)

---

## Objective

Create 10 project skills in `.claude/skills/` that provide supplementary operational depth on top of the full CLAUDE.md. Skills add detailed procedures, examples, checklists, and contextual guidance that load on-demand. CLAUDE.md is NOT modified -- it retains all governance rules, constraints, and procedures as always-on context.

Skills are progressive disclosure, not replacement. CC always has the rules. Skills add richness when relevant.

---

## Preconditions

- CLAUDE.md is the full version (restored from commit 56c30ef or later full version)
- CLAUDE.md contains all governance rules, policies, and constraints
- `.claude/` directory exists or can be created

---

## Scope

### In Scope

- Create 10 project skills in `.claude/skills/`
- Create `.claude/skills/README.md` cataloging all skills
- Each skill provides supplementary depth: detailed procedures, worked examples, decision trees, checklists
- Skills must not contradict CLAUDE.md

### Out of Scope

- Modifying CLAUDE.md (CLAUDE.md is READ ONLY for this WS)
- Installing marketplace skills (operator action)
- Modifying any application code
- Changing policies or ADRs

---

## Design Principle

CLAUDE.md states the rule. The skill explains how to follow it.

Example:
- CLAUDE.md says: "Bug-First Testing Rule: Reproduce in a test before fixing. No exceptions."
- Skill adds: step-by-step procedure, report format template, escalation decision tree, worked example with test name and root cause

If CLAUDE.md disappeared, CC loses the rules. If skills disappeared, CC still has the rules but less operational guidance. That asymmetry is intentional.

---

## Skill Inventory

| # | Skill | Directory | Supplements |
|---|-------|-----------|-------------|
| 1 | `ws-execution` | `.claude/skills/ws-execution/` | Do No Harm audit procedure, phase execution detail, remediation WS pattern, report format |
| 2 | `autonomous-bug-fix` | `.claude/skills/autonomous-bug-fix/` | Step-by-step fix procedure, report template, escalation decision tree, worked example |
| 3 | `subagent-dispatch` | `.claude/skills/subagent-dispatch/` | Parallelism detection from WP, allowed_paths isolation test, dispatch example with WP-DCW-001 |
| 4 | `metrics-reporting` | `.claude/skills/metrics-reporting/` | Endpoint formats, event_id generation, pinned enums reference, phase event JSON templates, scoreboard |
| 5 | `session-management` | `.claude/skills/session-management/` | Full session log template, backfill procedure, PROJECT_STATE update checklist |
| 6 | `config-governance` | `.claude/skills/config-governance/` | Version bump procedure, certification steps, ADR-040 detailed examples, ADR-049 composition patterns |
| 7 | `ia-validation` | `.claude/skills/ia-validation/` | Coverage level examples, Level 2 card-list/table/nested-object templates, no-guessing rule decision tree |
| 8 | `ia-golden-tests` | `.claude/skills/ia-golden-tests/` | Full test criteria reference, coverage report format, debugging guide, how to add tests for new doc types |
| 9 | `tier0-verification` | `.claude/skills/tier0-verification/` | All command variants, WS mode with --scope, result interpretation guide |
| 10 | `combine-governance` | `.claude/skills/combine-governance/` | POL-ADR-EXEC-001 decision flowchart, WS structure template, WP dependency chain examples |

---

## SKILL.md Content Rules

Each skill MUST:

1. Have valid YAML frontmatter with `name` and `description`
2. Include specific trigger phrases in `description` that enable discovery
3. Provide operational depth beyond what CLAUDE.md states (not restate the same text)
4. Include at least one worked example or template
5. Not contradict any rule in CLAUDE.md

Each skill MUST NOT:

1. Restate CLAUDE.md rules verbatim (reference them, don't copy them)
2. Weaken or soften any CLAUDE.md constraint
3. Add new governance rules (skills supplement, they do not govern)
4. Reference other skills as dependencies (each skill is self-contained for its trigger)

---

## Tier 1 Verification Criteria

All new Tier-1 tests written for this WS must fail prior to implementation and pass after.

### Structure

1. **All 10 skill directories exist**: `.claude/skills/<name>/SKILL.md` for each skill in inventory
2. **README exists**: `.claude/skills/README.md` catalogs all 10 skills with triggers and paths
3. **Each skill has valid frontmatter**: `name` and `description` fields present in YAML frontmatter
4. **Each description includes trigger phrases**: description field contains action verbs and context phrases

### CLAUDE.md Integrity

5. **CLAUDE.md unchanged**: CLAUDE.md byte-for-byte identical to pre-execution state (hash comparison)
6. **No CLAUDE.md sections removed**: All existing section headers still present
7. **No CLAUDE.md sections added**: No new sections introduced

### Content Quality

8. **Each skill has a worked example**: Every SKILL.md contains at least one code block, template, or concrete example
9. **No verbatim CLAUDE.md copying**: No skill contains a block of 5+ consecutive lines identical to CLAUDE.md
10. **No contradictions**: No skill states a rule that conflicts with CLAUDE.md (spot-check critical rules: Bug-First, ADR-040, POL-WS-001)

### Supplementary Value

11. **Bug-fix skill has report template**: autonomous-bug-fix includes structured report format with fields for description, root cause, test name, fix summary
12. **WS-execution skill has Do No Harm procedure**: ws-execution includes numbered steps for conducting the audit
13. **Metrics skill has JSON templates**: metrics-reporting includes complete JSON examples for phase events and bug fix reports
14. **Session skill has log template**: session-management includes the verbatim session log markdown template
15. **IA validation skill has Level 2 examples**: ia-validation includes card-list, table, and nested-object YAML examples

---

## Procedure

### Phase 1: Record CLAUDE.md Hash

Before any work, compute and record the SHA-256 hash of CLAUDE.md. This is the integrity baseline.

```bash
sha256sum ~/dev/TheCombine/CLAUDE.md
```

### Phase 2: Write Failing Tests

Write tests asserting criteria 1-15. Verify all fail.

For criteria 1-4: filesystem and YAML parsing checks.
For criteria 5-7: CLAUDE.md hash comparison and section header assertions.
For criteria 8-10: content analysis (example presence, duplication detection, contradiction spot-checks).
For criteria 11-15: specific content assertions per skill.

### Phase 3: Implement

1. Create `.claude/skills/` directory structure (10 subdirectories)
2. Write each SKILL.md with supplementary content:
   - Focus on procedures, templates, examples, decision trees
   - Reference CLAUDE.md rules by name, do not copy them
   - Add operational depth that helps CC execute better
3. Write `.claude/skills/README.md` with catalog
4. Verify CLAUDE.md hash unchanged

### Phase 4: Verify

1. CLAUDE.md hash matches Phase 1 baseline
2. All Tier 1 tests pass
3. Tier 0 returns zero

---

## Prohibited Actions

- Do NOT modify CLAUDE.md in any way
- Do NOT copy governance rules verbatim from CLAUDE.md into skills
- Do NOT add new governance rules in skills
- Do NOT create skills that contradict CLAUDE.md
- Do NOT modify any application code
- Do NOT modify policies, ADRs, or work statements

---

## Verification Checklist

- [ ] CLAUDE.md SHA-256 hash recorded before execution
- [ ] All Tier 1 tests fail before implementation
- [ ] 10 skill directories created with SKILL.md files
- [ ] README.md created in .claude/skills/
- [ ] Each SKILL.md has valid frontmatter with trigger description
- [ ] Each skill has at least one worked example or template
- [ ] No verbatim CLAUDE.md content copied into skills
- [ ] No contradictions between skills and CLAUDE.md
- [ ] CLAUDE.md SHA-256 hash unchanged after execution
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

## Lessons From WS-SKILLS-001

WS-SKILLS-001 slimmed CLAUDE.md to ~13K and moved governance rules to skills. This caused CC to lose critical always-on context because:

1. Skills are model-invoked -- CC must recognize it needs a skill before loading it
2. Without always-on rules, CC could not recognize when rules applied
3. This is a bootstrapping problem: you need the rules to know you need the rules

WS-SKILLS-002 corrects this by keeping CLAUDE.md full and using skills only for supplementary depth. The hash check on CLAUDE.md is a mechanical guard against repeating this mistake.

---

_End of WS-SKILLS-002_
