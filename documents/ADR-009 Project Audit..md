# Complete ECS Setup - PowerShell Version

## All Commands Converted for Windows PowerShell

---

## Part 1: Create ECR Repository

```powershell
# Create repository
aws ecr create-repository --repository-name the-combine --region us-east-1

# Save the URI
$ECR_URI = aws ecr describe-repositories `
  --repository-names the-combine `
  --query 'repositories[0].repositoryUri' `
  --output text `
  --region us-east-1

Write-Host "ECR Repository: $ECR_URI"
Write-Host "SAVE THIS!"
```

---

## Part 2: Create RDS Database

```powershell
# Set variables
$DB_PASSWORD = "YourSecurePassword123!"  # CHANGE THIS!
$REGION = "us-east-1"

# Create database
aws rds create-db-instance `
  --db-instance-identifier the-combine-db `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --engine-version 15.3 `
  --master-username combine_admin `
  --master-user-password "$DB_PASSWORD" `
  --allocated-storage 20 `
  --db-name combine `
  --publicly-accessible `
  --backup-retention-period 7 `
  --region $REGION

Write-Host "Creating database... (5-10 minutes)"

# Wait for database
aws rds wait db-instance-available `
  --db-instance-identifier the-combine-db `
  --region $REGION

Write-Host "✅ Database created!"

# Get endpoint
$DB_ENDPOINT = aws rds describe-db-instances `
  --db-instance-identifier the-combine-db `
  --query 'DBInstances[0].Endpoint.Address' `
  --output text `
  --region $REGION

Write-Host "Database endpoint: $DB_ENDPOINT"

# Get security group
$DB_SG = aws rds describe-db-instances `
  --db-instance-identifier the-combine-db `
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' `
  --output text `
  --region $REGION

# Open to all IPs (development only!)
aws ec2 authorize-security-group-ingress `
  --group-id $DB_SG `
  --protocol tcp `
  --port 5432 `
  --cidr 0.0.0.0/0 `
  --region $REGION

Write-Host "✅ Database accessible from anywhere"

# Build DATABASE_URL
$DATABASE_URL = "postgresql://combine_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/combine"
Write-Host ""
Write-Host "=========================================="
Write-Host "DATABASE_URL: $DATABASE_URL"
Write-Host "=========================================="
Write-Host "SAVE THIS!"
```

---

## Part 3: Create ECS Cluster

```powershell
# Create cluster
aws ecs create-cluster --cluster-name the-combine-cluster --region us-east-1

Write-Host "✅ ECS Cluster created"
```

---

## Part 4: Create Application Load Balancer

**See PART4_POWERSHELL.md for detailed version**

Quick version:
```powershell
$REGION = "us-east-1"

# Get VPC and subnets
$VPC_ID = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION
$SUBNET_IDS = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $REGION
$SUBNET_ARRAY = $SUBNET_IDS -split '\s+'

# Create ALB security group
$ALB_SG = aws ec2 create-security-group --group-name the-combine-alb-sg --description "Security group for The Combine ALB" --vpc-id $VPC_ID --region $REGION --output text --query 'GroupId'
aws ec2 authorize-security-group-ingress --group-id $ALB_SG --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION

# Create ALB
$ALB_ARN = aws elbv2 create-load-balancer --name the-combine-alb --subnets $SUBNET_ARRAY[0] $SUBNET_ARRAY[1] --security-groups $ALB_SG --scheme internet-facing --type application --region $REGION --query 'LoadBalancers[0].LoadBalancerArn' --output text
$ALB_DNS = aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].DNSName' --output text --region $REGION

# Create target group
$TG_ARN = aws elbv2 create-target-group --name the-combine-tg --protocol HTTP --port 8000 --vpc-id $VPC_ID --target-type ip --health-check-path /health --health-check-interval-seconds 30 --health-check-timeout-seconds 5 --healthy-threshold-count 2 --unhealthy-threshold-count 3 --region $REGION --query 'TargetGroups[0].TargetGroupArn' --output text

# Create listener
aws elbv2 create-listener --load-balancer-arn $ALB_ARN --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TG_ARN --region $REGION

Write-Host "✅ Load Balancer complete! URL: http://$ALB_DNS"
```

---

## Part 5: Create IAM Roles

### Task Execution Role

```powershell
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
```

### Task Role (for exec)

```powershell
# Create task role
aws iam create-role `
  --role-name ecsTaskRole `
  --assume-role-policy-document file://task-execution-trust-policy.json

