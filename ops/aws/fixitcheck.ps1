# Update Route53 to correct IP
$PUBLIC_IP = "54.166.36.176"
$HOSTED_ZONE_ID = aws route53 list-hosted-zones --query "HostedZones[?Name=='thecombine.ai.'].Id" --output text

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
aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --change-batch file://route53-change.json

Write-Host "DNS updated: thecombine.ai -> $PUBLIC_IP"