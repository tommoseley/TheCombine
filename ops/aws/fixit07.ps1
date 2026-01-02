# Part 7: Create Task Definition (PowerShell Fixed)

# Get necessary variables
$ACCOUNT_ID = "303985543798"
$REGION = "us-east-1"

# Get database endpoint if not already set
if (-not $DB_ENDPOINT) {
    $DB_ENDPOINT = aws rds describe-db-instances --db-instance-identifier the-combine-db --query 'DBInstances[0].Endpoint.Address' --output text --region $REGION
}

# Build DATABASE_URL
$DB_PASSWORD = "Gamecocks4896!"
$DATABASE_URL = "postgresql://combine_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/combine"

Write-Host "Account ID: $ACCOUNT_ID"
Write-Host "Region: $REGION"
Write-Host "Database: $DB_ENDPOINT"
Write-Host "DATABASE_URL: $DATABASE_URL"

# Create task definition JSON
$taskDefJson = @"
{
  "family": "the-combine-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "the-combine",
      "image": "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/the-combine:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "$DATABASE_URL"
        },
        {
          "name": "ENVIRONMENT",
          "value": "prod"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/the-combine",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "essential": true
    }
  ]
}
"@

# Write JSON without BOM
[System.IO.File]::WriteAllText("$PWD\task-definition.json", $taskDefJson)

# Verify JSON is valid
Write-Host "Verifying JSON..."
try {
    Get-Content task-definition.json | ConvertFrom-Json | Out-Null
    Write-Host "✅ JSON is valid"
} catch {
    Write-Host "❌ JSON validation failed: $_"
    exit 1
}

# Register task definition
Write-Host "Registering task definition..."
aws ecs register-task-definition --cli-input-json file://task-definition.json --region $REGION

Write-Host "✅ Task Definition registered"

# Verify it was created
aws ecs describe-task-definition --task-definition the-combine-task --region $REGION --query 'taskDefinition.taskDefinitionArn'