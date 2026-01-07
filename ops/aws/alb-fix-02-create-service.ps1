# =============================================================================
# Step 2: Create ECS service WITH ALB attached
# =============================================================================
# Run this after alb-fix-01-delete-service.ps1 completes

$cluster = "the-combine-cluster"
$service = "the-combine-service"
$taskDef = "the-combine-task:13"
$targetGroupArn = "arn:aws:elasticloadbalancing:us-east-1:303985543798:targetgroup/the-combine-tg/1e28c0dd8a46d74c"
$containerName = "the-combine"
$containerPort = 8000
$subnets = "subnet-b2bb9f9f,subnet-7213804e"
$securityGroup = "sg-0f56d0abd2aa04e8b"

Write-Host "=== Step 2: Creating service with ALB ===" -ForegroundColor Yellow

# Check if old service still exists
$existingService = aws ecs describe-services --cluster $cluster --services $service --query 'services[0].status' --output text 2>$null
if ($existingService -eq "ACTIVE") {
    Write-Host "ERROR: Old service still exists. Wait for deletion or run step 1 again." -ForegroundColor Red
    exit 1
}

Write-Host "Creating new service with load balancer..."

aws ecs create-service `
    --cluster $cluster `
    --service-name $service `
    --task-definition $taskDef `
    --desired-count 1 `
    --launch-type FARGATE `
    --platform-version LATEST `
    --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$securityGroup],assignPublicIp=ENABLED}" `
    --load-balancers "targetGroupArn=$targetGroupArn,containerName=$containerName,containerPort=$containerPort" `
    --health-check-grace-period-seconds 120 `
    --enable-execute-command

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Service created with ALB ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "1. Wait 2-3 minutes for task to start and register with ALB"
    Write-Host "2. Test: curl -I https://thecombine.ai"
    Write-Host "3. Run: .\alb-fix-03-update-task-def.ps1 to fix environment variables"
} else {
    Write-Host "ERROR: Service creation failed" -ForegroundColor Red
}