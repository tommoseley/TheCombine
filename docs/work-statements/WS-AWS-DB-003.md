# WS-AWS-DB-003: App Environment Profiles and Explicit DB Target Selection

## Status: Accepted

## Parent Work Package: WP-AWS-DB-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- app/core/
- tests/

---

## Objective

Extend the existing `ENVIRONMENT` / `EnvironmentType` system (in `app/core/environment.py`) so the app knows which database to connect to. Configuration must be explicit and deterministic — no silent fallbacks to a wrong environment. Do not create a parallel environment variable.

---

## Preconditions

- WS-AWS-DB-001 complete (RDS instances exist)
- WS-AWS-DB-002 complete (connection scripts can retrieve credentials)

---

## Tier 1 Verification Criteria

All tests must fail before implementation and pass after.

1. **EnvironmentType extended**: `app/core/environment.py` `EnvironmentType` enum includes `DEV_AWS` and `TEST_AWS` (or equivalent names) alongside existing `DEVELOPMENT`, `STAGING`, `PRODUCTION`, `TEST`
2. **App refuses invalid env**: If `ENVIRONMENT` is set to an unrecognized value, app startup fails with clear error
3. **DATABASE_URL per env**: Each env resolves to a distinct DATABASE_URL
4. **No secrets committed**: No connection strings, passwords, or hostnames in committed config files
5. **Backward compatible**: If `ENVIRONMENT` is not set but `DATABASE_URL` is set directly, app uses DATABASE_URL (preserves existing local dev workflow)
6. **DATABASE_URL resolution unified**: `app/core/config.py` and `app/core/database.py` use a single resolution path for DATABASE_URL (no duplicate handling)

---

## Procedure

### Phase 0: Reconcile DATABASE_URL Handling (Pre-requisite)

`app/core/config.py` raises if DATABASE_URL is missing; `app/core/database.py` silently defaults to `postgresql://localhost/combine`. These are two different resolution paths. Reconcile to a single path before adding env-profile logic, or the new logic will have to handle both.

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-6. Verify all fail.

### Phase 2: Implement

1. Extend `EnvironmentType` in `app/core/environment.py` to include `DEV_AWS` and `TEST_AWS`
2. Define resolution logic: `ENVIRONMENT` value → DATABASE_URL mapping (connection scripts from WS-002 provide the actual URLs)
3. Reject unrecognized `ENVIRONMENT` values at startup
4. Preserve existing DATABASE_URL fallback for local dev

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not introduce a new environment variable (extend existing ENVIRONMENT / EnvironmentType)
- Do not remove support for direct DATABASE_URL (backward compat)
- Do not commit secrets or connection strings
- Do not modify database schemas or migrations
- Do not change any business logic

---

## Verification Checklist

- [ ] DATABASE_URL handling reconciled (single resolution path in config.py and database.py)
- [ ] All Tier 1 tests fail before implementation
- [ ] EnvironmentType extended with DEV_AWS and TEST_AWS
- [ ] Invalid env rejected at startup
- [ ] Each env resolves to correct DATABASE_URL
- [ ] No secrets committed
- [ ] Existing local dev workflow unaffected
- [ ] All Tier 1 tests pass after implementation
- [ ] Tier 0 returns zero

---

_End of WS-AWS-DB-003_
