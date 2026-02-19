# WS-AWS-DB-002: Connection Scripts for DEV and TEST

## Status: Accepted

## Parent Work Package: WP-AWS-DB-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- ops/scripts/

---

## Objective

Add scripts that establish connections to DEV and TEST databases and print the connection string for use by the app or psql. Scripts fail with actionable errors if credentials or connectivity are missing.

---

## Preconditions

- WS-AWS-DB-001 complete (RDS instances exist, credentials in Secrets Manager)

---

## Tier 1 Verification Criteria

1. **Scripts exist**: `ops/scripts/db_connect_dev.sh` and `ops/scripts/db_connect_test.sh` (or equivalent)
2. **Scripts retrieve credentials**: Scripts pull credentials from Secrets Manager (not hardcoded)
3. **Scripts print connection string**: Output includes the DATABASE_URL or equivalent for the target env
4. **Scripts fail with actionable errors**: If AWS creds missing, Secrets Manager unreachable, or DB unreachable, script exits non-zero with clear error message
5. **Connection works**: Running the script and using the printed connection string connects to the correct database

---

## Procedure

### Phase 1: Implement

1. Create connection scripts in ops/scripts/
2. Scripts use AWS CLI to retrieve credentials from Secrets Manager
3. Scripts construct and print DATABASE_URL
4. Scripts validate connectivity (optional: quick pg_isready check)

### Phase 2: Verify

1. All five Tier 1 criteria met
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not hardcode credentials in scripts
- Do not commit credentials or connection strings to the repository
- Do not modify the RDS instances

---

## Verification Checklist

- [ ] Connection scripts exist
- [ ] Credentials retrieved from Secrets Manager
- [ ] Connection string printed to stdout
- [ ] Actionable errors on failure
- [ ] Connection verified for both DEV and TEST
- [ ] Tier 0 returns zero

---

_End of WS-AWS-DB-002_
