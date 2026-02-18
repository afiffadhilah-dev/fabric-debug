# Production Deployment: Render + Supabase

## Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │           Render.com             │
                    │                                  │
  HTTPS ──────────► │  ┌──────────────────────────┐   │
                    │  │  Web Service (FastAPI)    │   │
                    │  │  uvicorn api.main:app     │   │
                    │  │  Port: $PORT (Render)     │   │
                    │  │                           │   │
                    │  │  Background tasks run     │   │
                    │  │  in-process (FastAPI       │   │
                    │  │  BackgroundTasks)          │   │
                    │  └────────────┬──────────────┘   │
                    └───────────────┼──────────────────┘
                                    │
                    ┌───────────────┼───────────────────┐
                    │               │                    │
          ┌─────────▼────────┐  ┌──▼───────────────┐
          │  Supabase         │  │  External APIs   │
          │  PostgreSQL +     │  │  - OpenRouter    │
          │  pgvector         │  │  - Gemini        │
          │  + PgBouncer      │  │  - Langfuse      │
          └──────────────────┘  └──────────────────┘
```

### Services to Deploy

| Service        | Platform | Type        | Purpose                                 |
| -------------- | -------- | ----------- | --------------------------------------- |
| **FastAPI**    | Render   | Web Service | API server + background tasks           |
| **PostgreSQL** | Supabase | Managed DB  | Data + pgvector + LangGraph checkpoints |

> No separate worker or Redis needed. Background tasks (summarization) use FastAPI `BackgroundTasks` and run in the same process.
>
> **Streamlit UI** is optional for production. If needed, deploy as a separate Render web service.

---

## Security: No Direct DB Password

> **Team decision**: Avoid using the Supabase DB password directly, especially in production. The data contains detailed personal info - the postgres password is too privileged.

### Current State vs Target State

| Aspect               | Current (Direct DB)                       | Target (Supabase-native)                                |
| -------------------- | ----------------------------------------- | ------------------------------------------------------- |
| **App DB access**    | SQLAlchemy + `DATABASE_URL` with password | Supabase Python client + `service_role` key             |
| **Migrations**       | Alembic with DB password                  | Supabase CLI (uses access tokens, no password)          |
| **CI/CD migrations** | Manual / `migrate-stag.ps1`               | GitHub Actions + `supabase db push`                     |
| **Local dev**        | Docker PostgreSQL                         | `supabase start` (local containers, no remote password) |
| **Complex queries**  | SQLAlchemy ORM                            | PostgreSQL functions via `supabase.rpc()`               |

### Migration Roadmap (Phased)

This is a significant architectural change. We recommend doing it in phases:

**Phase 1 (Now - Deploy to Prod)**: Use Supabase CLI for migrations + GitHub Actions CI/CD. App still uses `DATABASE_URL` with pooled connection.

**Phase 2 (Backlog)**: Migrate data access layer from SQLAlchemy to Supabase Python client (`supabase-py`). Replace repositories with Supabase Data API calls. Create PostgreSQL functions for complex queries.

**Phase 3 (Backlog)**: Enable Row Level Security (RLS) on all tables. Remove direct DB password from all environments. App uses only `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.

This document focuses on **Phase 1**.

---

## Supabase Free Tier: What's Supported

All features needed for Phase 1 work on the **free tier**:

| Feature                         | Free Tier         | Notes                                        |
| ------------------------------- | ----------------- | -------------------------------------------- |
| Supabase CLI                    | Yes               | Full CLI access                              |
| `supabase db push` (migrations) | Yes               | Uses access tokens                           |
| GitHub Actions CI/CD            | Yes               | `SUPABASE_ACCESS_TOKEN` via `supabase login` |
| pgvector extension              | Yes               | Pre-enabled                                  |
| PgBouncer (connection pooling)  | Yes               | Port 6543                                    |
| PostgREST Data API              | Yes               | For future Phase 2                           |
| Row Level Security (RLS)        | Yes               | For future Phase 3                           |
| `service_role` key              | Yes               | For backend access                           |
| Database size                   | 500 MB            | Monitor usage                                |
| Daily backups                   | **No** (Pro only) | Critical for personal data                   |

