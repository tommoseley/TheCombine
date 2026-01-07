# =============================================================================
# Update Microsoft OAuth Credentials in ECS Task Definition
# =============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientSecret
)

Write-Host "=== Update Microsoft OAuth Credentials ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "New Client ID: $ClientId"
Write-Host "New Client Secret: $($ClientSecret.Substring(0,8))..."
Write-Host ""

# Get current task definition to preserve other settings
Write-Host "Fetching current task definition..."
$currentTaskDef = aws ecs describe-task-definition --task-definition the-combine-task --query 'taskDefinition' | ConvertFrom-Json

# Build environment array with updated Microsoft credentials
$environment = @(
    @{ name = "DATABASE_URL"; value = "postgresql://combine_admin:Gamecocks4896!@the-combine-db.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com:5432/combine" }
    @{ name = "ENVIRONMENT"; value = "production" }
    @{ name = "DOMAIN"; value = "thecombine.ai" }
    @{ name = "HTTPS_ONLY"; value = "true" }
    @{ name = "SESSION_SECRET_KEY"; value = "f6a76b9846ee64c4630c190cd7dd1510f734346d58a5582e827441c64ae9a88c" }
    @{ name = "GOOGLE_CLIENT_ID"; value = "1026213722180-cg52unse2snmbp2ee2b3v1eivls6bn5f.apps.googleusercontent.com" }
    @{ name = "GOOGLE_CLIENT_SECRET"; value = "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" }
    @{ name = "MICROSOFT_CLIENT_ID"; value = $ClientId }
    @{ name = "MICROSOFT_CLIENT_SECRET"; value = $ClientSecret }
)

$taskDef = @{
    family = "the-combine-task"
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = "256"
    memory = "512"
    executionRoleArn = "arn:aws:iam::303985543798:role/ecsTaskExecutionRole"
    taskRoleArn = "arn:aws:iam::303985543798:role/ecsTaskRole"
    containerDefinitions = @(
        @{
            name = "the-combine"
            image = "303985543798.dkr.ecr.us-east-1.amazonaws.com/the-combine:latest"
            portMappings = @(
                @{
                    containerPort = 8000
                    protocol = "tcp"
                }
            )
            environment = $environment
            logConfiguration = @{
                logDriver = "awslogs"
                options = @{
                    "awslogs-group" = "/ecs/the-combine"
                    "awslogs-region" = "us-east-1"
                    "awslogs-stream-prefix" = "ecs"
                    "awslogs-create-group" = "true"
                }
            }
            essential = $true
        }
    )
}

# Write to temp file
$tempFile = "$PSScriptRoot\task-def-microsoft-update.json"
$taskDef | ConvertTo-Json -Depth 10 | Set-Content $tempFile -Encoding UTF8
Write-Host "Created task definition: $tempFile"

# Register new task definition
Write-Host ""
Write-Host "Registering new task definition..."
$result = aws ecs register-task-definition --cli-input-json file://$tempFile | ConvertFrom-Json

if ($result.taskDefinition) {
    $newRevision = $result.taskDefinition.revision
    Write-Host "New task definition registered: the-combine-task:$newRevision" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Updating service to use new task definition..."
    aws ecs update-service `
        --cluster the-combine-cluster `
        --service the-combine-service `
        --task-definition "the-combine-task:$newRevision" `
        --force-new-deployment | Out-Null
    
    Write-Host ""
    Write-Host "=== Deployment started ===" -ForegroundColor Green
    Write-Host "New task with updated Microsoft credentials will be running in 2-3 minutes."
    Write-Host ""
    Write-Host "Test with: https://thecombine.ai/auth/login/microsoft"
} else {
    Write-Host "ERROR: Failed to register task definition" -ForegroundColor Red
}

# Cleanup temp file
Remove-Item $tempFile -ErrorAction SilentlyContinue