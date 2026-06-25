param(
    [switch]$Stage
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$phase1Name = [string]([char]0x4e00) + [string]([char]0x671f)
$phase2Name = [string]([char]0x4e8c) + [string]([char]0x671f)
$phase1 = Join-Path $root $phase1Name

$rootFiles = @(
    ".gitignore",
    "docker-compose.yml",
    "update_server.sh",
    "server_readonly_audit.sh",
    "docs/git-structure.md",
    "scripts/stage-deploy-fix.ps1",
    ($phase2Name + "/backend/api/admin_routes.py"),
    ($phase2Name + "/frontend/vite.config.js"),
    $phase1Name
)

$phase1Files = @(
    "backend/api/iptc_case_routes.py",
    "backend/collectors/base/playwright_collector_base.py",
    "backend/scripts/batch_match_cases.py",
    "backend/scripts/deployment_doctor.py",
    "backend/scripts/migrate_iptc_schema.py",
    "backend/scripts/seed_iptc_sources.py"
)

function Show-Command {
    param([string]$Command)
    Write-Host "> $Command" -ForegroundColor Cyan
}

Write-Host "Root repository: $root" -ForegroundColor Green
Show-Command "git status --short -- <deployment files>"
git -C $root status --short -- $rootFiles

Write-Host ""
Write-Host "Phase 1 submodule: $phase1" -ForegroundColor Green
Show-Command "git status --short -- <collector files>"
git -C $phase1 status --short -- $phase1Files

if (-not $Stage) {
    Write-Host ""
    Write-Host "Dry run only. Re-run with -Stage to stage these files." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Staging Phase 1 files..." -ForegroundColor Green
git -C $phase1 add -- $phase1Files
git -C $phase1 status --short -- $phase1Files

Write-Host ""
Write-Host "After committing/pushing Phase 1, stage root files with:" -ForegroundColor Yellow
Write-Host ("  git add -- .gitignore docker-compose.yml update_server.sh server_readonly_audit.sh docs/git-structure.md scripts/stage-deploy-fix.ps1 " + $phase2Name + "/backend/api/admin_routes.py " + $phase2Name + "/frontend/vite.config.js " + $phase1Name)
