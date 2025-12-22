# The Combine - AWS Infrastructure (Hardened)

Production-ready infrastructure with security best practices.

## Security Features

| Feature | Implementation |
|---------|----------------|
| **Secrets Management** | AWS Secrets Manager (not env vars) |
| **CI/CD Authentication** | GitHub OIDC (no stored keys) |
| **Migration Safety** | PostgreSQL advisory locks |
| **Network Isolation** | VPC connector for RDS access |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions                          │
│                           │                                  │
│                     OIDC (no keys)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        AWS IAM                               │
│              (Assume role via OIDC)                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────┐     ┌─────────────────────────────────┐
│        ECR          │     │      Secrets Manager            │
│   (Docker images)   │     │  - DB password                  │
└─────────┬───────────┘     │  - Anthropic API key            │
          │                 │  - Secret key                   │
          ▼                 └─────────────┬───────────────────┘
┌─────────────────────────────────────────┼───────────────────┐
│              AWS App Runner             │                   │
│                                         │                   │
│  ┌───────────────────────────────────┐  │                   │
│  │  The Combine Container            │◄─┘                   │
│  │  - Fetches secrets at startup     │   (reads secrets)    │
│  │  - Advisory lock for migrations   │                      │
│  │  - Health check: /health          │                      │
│  └───────────────────────────────────┘                      │
│                    │                                        │
│              VPC Connector                                  │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  RDS PostgreSQL                             │
│                  (Private subnet)                           │
└─────────────────────────────────────────────────────────────┘
```

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| App Runner (0.25 vCPU, 0.5GB) | ~$5-15 |
| RDS PostgreSQL (db.t3.micro) | ~$15 (or free tier) |
| Secrets Manager (3 secrets) | ~$1.20 |
| Route 53 hosted zone | $0.50 |
| Data transfer | ~$1-5 |
| **Total** | **~$22-37/month** |

## Prerequisites

1. **AWS CLI** configured (`aws sts get-caller-identity` works)
2. **Terraform** installed (`brew install terraform`)
3. **Docker** installed (for local testing)
4. **Route 53** domain registered (`thecombine.ui`)
5. **GitHub repository** for the code

## Quick Start

### 1. Get Route 53 Zone ID

```bash
aws route53 list-hosted-zones --query 'HostedZones[?Name==`thecombine.ui.`].Id' --output text
# Returns: /hostedzone/ZXXXXXXXXXXXXX
# Use just the ID part: ZXXXXXXXXXXXXX
```

### 2. Configure Variables

```bash
cd terraform

# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values:
# - route53_zone_id (from step 1)
# - github_repository (e.g., "tmoseley/the-combine")
# - db_password (generate: openssl rand -base64 24)
# - anthropic_api_key
# - secret_key (generate: openssl rand -hex 16)
```

Or use environment variables (more secure):
```bash
export TF_VAR_db_password="$(openssl rand -base64 24)"
export TF_VAR_anthropic_api_key="sk-ant-..."
export TF_VAR_secret_key="$(openssl rand -hex 16)"
export TF_VAR_route53_zone_id="ZXXXXXXXXXXXXX"
export TF_VAR_github_repository="your-username/the-combine"
```

### 3. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy (takes ~10-15 minutes for RDS)
terraform apply
```

### 4. Configure GitHub Repository

After `terraform apply`, get the role ARN:
```bash
terraform output github_actions_role_arn
```

In your GitHub repository:
1. Go to **Settings → Secrets and variables → Actions**
2. Click **Variables** tab (not Secrets!)
3. Add repository variable:
   - Name: `AWS_ROLE_ARN`
   - Value: (the ARN from terraform output)

### 5. Push First Docker Image

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(terraform output -raw ecr_repository_url | cut -d/ -f1)

# Build (from project root)
cd ../..
docker build -f infrastructure/Dockerfile -t the-combine .

# Tag and push
ECR_URL=$(cd infrastructure/terraform && terraform output -raw ecr_repository_url)
docker tag the-combine:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### 6. Verify Deployment

```bash
# Check App Runner status
aws apprunner list-services --query 'ServiceSummaryList[*].[ServiceName,Status]' --output table

# Test health endpoint (after a few minutes)
curl https://thecombine.ui/health
```

## Directory Structure

