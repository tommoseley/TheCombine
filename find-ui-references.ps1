# find-ui-references.ps1
# Finds all /ui/ references in HTML templates

Write-Host "Searching for /ui/ references in templates..." -ForegroundColor Cyan
Write-Host ""

$results = Get-ChildItem -Path "app\web\templates" -Recurse -Filter "*.html" -ErrorAction SilentlyContinue | 
    Select-String -Pattern '/ui/' | 
    Select-Object Path, LineNumber, Line

if ($results) {
    Write-Host "Found $($results.Count) references:" -ForegroundColor Yellow
    Write-Host ""
    
    $groupedByFile = $results | Group-Object Path
    
    foreach ($fileGroup in $groupedByFile) {
        $relativePath = $fileGroup.Name.Replace((Get-Location).Path + "\", "")
        Write-Host "📄 $relativePath" -ForegroundColor Green
        
        foreach ($match in $fileGroup.Group) {
            Write-Host "   Line $($match.LineNumber): " -NoNewline -ForegroundColor Gray
            Write-Host $match.Line.Trim() -ForegroundColor White
        }
        Write-Host ""
    }
    
    Write-Host "Summary by file:" -ForegroundColor Cyan
    foreach ($fileGroup in $groupedByFile) {
        $relativePath = $fileGroup.Name.Replace((Get-Location).Path + "\", "")
        Write-Host "  - $relativePath : $($fileGroup.Count) occurrence(s)" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "✅ No /ui/ references found in templates!" -ForegroundColor Green
}

Write-Host ""
Write-Host "To fix these, replace '/ui/' with '/' in each file." -ForegroundColor Cyan
