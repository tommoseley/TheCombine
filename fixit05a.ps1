# Create task role
aws iam create-role `
  --role-name ecsTaskRole `
  --assume-role-policy-document file://task-execution-trust-policy.json

# Create exec policy WITHOUT BOM
$execPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    }
  ]
}
"@

# Write without BOM
[System.IO.File]::WriteAllText("$PWD\ecs-exec-policy.json", $execPolicy)

# Attach policy
aws iam put-role-policy `
  --role-name ecsTaskRole `
  --policy-name ECSExecPolicy `
  --policy-document file://ecs-exec-policy.json

Write-Host "✅ Task Role created with exec access"