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