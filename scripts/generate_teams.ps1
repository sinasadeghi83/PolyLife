# Generate team1..team8 from teams/_template, substituting each team's name,
# unique port, and a simple unique DB password.
# Re-run any time to regenerate. Existing team folders are overwritten.

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$template = Join-Path $root "teams\_template"
$utf8 = New-Object System.Text.UTF8Encoding $false   # UTF-8, no BOM

foreach ($i in 1..8) {
    $team = "team$i"
    $port = 9100 + $i
    $pass = "${team}pass"            # simple, unique per team
    $dest = Join-Path $root "teams\$team"

    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item $template $dest -Recurse

    # Substitute placeholders in every file (UTF-8 safe, keeps Persian intact).
    Get-ChildItem $dest -Recurse -File | ForEach-Object {
        $text = [System.IO.File]::ReadAllText($_.FullName, $utf8)
        $text = $text -replace "__TEAM__", $team `
                      -replace "__PORT__", $port `
                      -replace "__PASSWORD__", $pass
        [System.IO.File]::WriteAllText($_.FullName, $text, $utf8)
    }

    # Rename the __TEAM__ folders (static/__TEAM__, templates/__TEAM__).
    Get-ChildItem $dest -Recurse -Directory |
        Where-Object { $_.Name -eq "__TEAM__" } |
        ForEach-Object { Rename-Item $_.FullName $team }

    Write-Output "generated $team  (port $port, db password $pass)"
}
