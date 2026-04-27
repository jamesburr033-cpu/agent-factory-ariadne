$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv_codex\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Codex Python venv executable not found at $Python"
}

$RunId = Get-Date -Format "yyyyMMddHHmmssfff"
$BaseTemp = Join-Path $env:TEMP "ariadne_pytest_codex_$RunId"

& $Python -m pytest --basetemp $BaseTemp -p no:cacheprovider