> **Recommendation**: Start with free tier for staging. For production with personal data, **Pro ($25/mo)** is strongly recommended for daily backups and point-in-time recovery.

---

## Phase 1: Supabase CLI + GitHub Actions CI/CD

### 1.1 Install Supabase CLI

```bash
# npm (cross-platform)
npm install -g supabase

# macOS
brew install supabase/tap/supabase

# Windows (scoop)
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

### 1.2 Initialize Supabase in the Project

```bash
# Login (generates access token - no DB password needed)
supabase login

# Initialize - creates supabase/ directory
supabase init

# Link to your remote project
supabase link --project-ref <your-project-ref>
```

This creates:

```
fabric/
├── supabase/
│   ├── config.toml      # Supabase project config
│   ├── migrations/       # SQL migration files
│   └── seed.sql          # Optional seed data
```

### 1.3 Transition from Alembic to Supabase CLI Migrations

We have 14 existing Alembic migrations. Here's how to transition:

```bash
# Step 1: Ensure all Alembic migrations are applied to Supabase
# (one-time, using direct connection - last time we use DB password for this)
set DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@db.[REF].supabase.co:5432/postgres
alembic upgrade head

# Step 2: Pull the current remote schema as a baseline
supabase db pull
# This creates: supabase/migrations/<timestamp>_remote_schema.sql
# This is your baseline - all existing tables captured in one SQL file

# Step 3: Verify the baseline matches
supabase db diff --linked
# Should show no differences

# Step 4: Commit
git add supabase/
git commit -m "init supabase CLI with baseline migration"
```

From this point forward, **all new migrations use Supabase CLI**:

```bash
# Create a new migration
supabase migration new add_new_feature
# Edit: supabase/migrations/<timestamp>_add_new_feature.sql

# Test locally
supabase db reset  # Reapplies all migrations from scratch

# Preview against remote (dry run)
supabase db push --dry-run

# Apply to remote
supabase db push
```

### 1.4 LangGraph Checkpoint Tables

The LangGraph `PostgresSaver.setup()` auto-creates checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, `checkpoint_migrations`). These are:

- **NOT managed by Alembic** (excluded in `migrations/env.py`)
- **Auto-created** on first app startup via `create_postgres_checkpointer()` in `agents/conversational/checkpointer.py`

For Supabase CLI, add a migration to handle this explicitly:

```bash
supabase migration new langgraph_checkpoint_tables
```

```sql
-- supabase/migrations/<timestamp>_langgraph_checkpoint_tables.sql
-- LangGraph checkpoint tables
-- These are normally auto-created by PostgresSaver.setup()
-- but we include them here for migration completeness.
-- The setup() call is idempotent and will skip if tables exist.

-- No SQL needed - the app creates these on startup.
-- This migration is a placeholder to document the dependency.
-- If you want explicit control, you can copy the CREATE TABLE
-- statements from LangGraph's source, but it's not required.
```

### 1.5 Local Development with Supabase CLI

Instead of `docker-compose up -d postgres`, developers can now use:

```bash
# Start local Supabase (PostgreSQL + PostgREST + Studio + more)
supabase start

# Output includes local connection details:
#   API URL: http://localhost:54321
#   DB URL: postgresql://postgres:postgres@localhost:54322/postgres
#   Studio URL: http://localhost:54323
#   anon key: eyJ...
#   service_role key: eyJ...

# No remote DB password needed for local development!

# Apply migrations locally
supabase db reset

# Stop
supabase stop
```

Update `.env` for local development:

```env
# Local Supabase (from `supabase start` output)
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
```

---

## GitHub Actions CI/CD

### 2.1 CI: Test Migrations on Pull Request

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  test-migrations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: supabase/setup-cli@v1
        with:
          version: latest

      - name: Start Supabase local
        run: supabase db start

      - name: Verify migrations apply cleanly
        run: supabase db reset

      - name: Check for schema drift
        run: |
          if ! supabase db diff --local | grep -q "No changes"; then
            echo "Schema drift detected!"
            supabase db diff --local
            exit 1
          fi
```