# Create exec policy file
@"
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
"@ | Out-File -FilePath ecs-exec-policy.json -Encoding utf8

# Attach policy
aws iam put-role-policy `
  --role-name ecsTaskRole `
  --policy-name ECSExecPolicy `
  --policy-document file://ecs-exec-policy.json

Write-Host "✅ Task Role created with exec access"
```

---

## Part 6: Build and Push Docker Image

```powershell
# Make sure you have Dockerfile_minimal
Copy-Item Dockerfile_minimal Dockerfile -Force

# Build
docker build -t the-combine .

# Test locally FIRST!
Write-Host "Testing locally..."
Start-Job -ScriptBlock {
    docker run --rm -p 8000:8000 -e DATABASE_URL="$using:DATABASE_URL" the-combine
}

Start-Sleep -Seconds 5
$response = curl http://localhost:8000/health
Write-Host "Health check response: $response"

# Stop test container
docker stop $(docker ps -q --filter ancestor=the-combine)

# If test passed, push to ECR
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = "us-east-1"

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Tag and push
docker tag the-combine:latest "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/the-combine:latest"
docker push "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/the-combine:latest"

Write-Host "✅ Image pushed to ECR"
```

---

## Part 7: Create Task Definition

```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = "us-east-1"

# Create task definition JSON
@"
{
  "family": "the-combine-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "the-combine",
      "image": "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/the-combine:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "${DATABASE_URL}"
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
          "awslogs-region": "${REGION}",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "essential": true
    }
  ]
}
"@ | Out-File -FilePath task-definition.json -Encoding utf8

# Register task definition
aws ecs register-task-definition `
  --cli-input-json file://task-definition.json `
  --region $REGION

Write-Host "✅ Task Definition registered"
```

---

## Part 8: Create ECS Security Group

```powershell
# Create security group for ECS tasks
$ECS_SG = aws ec2 create-security-group `
  --group-name the-combine-ecs-sg `
  --description "Security group for The Combine ECS tasks" `
  --vpc-id $VPC_ID `
  --region $REGION `
  --output text `
  --query 'GroupId'

# Allow traffic from ALB
aws ec2 authorize-security-group-ingress `
  --group-id $ECS_SG `
  --protocol tcp `
  --port 8000 `
  --source-group $ALB_SG `
  --region $REGION

Write-Host "✅ ECS Security Group created: $ECS_SG"
```

---

## Part 9: Create ECS Service

```powershell
# Create service with exec enabled
aws ecs create-service `
  --cluster the-combine-cluster `
  --service-name the-combine-service `
  --task-definition the-combine-task `
  --desired-count 1 `
  --launch-type FARGATE `
  --platform-version LATEST `
  --enable-execute-command `
  --network-configuration "awsvpcConfiguration={subnets=[$($SUBNET_ARRAY[0]),$($SUBNET_ARRAY[1])],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" `
  --load-balancers "targetGroupArn=$TG_ARN,containerName=the-combine,containerPort=8000" `
  --health-check-grace-period-seconds 60 `
  --region $REGION

Write-Host "✅ ECS Service created (starting up...)"
Write-Host "Wait 2-3 minutes for service to start"
```

---

## Part 10: Verify Deployment

```powershell
# Check service status
aws ecs describe-services `
  --cluster the-combine-cluster `
  --services the-combine-service `
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}' `
  --region us-east-1

# Check task status
aws ecs list-tasks `
  --cluster the-combine-cluster `
  --service-name the-combine-service `
  --region us-east-1

# View logs
aws logs tail /ecs/the-combine --follow --region us-east-1

# Test health endpoint
Invoke-WebRequest "http://$ALB_DNS/health"
# Or with curl if installed
curl "http://$ALB_DNS/health"
```

---

## Part 11: Test Exec Access

```powershell
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
```

---

## Quick Complete Setup Script

Save as `setup-ecs.ps1`:

