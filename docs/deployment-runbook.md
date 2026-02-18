# Deployment Runbook: Render + Supabase

Step-by-step guide for deploying Fabric to production (Phase 1).

**Scope**: Supabase CLI for migrations, Render for hosting, manual migration pushes.
No Celery/Redis - uses FastAPI BackgroundTasks for async work.

---

## Prerequisites

- Supabase account with a new project created
- Render account with GitHub repo connected
- OpenRouter API key
- Gemini API key (for resume analyzer)
- Docker Desktop installed and running (needed for local Supabase)

---

## Part 1: Supabase Setup (One-Time)

### 1.1 Install Supabase CLI

```powershell
# Windows (recommended: scoop)
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# Verify
supabase --version

# Alternative: use npx (no install needed, prefix all commands with npx)
# npx supabase --version
```

> If using `npx`, prefix all `supabase` commands in this runbook with `npx`.

### 1.2 Login

```powershell
supabase login
```

Opens browser for authentication. Stores access token locally.

### 1.3 Initialize in project

```powershell
cd D:\work\fabric
supabase init
```

This creates a `supabase/` directory with `config.toml`. The `migrations/` folder is created automatically when you create your first migration (step 1.5).

### 1.4 Link to remote project

Get your **project ref** from: Supabase Dashboard > Project Settings > General.

```powershell
supabase link --project-ref <your-project-ref>
```

Uses your login token from step 1.2. No DB password needed.

### 1.5 Create baseline migration from existing schema

Since this is a fresh Supabase DB, we need to create all tables. We'll use the local Supabase + Alembic to generate a baseline:

```powershell
# Ensure Docker Desktop is running, then start local Supabase
supabase start
```

Note the DB URL from the output (should be `postgresql://postgres:postgres@localhost:54322/postgres`).

```powershell
# Apply all Alembic migrations to local Supabase DB
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:54322/postgres"
alembic upgrade head
```

```powershell
# Generate a Supabase migration from the resulting schema
supabase db diff -f initial_schema
```

This creates `supabase/migrations/<timestamp>_initial_schema.sql` with all your tables as SQL.

```powershell
# Verify locally (resets DB and replays migration from scratch)
supabase db reset
```

### 1.6 Push to production Supabase

```powershell
# Preview what will be applied
supabase db push --dry-run

# Apply
supabase db push
```

### 1.7 Verify tables in Supabase

Go to Supabase Dashboard > SQL Editor and run:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
```

You should see all your tables (interviewsession, message, candidate, organization, etc.).

Also verify pgvector (pre-enabled on Supabase):

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

> **Note about LangGraph checkpointer**: The checkpointer tables (`checkpoints`, `checkpoint_writes`, etc.)
> are NOT created by migrations. They are auto-created on first app startup via `PostgresSaver.setup()`.
> No manual action needed.

### 1.8 Seed production data

You need an API key and organization to use the API.

> **Note**: This is the one step that requires the production DB password. It's a one-time operation.
> Get the connection string from: Supabase Dashboard > Project Settings > Database > Connection string (URI).

```powershell
# Point to production Supabase (pooled connection, port 6543)
$env:DATABASE_URL = "postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres"

python scripts/seed_api_key.py
python scripts/seed_predefined_questions.py
```

Save the API key output - you'll need it for Render env vars and testing.

### 1.9 Stop local Supabase

```powershell
supabase stop
```

### 1.10 Commit Supabase files

```powershell
git add supabase/
git commit -m "Add Supabase CLI baseline migration"
```

---

## Part 2: Render Setup

### 2.1 Create Web Service

1. Go to [Render Dashboard](https://dashboard.render.com) > **New** > **Web Service**
2. Select your connected GitHub repo
3. Select branch: `main`

### 2.2 Configure Build & Start

| Setting               | Value                                              |
| --------------------- | -------------------------------------------------- |
| **Runtime**           | Python                                             |
| **Build Command**     | `pip install -r requirements.txt`                  |
| **Start Command**     | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health`                                          |
| **Auto-Deploy**       | Yes (deploys on push to main)                      |

> Note: `uvicorn` is already in `requirements.txt`.

### 2.3 Set Environment Variables

In Render Dashboard > your service > **Environment**:

**Secrets** (click "Add Secret"):

| Key                  | Value                                                                                     |
| -------------------- | ----------------------------------------------------------------------------------------- |
| `DATABASE_URL`       | `postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres` |
| `OPENROUTER_API_KEY` | Your OpenRouter key                                                                       |
| `GEMINI_API_KEY`     | Your Gemini key                                                                           |
| `API_SECRET_KEY`     | Generate a random string                                                                  |

**Config** (click "Add Environment Variable"):

