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
Write-Host "✅ Load Balancer complete! URL: http://$ALB_DNS"