$ErrorActionPreference = "Stop"

Write-Host "Starting The Combine server..."
$env:PYTHONPATH = "$PSScriptRoot"
python scripts\run.py
exit $LASTEXITCODE
