$ErrorActionPreference = "Stop"

Write-Host "Running setup for The Combine..."
python scripts\setup.py
exit $LASTEXITCODE
