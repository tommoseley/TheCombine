# ECS Complete Setup Script
$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "Starting ECS Setup"
Write-Host "=========================================="

# Variables
$REGION = "us-east-1"
$DB_PASSWORD = "Gamecocks4896!"  # CHANGE THIS!

$ECR_uri="303985543798.dkr.ecr.us-east-1.amazonaws.com/the-combine"
$DB_ENDPOINT = "the-combine-db.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com"
$DB_SG = "sg-6b401a17"
$DATABASE_URL = "postgresql://combine_admin:Gamecocks4896!@the-combine-db.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com:5432/combine"

$VPC_ID = "vpc-e806728e"
$SUBNET_IDS = "subnet-b2bb9f9f subnet-7213804e subnet-09124052 subnet-1b37b217 subnet-f01703b9 subnet-d31996b6"
$SUBNET_ARRAY = $SUBNET_IDS -split '\s+'
$ECS_SG = "sg-0f56d0abd2aa04e8b"
# # Create ECS security group (allow all traffic for testing)
# $ECS_SG = aws ec2 create-security-group `
#   --group-name the-combine-ecs-sg `
#   --description "Security group for The Combine ECS tasks" `
#   --vpc-id $VPC_ID `
#   --region us-east-1 `
#   --output text `
#   --query 'GroupId'

# # Allow HTTP traffic from anywhere
# aws ec2 authorize-security-group-ingress `
#   --group-id $ECS_SG `
#   --protocol tcp `
#   --port 8000 `
#   --cidr 0.0.0.0/0 `
#   --region us-east-1

# Create service (no load balancer)
aws ecs create-service `
  --cluster the-combine-cluster `
  --service-name the-combine-service `
  --task-definition the-combine-task `
  --desired-count 1 `
  --launch-type FARGATE `
  --enable-execute-command `
  --network-configuration "awsvpcConfiguration={subnets=[$($SUBNET_ARRAY[0])],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" `
  --region us-east-1

# Get public IP
Start-Sleep -Seconds 30
$TASK_ARN = aws ecs list-tasks --cluster the-combine-cluster --service-name the-combine-service --query 'taskArns[0]' --output text --region us-east-1
$ENI_ID = aws ecs describe-tasks --cluster the-combine-cluster --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text --region us-east-1
$PUBLIC_IP = aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region us-east-1

Write-Host "✅ Your app is running at: http://${PUBLIC_IP}:8000"
Write-Host "Health check: http://${PUBLIC_IP}:8000/health"