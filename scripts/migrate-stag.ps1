# PowerShell script to run database migrations on staging (Supabase)
# Usage: .\migrate-stag.ps1 or make migrate-stag

Write-Host "Running migrations on staging database..." -ForegroundColor Cyan

# Load .env file and get DATABASE_URL_STAG
$envFile = Get-Content .env
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

Write-Host "Connecting to database..." -ForegroundColor Gray

# Run migrations
alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Staging migrations completed!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Migration failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
