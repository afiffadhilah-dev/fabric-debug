# Database Setup Guide

This project supports two database configurations:
- **Local Development**: Docker with PostgreSQL + pgvector
- **Production**: Supabase (PostgreSQL + pgvector pre-enabled)

## Quick Start (Local Development)

### Prerequisites
- Docker and Docker Compose installed
- Python virtual environment activated

### Steps

1. **Start the database**:
```bash
docker-compose up -d
```

This will:
- Pull the official `pgvector/pgvector:pg16` image
- Start PostgreSQL on `localhost:5432`
- Automatically enable pgvector extension
- Create database: `fabric_db`
- Create user: `fabric_user` / `fabric_password`

2. **Verify database is running**:
```bash
docker-compose ps
```

You should see:
```
NAME              IMAGE                     STATUS
fabric_postgres   pgvector/pgvector:pg16   Up (healthy)
```

3. **Run database migrations**:
```bash
alembic upgrade head
```

4. **Test the connection** (optional):
```bash
# Connect to database
docker exec -it fabric_postgres psql -U fabric_user -d fabric_db

# Inside psql, check pgvector extension:
\dx vector

# Exit psql
\q
```

### Common Commands

```bash
# View logs
docker-compose logs -f postgres

# Stop database (keeps data)
docker-compose down

# Stop and remove all data (fresh start)
docker-compose down -v

# Restart database
docker-compose restart
```

## Production Setup (Supabase)

### Steps

1. **Create Supabase project**:
   - Go to https://supabase.com
   - Create new project
   - Wait for project to be ready (~2 minutes)

2. **Get connection string**:
   - Go to Project Settings > Database
   - Copy "Connection string" (Direct connection or Pooler)
   - Example format:
     ```
     postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```

3. **Update environment variable**:
   ```bash
   # In your .env file, replace DATABASE_URL with Supabase connection string
   DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```

4. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Verify in Supabase**:
   - Go to Table Editor in Supabase Dashboard
   - You should see `candidate` and `candidatechunk` tables

### Notes about Supabase

- ✅ pgvector extension is **pre-enabled** (no setup needed)
- ✅ Supports up to 2000-dimensional vectors
- ✅ Free tier includes 500MB database + 50MB file storage
- ✅ Automatic backups on paid plans
- ✅ Built-in connection pooler (use port 6543 for pooler, 5432 for direct)

## Switching Between Environments

Simply change the `DATABASE_URL` in your `.env` file:

```bash
# Local Docker
DATABASE_URL=postgresql://fabric_user:fabric_password@localhost:5432/fabric_db

# Supabase
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

## Troubleshooting

### "Connection refused" error
- Make sure Docker is running
- Check if database container is up: `docker-compose ps`
- Check logs: `docker-compose logs postgres`

### "Extension 'vector' does not exist"
- For local: The extension should be auto-created by `init-db.sql`
- For Supabase: pgvector is pre-enabled, contact support if missing

### Port 5432 already in use
- Another PostgreSQL instance is running
- Stop it or change port in `docker-compose.yml`:
  ```yaml
  ports:
    - "5433:5432"  # Use 5433 on host
  ```
- Update `DATABASE_URL` to use the new port

### Fresh database reset
```bash
# Stop and remove all data
docker-compose down -v

# Start fresh
docker-compose up -d
alembic upgrade head
```
