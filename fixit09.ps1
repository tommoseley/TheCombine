# Get subnets if not already set
$VPC_ID = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region us-east-1
$SUBNET_IDS = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region us-east-1
$SUBNET_ARRAY = $SUBNET_IDS -split '\s+'

# Get or verify security group
$ECS_SG = aws ec2 describe-security-groups --filters "Name=group-name,Values=the-combine-ecs-sg" --query 'SecurityGroups[0].GroupId' --output text --region us-east-1

Write-Host "VPC: $VPC_ID"
Write-Host "Subnets: $($SUBNET_ARRAY[0]), $($SUBNET_ARRAY[1])"
Write-Host "Security Group: $ECS_SG"

# Create service WITHOUT load balancer
aws ecs create-service `
  --cluster the-combine-cluster `
  --service-name the-combine-service `
  --task-definition the-combine-task:1 `
  --desired-count 1 `
  --launch-type FARGATE `
  --enable-execute-command `
  --network-configuration awsvpcConfiguration="{subnets=[$($SUBNET_ARRAY[0]),$($SUBNET_ARRAY[1])],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" `
  --region us-east-1

Write-Host "✅ ECS Service created (starting up...)"
Write-Host "Wait 2-3 minutes for service to start"