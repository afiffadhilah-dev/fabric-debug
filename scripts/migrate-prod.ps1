# PowerShell script to run database migrations on production (Supabase)
# Usage: .\scripts\migrate-prod.ps1 or make migrate-prod

Write-Host "Running migrations on production database..." -ForegroundColor Cyan

# Load .env file and get DATABASE_URL_PROD
$envFile = Get-Content .env
foreach ($line in $envFile) {
    if ($line -match '^DATABASE_URL_PROD=(.+)$') {
        $env:DATABASE_URL = $matches[1]
        break
    }
}

if (-not $env:DATABASE_URL) {
    Write-Host "ERROR: DATABASE_URL_PROD not found in .env file" -ForegroundColor Red
    exit 1
}

Write-Host "Connecting to database..." -ForegroundColor Gray

# Run migrations
alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Production migrations completed!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Migration failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
