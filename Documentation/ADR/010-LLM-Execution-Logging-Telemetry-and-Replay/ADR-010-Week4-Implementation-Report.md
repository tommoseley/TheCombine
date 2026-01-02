# ADR-010 Week 4 Implementation Report
## Deploy to Test Environment

**Date:** January 2, 2026  
**Status:** Complete ✓  
**Sprint:** Week 4 of 4

---

## Executive Summary

Week 4 delivered the full deployment pipeline for The Combine, migrating from App Runner to ECS Fargate with Route 53 DNS management. The system is now fully operational in the test environment with LLM execution logging, replay functionality, and secure secrets management.

**Key Outcome:** Automated CI/CD pipeline deploys to ECS Fargate, updates DNS automatically, and manages secrets via AWS Secrets Manager.

---

## Objectives Achieved

| Objective | Status |
|-----------|--------|
| GitHub Actions workflow updated for ECS | ✓ Complete |
| IAM OIDC authentication configured | ✓ Complete |
| IAM permissions updated (ECS, Route53, etc.) | ✓ Complete |
| Anthropic API key in Secrets Manager | ✓ Complete |
| Route 53 DNS auto-update on deploy | ✓ Complete |
| End-to-end deployment verified | ✓ Complete |
| Document generation working | ✓ Complete |

---

## Architecture

### Deployment Flow

```
GitHub Push (main)
        │
        ▼
┌─────────────────────────────────────┐
│  1. Test Job                        │
│     - Spin up Postgres service      │
│     - Run pytest suite              │
│     - Upload coverage               │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  2. Build & Deploy Job              │
│     - OIDC auth to AWS              │
│     - Build Docker image            │
│     - Push to ECR (:sha + :latest)  │
│     - Update ECS task definition    │
│     - Deploy to ECS service         │
│     - Get new task public IP        │
│     - Update Route 53 A record      │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  3. Smoke Test Job                  │
│     - Wait for DNS propagation      │
│     - Health check via domain       │
│     - Fallback to direct IP         │
└─────────────────────────────────────┘
```

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Account                          │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │    ECR      │    │    ECS      │    │   Route 53  │     │
│  │ the-combine │───▶│  Fargate    │◀───│ thecombine  │     │
│  │   :latest   │    │   Task      │    │    .ai      │     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘     │
│                            │                                │
│                            ▼                                │
│                     ┌─────────────┐                         │
│                     │    RDS      │                         │
│                     │  Postgres   │                         │
│                     └─────────────┘                         │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐                         │
│  │  Secrets    │    │    IAM      │                         │
│  │  Manager    │    │   Roles     │                         │
│  │ anthropic-  │    │ - ecsTask*  │                         │
│  │  api-key    │    │ - github-*  │                         │
│  └─────────────┘    └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Files Modified

| File | Changes |
|------|---------|
| `.github/workflows/deploy.yml` | Migrated from App Runner to ECS Fargate + Route53 |
| `app/domain/services/document_builder.py` | Fixed corrupted emoji characters in progress messages |

## Scripts Created

| File | Purpose |
|------|---------|
| `private/check-github-oidc.ps1` | Verify GitHub OIDC configuration |
| `private/setup-github-oidc.ps1` | Create OIDC provider and IAM role |
| `private/setup-anthropic-secret.ps1` | Store API key in Secrets Manager |
| `private/github-actions-policy-ecs.json` | IAM policy for GitHub Actions |

---

## IAM Configuration

### GitHub Actions Role

**Role:** `the-combine-github-actions`

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::303985543798:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:tommoseley/TheCombine:*"
      }
    }
  }]
}
```

**Permissions:**
- ECR: GetAuthorizationToken, Push/Pull images
- ECS: Describe/Register task definitions, Update service, List/Describe tasks
- EC2: DescribeNetworkInterfaces (get task public IP)
- Route53: ListHostedZones, ChangeResourceRecordSets
- IAM: PassRole (for ecsTaskExecutionRole, ecsTaskRole)

### Secrets Manager

**Secret:** `the-combine/anthropic-api-key`

- Stored securely in AWS Secrets Manager
- Injected into ECS task as `ANTHROPIC_API_KEY` environment variable
- `ecsTaskExecutionRole` has permission to read the secret

---

## Deployment Verification

### GitHub Actions Run
- Workflow triggered on push to main
- All jobs passed: Test → Build & Deploy → Smoke Test
- Warning about git submodule (aws-mcp-server) - non-blocking

### Infrastructure Verification
```
Route 53 A Record: thecombine.ai → 54.166.36.176
ECS Task Status: RUNNING
Security Group: Port 8000 open to 0.0.0.0/0
Health Check: http://thecombine.ai:8000/health ✓
```

### Application Verification
- Database connection: ✓
- Anthropic API authentication: ✓
- Document generation: ✓
- LLM execution logging: ✓

---

## Issues Resolved

| Issue | Resolution |
|-------|------------|
| App Runner workflow outdated | Rewrote for ECS Fargate + Route53 |
| IAM policy missing ECS permissions | Added ECS, EC2, Route53, PassRole |
| Route53 pointing to wrong IP | Updated `fixip.ps1`, workflow auto-updates |
| Anthropic API key 401 error | Stored in Secrets Manager, injected to task |
| Corrupted emoji in progress messages | Cleaned `document_builder.py` |
| Git submodule warning | Added `aws-scp-server/` to `.gitignore` |

---

## Known Limitations

1. **No ALB** - Direct Route53 → task IP (IP changes on redeploy)
2. **Single task** - No load balancing or redundancy
3. **HTTP only** - No HTTPS/TLS (requires ALB or CloudFront)
4. **Manual IP update fallback** - `fixip.ps1` for emergencies

---

## Future Improvements

1. **Add ALB** - Stable endpoint, health checks, HTTPS termination
2. **Add CloudFront** - CDN, HTTPS, WAF integration
3. **Multi-AZ deployment** - Redundancy across availability zones
4. **Blue-green deployments** - Zero-downtime releases
5. **Monitoring dashboards** - CloudWatch metrics and alarms

---

## ADR-010 Complete Summary

| Week | Deliverable | Status |
|------|-------------|--------|
| Week 1 | Schema + Migration + Service | ✓ Complete |
| Week 2 | Repository Pattern + Integration | ✓ Complete |
| Week 3 | Replay Implementation | ✓ Complete |
| Week 4 | Deploy to Test | ✓ Complete |

### ADR-010 Acceptance Criteria

- [x] LLM execution logging captures all runs
- [x] Content deduplication working (hash-based)
- [x] Replay endpoint functional
- [x] Comparison logic returns token/output deltas
- [x] Deployed to test environment
- [x] End-to-end verification passed

---

## Conclusion

ADR-010 is **COMPLETE**. The Combine now has:

1. **Full LLM telemetry** - Every call logged with inputs, outputs, tokens, timing
2. **Content deduplication** - Efficient storage via SHA-256 hashing
3. **Replay capability** - Re-execute any run with identical inputs
4. **Automated deployment** - Push to main → test environment updated

The system is ready for production deployment when approved.
