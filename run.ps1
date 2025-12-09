$ErrorActionPreference = "Stop"

Write-Host "Starting The Combine server..."
python scripts\run.py
exit $LASTEXITCODE
