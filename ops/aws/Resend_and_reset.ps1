# Register and deploy
aws ecs register-task-definition --cli-input-json file://task-definition-with-domain.json --region us-east-1
aws ecs update-service --cluster the-combine-cluster --service the-combine-service --task-definition the-combine-task --force-new-deployment --region us-east-1

Write-Host "Deploying with DOMAIN=thecombine.ai:8000..."
Start-Sleep -Seconds 60

# Get new IP
$TASK_ARN = aws ecs list-tasks --cluster the-combine-cluster --service-name the-combine-service --query 'taskArns[0]' --output text --region us-east-1
$ENI_ID = aws ecs describe-tasks --cluster the-combine-cluster --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text --region us-east-1
$PUBLIC_IP = aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region us-east-1

Write-Host "New IP: $PUBLIC_IP"

# Get your hosted zone ID
$HOSTED_ZONE_ID = aws route53 list-hosted-zones --query "HostedZones[?Name=='thecombine.ai.'].Id" --output text

# Create change batch JSON
$changeBatch = @"
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "thecombine.ai",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [
          {
            "Value": "$PUBLIC_IP"
          }
        ]
      }
    }
  ]
}
"@

[System.IO.File]::WriteAllText("$PWD\route53-change.json", $changeBatch)

# Apply change
aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --change-batch file://route53-change.json

Write-Host "✅ DNS updated: thecombine.ai → $PUBLIC_IP"

# Wait for DNS to propagate (30-60 seconds)
Start-Sleep -Seconds 60

# Test
Invoke-WebRequest http://thecombine.ai:8000/health

# Open in browser
Start-Process http://thecombine.ai:8000