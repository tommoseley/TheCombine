# Get task ID
$TASK_ARN = aws ecs list-tasks `
  --cluster the-combine-cluster `
  --service-name the-combine-service `
  --query 'taskArns[0]' `
  --output text `
  --region us-east-1

$TASK_ID = $TASK_ARN.Split('/')[-1]

Write-Host "Task ID: $TASK_ID"

# Exec into container!
aws ecs execute-command `
  --cluster the-combine-cluster `
  --task $TASK_ID `
  --container the-combine `
  --interactive `
  --command "/bin/bash" `
  --region us-east-1

# Inside container:
# ls -la
# alembic current
# env | grep DATABASE
# exit