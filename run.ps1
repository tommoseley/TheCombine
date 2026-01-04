# Run The Combine locally
$ErrorActionPreference = "Stop"

# Load .env if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -and -not $_.StartsWith("#")) {
            $key, $value = $_ -split "=", 2
            [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
        }
    }
}

Write-Host "Starting The Combine API..." -ForegroundColor Cyan
Write-Host "  API docs: http://localhost:8000/docs"
Write-Host "  Health:   http://localhost:8000/health"
Write-Host ""

python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
