# =============================================================================
# Fix blank Open Questions - Update fragment markup in production database
# =============================================================================

Write-Host "=== Fix Blank Open Questions ===" -ForegroundColor Yellow
Write-Host ""

# Get the running task ID
Write-Host "Getting running task ID..."
$taskArn = aws ecs list-tasks --cluster the-combine-cluster --query 'taskArns[0]' --output text
$taskId = ($taskArn -split '/')[-1]

if (-not $taskId -or $taskId -eq "None") {
    Write-Host "ERROR: No running tasks found" -ForegroundColor Red
    exit 1
}

Write-Host "Task ID: $taskId" -ForegroundColor Green
Write-Host ""
Write-Host "Run this command to connect to the container:" -ForegroundColor Cyan
Write-Host ""
Write-Host "aws ecs execute-command --cluster the-combine-cluster --task $taskId --container the-combine --interactive --command '/bin/bash'"
Write-Host ""
Write-Host "Then inside the container, run this one-liner:" -ForegroundColor Cyan
Write-Host ""

$cmd = 'psql $DATABASE_URL -c "UPDATE fragment_artifacts SET fragment_markup = '"'"'<div class=\"flex items-start\" data-question-id=\"{{ item.id }}\">{% if item.blocking %}<i data-lucide=\"alert-circle\" class=\"w-4 h-4 mr-2 text-red-600 dark:text-red-500 flex-shrink-0 mt-0.5\"></i>{% else %}<i data-lucide=\"help-circle\" class=\"w-4 h-4 mr-2 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5\"></i>{% endif %}<div class=\"flex-1\"><span class=\"text-gray-900 dark:text-gray-50 text-sm\">{{ item.text }}</span>{% if item.blocking %}<span class=\"ml-2 px-1.5 py-0.5 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded text-xs\">Blocking</span>{% endif %}{% if item.priority %}<span class=\"ml-1 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs\">{{ item.priority | capitalize }}</span>{% endif %}{% if item.why_it_matters %}<p class=\"text-xs text-gray-500 dark:text-gray-400 mt-1\">{{ item.why_it_matters }}</p>{% endif %}</div></div>'"'"' WHERE fragment_id = '"'"'OpenQuestionV1Fragment'"'"';"'

Write-Host $cmd
Write-Host ""
Write-Host "Or for a cleaner approach, run 'psql `$DATABASE_URL' then paste:" -ForegroundColor Cyan
Write-Host ""
Write-Host @"
UPDATE fragment_artifacts 
SET fragment_markup = '<div class="flex items-start" data-question-id="{{ item.id }}">
    {% if item.blocking %}
    <i data-lucide="alert-circle" class="w-4 h-4 mr-2 text-red-600 dark:text-red-500 flex-shrink-0 mt-0.5"></i>
    {% else %}
    <i data-lucide="help-circle" class="w-4 h-4 mr-2 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5"></i>
    {% endif %}
    <div class="flex-1">
        <span class="text-gray-900 dark:text-gray-50 text-sm">{{ item.text }}</span>
        {% if item.blocking %}
        <span class="ml-2 px-1.5 py-0.5 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded text-xs">Blocking</span>
        {% endif %}
        {% if item.priority %}
        <span class="ml-1 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs">{{ item.priority | capitalize }}</span>
        {% endif %}
        {% if item.why_it_matters %}
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ item.why_it_matters }}</p>
        {% endif %}
    </div>
</div>'
WHERE fragment_id = 'OpenQuestionV1Fragment';
"@