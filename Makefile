.PHONY: help install db-start db-stop db-reset db-logs db-connect migrate migrate-create api ui app clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

# Database commands
db-start: ## Start PostgreSQL database (Docker)
	@docker-compose up -d
	@timeout /t 3 /nobreak > nul 2>&1 || sleep 3 || true
	@docker-compose ps

db-stop: ## Stop PostgreSQL database
	@docker-compose down

db-reset: ## Reset database (remove all data and restart)
	@docker-compose down -v
	@docker-compose up -d
	@timeout /t 5 /nobreak > nul 2>&1 || sleep 5 || true
	@alembic upgrade head

db-logs: ## View database logs
	@docker-compose logs -f postgres

db-connect: ## Connect to database with psql
	@docker exec -it fabric_postgres psql -U fabric_user -d fabric_db

db-status: ## Check database status
	@docker-compose ps

db-tables: ## Show all database tables
	@docker exec fabric_postgres psql -U fabric_user -d fabric_db -c "\dt"

db-schema: ## Show candidatechunk table schema
	@docker exec fabric_postgres psql -U fabric_user -d fabric_db -c "\d+ candidatechunk"

# Migration commands
migrate: ## Run all pending migrations (local Docker)
	@alembic upgrade head

migrate-stag: ## Run migrations on staging database (Supabase)
	@powershell -File scripts/migrate-stag.ps1

migrate-create: ## Create new migration (usage: make migrate-create MSG="your message")
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make migrate-create MSG=\"your migration message\""; \
		exit 1; \
	fi
	@alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Rollback one migration
	@alembic downgrade -1

migrate-history: ## Show migration history
	@alembic history

migrate-current: ## Show current migration
	@alembic current

# Application commands
api: ## Run FastAPI server
	@uvicorn api.main:app --reload

ui: ## Run Streamlit UI
	@streamlit run ui/app.py

app: ## Run main CLI application
	@python main.py

# Development setup
setup: install ## Complete setup (install deps, start DB, run migrations)
	@docker-compose up -d
	@timeout /t 5 /nobreak > nul 2>&1 || sleep 5 || true
	@alembic upgrade head

dev: ## Start development environment (DB + migrations)
	@docker-compose up -d
	@timeout /t 3 /nobreak > nul 2>&1 || sleep 3 || true
	@alembic upgrade head

# Cleanup
clean: ## Remove Python cache files
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
