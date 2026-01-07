# =============================================================================
# Step 1: Delete existing ECS service (no ALB attached)
# =============================================================================
# Run this first, then wait for completion before running step 2

$cluster = "the-combine-cluster"
$service = "the-combine-service"

Write-Host "=== Step 1: Deleting existing service ===" -ForegroundColor Yellow

# Scale down to 0
Write-Host "Scaling down service to 0 tasks..."
aws ecs update-service --cluster $cluster --service $service --desired-count 0

Write-Host "Waiting 30 seconds for tasks to drain..."
Start-Sleep -Seconds 30

# Delete the service
Write-Host "Deleting service..."
aws ecs delete-service --cluster $cluster --service $service

Write-Host ""
Write-Host "=== Service deletion initiated ===" -ForegroundColor Green
Write-Host "Wait 1-2 minutes, then run: .\alb-fix-02-create-service.ps1"