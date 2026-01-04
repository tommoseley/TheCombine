# run-local.ps1
# Run The Combine Docker container locally for testing

# Configuration - edit these values or set environment variables
$DB_USER = "combine_user"
$DB_PASSWORD = "Gamecocks1!"
$DB_NAME = "combine"

# API key should be in environment variable, not hardcoded
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Host "ERROR: ANTHROPIC_API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Set it with: `$env:ANTHROPIC_API_KEY = 'your-key'" -ForegroundColor Yellow
    exit 1
}

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
    -e ANTHROPIC_API_KEY="$env:ANTHROPIC_API_KEY" `
    -e SECRET_KEY="oyU3rlXQUYaVYCimyaTMX4hsZ17tjRZPCcxkdfH31pk=" `
    -e ENVIRONMENT="development" `
    -v "${PWD}/scripts/docker-entrypoint-local.sh:/app/scripts/docker-entrypoint.sh" `
    the-combine
