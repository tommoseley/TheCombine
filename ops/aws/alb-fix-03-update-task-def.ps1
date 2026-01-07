# =============================================================================
# Step 3: Update task definition for ALB
# =============================================================================
# Updates DOMAIN and HTTPS_ONLY for proper ALB operation

Write-Host "=== Step 3: Updating task definition for ALB ===" -ForegroundColor Yellow

$tempFile = "$PSScriptRoot\task-def-alb.json"

if (-not (Test-Path $tempFile)) {
    Write-Host "ERROR: task-def-alb.json not found" -ForegroundColor Red
    exit 1
}

Write-Host "Registering new task definition..."
$resultJson = aws ecs register-task-definition --cli-input-json file://$tempFile
$result = $resultJson | ConvertFrom-Json

if ($result.taskDefinition) {
    $newRevision = $result.taskDefinition.revision
    Write-Host "New task definition registered: the-combine-task:$newRevision" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Updating service to use new task definition..."
    aws ecs update-service `
        --cluster the-combine-cluster `
        --service the-combine-service `
        --task-definition "the-combine-task:$newRevision" `
        --force-new-deployment
    
    Write-Host ""
    Write-Host "=== Task definition updated ===" -ForegroundColor Green
    Write-Host "Service will rolling-deploy with new settings."
    Write-Host "Wait 2-3 minutes, then test: curl -I https://thecombine.ai"
} else {
    Write-Host "ERROR: Failed to register task definition" -ForegroundColor Red
}