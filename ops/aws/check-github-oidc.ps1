# Check GitHub OIDC Setup for AWS
# Run from a terminal with AWS CLI configured

$REGION = "us-east-1"
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GitHub OIDC Configuration Check" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Account ID: $ACCOUNT_ID"
Write-Host "Region: $REGION"
Write-Host ""

# 1. Check for GitHub OIDC Provider
Write-Host "1. Checking for GitHub OIDC Provider..." -ForegroundColor Yellow
$OIDC_PROVIDERS = aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[*].Arn' --output text

$GITHUB_OIDC = $OIDC_PROVIDERS | Select-String -Pattern "token.actions.githubusercontent.com"

if ($GITHUB_OIDC) {
    Write-Host "   [FOUND] GitHub OIDC Provider exists" -ForegroundColor Green
    $OIDC_ARN = ($OIDC_PROVIDERS -split '\s+' | Where-Object { $_ -match "token.actions.githubusercontent.com" })
    Write-Host "   ARN: $OIDC_ARN" -ForegroundColor Gray
} else {
    Write-Host "   [MISSING] GitHub OIDC Provider not found" -ForegroundColor Red
    Write-Host "   You need to create it first" -ForegroundColor Red
}
Write-Host ""

# 2. Look for roles that trust GitHub Actions
Write-Host "2. Checking for roles that trust GitHub Actions..." -ForegroundColor Yellow

$ROLES = aws iam list-roles --query 'Roles[*].RoleName' --output text
$GITHUB_ROLES = @()

foreach ($role in ($ROLES -split '\s+')) {
    $trustPolicy = aws iam get-role --role-name $role --query 'Role.AssumeRolePolicyDocument' --output json 2>$null
    if ($trustPolicy -match "token.actions.githubusercontent.com") {
        $GITHUB_ROLES += $role
    }
}

if ($GITHUB_ROLES.Count -gt 0) {
    Write-Host "   [FOUND] Roles trusting GitHub Actions:" -ForegroundColor Green
    foreach ($role in $GITHUB_ROLES) {
        $roleArn = "arn:aws:iam::${ACCOUNT_ID}:role/$role"
        Write-Host "   - $role" -ForegroundColor Green
        Write-Host "     ARN: $roleArn" -ForegroundColor Gray
        
        # Check attached policies
        Write-Host "     Attached Policies:" -ForegroundColor Gray
        $attachedPolicies = aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[*].PolicyName' --output text
        if ($attachedPolicies) {
            foreach ($policy in ($attachedPolicies -split '\s+')) {
                Write-Host "       - $policy" -ForegroundColor Gray
            }
        }
        
        # Check inline policies
        $inlinePolicies = aws iam list-role-policies --role-name $role --query 'PolicyNames' --output text
        if ($inlinePolicies -and $inlinePolicies -ne "None") {
            Write-Host "     Inline Policies:" -ForegroundColor Gray
            foreach ($policy in ($inlinePolicies -split '\s+')) {
                Write-Host "       - $policy" -ForegroundColor Gray
            }
        }
        
        # Show trust policy conditions
        Write-Host "     Trust Policy Conditions:" -ForegroundColor Gray
        $trustDoc = aws iam get-role --role-name $role --query 'Role.AssumeRolePolicyDocument.Statement[0].Condition' --output json 2>$null
        if ($trustDoc -and $trustDoc -ne "null") {
            $trustDoc -split "`n" | ForEach-Object { Write-Host "       $_" -ForegroundColor Gray }
        }
        Write-Host ""
    }
} else {
    Write-Host "   [MISSING] No roles found that trust GitHub Actions" -ForegroundColor Red
}
Write-Host ""

# 3. Check GitHub repo variable (reminder)
Write-Host "3. GitHub Repository Configuration" -ForegroundColor Yellow
Write-Host "   Make sure you have set these in GitHub:" -ForegroundColor Gray
Write-Host "   Settings > Secrets and variables > Actions > Variables" -ForegroundColor Gray
Write-Host ""
if ($GITHUB_ROLES.Count -gt 0) {
    $suggestedArn = "arn:aws:iam::${ACCOUNT_ID}:role/$($GITHUB_ROLES[0])"
    Write-Host "   AWS_ROLE_ARN = $suggestedArn" -ForegroundColor Cyan
} else {
    Write-Host "   AWS_ROLE_ARN = (create role first)" -ForegroundColor Red
}
Write-Host ""

# 4. Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if ($GITHUB_OIDC -and $GITHUB_ROLES.Count -gt 0) {
    Write-Host "[READY] GitHub OIDC is configured" -ForegroundColor Green
    Write-Host ""
    Write-Host "Set this variable in GitHub Actions:" -ForegroundColor Yellow
    Write-Host "  AWS_ROLE_ARN = arn:aws:iam::${ACCOUNT_ID}:role/$($GITHUB_ROLES[0])" -ForegroundColor Cyan
} elseif ($GITHUB_OIDC) {
    Write-Host "[PARTIAL] OIDC Provider exists but no role configured" -ForegroundColor Yellow
    Write-Host "Run the role creation script" -ForegroundColor Yellow
} else {
    Write-Host "[NOT CONFIGURED] Need to set up GitHub OIDC" -ForegroundColor Red
    Write-Host "Run the OIDC setup script" -ForegroundColor Red
}
