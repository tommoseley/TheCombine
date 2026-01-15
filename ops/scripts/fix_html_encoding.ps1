$htmlFiles = Get-ChildItem "C:\Dev\The Combine\app\web\templates" -Recurse -Filter "*.html"
$fixed = @()
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

foreach ($file in $htmlFiles) {
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    $content = [System.Text.Encoding]::UTF8.GetString($bytes)
    $originalContent = $content
    
    $hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
    $hasNonAscii = $content -match '[^\x00-\x7F]'
    
    if ($hasBom -or $hasNonAscii) {
        # Remove BOM character
        $content = $content.Replace([char]0xFEFF, '')
        
        # Replace unicode punctuation with ASCII
        $content = $content.Replace([char]0x2013, '-')
        $content = $content.Replace([char]0x2014, '-')
        $content = $content.Replace([char]0x2018, [char]39)
        $content = $content.Replace([char]0x2019, [char]39)
        $content = $content.Replace([char]0x201C, [char]34)
        $content = $content.Replace([char]0x201D, [char]34)
        $content = $content.Replace([char]0x2022, '-')
        
        # Remove any remaining non-ASCII characters
        $cleaned = ""
        foreach ($char in $content.ToCharArray()) {
            if ([int]$char -lt 128) {
                $cleaned += $char
            }
        }
        $content = $cleaned
        
        if ($content -ne $originalContent) {
            [System.IO.File]::WriteAllText($file.FullName, $content, $utf8NoBom)
            $relativePath = $file.FullName.Replace("C:\Dev\The Combine\app\web\templates\", "")
            $fixed += $relativePath
        }
    }
}

Write-Output "Fixed $($fixed.Count) files:"
$fixed | ForEach-Object { Write-Output "  - $_" }
