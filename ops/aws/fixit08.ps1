# Create security group for ECS tasks
$ECS_SG = aws ec2 create-security-group `
  --group-name the-combine-ecs-sg `
  --description "Security group for The Combine ECS tasks" `
  --vpc-id $VPC_ID `
  --region us-east-1 `
  --output text `
  --query 'GroupId'

# Allow HTTP traffic from ANYWHERE (since no ALB)
aws ec2 authorize-security-group-ingress `
  --group-id $ECS_SG `
  --protocol tcp `
  --port 8000 `
  --cidr 0.0.0.0/0 `
  --region us-east-1

Write-Host "✅ ECS Security Group created: $ECS_SG"
Write-Host "Allows port 8000 from anywhere"