# Temporary script to check staging migration status
Write-Host "Checking staging migration status..." -ForegroundColor Cyan

# Load .env file and get DATABASE_URL_STAG
$envFile = Get-Content "$PSScriptRoot\..\\.env"
foreach ($line in $envFile) {
    if ($line -match '^DATABASE_URL_STAG=(.+)$') {
        $env:DATABASE_URL = $matches[1]
        break
    }
}

if (-not $env:DATABASE_URL) {
    Write-Host "ERROR: DATABASE_URL_STAG not found in .env file" -ForegroundColor Red
    exit 1
}

Write-Host "Connected to staging database" -ForegroundColor Gray
Write-Host ""

# Step 1: Show current migration version on staging
Write-Host "=== Current Migration Version ===" -ForegroundColor Yellow
alembic current

Write-Host ""

# Step 2: Show migration history
Write-Host "=== Migration History ===" -ForegroundColor Yellow
alembic history

Write-Host ""

# Step 3: Dry-run - show SQL that would be executed
Write-Host "=== SQL That Would Be Executed (Dry Run) ===" -ForegroundColor Yellow
alembic upgrade head --sql
