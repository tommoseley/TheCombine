# =============================================================================
# Step 4: Update fragment markup in production database
# =============================================================================
# Fixes the blank Open Questions issue - updates fragment with Tailwind classes

Write-Host "=== Step 4: Update fragment markup in database ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "The fragment markup needs to be updated in the production database."
Write-Host "This fixes the blank Open Questions display."
Write-Host ""
Write-Host "SQL file: update-fragment-markup.sql" -ForegroundColor Cyan
Write-Host ""
Get-Content "$PSScriptRoot\update-fragment-markup.sql"
Write-Host ""
Write-Host "=== How to run ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: ECS Exec into container"
Write-Host "  1. Get task ID:"
Write-Host "     aws ecs list-tasks --cluster the-combine-cluster --query 'taskArns[0]' --output text"
Write-Host ""
Write-Host "  2. Exec into container:"
Write-Host "     aws ecs execute-command --cluster the-combine-cluster --task <TASK_ID> --container the-combine --interactive --command '/bin/bash'"
Write-Host ""
Write-Host "  3. Run psql with SQL:"
Write-Host "     psql \$DATABASE_URL -c "<paste SQL here>""
Write-Host ""
Write-Host "Option 2: Direct psql (if RDS is publicly accessible)"
Write-Host "  psql 'postgresql://combine_admin:Gamecocks4896!@the-combine-db.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com:5432/combine' -f update-fragment-markup.sql"
Write-Host ""