### 2.2 CD: Deploy Migrations on Merge to Main

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  migrate:
    runs-on: ubuntu-latest
    env:
      SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
      SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
    steps:
      - uses: actions/checkout@v4

      - uses: supabase/setup-cli@v1
        with:
          version: latest

      - name: Link to Supabase project
        run: supabase link --project-ref ${{ secrets.SUPABASE_PROJECT_REF }}

      - name: Push migrations
        run: supabase db push

  deploy-api:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Render deploy
        run: |
          curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"
```

### 2.3 GitHub Secrets Required

| Secret                   | Source                                   | Purpose                          |
| ------------------------ | ---------------------------------------- | -------------------------------- |
| `SUPABASE_ACCESS_TOKEN`  | `supabase login` → copy token            | CLI auth (no DB password!)       |
| `SUPABASE_PROJECT_REF`   | Supabase Dashboard → Settings            | Project identifier               |
| `SUPABASE_DB_PASSWORD`   | Supabase Dashboard → Database            | Required by `supabase link` only |
| `RENDER_DEPLOY_HOOK_URL` | Render Dashboard → Service → Deploy Hook | Trigger deploy after migrations  |

> **Note on `SUPABASE_DB_PASSWORD`**: The `supabase link` command currently requires the DB password. However, this password is only used in CI during `link` - it never reaches your app runtime. The Supabase team is working on removing this requirement. The app itself uses the pooled connection URL set on Render.

### 2.4 Migration Workflow for Developers

```
Developer flow:
1. Create branch: git checkout -b feat/new-table
2. Create migration: supabase migration new create_new_table
3. Write SQL in supabase/migrations/<timestamp>_create_new_table.sql
4. Test locally: supabase db reset
5. Commit & push: git add supabase/migrations/ && git commit && git push
6. Open PR → CI runs, tests migrations locally
7. Merge to main → CD runs:
   a. supabase db push (applies migration to prod Supabase)
   b. Trigger Render deploy (new app code goes live)
```

---

## Render Setup

### 3.1 `render.yaml` (Infrastructure as Code)

Create this file in your repo root:

```yaml
# render.yaml
services:
  # FastAPI Web Service (includes background tasks in-process)
  - type: web
    name: fabric-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false # Set manually (Supabase pooled connection)
      - key: OPENROUTER_API_KEY
        sync: false
      - key: OPENROUTER_BASE_URL
        value: https://openrouter.ai/api/v1
      - key: LLM_PROVIDER
        value: openrouter
      - key: LLM_MODEL
        value: openai/gpt-4.1-nano
      - key: RESUME_ANALYZER_PROVIDER
        value: openrouter
      - key: RESUME_ANALYZER_MODEL
        value: google/gemini-2.5-flash
      - key: LLM_FAST_MODEL
        value: openai/gpt-4.1-nano
      - key: LLM_DEEP_MODEL
        value: openai/gpt-4.1-nano
      - key: EMBEDDING_MODEL
        value: openai/text-embedding-3-small
      - key: GEMINI_API_KEY
        sync: false
      - key: API_HOST
        value: "0.0.0.0"
      - key: API_SECRET_KEY
        generateValue: true
      - key: LANGFUSE_ENABLED
        value: "false"
      - key: PYTHON_VERSION
        value: "3.11.6"
    healthCheckPath: /health
    autoDeploy: false # Deploy via GitHub Actions, not auto
```

### 3.2 Python Version

Create a `.python-version` file in repo root:

```
3.11.6
```

---

## Code Changes Required

### 4.1 Restrict CORS for Production

In `api/main.py`, the CORS is currently `allow_origins=["*"]`. Update:

```python
import os

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Set `ALLOWED_ORIGINS` env var on Render to your frontend domain(s).

### 4.2 Add `gunicorn` for Production (Recommended)

Add to `requirements.txt`:

```
gunicorn>=21.2.0
```

Update start command in `render.yaml`:

```
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

### 4.3 Database URL Compatibility (Already Done)

`utils/database.py` already converts `postgresql://` to `postgresql+psycopg://` and sets `prepare_threshold=None` for PgBouncer. Supabase-ready.

`checkpointer.py` uses raw `psycopg` with `prepare_threshold=None`. Also Supabase-ready.

---

## Environment Variables Summary

### Required on Render (Secrets)

| Variable             | Source   | Notes                                 |
| -------------------- | -------- | ------------------------------------- |
| `DATABASE_URL`       | Supabase | Use **pooled** connection (port 6543) |
| `OPENROUTER_API_KEY` | OpenRouter | Primary LLM provider                |
| `GEMINI_API_KEY`     | Google AI | Resume analyzer provider             |
| `API_SECRET_KEY`     | Generate | Random string for API security        |

### Required on Render (Config)

| Variable                   | Value                           |
| -------------------------- | ------------------------------- |
| `LLM_PROVIDER`             | `openrouter`                    |
| `LLM_MODEL`                | `openai/gpt-4.1-nano`           |
| `RESUME_ANALYZER_PROVIDER` | `openrouter`                    |
| `RESUME_ANALYZER_MODEL`    | `google/gemini-2.5-flash`       |
| `LLM_FAST_MODEL`           | `openai/gpt-4.1-nano`           |
| `LLM_DEEP_MODEL`           | `openai/gpt-4.1-nano`           |
| `EMBEDDING_MODEL`          | `openai/text-embedding-3-small` |
| `API_HOST`                 | `0.0.0.0`                       |
| `ALLOWED_ORIGINS`          | `https://yourdomain.com`        |

### Required in GitHub Secrets

| Secret                   | Source             | Purpose                         |
| ------------------------ | ------------------ | ------------------------------- |
| `SUPABASE_ACCESS_TOKEN`  | `supabase login`   | CLI auth for migrations         |
| `SUPABASE_PROJECT_REF`   | Supabase Dashboard | Project identifier              |
| `SUPABASE_DB_PASSWORD`   | Supabase Dashboard | For `supabase link` in CI       |
| `RENDER_DEPLOY_HOOK_URL` | Render Dashboard   | Trigger deploy after migrations |

### Optional (Observability)

| Variable              | Source   | Notes                                 |
| --------------------- | -------- | ------------------------------------- |
| `LANGFUSE_ENABLED`    | -        | Set `true` to enable                  |
| `LANGFUSE_PUBLIC_KEY` | Langfuse |                                       |
| `LANGFUSE_SECRET_KEY` | Langfuse |                                       |
| `LANGFUSE_HOST`       | Langfuse | Default: `https://cloud.langfuse.com` |

---

## Testing Plan

### Phase 1: Local Supabase CLI Testing

```bash
# 1. Init and start local supabase
supabase init
supabase start

# 2. Verify local services are running
# Studio: http://localhost:54323 (visual DB editor)
# API: http://localhost:54321

# 3. Test migrations apply cleanly
supabase db reset

# 4. Start app against local supabase
set DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
uvicorn api.main:app --reload

# 5. Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ping
```

### Phase 2: Test Against Remote Supabase

```bash
# 1. Link to remote project
supabase link --project-ref <ref>

# 2. Push migrations (dry run first)
supabase db push --dry-run
supabase db push

# 3. Verify tables exist (in Supabase SQL Editor)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;

# 4. Verify pgvector
SELECT * FROM pg_extension WHERE extname = 'vector';

# 5. Seed data
python scripts/seed_api_key.py
python scripts/seed_predefined_questions.py

# 6. Test app with remote DB (pooled connection)
set DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
uvicorn api.main:app --reload
```

### Phase 3: Test Core API Endpoints

```bash
# Test authentication
curl -H "X-API-Key: <your-key>" http://localhost:8000/

# Test interview start
curl -X POST http://localhost:8000/interview/start \
  -H "X-API-Key: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": "test-1", "resume_text": "Senior Python developer with 5 years experience..."}'

# Test interview chat (use session_id from above)
curl -X POST http://localhost:8000/interview/chat/<session_id> \
  -H "X-API-Key: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"answer": "I have worked with Python for 5 years..."}'

# Test SSE streaming
curl -N -X POST http://localhost:8000/interview/start/stream \
  -H "X-API-Key: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": "test-sse", "resume_text": "..."}'
```

