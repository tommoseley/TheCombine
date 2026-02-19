# WP-AWS-DB-001: Remote DEV/TEST Postgres on AWS for Multi-Machine Development

## Status: Accepted

## Governing References

- ADR-050 -- Work Statement Verification Constitution

---

## Intent

Move Combine's DEV and TEST databases to AWS RDS so development can happen from any machine on the home network consistently, with secure access and hard guardrails to prevent environment mistakes.

---

## Scope In

- AWS RDS Postgres for DEV and TEST
- Secure connectivity from home network (security group, matching existing RDS pattern)
- App config for env selection
- Migration and seed commands per env
- Safety rails (destructive action guards)
- CLAUDE.md quick commands

## Scope Out

- Full AWS app deployment (ECS, ALB, etc.)
- Prod environment changes
- SSM tunneling (tech debt -- tighten later)
- Terraform migration (tech debt -- match existing ops/aws/ pattern for now)
- Program-level logbooks or multi-tenant concerns

---

## Definition of Done

1. DEV and TEST DB endpoints exist in AWS RDS
2. Local app can connect to each from home network
3. Migrations run cleanly in both envs
4. Seeds exist and are safe
5. Guardrails prevent accidental cross-env destructive actions
6. Tier 0 green

---

## Tech Debt (Acknowledged)

| Item | Current Approach | Preferred Approach | When |
|------|------------------|--------------------|------|
| Network access | Security group with home IP | SSM port forwarding via bastion or ECS exec | When security posture tightens |
| Infrastructure-as-code | PowerShell scripts in ops/aws/ | Terraform or CloudFormation | When infra complexity warrants it |
| RDS public accessibility | Publicly accessible with SG restriction | Private subnet + tunnel | When VPC topology is revisited |

---

## Execution Order

1. WS-AWS-DB-001 -- Provision RDS instances
2. WS-AWS-DB-002 -- Connection scripts
3. WS-AWS-DB-003 -- App env profiles
4. WS-AWS-DB-004 -- Migration and seed scripts
5. WS-AWS-DB-005 -- Destructive action guardrails
6. WS-AWS-DB-006 -- Documentation

Each WS depends on the previous. Execute in order.

---

_End of WP-AWS-DB-001_
