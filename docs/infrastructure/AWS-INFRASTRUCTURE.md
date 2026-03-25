# AWS Infrastructure — The Combine

**Last Audited:** 2026-03-25
**Region:** us-east-1
**Account:** 303985543798
**Domain:** thecombine.ai / www.thecombine.ai

---

## Architecture Overview

```
User (HTTPS)
  │
  ▼
Route 53 (thecombine.ai → ALB alias)
  │
  ▼
ALB (the-combine-alb)
  ├── :443 HTTPS → forward to target group (TLS termination)
  └── :80 HTTP → redirect to HTTPS
  │
  ▼
Target Group (the-combine-tg, port 8000, IP target type)
  │
  ▼
ECS Fargate Task (the-combine-service)
  ├── Container: the-combine (port 8000, uvicorn)
  ├── Secrets: ANTHROPIC_API_KEY, DATABASE_URL (from Secrets Manager)
  └── Logs: CloudWatch /ecs/the-combine
  │
  ▼
RDS PostgreSQL (combine-devtest, port 5432)
  ├── combine_dev (development)
  ├── combine_test (testing)
  └── combine_prod (via db-prod secret, separate DB on same instance)
```

---

## 1. DNS (Route 53)

| Record | Type | Target |
|--------|------|--------|
| `thecombine.ai` | A (Alias) | `the-combine-alb-1273570928.us-east-1.elb.amazonaws.com` |
| `www.thecombine.ai` | CNAME | `thecombine.ai` |
| `app.thecombine.ai` | CNAME | `bcgsppubhf.us-east-1.awsapprunner.com` (legacy App Runner) |

**Hosted Zone ID:** `Z1048118IKS45MJ7WHZX`

**IMPORTANT:** DNS points to the ALB, NOT to the ECS task's public IP. The ALB handles HTTPS termination. Do NOT update DNS on redeployment — the ALB target group auto-registers new tasks.

### ACM Certificate

| Field | Value |
|-------|-------|
| ARN | `arn:aws:acm:us-east-1:303985543798:certificate/51a1906d-06cb-4575-a05b-5fc963d79963` |
| Domain | `thecombine.ai` |
| SANs | `thecombine.ai`, `*.thecombine.ai` |
| Status | ISSUED (Amazon-issued, auto-renewing) |
| Used by | ALB `the-combine-alb` |

---

## 2. Load Balancer (ALB)

| Field | Value |
|-------|-------|
| Name | `the-combine-alb` |
| DNS | `the-combine-alb-1273570928.us-east-1.elb.amazonaws.com` |
| Scheme | internet-facing |
| Type | application |
| VPC | `vpc-e806728e` (default VPC) |
| Subnets | `subnet-b2bb9f9f` (us-east-1a), `subnet-f01703b9` (us-east-1b) |
| Security Group | `sg-6b401a17` (default — allows all inbound) |
| Hosted Zone ID | `Z35SXDOTRQ7X7K` (for Route 53 alias) |

### Listeners

| Port | Protocol | Action | TLS Policy | Certificate |
|------|----------|--------|------------|-------------|
| 443 | HTTPS | Forward to `the-combine-tg` | `ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09` | ACM wildcard cert |
| 80 | HTTP | Redirect to HTTPS | — | — |

### Target Group

| Field | Value |
|-------|-------|
| Name | `the-combine-tg` |
| Port | 8000 |
| Protocol | HTTP |
| Target Type | ip |
| Health Check Path | `/health` |
| Health Check Interval | 30s |
| Healthy Threshold | 2 |
| Unhealthy Threshold | 3 |

---

## 3. ECS (Fargate)

### Cluster

| Field | Value |
|-------|-------|
| Name | `the-combine-cluster` |
| Status | ACTIVE |

### Service

| Field | Value |
|-------|-------|
| Name | `the-combine-service` |
| Launch Type | FARGATE |
| Platform Version | LATEST |
| Desired Count | 1 |
| Deployment Strategy | ROLLING (max 200%, min 100%) |
| Circuit Breaker | Disabled |
| Subnets | `subnet-b2bb9f9f` (us-east-1a), `subnet-7213804e` (us-east-1e) |
| Security Group | `sg-0f56d0abd2aa04e8b` (the-combine-ecs-sg) |
| Public IP | ENABLED |
| Load Balancer | `the-combine-tg` → container `the-combine` port 8000 |

### Task Definition

| Field | Value |
|-------|-------|
| Family | `the-combine-task` |
| Current Revision | 108 |
| CPU | 256 (0.25 vCPU) |
| Memory | 512 MB |
| Network Mode | awsvpc |
| Execution Role | `ecsTaskExecutionRole` |
| Task Role | `ecsTaskRole` |

### Container Definition

| Field | Value |
|-------|-------|
| Name | `the-combine` |
| Image | `303985543798.dkr.ecr.us-east-1.amazonaws.com/the-combine:<commit-sha>` |
| Port | 8000 (TCP) |
| Log Driver | awslogs → `/ecs/the-combine` |

### Environment Variables (set in task definition)

