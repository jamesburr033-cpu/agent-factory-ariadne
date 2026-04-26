param(
    [string]$BaseTemp = ".\.pytest_tmp_codex"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv_codex\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Codex Python venv executable not found at $Python"
}

& $Python -m pytest --basetemp $BaseTemp