```
infrastructure/
├── Dockerfile                    # Production image (with boto3)
├── scripts/
│   └── docker-entrypoint.sh     # Secrets fetch + migration lock
├── terraform/
│   ├── main.tf                  # Provider config
│   ├── variables.tf             # Input variables
│   ├── secrets.tf               # 🔐 AWS Secrets Manager
│   ├── ecr.tf                   # Container registry
│   ├── rds.tf                   # PostgreSQL database
│   ├── apprunner.tf             # App Runner (reads from Secrets Manager)
│   ├── route53.tf               # DNS + SSL
│   ├── iam-github-oidc.tf       # 🔑 GitHub OIDC (no access keys)
│   ├── outputs.tf               # Useful outputs
│   └── terraform.tfvars.example
└── .github/
    └── workflows/
        └── deploy.yml           # CI/CD with OIDC auth
```

## How It Works

### Secrets Flow

1. Terraform creates secrets in AWS Secrets Manager
2. Terraform passes secret **ARNs** (not values) to App Runner as env vars
3. Container startup script uses boto3 to fetch actual secret values
4. Values are loaded into environment for the application

**Benefits:**
- Terraform state contains only ARNs
- Secrets never appear in container env vars in AWS console
- Easy rotation (update Secrets Manager, restart container)

### Migration Safety

1. Container starts and fetches secrets
2. Waits for database connectivity
3. Acquires PostgreSQL advisory lock (blocks other instances)
4. Runs migrations
5. Releases lock
6. Seeds data (idempotent)
7. Starts uvicorn

**Benefits:**
- No race conditions when scaling to multiple instances
- Only one instance runs migrations at a time
- Others wait or skip if already done

### GitHub OIDC

1. GitHub Actions requests an OIDC token from GitHub
2. Token contains claims about the repo and workflow
3. AWS validates token against configured OIDC provider
4. AWS returns temporary credentials (15 min - 1 hour)
5. No stored secrets in GitHub

**Benefits:**
- No access keys to rotate or leak
- Credentials are temporary and scoped
- Easy to audit (CloudTrail shows assumed role)

## Operations

### Rotate a Secret

```bash
# Update secret in Secrets Manager
aws secretsmanager update-secret \
  --secret-id the-combine/anthropic-api-key \
  --secret-string "sk-ant-new-key-here"

# Force App Runner to restart and pick up new secret
aws apprunner start-deployment \
  --service-arn $(aws apprunner list-services \
    --query 'ServiceSummaryList[?ServiceName==`the-combine`].ServiceArn' \
    --output text)
```

### View Logs

```bash
# Find log group
aws logs describe-log-groups \
  --log-group-name-prefix /aws/apprunner/the-combine

# Tail logs
aws logs tail /aws/apprunner/the-combine/xxx --follow
```

### Connect to Database

Database is not publicly accessible. Options:

1. **Bastion host** (add an EC2 instance in VPC)
2. **SSM Session Manager** (if you have an EC2)
3. **Temporarily enable public access** (not recommended)

### Force Redeploy

```bash
aws apprunner start-deployment \
  --service-arn $(aws apprunner list-services \
    --query 'ServiceSummaryList[?ServiceName==`the-combine`].ServiceArn' \
    --output text)
```

### Destroy Everything

```bash
cd terraform
terraform destroy
```

⚠️ This deletes the database! RDS snapshots are kept for 7 days.

## Troubleshooting

### "Unable to assume role" in GitHub Actions
- Verify `AWS_ROLE_ARN` variable is set correctly in GitHub
- Check the `github_repository` variable in Terraform matches exactly
- Ensure workflow has `permissions: id-token: write`

### Container keeps restarting
- Check CloudWatch logs for the entrypoint script
- Verify secrets exist in Secrets Manager
- Check database connectivity (VPC connector attached?)

### Migrations failing
- Check advisory lock isn't stuck (shouldn't happen, but restart DB if so)
- Verify `init_db.py` is idempotent
- Check CloudWatch logs for specific error

### Health check failing
- Ensure `/health` endpoint exists and returns 200
- Check container has time to start (adjust `start-period` in Dockerfile)
- Verify database is accessible from App Runner

## Next Steps

1. **Add staging environment** - Duplicate Terraform with `environment = "staging"`
2. **Set up CloudWatch alarms** - Alert on 5xx errors, high latency
3. **Enable AWS WAF** - Web Application Firewall for production
4. **Add Terraform remote state** - S3 + DynamoDB for team use
