# PowerShell development script for Windows users without make
# Usage: .\dev.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1)]
    [string]$Message = ""
)

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Blue
    Write-Host "  install          " -ForegroundColor Green -NoNewline; Write-Host "Install Python dependencies"
    Write-Host "  db-start         " -ForegroundColor Green -NoNewline; Write-Host "Start PostgreSQL database (Docker)"
    Write-Host "  db-stop          " -ForegroundColor Green -NoNewline; Write-Host "Stop PostgreSQL database"
    Write-Host "  db-reset         " -ForegroundColor Green -NoNewline; Write-Host "Reset database (remove all data)"
    Write-Host "  db-logs          " -ForegroundColor Green -NoNewline; Write-Host "View database logs"
    Write-Host "  db-connect       " -ForegroundColor Green -NoNewline; Write-Host "Connect to database with psql"
    Write-Host "  db-status        " -ForegroundColor Green -NoNewline; Write-Host "Check database status"
    Write-Host "  db-tables        " -ForegroundColor Green -NoNewline; Write-Host "Show all database tables"
    Write-Host "  migrate          " -ForegroundColor Green -NoNewline; Write-Host "Run all pending migrations"
    Write-Host "  migrate-create   " -ForegroundColor Green -NoNewline; Write-Host "Create new migration (add message)"
    Write-Host "  migrate-rollback " -ForegroundColor Green -NoNewline; Write-Host "Rollback one migration"
    Write-Host "  api              " -ForegroundColor Green -NoNewline; Write-Host "Run FastAPI server"
    Write-Host "  ui               " -ForegroundColor Green -NoNewline; Write-Host "Run Streamlit UI"
    Write-Host "  app              " -ForegroundColor Green -NoNewline; Write-Host "Run main CLI application"
    Write-Host "  setup            " -ForegroundColor Green -NoNewline; Write-Host "Complete setup (install + DB + migrations)"
    Write-Host "  dev              " -ForegroundColor Green -NoNewline; Write-Host "Start development environment"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Blue
    Write-Host "  .\dev.ps1 db-start"
    Write-Host "  .\dev.ps1 migrate-create 'add user table'"
}

switch ($Command) {
    "install" {
        Write-Host "Installing dependencies..." -ForegroundColor Blue
        pip install -r requirements.txt
        Write-Host "Dependencies installed!" -ForegroundColor Green
    }

    "db-start" {
        Write-Host "Starting PostgreSQL with pgvector..." -ForegroundColor Blue
        docker-compose up -d
        Start-Sleep -Seconds 3
        docker-compose ps
        Write-Host "Database started!" -ForegroundColor Green
    }

    "db-stop" {
        Write-Host "Stopping database..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "Database stopped!" -ForegroundColor Green
    }

    "db-reset" {
        Write-Host "Resetting database..." -ForegroundColor Yellow
        docker-compose down -v
        docker-compose up -d
        Start-Sleep -Seconds 5
        Write-Host "Running migrations..." -ForegroundColor Blue
        alembic upgrade head
        Write-Host "Database reset complete!" -ForegroundColor Green
    }

    "db-logs" {
        docker-compose logs -f postgres
    }

    "db-connect" {
        docker exec -it fabric_postgres psql -U fabric_user -d fabric_db
    }

    "db-status" {
        docker-compose ps
        Write-Host ""
        docker exec fabric_postgres psql -U fabric_user -d fabric_db -c "\dx vector"
    }

    "db-tables" {
        docker exec fabric_postgres psql -U fabric_user -d fabric_db -c "\dt"
    }

    "db-schema" {
        docker exec fabric_postgres psql -U fabric_user -d fabric_db -c "\d+ candidatechunk"
    }

    "migrate" {
        Write-Host "Running migrations..." -ForegroundColor Blue
        alembic upgrade head
        Write-Host "Migrations complete!" -ForegroundColor Green
    }

    "migrate-create" {
        if ($Message -eq "") {
            Write-Host "Usage: .\dev.ps1 migrate-create 'your migration message'" -ForegroundColor Yellow
            exit 1
        }
        alembic revision --autogenerate -m $Message
    }

    "migrate-rollback" {
        Write-Host "Rolling back migration..." -ForegroundColor Yellow
        alembic downgrade -1
    }

    "migrate-history" {
        alembic history
    }

    "migrate-current" {
        alembic current
    }

    "api" {
        Write-Host "Starting FastAPI server..." -ForegroundColor Blue
        uvicorn api.main:app --reload
    }

    "ui" {
        Write-Host "Starting Streamlit UI..." -ForegroundColor Blue
        streamlit run ui/app.py
    }

    "app" {
        Write-Host "Running main application..." -ForegroundColor Blue
        python main.py
    }

    "setup" {
        Write-Host "Setting up development environment..." -ForegroundColor Blue
        pip install -r requirements.txt
        docker-compose up -d
        Start-Sleep -Seconds 5
        alembic upgrade head
        Write-Host "Setup complete! Ready to develop." -ForegroundColor Green
    }

    "dev" {
        docker-compose up -d
        Start-Sleep -Seconds 3
        alembic upgrade head
        Write-Host "Development environment ready!" -ForegroundColor Green
        Write-Host "Run '.\dev.ps1 api' or '.\dev.ps1 ui' to start the application" -ForegroundColor Blue
    }

    "clean" {
        Write-Host "Cleaning up..." -ForegroundColor Yellow
        Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
        Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" | Remove-Item -Force
        Get-ChildItem -Path . -Recurse -File -Filter "*.pyo" | Remove-Item -Force
        Write-Host "Cleanup complete!" -ForegroundColor Green
    }

    default {
        Show-Help
    }
}
