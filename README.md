# AI Agents Project

A modular Python project with three specialized agents: Conversational, Summarization, and RAG.

## Project Structure

```
project/
├── agents/                  # Agent modules
│   ├── conversational/      # Conversational agent
│   ├── summarization/       # Summarization agent
│   └── rag/                 # RAG agent
├── tools/                   # Agent tools
├── models/                  # Database models (SQLModel)
├── api/                     # FastAPI application
├── ui/                      # Streamlit UI
├── prompts/                 # Prompt templates (MD files)
├── migrations/              # Alembic database migrations
├── utils/                   # Utilities (LLM, prompts)
├── config/                  # Configuration
├── scripts/                 # Development scripts
├── Makefile                 # Build automation
└── alembic.ini              # Alembic configuration
```

## Setup

### Quick Setup (Using Make - Recommended)

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2. Copy .env.example to .env and configure
cp .env.example .env

# 3. Run complete setup (installs deps, starts DB, runs migrations)
make setup
```

### Alternative Setup (Windows PowerShell)

If you don't have `make` installed:

```powershell
# 1. Create and activate virtual environment
python -m venv venv
.venv\Scripts\Activate.ps1

# 2. Copy .env.example to .env and configure
cp .env.example .env

# 3. Run complete setup
.\scripts\dev.ps1 setup
```

### Manual Setup

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate virtual environment:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up database:
```bash
# Start PostgreSQL with Docker (recommended for local dev)
docker-compose up -d

# Run migrations
alembic upgrade head
```

**See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed setup instructions** (local Docker vs Supabase production)

## Database Migrations

This project uses Alembic for database migrations with PostgreSQL and pgvector extension.

### Run Migrations
```bash
# Upgrade to latest migration
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Create New Migration
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration
alembic revision -m "description of changes"
```

### Database Schema
- **candidate**: Stores candidate information (id, created_at)
- **candidatechunk**: Stores chunked candidate data with vector embeddings (id, candidate_id, chunk_index, content, embedding, created_at)
- Uses pgvector extension for vector similarity search (1536-dimensional embeddings)

## Running

### Using Make (Recommended)

```bash
make help          # Show all available commands

# Database
make db-start      # Start PostgreSQL
make db-stop       # Stop PostgreSQL
make db-reset      # Reset database (fresh start)
make db-logs       # View database logs
make db-connect    # Connect to database with psql

# Migrations
make migrate       # Run migrations
make migrate-create MSG="add user table"  # Create new migration

# Applications
make api           # Run FastAPI server
make ui            # Run Streamlit UI
make app           # Run main CLI app

# Development
make dev           # Start DB + run migrations (ready to code)
```

### Using PowerShell Script (Windows)

```powershell
.\scripts\dev.ps1 help     # Show all available commands
.\scripts\dev.ps1 db-start # Start PostgreSQL
.\scripts\dev.ps1 api      # Run FastAPI server
.\scripts\dev.ps1 ui       # Run Streamlit UI
```

### Manual Commands

```bash
# API (FastAPI)
uvicorn api.main:app --reload

# UI (Streamlit)
streamlit run ui/app.py

# Main Application
python main.py
```

## Observability with Langfuse

This project integrates [Langfuse](https://langfuse.com) for LLM observability and tracing.

### Quick Setup

1. **Get Credentials**: Sign up at [cloud.langfuse.com](https://cloud.langfuse.com) and create a project

2. **Configure `.env`**:
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
```

3. **Verify**: Run the app and look for `✅ Langfuse initialized`

### Usage

**In Agents** (LangGraph):
```python
from langfuse.langchain import CallbackHandler

config = {
    "callbacks": [CallbackHandler()],
    "metadata": {
        "langfuse_session_id": session_id,
        "langfuse_user_id": user_id,
        "langfuse_tags": ["my_agent"]
    }
}
result = graph.invoke(input, config)
```

**In Tools** (Standalone):
```python
from langfuse.decorators import observe

@observe(as_type="generation")
def my_tool(input: str) -> str:
    # Your LLM calls here
    return result
```

**See [docs/LANGFUSE_OBSERVABILITY.md](docs/LANGFUSE_OBSERVABILITY.md) for complete implementation guide.**

## Development

- **Agents**: Located in `agents/` directory
- **Tools**: Located in `tools/` directory
- **Prompts**: MD files in `prompts/` directory
- **API Routes**: Located in `api/routes/`
- **UI Components**: Located in `ui/components/`