### Phase 4: Test Background Tasks (Summarization)

```bash
# Trigger summarization (runs as FastAPI BackgroundTask, no separate worker needed)
curl -X POST http://localhost:8000/summarization/analyze-session \
  -H "X-API-Key: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session-id>"}'

# Trigger profile summarization
curl -X POST http://localhost:8000/summarization/summarize-profile \
  -H "X-API-Key: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": "<candidate-id>"}'
```

### Phase 5: Test GitHub Actions CI/CD

```bash
# 1. Create a test migration
supabase migration new test_cicd
# Add a harmless change to the SQL file:
# CREATE TABLE IF NOT EXISTS _test_cicd (id int); DROP TABLE IF EXISTS _test_cicd;

# 2. Push to a feature branch
git checkout -b test/cicd-pipeline
git add supabase/migrations/
git commit -m "Test CI/CD pipeline"
git push -u origin test/cicd-pipeline

# 3. Open PR → verify CI workflow runs and passes

# 4. Merge → verify CD workflow:
#    a. Migrations are pushed to Supabase
#    b. Render deploy is triggered

# 5. Clean up the test migration
```

### Phase 6: Post-Deploy Verification on Render

```bash
BASE_URL=https://fabric-api.onrender.com
API_KEY=<your-production-api-key>

# Health checks
curl $BASE_URL/health
curl $BASE_URL/ping

# Swagger docs
# Visit: $BASE_URL/docs

# End-to-end interview flow
curl -X POST $BASE_URL/interview/start \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"candidate_id":"prod-test","resume_text":"Senior Python developer..."}'

# Test cold start recovery (wait 15+ min, then hit /health again)
```

### Phase 7: Security & Production Readiness

- [ ] CORS origins restricted (not `*`)
- [ ] API keys rotated from dev values
- [ ] No secrets in git (check `.gitignore`)
- [ ] `supabase/` directory committed (migrations, config)
- [ ] `.env` is in `.gitignore`
- [ ] Supabase RLS considered for future Phase 3
- [ ] HTTPS enforced (Render handles automatically)
- [ ] Render health check configured (`/health`)
- [ ] Langfuse enabled for LLM observability

---

## Future: Phase 2 - Supabase Data API Migration (Backlog)

This is the work Anas recommended: move from direct DB access to the Supabase interface.

### Why

- No DB password in app runtime (only `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`)
- Row Level Security (RLS) enforced at database level
- Better security for personal data
- Supabase Dashboard visibility into all data access

### What Changes

| Current                                       | Target                                                         |
| --------------------------------------------- | -------------------------------------------------------------- |
| `SQLModel` + `create_engine(DATABASE_URL)`    | `supabase.create_client(url, service_role_key)`                |
| `session.query(InterviewSession).filter(...)` | `supabase.table("interviewsession").select("*").eq(...)`       |
| Complex joins in SQLAlchemy                   | PostgreSQL functions + `supabase.rpc("function_name", params)` |
| `repositories/*.py` (10 repository classes)   | Rewrite to use `supabase-py` client                            |

### supabase-py Example (What It Looks Like)

```python
from supabase import create_client

# No DB password - uses service_role key
supabase = create_client(
    supabase_url="https://<ref>.supabase.co",
    supabase_key="<service_role_key>"  # Not the DB password!
)

# Simple query (replaces SQLAlchemy)
response = supabase.table("interviewsession") \
    .select("*") \
    .eq("candidate_id", candidate_id) \
    .eq("organization_id", org_id) \
    .execute()
sessions = response.data

# Complex query via PostgreSQL function (RPC)
response = supabase.rpc("get_session_with_messages", {
    "p_session_id": session_id,
    "p_org_id": org_id
}).execute()
```

### PostgreSQL Functions for Complex Queries

