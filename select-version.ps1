param(
    [string]$ResultFile
)

$ErrorActionPreference = "SilentlyContinue"

git fetch --quiet origin 2>$null | Out-Null
git fetch --quiet --tags origin 2>$null | Out-Null

$tags = @(git tag --sort=-creatordate 2>$null)
$branch = (git rev-parse --abbrev-ref HEAD 2>$null)
$onMain = ($branch -eq "main")
$currentTag = $null
if (-not $onMain) {
    $currentTag = (git describe --tags --exact-match 2>$null)
}

$options = New-Object System.Collections.Generic.List[object]

if ($onMain) {
    $options.Add([PSCustomObject]@{ Label = "Bleiben (neueste Version, main)"; Action = "STAY"; Ref = "main" })
} elseif ($currentTag) {
    $options.Add([PSCustomObject]@{ Label = "Bleiben auf $currentTag"; Action = "STAY"; Ref = $currentTag })
    $options.Add([PSCustomObject]@{ Label = "Neueste Version (main, folgt automatisch)"; Action = "MAIN"; Ref = "main" })
} else {
    $options.Add([PSCustomObject]@{ Label = "Bleiben (aktueller Stand)"; Action = "STAY"; Ref = "" })
    $options.Add([PSCustomObject]@{ Label = "Neueste Version (main, folgt automatisch)"; Action = "MAIN"; Ref = "main" })
}

$maxAlternatives = 5
$added = 0
foreach ($t in $tags) {
    if ($added -ge $maxAlternatives) { break }
    if ($t -eq $currentTag) { continue }
    $isNewer = $true
    if ($currentTag -and $tags.Contains($currentTag)) {
        $isNewer = ([Array]::IndexOf($tags, $t)) -lt ([Array]::IndexOf($tags, $currentTag))
    } elseif ($onMain) {
        $isNewer = $false
    }
    $verb = if ($isNewer) { "Update auf" } else { "Zurueck zu" }
    $options.Add([PSCustomObject]@{ Label = "$verb $t"; Action = "CHECKOUT"; Ref = $t })
    $added++
}

function Write-Result($opt) {
    "$($opt.Action)|$($opt.Ref)" | Set-Content -Path $ResultFile -Encoding ascii
}

if ($options.Count -le 1) {
    Write-Result $options[0]
    exit 0
}

Write-Host ""
Write-Host "Welche Version soll laufen? (Pfeiltasten + Enter, Standard in 5s: Bleiben)"
$menuTop = [Console]::CursorTop
$selected = 0

function Draw-Menu($opts, $sel, $top) {
    [Console]::SetCursorPosition(0, $top)
    for ($i = 0; $i -lt $opts.Count; $i++) {
        $prefix = if ($i -eq $sel) { "> " } else { "  " }
        $line = "$prefix$($opts[$i].Label)"
        Write-Host $line.PadRight(70)
    }
}

Draw-Menu $options $selected $menuTop

$confirmed = $false
$sw = [Diagnostics.Stopwatch]::StartNew()
while ($sw.ElapsedMilliseconds -lt 5000) {
    $keyAvailable = $false
    try { $keyAvailable = [Console]::KeyAvailable } catch { $keyAvailable = $false }
    if ($keyAvailable) {
        $key = [Console]::ReadKey($true)
        switch ($key.Key) {
            "UpArrow"   { $selected = [Math]::Max(0, $selected - 1); Draw-Menu $options $selected $menuTop }
            "DownArrow" { $selected = [Math]::Min($options.Count - 1, $selected + 1); Draw-Menu $options $selected $menuTop }
            "Enter"     { $confirmed = $true }
        }
        if ($confirmed) { break }
    } else {
        Start-Sleep -Milliseconds 50
    }
}

[Console]::SetCursorPosition(0, $menuTop + $options.Count)
if (-not $confirmed) {
    Write-Host "(Zeit abgelaufen -- bleibe auf aktueller Version)"
    $selected = 0
}

Write-Result $options[$selected]
