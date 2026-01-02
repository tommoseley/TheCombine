# Setup GitHub OIDC for AWS - The Combine
# Run this ONCE to configure GitHub Actions to deploy to AWS

$ErrorActionPreference = "Stop"

# Use full path to AWS CLI
$awscli = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
Set-Alias -Name aws -Value $awscli -Scope Script

$REGION = "us-east-1"
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$GITHUB_ORG = "TomMoseley"          # <-- CHANGE THIS to your GitHub username or org
$GITHUB_REPO = "the-combine"        # <-- CHANGE THIS to your repo name
$ROLE_NAME = "GitHubActionsDeployRole"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GitHub OIDC Setup for AWS" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Account ID: $ACCOUNT_ID"
Write-Host "GitHub: $GITHUB_ORG/$GITHUB_REPO"
Write-Host "Role Name: $ROLE_NAME"
Write-Host ""

# ============================================================
# Step 1: Create OIDC Provider
# ============================================================
Write-Host "Step 1: Creating GitHub OIDC Provider..." -ForegroundColor Yellow

# Check if already exists
$existingProvider = aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[*].Arn' --output text 2>$null
if ($existingProvider -match "token.actions.githubusercontent.com") {
    Write-Host "   [SKIP] OIDC Provider already exists" -ForegroundColor Green
} else {
    # GitHub's OIDC thumbprint (this is stable)
    aws iam create-open-id-connect-provider `
        --url "https://token.actions.githubusercontent.com" `
        --client-id-list "sts.amazonaws.com" `
        --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" `
        --region $REGION
    
    Write-Host "   [CREATED] OIDC Provider" -ForegroundColor Green
}
Write-Host ""

# ============================================================
# Step 2: Create Trust Policy
# ============================================================
Write-Host "Step 2: Creating IAM Role with trust policy..." -ForegroundColor Yellow

$trustPolicy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
                }
            }
        }
    ]
}
"@

[System.IO.File]::WriteAllText("$PWD\github-trust-policy.json", $trustPolicy)

# Check if role exists
$existingRole = aws iam get-role --role-name $ROLE_NAME 2>$null
if ($existingRole) {
    Write-Host "   [SKIP] Role $ROLE_NAME already exists" -ForegroundColor Green
    Write-Host "   Updating trust policy..." -ForegroundColor Gray
    aws iam update-assume-role-policy --role-name $ROLE_NAME --policy-document file://github-trust-policy.json
} else {
    aws iam create-role `
        --role-name $ROLE_NAME `
        --assume-role-policy-document file://github-trust-policy.json `
        --description "Role for GitHub Actions to deploy The Combine"
    
    Write-Host "   [CREATED] Role $ROLE_NAME" -ForegroundColor Green
}
Write-Host ""

# ============================================================
# Step 3: Create and Attach Permissions Policy
# ============================================================
Write-Host "Step 3: Attaching permissions policy..." -ForegroundColor Yellow

$permissionsPolicy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECR",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECRRepo",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "arn:aws:ecr:${REGION}:${ACCOUNT_ID}:repository/the-combine"
        },
        {
            "Sid": "ECSRead",
            "Effect": "Allow",
            "Action": [
                "ecs:DescribeTaskDefinition",
                "ecs:DescribeServices",
                "ecs:ListTasks",
                "ecs:DescribeTasks"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECSWrite",
            "Effect": "Allow",
            "Action": [
                "ecs:RegisterTaskDefinition",
                "ecs:UpdateService"
            ],
            "Resource": "*"
        },
        {
            "Sid": "EC2Describe",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeNetworkInterfaces"
            ],
            "Resource": "*"
        },
        {
            "Sid": "Route53",
            "Effect": "Allow",
            "Action": [
                "route53:ListHostedZones",
                "route53:ChangeResourceRecordSets",
                "route53:GetHostedZone"
            ],
            "Resource": "*"
        },
        {
            "Sid": "PassRole",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
                "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskRole"
            ]
        }
    ]
}
"@

[System.IO.File]::WriteAllText("$PWD\github-deploy-policy.json", $permissionsPolicy)

# Create or update inline policy
aws iam put-role-policy `
    --role-name $ROLE_NAME `
    --policy-name "TheCombineDeployPolicy" `
    --policy-document file://github-deploy-policy.json

Write-Host "   [ATTACHED] Permissions policy" -ForegroundColor Green
Write-Host ""

# ============================================================
# Step 4: Output Results
# ============================================================
$ROLE_ARN = "arn:aws:iam::${ACCOUNT_ID}:role/$ROLE_NAME"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Role ARN:" -ForegroundColor Yellow
Write-Host "  $ROLE_ARN" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Go to GitHub repo: https://github.com/$GITHUB_ORG/$GITHUB_REPO" -ForegroundColor White
Write-Host "2. Settings > Secrets and variables > Actions > Variables" -ForegroundColor White
Write-Host "3. Click 'New repository variable'" -ForegroundColor White
Write-Host "4. Name: AWS_ROLE_ARN" -ForegroundColor White
Write-Host "   Value: $ROLE_ARN" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then push to main branch to trigger deployment!" -ForegroundColor Green

# Cleanup temp files
Remove-Item -Path "github-trust-policy.json" -ErrorAction SilentlyContinue
Remove-Item -Path "github-deploy-policy.json" -ErrorAction SilentlyContinue