| Variable | Source | Notes |
|----------|--------|-------|
| `ANTHROPIC_API_KEY` | Secrets Manager | `the-combine/anthropic-api-key` |
| `DATABASE_URL` | Secrets Manager | `the-combine/db-prod` (JSON key: `DATABASE_URL`) |
| `ENVIRONMENT` | Plain text | `production` |
| `DOMAIN` | Plain text | `www.thecombine.ai` |
| `HTTPS_ONLY` | Plain text | `true` |
| `ADMIN_EMAILS` | Plain text | `tommoseley@outlook.com` |
| `SESSION_SECRET_KEY` | Plain text | Session signing key |
| `GOOGLE_CLIENT_ID` | Plain text | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Plain text | OAuth client secret |
| `MICROSOFT_CLIENT_ID` | Plain text | OAuth client ID |
| `MICROSOFT_CLIENT_SECRET` | Plain text | OAuth client secret |

**NOTE:** OAuth secrets are currently in plain-text environment variables, not Secrets Manager. Consider migrating to Secrets Manager for better security posture.

---

## 4. ECR (Container Registry)

| Field | Value |
|-------|-------|
| Repository | `the-combine` |
| URI | `303985543798.dkr.ecr.us-east-1.amazonaws.com/the-combine` |
| Encryption | AES256 |
| Scan on Push | Disabled |
| Image Size | ~203 MB |
| Tagging | Commit SHA + `latest` |

---

## 5. RDS (PostgreSQL)

| Field | Value |
|-------|-------|
| Instance | `combine-devtest` |
| Engine | PostgreSQL 18.1 |
| Class | `db.t3.micro` |
| Storage | 20 GB (gp2) |
| Multi-AZ | No |
| Publicly Accessible | Yes |
| Endpoint | `combine-devtest.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com:5432` |
| Master Username | `combine_admin` |
| Security Group | `sg-0edb6a93c034f7e38` (combine-devtest-sg) |

### Databases

| Database | Purpose | Secret |
|----------|---------|--------|
| `combine_dev` | Development | `the-combine/db-dev` |
| `combine_test` | Testing | `the-combine/db-test` |
| `combine_prod` | Production (ECS uses this) | `the-combine/db-prod` |

**NOTE:** All three databases are on the same RDS instance (`combine-devtest`). Production should eventually move to a dedicated instance.

---

## 6. Networking

### VPC

| Field | Value |
|-------|-------|
| VPC ID | `vpc-e806728e` |
| CIDR | `172.31.0.0/16` |
| Type | Default VPC |

### Subnets Used

| Subnet | AZ | CIDR | Used By |
|--------|----|------|---------|
| `subnet-b2bb9f9f` | us-east-1a | `172.31.64.0/20` | ECS, ALB |
| `subnet-7213804e` | us-east-1e | `172.31.48.0/20` | ECS |
| `subnet-f01703b9` | us-east-1b | `172.31.16.0/20` | ALB |

### Security Groups

#### `sg-6b401a17` — ALB Security Group (default VPC SG)

| Protocol | Port | Source | Notes |
|----------|------|--------|-------|
| All | All | `0.0.0.0/0` | Wide open — allows all inbound |
| TCP | 5432 | `0.0.0.0/0` | PostgreSQL (should be removed from ALB SG) |

**WARNING:** This SG is too permissive. The ALB should only allow TCP 80 and 443 from `0.0.0.0/0`.

#### `sg-0f56d0abd2aa04e8b` — ECS Task Security Group

| Protocol | Port | Source | Notes |
|----------|------|--------|-------|
| TCP | 8000 | `0.0.0.0/0` | App port — should restrict to ALB SG only |

**NOTE:** ECS SG allows 8000 from anywhere. Should be restricted to ALB security group source.

#### `sg-0edb6a93c034f7e38` — RDS Security Group

| Protocol | Port | Source | Notes |
|----------|------|--------|-------|
| TCP | 5432 | `75.189.68.234/32` | Home IP only |

**NOTE:** RDS SG only allows home IP. ECS tasks access the DB via the same VPC (no SG rule needed since default VPC SG allows internal traffic).

---

## 7. Secrets Manager

| Secret | Description | Used By |
|--------|-------------|---------|
| `the-combine/anthropic-api-key` | Anthropic API key for Claude | ECS task (injected as env var) |
| `the-combine/db-prod` | Production DB credentials (JSON with DATABASE_URL key) | ECS task (injected as env var) |
| `the-combine/db-dev` | Dev DB credentials | Local development (`ops/scripts/db_connect.sh dev`) |
| `the-combine/db-test` | Test DB credentials | Local testing (`ops/scripts/db_connect.sh test`) |
| `the-combine/db-devtest-master` | RDS master credentials | DB administration |

---

## 8. IAM Roles

### `ecsTaskExecutionRole` — ECS pulls images and reads secrets

**Managed Policies:**
- `AmazonECSTaskExecutionRolePolicy`

**Inline Policies:**
- `SecretsManagerAccess` — GetSecretValue for anthropic-api-key and db-prod
- `CloudWatchLogsFullPolicy` — CreateLogGroup, CreateLogStream, PutLogEvents
- `CloudWatchLogsPolicy` — (duplicate of above, should be consolidated)

