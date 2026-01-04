# Part 6: Build and Push Docker Image

# Make sure you have Dockerfile_minimal
Copy-Item Dockerfile_minimal Dockerfile -Force

# Build
docker build -t the-combine .

# Get DATABASE_URL (if not already set)
if (-not $DATABASE_URL) {
    $DB_ENDPOINT = aws rds describe-db-instances --db-instance-identifier the-combine-db --query 'DBInstances[0].Endpoint.Address' --output text --region us-east-1
    $DB_PASSWORD = "YourPasswordHere"  # PUT YOUR ACTUAL PASSWORD
    $DATABASE_URL = "postgresql://combine_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/combine"
    Write-Host "DATABASE_URL: $DATABASE_URL"
}

# Test locally FIRST - simpler method
Write-Host "Testing locally..."

# Start container in background (simple way)
Start-Process powershell -ArgumentList "-NoProfile", "-Command", "docker run --rm -p 8000:8000 -e DATABASE_URL='$DATABASE_URL' the-combine" -WindowStyle Hidden

# Wait for container to start
Write-Host "Waiting for container to start..."
Start-Sleep -Seconds 10

# Test health endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "✅ Health check passed: $($response.Content)"
} catch {
    Write-Host "❌ Health check failed: $_"
    Write-Host "Check if container is running: docker ps"
}

# Stop test container
Write-Host "Stopping test container..."
docker ps -q --filter ancestor=the-combine | ForEach-Object { docker stop $_ }

# If test passed, push to ECR
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = "us-east-1"

Write-Host "Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Tag and push
Write-Host "Tagging and pushing image..."
docker tag the-combine:latest "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/the-combine:latest"
docker push "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/the-combine:latest"

Write-Host "✅ Image pushed to ECR"