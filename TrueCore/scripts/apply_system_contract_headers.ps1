<#
CONTRACT: TrueCore/CortexEvolved authored system utility
Owner: Lee Mercey
Watermark: CortexEvolved | Lee Mercey | Codex contributor
Copyright: Copyright (c) 2026 Lee Mercey. All rights reserved.
Role: Operator-run contract header utility for active TrueCore system files.
Rules: Dry-run by default. Do not stamp secrets, runtime data, generated files, or legacy folders.
#>

[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$ManifestPath = ''
)

$ErrorActionPreference = 'Stop'

$Marker = 'CONTRACT: TrueCore/CortexEvolved authored system file'
$UtilityMarker = 'CONTRACT: TrueCore/CortexEvolved authored system utility'

$AllowedExtensions = @(
    '.py',
    '.ps1',
    '.rs',
    '.js',
    '.css',
    '.html',
    '.toml',
    '.txt',
    '.example'
)

$ExcludedPathFragments = @(
    '\.git\',
    '\.test_tmp\',
    '\frontdoor\target\',
    '\instance\',
    '\security_local\',
    '\tests\',
    '\UI\',
    '\docs\',
    '\__pycache__\',
    '\data\',
    '\logs\',
    '\dist\',
    '\build\',
    '\node_modules\'
)

$ExplicitIncludeRoots = @(
    (Join-Path $Root 'truecore'),
    (Join-Path $Root 'frontdoor\src'),
    (Join-Path $Root 'frontdoor\static')
)

$ExplicitIncludeFiles = @(
    (Join-Path $Root 'frontdoor\Cargo.toml')
)

function Test-IsExcludedPath {
    param([string]$Path)

    $normalized = $Path.Replace('/', '\')
    foreach ($fragment in $ExcludedPathFragments) {
        if ($normalized -like "*$fragment*") {
            return $true
        }
    }
    return $false
}

function Get-HeaderForFile {
    param(
        [System.IO.FileInfo]$File,
        [string]$RelativePath
    )

    $ext = $File.Extension.ToLowerInvariant()
    $common = @(
        'CONTRACT: TrueCore/CortexEvolved authored system file',
        'Owner: Lee Mercey',
        'Watermark: CortexEvolved | Lee Mercey | Codex contributor',
        'Copyright: Copyright (c) 2026 Lee Mercey. All rights reserved.',
        'Rules: Preserve security boundaries; no prompt-only agents, hidden mutation lanes, or untested authority paths.',
        "Path: $RelativePath"
    )

    if ($ext -eq '.html') {
        return "<!--`r`n$($common -join "`r`n")`r`n-->`r`n`r`n"
    }

    if ($ext -in @('.rs', '.js', '.css')) {
        return "/*`r`n$($common -join "`r`n")`r`n*/`r`n`r`n"
    }

    $commented = $common | ForEach-Object { "# $_" }
    return "$($commented -join "`r`n")`r`n`r`n"
}

function Get-RelativePath {
    param(
        [string]$Base,
        [string]$Path
    )

    $baseFull = [System.IO.Path]::GetFullPath($Base).TrimEnd('\') + '\'
    $pathFull = [System.IO.Path]::GetFullPath($Path)
    return $pathFull.Substring($baseFull.Length).Replace('\', '/')
}

$candidates = New-Object System.Collections.Generic.List[System.IO.FileInfo]

foreach ($includeRoot in $ExplicitIncludeRoots) {
    if (Test-Path -LiteralPath $includeRoot) {
        Get-ChildItem -LiteralPath $includeRoot -Recurse -File -Force |
            ForEach-Object { [void]$candidates.Add($_) }
    }
}

foreach ($includeFile in $ExplicitIncludeFiles) {
    if (Test-Path -LiteralPath $includeFile) {
        [void]$candidates.Add((Get-Item -LiteralPath $includeFile))
    }
}

$manifest = New-Object System.Collections.Generic.List[object]

foreach ($file in ($candidates | Sort-Object FullName -Unique)) {
    $relative = Get-RelativePath -Base $Root -Path $file.FullName
    $ext = $file.Extension.ToLowerInvariant()
    $action = 'skip'
    $reason = ''

    if (Test-IsExcludedPath -Path $file.FullName) {
        $reason = 'excluded_path'
    } elseif (($AllowedExtensions -notcontains $ext) -and (-not $file.Name.EndsWith('.example'))) {
        $reason = 'unsupported_extension'
    } elseif ($file.Name -eq '.env') {
        $reason = 'secret_file'
    } elseif ($file.Name -eq 'Cargo.lock') {
        $reason = 'lockfile'
    } else {
        $text = Get-Content -LiteralPath $file.FullName -Raw
        if (($text -like "*$Marker*") -or ($text -like "*$UtilityMarker*")) {
            $reason = 'already_has_header'
        } else {
            $action = if ($Apply) { 'write' } else { 'would_write' }
            $reason = 'eligible'

            if ($Apply) {
                $header = Get-HeaderForFile -File $file -RelativePath $relative
                if (($ext -eq '.py' -or $ext -eq '.ps1') -and $text.StartsWith('#!')) {
                    $lineEnd = $text.IndexOf("`n")
                    if ($lineEnd -ge 0) {
                        $text = $text.Substring(0, $lineEnd + 1) + $header + $text.Substring($lineEnd + 1)
                    } else {
                        $text = $text + "`r`n" + $header
                    }
                } else {
                    $text = $header + $text
                }
                Set-Content -LiteralPath $file.FullName -Value $text -Encoding UTF8
            }
        }
    }

    [void]$manifest.Add([pscustomobject]@{
        action = $action
        reason = $reason
        path = $relative
        bytes = $file.Length
    })
}

$manifest | Sort-Object action, path | Format-Table -AutoSize

if ($ManifestPath -ne '') {
    $manifestFull = if ([System.IO.Path]::IsPathRooted($ManifestPath)) {
        $ManifestPath
    } else {
        Join-Path $Root $ManifestPath
    }
    $manifest | Export-Csv -LiteralPath $manifestFull -NoTypeInformation -Encoding UTF8
    Write-Host "Manifest written: $manifestFull"
}

if (-not $Apply) {
    Write-Host ''
    Write-Host 'DRY RUN ONLY. Re-run with -Apply to write headers.'
}
