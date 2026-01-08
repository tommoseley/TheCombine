# Get current task def as JSON string
$json = aws ecs describe-task-definition --task-definition the-combine-task:21 --query 'taskDefinition' --output json

# Replace DOMAIN value
$json = $json -replace '"name":\s*"DOMAIN",\s*"value":\s*"thecombine.ai"', '"name": "DOMAIN", "value": "www.thecombine.ai"'

# Remove read-only fields
$obj = $json | ConvertFrom-Json
$obj.PSObject.Properties.Remove('taskDefinitionArn')
$obj.PSObject.Properties.Remove('revision')
$obj.PSObject.Properties.Remove('status')
$obj.PSObject.Properties.Remove('requiresAttributes')
$obj.PSObject.Properties.Remove('compatibilities')
$obj.PSObject.Properties.Remove('registeredAt')
$obj.PSObject.Properties.Remove('registeredBy')

# Save to file
$obj | ConvertTo-Json -Depth 20 | Set-Content -Path "taskdef-www.json" -Encoding UTF8

# Register new task definition
aws ecs register-task-definition --cli-input-json file://taskdef-www.json

# Update service
aws ecs update-service --cluster the-combine-cluster --service the-combine-service --task-definition the-combine-task --force-new-deployment