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
$currentDescribe = (git describe --tags 2>$null)
if (-not $currentDescribe) { $currentDescribe = "unbekannt" }

function Write-Result($action, $ref) {
    "$action|$ref" | Set-Content -Path $ResultFile -Encoding ascii
}

# --- Menu-Knoten aufbauen: main (rollend) zuoberst, dann Tags neueste zuerst ---
$nodes = New-Object System.Collections.Generic.List[object]
$nodes.Add([PSCustomObject]@{ Label = ""; Action = "MAIN"; Ref = "main"; IsCurrent = $false })

$maxTags = 6
$count = 0
foreach ($t in $tags) {
    if ($count -ge $maxTags) { break }
    $nodes.Add([PSCustomObject]@{ Label = ""; Action = "CHECKOUT"; Ref = $t; IsCurrent = $false })
    $count++
}

$currentIndex = -1
if ($onMain) {
    $currentIndex = 0
} elseif ($currentTag) {
    for ($i = 1; $i -lt $nodes.Count; $i++) {
        if ($nodes[$i].Ref -eq $currentTag) { $currentIndex = $i; break }
    }
}
$defaultIndex = if ($currentIndex -ge 0) { $currentIndex } else { 0 }
if ($currentIndex -ge 0) {
    $nodes[$currentIndex].IsCurrent = $true
    $nodes[$currentIndex].Action = "STAY"
}

# --- Labels vergeben ---
for ($i = 0; $i -lt $nodes.Count; $i++) {
    $n = $nodes[$i]
    if ($n.IsCurrent) {
        if ($onMain) {
            $n.Label = "$currentDescribe  <-- laeuft jetzt (main, folgt automatisch)"
        } else {
            $n.Label = "$($n.Ref)  <-- laeuft jetzt"
        }
    } elseif ($n.Ref -eq "main") {
        $n.Label = "Update auf main (neueste, folgt automatisch)"
    } else {
        $verb = if ($i -lt $currentIndex) { "Update auf" } else { "Zurueck zu" }
        $n.Label = "$verb $($n.Ref)"
    }
}

if ($nodes.Count -le 1) {
    Write-Result "STAY" $nodes[0].Ref
    exit 0
}

Write-Host ""
Write-Host "Welche Version soll laufen? (Pfeiltasten + Enter)"
$menuTop = [Console]::CursorTop
$selected = $defaultIndex

function Draw-Menu($opts, $sel, $top) {
    [Console]::SetCursorPosition(0, $top)
    for ($i = 0; $i -lt $opts.Count; $i++) {
        $prefix = if ($i -eq $sel) { "> " } else { "  " }
        $line = "$prefix$($opts[$i].Label)"
        Write-Host $line.PadRight(70)
    }
}

Draw-Menu $nodes $selected $menuTop
$countdownRow = $menuTop + $nodes.Count + 1

$timeoutMs = 10000
$barWidth = 24
$confirmed = $false
$sw = [Diagnostics.Stopwatch]::StartNew()

while ($sw.ElapsedMilliseconds -lt $timeoutMs) {
    $remainingMs = $timeoutMs - $sw.ElapsedMilliseconds
    $remainingS = [Math]::Ceiling($remainingMs / 1000)
    $filled = [Math]::Max(0, [int]($barWidth * ($remainingMs / $timeoutMs)))
    $bar = ("#" * $filled).PadRight($barWidth, "-")
    [Console]::SetCursorPosition(0, $countdownRow)
    Write-Host ("[$bar] noch " + $remainingS + "s bis automatisch '" + $nodes[$defaultIndex].Label.Trim() + "'").PadRight(90) -NoNewline

    $keyAvailable = $false
    try { $keyAvailable = [Console]::KeyAvailable } catch { $keyAvailable = $false }
    if ($keyAvailable) {
        $key = [Console]::ReadKey($true)
        switch ($key.Key) {
            "UpArrow"   { $selected = [Math]::Max(0, $selected - 1); Draw-Menu $nodes $selected $menuTop }
            "DownArrow" { $selected = [Math]::Min($nodes.Count - 1, $selected + 1); Draw-Menu $nodes $selected $menuTop }
            "Enter"     { $confirmed = $true }
        }
        if ($confirmed) { break }
    } else {
        Start-Sleep -Milliseconds 100
    }
}

[Console]::SetCursorPosition(0, $countdownRow)
if (-not $confirmed) {
    Write-Host "(Zeit abgelaufen -- bleibe auf aktueller Version)".PadRight(90)
    $selected = $defaultIndex
} else {
    Write-Host "".PadRight(90)
}

Write-Result $nodes[$selected].Action $nodes[$selected].Ref
