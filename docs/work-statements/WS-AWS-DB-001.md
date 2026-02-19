# WS-AWS-DB-001: Provision AWS RDS Postgres for DEV and TEST

## Status: Accepted

## Parent Work Package: WP-AWS-DB-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- ops/aws/

---

## Objective

Create two isolated RDS PostgreSQL instances (or one instance with two databases and separate credentials) for DEV and TEST environments. Establish provisioning scripts in ops/aws/ alongside existing ECS/Route53/IAM scripts.

---

## Preconditions

- AWS account access with RDS provisioning permissions
- Existing ops/aws/ directory with ECS/Route53/IAM scripts (PowerShell convention)
- AWS Secrets Manager available

---

## Tier 1 Verification Criteria

1. **Two isolated DB targets exist**: DEV and TEST with separate connection strings and credentials
2. **Security group restricts access**: Inbound limited to home network IP (matching existing RDS pattern, not 0.0.0.0/0)
3. **Credentials in Secrets Manager**: DB credentials stored in AWS Secrets Manager (not in code, not in .env committed to repo)
4. **Provisioning scripted**: PowerShell script(s) in ops/aws/ can recreate the infrastructure
5. **Connection succeeds**: Can connect to both DEV and TEST from home network using psql or equivalent

---

## Procedure

### Phase 1: Write Provisioning Scripts

Create PowerShell scripts in ops/aws/ (alongside existing ECS/Route53/IAM scripts):
- RDS instance creation (or database creation within shared instance)
- Security group configuration
- Secrets Manager entries for credentials

### Phase 2: Provision

Run scripts to create DEV and TEST database targets.

### Phase 3: Verify

1. All five Tier 1 criteria met
2. Connection verified from local machine

---

## Prohibited Actions

- Do not make RDS accessible from 0.0.0.0/0
- Do not commit credentials to the repository
- Do not modify the existing production RDS instance
- Do not introduce Terraform or CloudFormation (use PowerShell + AWS CLI, consistent with existing ops/aws/ scripts)

---

## Verification Checklist

- [ ] DEV database accessible with its own credentials
- [ ] TEST database accessible with its own credentials
- [ ] Security group limits access to home IP
- [ ] Credentials in Secrets Manager
- [ ] Provisioning script exists in ops/aws/
- [ ] Connection verified from local machine

---

_End of WS-AWS-DB-001_
