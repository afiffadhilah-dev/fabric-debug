# Celery Quick Start

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

- `celery>=5.4.0`
- `redis>=5.0.0`

## 2. Start Redis

### Option A: Docker (Recommended)

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Option B: Native

```bash
# macOS
brew install redis
redis-server

# Windows (WSL)
wsl
sudo apt update && sudo apt install redis-server
redis-server

# Linux
sudo apt update && sudo apt install redis-server
redis-server
```

### Verify Redis is Running

```bash
redis-cli ping
# Output: PONG
```

### Access Redis CLI (Docker)

If you're using Docker Compose, access Redis CLI with:

```bash
docker exec -it fabric_redis redis-cli
```

Then you can use Redis commands:

```
KEYS *           # List all keys
LLEN celery      # Check pending Celery tasks
DBSIZE           # Total number of keys
INFO             # Server information
FLUSHDB          # Clear all data
exit             # Exit Redis CLI
```

## 3. Start Celery Worker

In a **new terminal**:

### All Platforms

```bash
# From project root, activate virtual environment first
source venv/bin/activate  # Linux/macOS/WSL
# or
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Then start Celery
celery -A config.celery_config worker --loglevel=info
```

You should see:

```
 -------------- celery@YourComputer v5.4.0
--- ***** -----
-- ******* ----
- *** --- * ---
- ** ---------- [config]
- ** ---------- .broker: redis://localhost:6379/0
- ** ---------- .result_backend: redis://localhost:6379/1
- ** ---------- .concurrency: 4
```

## 4. Start FastAPI Server

In **another terminal**:

```bash
python -m uvicorn api.main:app --reload
```

Visit: http://localhost:8000/docs

## 5. Test an Endpoint

### Create a Session Summary Task

```bash
curl -X POST "http://localhost:8000/summarization/summarize-session" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "session_id": "test-session-123",
    "candidate_id": "test-candidate-456",
    "mode": "SELF_REPORT"
  }'
```

**Response (HTTP 202):**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "INITIATED",
  "message": "Session summarization task queued..."
}
```

### Check Task Status

```bash
curl "http://localhost:8000/summarization/task-status/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Response:**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "SUCCESS",
  "message": "Task status: SUCCESS",
  "error": null
}
```

## 6. Using Docker Compose (Database & Cache Only)

Docker Compose starts **PostgreSQL** and **Redis** only. Celery Worker and FastAPI run locally on your machine.

```bash
# Start database and cache services
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

**Services:**

- **PostgreSQL**: localhost:5432 (database)
- **Redis**: localhost:6379 (message broker & cache)
- **FastAPI**: localhost:8000 (run locally: `python -m uvicorn api.main:app --reload`)
- **Celery Worker**: localhost (run locally with PYTHONPATH set)

## Troubleshooting

### ModuleNotFoundError: No module named 'agents'

**Solution:** Activate the virtual environment before running Celery.

```bash
# Linux/macOS/WSL
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Then run Celery
celery -A config.celery_config worker --loglevel=info
```

### "Connection refused" when running tasks

1. Verify Redis is running:

   ```bash
   docker-compose ps
   ```

2. Check .env file has correct URLs:

   ```env
   REDIS_URL=redis://localhost:6379/0
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/1
   ```

3. Restart Celery worker

### Worker not picking up tasks

1. Check worker logs for errors
2. Verify Redis has tasks:
   ```bash
   docker exec fabric_redis redis-cli LLEN celery
   ```
3. Ensure PYTHONPATH is set so modules can be imported

### Tasks stuck in PENDING

1. Restart the Celery worker (Ctrl+C, then restart with PYTHONPATH)
2. Clear stuck tasks:
   ```bash
   docker exec fabric_redis redis-cli FLUSHDB
   ```

---

**For detailed documentation, see [CELERY_INTEGRATION.md](CELERY_INTEGRATION.md)**
