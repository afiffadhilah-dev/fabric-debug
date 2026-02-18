# Celery Integration Guide

This document outlines the migration from custom background task worker to **Celery** with **Redis**.

## Overview

### What Changed

- **Before**: Custom `BackgroundTaskWorker` polling database for tasks
- **Now**: Celery distributed task queue with Redis message broker

### Benefits

✅ Production-grade task queue  
✅ Redis for fast in-memory operations  
✅ Automatic retries with exponential backoff  
✅ Task status monitoring via Redis  
✅ Horizontal scaling (multiple workers)  
✅ Dead letter queue for failed tasks  
✅ Native task persistence and result backends

---

## Architecture

### Components

```
API Request
    ↓
Service Layer (summarize_*_async)
    ↓
Celery Task (delay/apply_async)
    ↓
Redis (message broker)
    ↓
Celery Worker (processes tasks)
    ↓
Background Execution
```

### Task Flow

1. **API Endpoint** receives request
2. **Service** calls `summarize_session_async()` or `summarize_profile_async()`
3. **Celery** enqueues task to Redis (non-blocking)
4. **API** immediately returns Celery task ID (HTTP 202)
5. **Celery Worker** picks up task from Redis when available
6. **Worker** executes task and stores result in Redis
7. **Client** polls `/task-status/{task_id}` to check progress

---

## Configuration

### Environment Variables (.env)

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

**Note**: Using separate Redis databases (0 for broker, 1 for results) prevents conflicts.

### Celery Config (config/celery_config.py)

```python
from celery import Celery
from config.settings import settings

celery_app = Celery("fabric")
celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,    # 30 min hard limit
    task_soft_time_limit=25 * 60, # 25 min soft limit
)

celery_app.autodiscover_tasks(["agents.summarization"])
```

---

## Running the Application

### Local Development

#### 1. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using Homebrew (macOS)
brew services start redis

# Or native installation (Windows - WSL/native)
redis-server
```

#### 2. Start Celery Worker

```bash
# From project root
celery -A config.celery_config worker --loglevel=info
```

**Output should show:**

```
 -------------- celery@hostname v5.4.0 (oasis)
--- ***** -----
-- ******* ----
- *** --- * ---
- ** ---------- [config]
- ** ---------- .broker: redis://localhost:6379/0
- ** ---------- .concurrency: 4
- ** ---------- .loglevel: INFO
```

#### 3. Start FastAPI Server

```bash
python -m uvicorn api.main:app --reload
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f celery_worker
docker-compose logs -f postgres
docker-compose logs -f redis
```

---

## Tasks

### Available Tasks

#### 1. summarize_session_task

```python
from agents.summarization.tasks import summarize_session_task

# Dispatch task
task = summarize_session_task.delay(
    session_id="18426303-9f4f-49ec-bb82-bb7820bb7485",
    candidate_id="0c6dec64-5292-4293-859f-700411c57e6c",
    mode="SELF_REPORT"
)

# Get task ID
print(task.id)

# Check status
print(task.status)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY

# Get result (blocks if not ready)
result = task.get(timeout=300)  # 5 min timeout
```

#### 2. summarize_profile_task

```python
from agents.summarization.tasks import summarize_profile_task

task = summarize_profile_task.delay(
    candidate_id="0c6dec64-5292-4293-859f-700411c57e6c"
)
```

### Task Retry Logic

Tasks have automatic retry configured:

```python
@celery_app.task(bind=True, max_retries=3)
def summarize_session_task(self, session_id, candidate_id, mode="SELF_REPORT"):
    try:
        # Execute task
        ...
    except Exception as exc:
        # Exponential backoff: 60s, 120s, 240s
        retry_delay = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)