```powershell
# ECS Complete Setup Script
$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "Starting ECS Setup"
Write-Host "=========================================="

# Variables
$REGION = "us-east-1"
$DB_PASSWORD = "YourSecurePassword123!"  # CHANGE THIS!

Write-Host "1/9 Creating ECR repository..."
aws ecr create-repository --repository-name the-combine --region $REGION | Out-Null

Write-Host "2/9 Creating RDS database (10 minutes)..."
aws rds create-db-instance --db-instance-identifier the-combine-db --db-instance-class db.t3.micro --engine postgres --engine-version 15.3 --master-username combine_admin --master-user-password "$DB_PASSWORD" --allocated-storage 20 --db-name combine --publicly-accessible --backup-retention-period 7 --region $REGION | Out-Null
aws rds wait db-instance-available --db-instance-identifier the-combine-db --region $REGION

$DB_ENDPOINT = aws rds describe-db-instances --db-instance-identifier the-combine-db --query 'DBInstances[0].Endpoint.Address' --output text --region $REGION
$DB_SG = aws rds describe-db-instances --db-instance-identifier the-combine-db --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text --region $REGION
aws ec2 authorize-security-group-ingress --group-id $DB_SG --protocol tcp --port 5432 --cidr 0.0.0.0/0 --region $REGION | Out-Null
$DATABASE_URL = "postgresql://combine_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/combine"

Write-Host "3/9 Creating ECS cluster..."
aws ecs create-cluster --cluster-name the-combine-cluster --region $REGION | Out-Null

Write-Host "4/9 Creating load balancer..."
$VPC_ID = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION
$SUBNET_IDS = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $REGION
$SUBNET_ARRAY = $SUBNET_IDS -split '\s+'
$ALB_SG = aws ec2 create-security-group --group-name the-combine-alb-sg --description "ALB SG" --vpc-id $VPC_ID --region $REGION --output text --query 'GroupId'
aws ec2 authorize-security-group-ingress --group-id $ALB_SG --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION | Out-Null
$ALB_ARN = aws elbv2 create-load-balancer --name the-combine-alb --subnets $SUBNET_ARRAY[0] $SUBNET_ARRAY[1] --security-groups $ALB_SG --scheme internet-facing --type application --region $REGION --query 'LoadBalancers[0].LoadBalancerArn' --output text
$ALB_DNS = aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].DNSName' --output text --region $REGION
$TG_ARN = aws elbv2 create-target-group --name the-combine-tg --protocol HTTP --port 8000 --vpc-id $VPC_ID --target-type ip --health-check-path /health --health-check-interval-seconds 30 --health-check-timeout-seconds 5 --healthy-threshold-count 2 --unhealthy-threshold-count 3 --region $REGION --query 'TargetGroups[0].TargetGroupArn' --output text
aws elbv2 create-listener --load-balancer-arn $ALB_ARN --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TG_ARN --region $REGION | Out-Null

Write-Host "5/9 Creating IAM roles..."
# (Shortened for space - use full commands from Part 5)

Write-Host "6/9 Building and pushing Docker image..."
# (Use full commands from Part 6)

Write-Host "7/9 Creating task definition..."
# (Use full commands from Part 7)

Write-Host "8/9 Creating ECS service..."
# (Use full commands from Parts 8-9)

Write-Host "9/9 Complete!"
Write-Host ""
Write-Host "=========================================="
Write-Host "Your app will be at: http://$ALB_DNS"
Write-Host "Database: $DB_ENDPOINT"
Write-Host "DATABASE_URL: $DATABASE_URL"
Write-Host "=========================================="
```

---

## All Important Commands Reference

```powershell
# View logs
aws logs tail /ecs/the-combine --follow --region us-east-1

# Exec into container
$TASK_ID = (aws ecs list-tasks --cluster the-combine-cluster --service-name the-combine-service --query 'taskArns[0]' --output text --region us-east-1).Split('/')[-1]
aws ecs execute-command --cluster the-combine-cluster --task $TASK_ID --container the-combine --interactive --command "/bin/bash" --region us-east-1

# Connect to database
psql -h $DB_ENDPOINT -U combine_admin -d combine

# Force new deployment
aws ecs update-service --cluster the-combine-cluster --service the-combine-service --force-new-deployment --region us-east-1

# Get service status
aws ecs describe-services --cluster the-combine-cluster --services the-combine-service --region us-east-1
```

---

## Notes

**PowerShell vs Bash differences:**
- Use backtick `` ` `` for line continuation (not `\`)
- Variables: `$VAR` not `VAR=`
- Arrays: `-split` to create from string
- String files: `Out-File` not `>`
- HTTP requests: `Invoke-WebRequest` or `curl`

**All AWS CLI commands are identical**, just wrapped in PowerShell syntax!