### `ecsTaskRole` — ECS task runtime permissions

**Policies:** None attached (task has no AWS API access at runtime)

### `the-combine-github-actions` — CI/CD via OIDC

**Trust:** GitHub OIDC provider (no stored credentials)

**Inline Policy (`the-combine-github-actions-policy`):**
- ECR: Login, push/pull images to `the-combine` repository
- ECS: Describe and update services, register task definitions
- EC2: Describe network interfaces (for deployment summary)
- Route53: Change record sets (for DNS updates — not currently used by CI)
- IAM: PassRole for execution and task roles

---

## 9. CI/CD Pipeline (GitHub Actions)

**Workflow:** `.github/workflows/deploy.yml`
**Trigger:** Push to `main` branch
**Authentication:** GitHub OIDC → `the-combine-github-actions` role (no stored AWS credentials)

### GitHub Repository Variables

| Variable | Value |
|----------|-------|
| `AWS_ROLE_ARN` | `arn:aws:iam::303985543798:role/the-combine-github-actions` |
| `ANTHROPIC_SECRET_ARN` | `arn:aws:secretsmanager:us-east-1:303985543798:secret:the-combine/anthropic-api-key-eHaYY3` |
| `DB_PROD_SECRET_ARN` | `arn:aws:secretsmanager:us-east-1:303985543798:secret:the-combine/db-prod-bJix3T` |

### Pipeline Jobs

| Job | Trigger | Duration | What it does |
|-----|---------|----------|--------------|
| **Test** | All pushes + PRs | ~2m40s | pytest against ephemeral Postgres 15 |
| **Build & Deploy** | main push only | ~13m | Build Docker → push to ECR → update ECS task def → rolling deploy |
| **Smoke Test** | After deploy | ~30s | curl `https://www.thecombine.ai/health` with retries |
| **Notify** | After smoke test | ~5s | Log deployment status |

### Deployment Flow

```
git push main
  → GitHub Actions triggered
  → Test job: pytest against CI Postgres
  → Build: docker build → ECR push (tagged with commit SHA + latest)
  → Deploy: register new task def → update ECS service → wait for stability
  → Smoke test: health check via ALB
  → ALB auto-registers new task IP (NO DNS update needed)
```

**IMPORTANT:** The ALB target group handles task registration automatically. DNS does NOT need updating on redeployment. The `fixip.ps1` script and Route 53 updates are only needed if the ALB itself changes (which it doesn't).

---

## 10. CloudWatch

| Field | Value |
|-------|-------|
| Log Group | `/ecs/the-combine` |
| Retention | Unlimited (no policy set) |
| Stored | ~140 MB |

**NOTE:** No log retention policy. Consider setting 30-day or 90-day retention to manage costs.

---

## 11. Known Issues and Recommendations

### Security

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| ALB SG (`sg-6b401a17`) allows all inbound traffic | Medium | Restrict to TCP 80, 443 from `0.0.0.0/0` only |
| ECS SG allows port 8000 from `0.0.0.0/0` | Low | Restrict to ALB security group source |
| OAuth secrets in plain-text env vars | Medium | Migrate to Secrets Manager |
| Duplicate CloudWatch IAM policies | Low | Consolidate into single policy |
| No CloudWatch log retention | Low | Set 30-day or 90-day retention |

### Architecture

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| Prod DB on same instance as dev/test | Medium | Dedicated RDS instance for production |
| Single Fargate task (no HA) | Low (acceptable for MVP) | Add second task + AZ for HA when needed |
| `app.thecombine.ai` still points to App Runner | Low | Clean up or repurpose |
| `fixip.ps1` is misleading | Low | Delete or document as obsolete |

---

## 12. Staging Environment Blueprint

To create a staging environment that mirrors production:

### Resources to Duplicate

| Resource | Production | Staging Equivalent |
|----------|-----------|-------------------|
| ECS Cluster | `the-combine-cluster` | `the-combine-staging-cluster` |
| ECS Service | `the-combine-service` | `the-combine-staging-service` |
| Task Definition | `the-combine-task` | `the-combine-staging-task` |
| ALB | `the-combine-alb` | `the-combine-staging-alb` |
| Target Group | `the-combine-tg` | `the-combine-staging-tg` |
| ECR | `the-combine` (shared) | Same repo, different tag convention |
| RDS Database | `combine_prod` | `combine_staging` (on same or separate instance) |
| Secret | `the-combine/db-prod` | `the-combine/db-staging` |
| DNS | `www.thecombine.ai` | `staging.thecombine.ai` |
| ACM Cert | Wildcard `*.thecombine.ai` | Same cert (wildcard covers staging) |

### What Can Be Shared

- ECR repository (use `staging-<sha>` tags)
- VPC and subnets
- ACM wildcard certificate
- GitHub Actions workflow (add staging deploy job triggered by staging branch)

### What Must Be Separate

- ECS cluster/service/task (different env vars, different DB secret)
- ALB + target group (separate endpoint)
- RDS database (separate schema or instance)
- Secrets Manager entries (staging credentials)
- Route 53 record (`staging.thecombine.ai`)
