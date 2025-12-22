# run-local.ps1
# Run The Combine Docker container locally for testing

# Configuration - edit these values
$DB_USER = "postgres"
$DB_PASSWORD = "your-password-here"
$DB_NAME = "combine"
$ANTHROPIC_KEY = "sk-ant-your-key-here"

# Build the image first
Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build -f infrastructure/Dockerfile -t the-combine .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting container..." -ForegroundColor Cyan
Write-Host "App will be available at: http://localhost:8000" -ForegroundColor Green
Write-Host "Health check: http://localhost:8000/health" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Run the container with local entrypoint (no AWS Secrets Manager)
docker run -it --rm `
    -p 8000:8000 `
    -e DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@host.docker.internal:5432/${DB_NAME}" `
    -e ANTHROPIC_API_KEY="$ANTHROPIC_KEY" `
    -e SECRET_KEY="local-dev-secret-key-not-for-prod" `
    -e ENVIRONMENT="development" `
    -v "${PWD}/scripts/docker-entrypoint-local.sh:/app/scripts/docker-entrypoint.sh" `
    the-combine
