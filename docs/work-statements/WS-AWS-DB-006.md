# WS-AWS-DB-006: Documentation -- CLAUDE.md Quick Commands

## Status: Accepted

## Parent Work Package: WP-AWS-DB-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- CLAUDE.md

---

## Objective

Document the complete workflow for connecting to, migrating, and operating against DEV and TEST databases so that any executor (human or Claude Code) can work from any machine without tribal knowledge.

---

## Preconditions

- WS-AWS-DB-001 through WS-AWS-DB-005 complete

---

## Tier 1 Verification Criteria

1. **CLAUDE.md documents DEV workflow**: How to connect, migrate, run app against DEV
2. **CLAUDE.md documents TEST workflow**: How to connect, migrate, run app against TEST
3. **Connection recovery documented**: "What to do when connection drops" note included
4. **Guardrail usage documented**: How CONFIRM_ENV works for destructive actions
5. **No unrelated edits**: Only CLAUDE.md modified

---

## Procedure

### Phase 1: Implement

Add a section to CLAUDE.md covering:
- Start DEV connection (script name, expected output)
- Run app against DEV (`ENVIRONMENT=dev_aws`)
- Migrate DEV (script name)
- Same for TEST
- Destructive action guards (CONFIRM_ENV pattern)
- Troubleshooting: connection drops, credential refresh, common errors

### Phase 2: Verify

1. All five Tier 1 criteria met
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify any scripts or application code
- Do not commit credentials or connection strings in documentation
- Do not document production workflows (out of scope)

---

## Verification Checklist

- [ ] DEV workflow documented
- [ ] TEST workflow documented
- [ ] Connection recovery documented
- [ ] Guardrail usage documented
- [ ] No unrelated edits
- [ ] Tier 0 returns zero

---

_End of WS-AWS-DB-006_
