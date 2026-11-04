# Ariadne AA-001 local staging script. Run manually in a PowerShell session ON the P620.
# This script stops if the repo is dirty, baseline tests fail, or any target file exists.
# It changes only a new, uncommitted feature branch. No network/install/push/merge.
param(
    [string]$RepoPath = "C:\AI\agent_factory_ariadne"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoPath = (Resolve-Path $RepoPath).Path
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$ReportDir = Join-Path $env:TEMP "AriadneAA001-$RunId"
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

function Assert-Exit([string]$Description) {
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit code $LASTEXITCODE. No deployment or merge performed." }
}

if (-not (Test-Path (Join-Path $RepoPath "pyproject.toml"))) {
    throw "Not an Ariadne Python repository: $RepoPath"
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git is unavailable." }
Push-Location $RepoPath
try {
    git rev-parse --is-inside-work-tree | Out-Null
    Assert-Exit "Git repository check"
    $status = @(git status --porcelain=v1 --untracked-files=all)
    Assert-Exit "Git status"
    if ($status.Count -gt 0) {
        $status | Set-Content -Encoding UTF8 (Join-Path $ReportDir "dirty_status.txt")
        throw "Repo contains local modifications. No files copied. Saved status to $ReportDir. Commit, stash, or reconcile them first."
    }
    $BaseBranch = (git branch --show-current).Trim()
    $BaseCommit = (git rev-parse HEAD).Trim()
    "branch=$BaseBranch`nsha=$BaseCommit" | Set-Content -Encoding UTF8 (Join-Path $ReportDir "baseline_git.txt")

    $Python = Join-Path $RepoPath ".venv\Scripts\python.exe"
    if (-not (Test-Path $Python)) {
        throw "Expected existing .venv at $Python. No environment created or downloads attempted."
    }
    $PythonVersion = (& $Python --version 2>&1 | Out-String).Trim()
    $PythonVersion | Set-Content -Encoding UTF8 (Join-Path $ReportDir "python_version.txt")
    Assert-Exit "Python version"
    if ($PythonVersion -notmatch '^Python 3\.12\.') {
        throw "Ariadne AA-001 needs Python 3.12 in the existing .venv. Found: $PythonVersion"
    }
    & $Python -m pytest -q 2>&1 | Tee-Object -FilePath (Join-Path $ReportDir "baseline_pytest.txt")
    Assert-Exit "Unmodified Ariadne baseline tests"

    $Files = @(
        "src/agent_factory/assurance/__init__.py",
        "src/agent_factory/assurance/models.py",
        "src/agent_factory/assurance/policy.py",
        "src/agent_factory/assurance/grants.py",
        "src/agent_factory/assurance/ledger.py",
        "src/agent_factory/assurance/broker.py",
        "src/agent_factory/assurance/monitor.py",
        "tests/assurance/test_runtime_contract.py",
        "tests/assurance/test_reconciliation.py",
        "docs/ASSURANCE_AA001.md",
        "scripts/assurance_demo.py"
    )
    foreach ($Relative in $Files) {
        $dest = Join-Path $RepoPath $Relative
        $src = Join-Path $PackageRoot $Relative
        if (-not (Test-Path $src -PathType Leaf)) { throw "Missing bundle file: $Relative" }
        if (Test-Path $dest) { throw "Existing source at $Relative. No overwrite attempted." }
    }

    $Backup = "backup/pre-aa001-$RunId"
    $Work = "work/aa001-$RunId"
    git branch $Backup $BaseCommit
    Assert-Exit "Backup branch creation"
    git switch -c $Work
    Assert-Exit "Feature branch creation"
    foreach ($Relative in $Files) {
        $dest = Join-Path $RepoPath $Relative
        $src = Join-Path $PackageRoot $Relative
        New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $src -Destination $dest -ErrorAction Stop
    }
    & $Python -m pytest -q tests/assurance 2>&1 | Tee-Object -FilePath (Join-Path $ReportDir "assurance_pytest.txt")
    Assert-Exit "AA-001 assurance tests"
    & $Python -m pytest -q 2>&1 | Tee-Object -FilePath (Join-Path $ReportDir "full_pytest.txt")
    Assert-Exit "Ariadne full regression tests"
    & $Python scripts/assurance_demo.py 2>&1 | Tee-Object -FilePath (Join-Path $ReportDir "synthetic_demo.json")
    Assert-Exit "Synthetic assurance demo"
    git status --short | Tee-Object -FilePath (Join-Path $ReportDir "result_git_status.txt")
    Write-Host "AA-001 authorization and AA-002 read-only reconciliation validated on local workstation."
    Write-Host "Working branch: $Work"
    Write-Host "Original backup: $Backup"
    Write-Host "Review reports: $ReportDir"
    Write-Host "No commits, pushes, merges, messages, or deployments performed."
}
finally { Pop-Location }