| Key                        | Value                                        |
| -------------------------- | -------------------------------------------- |
| `LLM_PROVIDER`             | `openrouter`                                 |
| `LLM_MODEL`                | `openai/gpt-4.1-nano`                        |
| `RESUME_ANALYZER_PROVIDER` | `openrouter`                                 |
| `RESUME_ANALYZER_MODEL`    | `google/gemini-2.5-flash`                    |
| `LLM_FAST_MODEL`           | `openai/gpt-4.1-nano`                        |
| `LLM_DEEP_MODEL`           | `openai/gpt-4.1-nano`                        |
| `EMBEDDING_MODEL`          | `openai/text-embedding-3-small`              |
| `API_HOST`                 | `0.0.0.0`                                    |
| `ALLOWED_ORIGINS`          | `*` (restrict later to your frontend domain) |
| `LANGFUSE_ENABLED`         | `false`                                      |

---

## Part 3: Code Changes

The `test/deploy-prod` branch (based on dev) already has these changes:

- **CORS**: `api/main.py` reads `ALLOWED_ORIGINS` env var
- **FastAPI BackgroundTasks**: Replaces Celery/Redis for async work
- **All dev features**: 99 commits ahead of main

### 3.1 Commit any pending changes and push

```powershell
git checkout test/deploy-prod
git add -A
git commit -m "Production deployment prep"
git push -u origin test/deploy-prod
```

---

## Part 4: Deploy

### 4.1 Create PR and merge

```powershell
# Create PR from test/deploy-prod to main
gh pr create --base main --title "Production deployment setup" --body "Supabase CLI + Render config"
```

Review and merge the PR. Render auto-deploys from main.

### 4.2 Verify deployment

```powershell
# Health check
curl https://<your-app>.onrender.com/health

# Ping
curl https://<your-app>.onrender.com/ping

# Swagger docs
# Open: https://<your-app>.onrender.com/docs

# Test with API key
curl -H "X-API-Key: <your-key>" https://<your-app>.onrender.com/
```

### 4.3 End-to-end test

```powershell
$BASE = "https://<your-app>.onrender.com"
$KEY = "<your-api-key>"

# Start interview
curl -X POST "$BASE/interview/start" `
  -H "X-API-Key: $KEY" `
  -H "Content-Type: application/json" `
  -d '{"candidate_id":"prod-test","resume_text":"Senior Python developer with 5 years experience in FastAPI and PostgreSQL"}'
```

---

## Part 5: Ongoing Workflow

### For new database migrations

> **Important**: Use Supabase CLI for all new migrations. Do NOT use `alembic revision` anymore.
> Alembic migrations are kept for history only.

```powershell
# 1. Create migration
supabase migration new add_new_feature

# 2. Edit the SQL file
# supabase/migrations/<timestamp>_add_new_feature.sql

# 3. Test locally
supabase start
supabase db reset    # replays all migrations from scratch
supabase stop

# 4. Push to production Supabase
supabase db push --dry-run   # preview
supabase db push              # apply

# 5. Commit migration file
git add supabase/migrations/
git commit -m "Add migration: add_new_feature"
git push
```

### For code changes (no DB migration)

Just push to main. Render auto-deploys.

### For new team members

New developers only need to:

```powershell
# 1. Clone repo
git clone <repo-url>
cd fabric

# 2. Setup Python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Install Supabase CLI
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
# Or use npx: prefix all supabase commands with "npx"

# 4. Start local Supabase (Docker Desktop must be running)
supabase start

# 5. Create .env for local dev
# Copy .env.example, set:
# DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
# OPENROUTER_API_KEY=<your-key>

# 6. Apply migrations locally
supabase db reset

# 7. Seed local data
python scripts/seed_api_key.py
python scripts/seed_predefined_questions.py

# 8. Run
uvicorn api.main:app --reload
```

No production passwords needed for local development.

---

## Future: Restricted DB Role

Replace the superuser `DATABASE_URL` in Render with a limited role that can only read/write data (no DDL).

1. Create role in Supabase SQL Editor:
2. Update `DATABASE_URL` in Render to use `fabric_backend` instead of `postgres`
3. No code changes needed

---

## Future: CI/CD with GitHub Actions

When the team is ready, add automated migration testing and deployment:

**CI** (`.github/workflows/ci.yml`) - runs on every PR:

- Starts local Supabase in GitHub Actions
- Applies all migrations
- Verifies no schema drift

**CD** (`.github/workflows/deploy.yml`) - runs on merge to main:

- Runs `supabase db push` to apply migrations to production
- Triggers Render deploy

**GitHub Secrets needed:**

| Secret                   | Source                                   |
| ------------------------ | ---------------------------------------- |
| `SUPABASE_ACCESS_TOKEN`  | `supabase login` → copy token            |
| `SUPABASE_PROJECT_REF`   | Supabase Dashboard > Settings            |
| `SUPABASE_DB_PASSWORD`   | Supabase Dashboard > Database            |
| `RENDER_DEPLOY_HOOK_URL` | Render Dashboard > Service > Deploy Hook |

This removes the need for anyone to run `supabase db push` manually.