For queries too complex for PostgREST, create PostgreSQL functions:

```sql
-- supabase/migrations/<timestamp>_add_rpc_functions.sql
CREATE OR REPLACE FUNCTION get_session_with_messages(
    p_session_id UUID,
    p_org_id UUID
)
RETURNS JSON AS $$
    SELECT json_build_object(
        'session', row_to_json(s),
        'messages', (
            SELECT json_agg(row_to_json(m))
            FROM message m
            WHERE m.session_id = s.id
        )
    )
    FROM interviewsession s
    WHERE s.id = p_session_id
    AND s.organization_id = p_org_id;
$$ LANGUAGE sql SECURITY DEFINER;
```

### LangGraph Checkpointer Consideration

The LangGraph `PostgresSaver` requires direct PostgreSQL access (psycopg). This cannot use the Supabase Data API. Options for Phase 2:

1. Keep a **minimal** pooled connection URL just for the checkpointer
2. Use `service_role` key with Supabase's direct connection (port 5432)
3. Investigate if LangGraph supports custom storage backends

### Dependencies to Add (Phase 2)

```
supabase>=2.0.0
```

---

## Known Issues & Gotchas

### 1. Supabase PgBouncer + Prepared Statements

Already handled. Both `utils/database.py` and `checkpointer.py` set `prepare_threshold=None`.

### 2. Supabase Direct vs Pooled Connection

| Use Case                        | Connection Type    | Port |
| ------------------------------- | ------------------ | ---- |
| Migrations (`supabase db push`) | Handled by CLI     | N/A  |
| App runtime (FastAPI)           | Pooled (PgBouncer) | 6543 |
| LangGraph checkpointer          | Pooled (PgBouncer) | 6543 |

### 3. Render Cold Starts

Starter plans spin down after ~15 min idle. First request takes 10-30s. Options:

- Use Standard plan ($7/mo) for always-on
- Add a cron health check to keep service warm

### 4. `supabase link` Needs DB Password

The `supabase link` command currently requires the DB password. This is only used:

- Once during initial setup
- In GitHub Actions CI/CD (stored as a secret)
- Never in app runtime

### 5. psycopg2 vs psycopg (v3)

`requirements.txt` has both `psycopg2` and `psycopg[binary]`. Consider removing `psycopg2` if only `psycopg` (v3) is used in app code. On Render (Linux), `psycopg2` may need `libpq-dev`.

### 6. Alembic Retirement

After transitioning to Supabase CLI:

- Keep `alembic.ini` and `migrations/` in the repo for historical reference
- Remove Alembic from dev workflow docs
- Don't delete - the migration history is valuable documentation

---

## Deployment Steps (Summary)

```
One-time setup:
1. supabase login
2. supabase init
3. supabase link --project-ref <ref>
4. Run existing Alembic migrations against Supabase (last time)
5. supabase db pull (baseline)
6. Set up GitHub secrets (SUPABASE_ACCESS_TOKEN, PROJECT_REF, DB_PASSWORD, RENDER_DEPLOY_HOOK)
7. Add .github/workflows/ci.yml and deploy.yml
8. Add render.yaml and .python-version
9. Create Render services, set env vars
10. Seed data (API keys, predefined questions)
11. Push to main → GitHub Actions deploys

Ongoing workflow:
1. Create branch
2. supabase migration new <name>
3. Write SQL migration
4. supabase db reset (test locally)
5. Push + open PR → CI tests migrations
6. Merge → CD pushes migrations + triggers Render deploy
```

---

## Cost Estimates

| Service                               | Plan    | Cost/mo    |
| ------------------------------------- | ------- | ---------- |
| Render Web Service (API)              | Starter | $7         |
| **Render Total**                      |         | **~$7/mo** |
| Supabase (Free)                       | Free    | $0         |
| Supabase (Pro - recommended for prod) | Pro     | $25/mo     |
| **Total (Free DB)**                   |         | **~$7/mo** |
| **Total (Pro DB)**                    |         | **~$32/mo** |

> LLM API costs (OpenRouter, Gemini) are usage-based and separate.
