# WS-AWS-DB-004: Migration and Seed Scripts per Environment

## Status: Accepted

## Parent Work Package: WP-AWS-DB-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- ops/scripts/
- ops/db/

---

## Objective

Add per-environment scripts to run Alembic migrations and optional seed data against DEV and TEST databases. Scripts must be safe and idempotent.

---

## Preconditions

- WS-AWS-DB-001 complete (RDS instances exist)
- WS-AWS-DB-002 complete (connection scripts retrieve credentials)
- WS-AWS-DB-003 complete (COMBINE_ENV profiles exist)

---

## Tier 1 Verification Criteria

1. **Migration scripts exist**: `ops/scripts/db_migrate_dev.sh` and `ops/scripts/db_migrate_test.sh` (or parameterized equivalent)
2. **Migrations run cleanly**: Scripts run Alembic migrations against the target env and succeed
3. **Seed scripts safe**: If seed scripts exist, they are idempotent (running twice does not corrupt data)
4. **Env guard on seeds**: Seed scripts verify COMBINE_ENV matches the target before executing (cannot accidentally seed dev data into test or vice versa)
5. **Smoke query**: After migration, a basic query confirms expected tables exist

---

## Procedure

### Phase 1: Implement

1. Create migration scripts (or parameterized script with env argument)
2. Scripts set COMBINE_ENV, retrieve connection string (reuse WS-AWS-DB-002 scripts), run Alembic
3. Create optional seed scripts with idempotency and env guards
4. Add smoke query step (list tables, check count)

### Phase 2: Verify

1. All five Tier 1 criteria met
2. Migrations run successfully on both DEV and TEST
3. Tier 0 returns zero

---

## Prohibited Actions

- Do not run migrations against production
- Do not create seed scripts that are destructive (DROP/TRUNCATE without guard)
- Do not hardcode credentials
- Do not modify Alembic migration files themselves

---

## Verification Checklist

- [ ] Migration scripts exist
- [ ] Migrations run cleanly on DEV
- [ ] Migrations run cleanly on TEST
- [ ] Seed scripts are idempotent (if created)
- [ ] Env guard prevents cross-env seeding
- [ ] Smoke query confirms tables exist
- [ ] Tier 0 returns zero

---

_End of WS-AWS-DB-004_