```

---

## API Endpoints

### POST /summarization/summarize-session

Enqueue a session summarization task.

**Request:**

```json
{
  "session_id": "18426303-9f4f-49ec-bb82-bb7820bb7485",
  "candidate_id": "0c6dec64-5292-4293-859f-700411c57e6c",
  "mode": "SELF_REPORT"
}
```

**Response (202 Accepted):**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "INITIATED",
  "message": "Session summarization task queued. Task ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### POST /summarization/summarize-profile

Enqueue a profile summarization task.

**Request:**

```json
{
  "candidate_id": "0c6dec64-5292-4293-859f-700411c57e6c"
}
```

**Response (202 Accepted):**

```json
{
  "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "status": "INITIATED",
  "message": "Profile summarization task queued. Task ID: b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

### GET /summarization/task-status/{task_id}

Check status of a Celery task.

**Response (200 OK):**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "SUCCESS",
  "message": "Task status: SUCCESS",
  "error": null
}
```

**Task Statuses:**

- `PENDING` - Task enqueued, waiting for worker
- `STARTED` - Worker started processing
- `SUCCESS` - Task completed successfully
- `FAILURE` - Task failed
- `RETRY` - Task is retrying
- `UNKNOWN` - Task not found or expired

---

## Monitoring

### Redis CLI

```bash
# Connect to Redis
redis-cli

# Check pending tasks
LLEN celery

# Monitor in real-time
MONITOR

# View task results
KEYS *
GET celery-task-meta-{task_id}
```

### Celery Flower (Optional)

Real-time task monitoring web UI.

```bash
# Install
pip install flower

# Start
celery -A config.celery_config flower

# Open browser
http://localhost:5555
```

### Celery Events

```bash
# Monitor tasks in real-time
celery -A config.celery_config events
```

---

## Troubleshooting

### Tasks Not Processing

**Check 1**: Is Celery worker running?

```bash
celery -A config.celery_config worker --loglevel=debug
```

**Check 2**: Is Redis accessible?

```bash
redis-cli ping
# Should output: PONG
```

**Check 3**: Check Redis connection in settings

```python
# config/settings.py
CELERY_BROKER_URL=redis://localhost:6379/0  # Must match .env
```

### Task Stuck in PENDING

```bash
# Check worker logs
celery -A config.celery_config worker --loglevel=debug

# Check Redis
redis-cli
LLEN celery  # Should show pending tasks
```

### Clear All Tasks (Warning: destructive)

```bash
# Via Redis
redis-cli
FLUSHDB  # Clears entire Redis database!

# Via Celery
celery -A config.celery_config purge
```

### View Task Result After Completion

```python
from config.celery_config import celery_app

result = celery_app.AsyncResult('task_id_here')
print(result.result)  # Prints the return value
```

---

## Migration Checklist

- ✅ Redis installed and running
- ✅ Celery & Redis Python packages installed (`pip install -r requirements.txt`)
- ✅ Celery config created (`config/celery_config.py`)
- ✅ Tasks module created (`agents/summarization/tasks.py`)
- ✅ Service layer updated to use Celery (`agents/summarization/service.py`)
- ✅ API routes updated for Celery (`api/routes/candidate_summarization.py`)
- ✅ .env configured with Redis URLs
- ✅ docker-compose.yml updated with Redis & Celery worker
- ✅ Old worker code (`worker.py`, `task_dispatcher.py`) can be removed (optional)

---

## Next Steps

### Optional: Task Persistence

Store task results in PostgreSQL instead of Redis:

```python
from sqlalchemy import create_engine
from celery_sqlalchemy_scheduler import DatabaseScheduler

celery_app.conf.beat_scheduler = 'celery_sqlalchemy_scheduler:DatabaseScheduler'
celery_app.conf.beat_scheduler_engine = create_engine(settings.DATABASE_URL)
```

### Optional: Task Scheduling

Schedule recurring tasks:

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'agents.summarization.tasks.cleanup_old_summaries',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}
```

### Optional: Task Routing

Route different task types to different workers:

```python
celery_app.conf.task_routes = {
    'agents.summarization.tasks.summarize_session_task': {'queue': 'long_running'},
    'agents.summarization.tasks.summarize_profile_task': {'queue': 'quick'},
}
```

---

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/docs/)
- [Celery Task Routing](https://docs.celeryproject.org/en/stable/userguide/routing.html)
- [Flower Monitoring](https://flower.readthedocs.io/)
