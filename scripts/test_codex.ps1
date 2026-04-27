$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv_codex\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Codex Python venv executable not found at $Python"
}

$TempRoot = "C:\AI\codex_pytest_tmp"
New-Item -ItemType Directory -Force $TempRoot | Out-Null

$RunId = Get-Date -Format "yyyyMMddHHmmssfff"
$BaseTemp = Join-Path $TempRoot "ariadne_pytest_codex_$RunId"

& $Python -m pytest --basetemp $BaseTemp -p no:cacheprovider
