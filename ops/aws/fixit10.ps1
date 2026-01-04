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