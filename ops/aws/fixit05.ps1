# Create trust policy file
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@ | Out-File -FilePath task-execution-trust-policy.json -Encoding utf8

# Create role
aws iam create-role `
  --role-name ecsTaskExecutionRole `
  --assume-role-policy-document file://task-execution-trust-policy.json

# Attach policy
aws iam attach-role-policy `
  --role-name ecsTaskExecutionRole `
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

Write-Host "✅ Task Execution Role created"
