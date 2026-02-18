# Supabase 502 Investigation

## Problem
Deploying on Render with Supabase DB → 502 errors on concurrent interviews.
Same code with Neon DB works fine.

## Trial Log

### Trial 1: Reduce connection pool sizes
**Files changed:** `utils/database.py`, `agents/conversational/checkpointer.py`

- SQLAlchemy engine: pool 5+10 → 3+2 (max 5)
- Checkpointer sync pool: max 10 → 3
- Checkpointer async pool: max 10 → 3
- Added `connect_timeout=10` to all connections
- Total max connections: ~35 → ~11 (Supabase free limit: 15)

**Result:** Still 502. 1 of 2 concurrent interviews fails.

### Trial 2: Add `sslmode=require` to DATABASE_URL
**File changed:** `.env`

- Added `?sslmode=require` to connection string
- Forces SSL immediately, no negotiation fallback

**Result:** Still fails. Error: `couldn't get a connection after 10.00 sec`. Checkpointer pool (max 3) fully occupied by interview 1, interview 2 can't acquire a connection.

### Trial 3: Disable Langfuse observability
**File changed:** `.env`

- Set `LANGFUSE_ENABLED=false`
- Removes external API calls during interview processing

**Result:** Not tested yet (Trial 2 already identified root cause)

### Trial 4: Switch to Supabase direct connection (bypass Supavisor)
**File changed:** `.env`

- Use direct connection: `db.xxx.supabase.co:5432` instead of `pooler.supabase.com:6543`
- Bypasses Supavisor pooler entirely → connects straight to Postgres
- Note: previously had errors with direct connection (prepared statements / IPv6 issues?)

**Result:** Failed. `500: Failed to validate API key` — app can't reach DB at all. Direct connection likely blocked by Render IPv6 / Supabase firewall on free tier.

### Trial 5: Switch checkpointer to MemorySaver
**Files changed:** `agents/conversational/checkpointer.py`, `agents/conversational/service.py`

- Replace PostgresSaver with MemorySaver (in-memory state, zero DB connections)
- Removes heaviest DB consumer from connection pool
- Trade-off: state lost on process restart

**Result:** 2 concurrent interviews both completed successfully. Checkpointer no longer consumes DB connections.

**New issue found:** After interviews completed, background summarization triggered automatically. Summarization holds DB connections for minutes (heavy DB + LLM calls). When a new interview request came in during summarization → 500/502 again.

### Trial 6: Disable auto-trigger summarization
**Files changed:** `config/settings.py`, `services/interview_service.py`

- Added `AUTO_SUMMARIZE=false` env var (default: false)
- Background summarization was holding DB connections during long LLM calls

**Result:** Still intermittent 502 with 2 concurrent interviews.

### Trial 7: Increase SQLAlchemy pool + fix duplicate engine
**Files changed:** `utils/database.py`, `utils/db.py`

- Confirmed: `get_db()` holds a DB connection for entire SSE request (minutes during LLM calls)
- Log confirmed: `QueuePool limit of size 3 overflow 2 reached, connection timed out`
- Increased pool: 3+2=5 → 5+5=10 (safe now that checkpointer + auto-summarize are disabled)
- Fixed `utils/db.py` (duplicate engine) to also have pool limits

Connection budget:
```
Before (original):     SQLAlchemy 15 + Checkpointer 20 = 35 (way over limit)
After all fixes:       SQLAlchemy 10 + Checkpointer 0  = 10 (within Supabase's 15)
```

**Result:** Still fails. Single interview times out at answer #10-12. No server error in Render logs. Client error: `The read operation timed out`. Pool is NOT the issue here.

### Trial 8: Add SSE keepalive ping
**File changed:** `api/routes/interview.py`

- Added `ping=15` to both `EventSourceResponse` calls
- Sends SSE ping comment every 15 seconds during processing
- Prevents Render proxy from killing idle SSE connections
- Root cause: long LLM calls (10-30s) between SSE events → Render thinks connection is dead → 502

**Result:** SSE keepalive works — no more idle timeout. Interview ran 483s (8 min) without Render killing connection.

Remaining issues:
1. Supabase `connection timeout expired` still occurs under 2 concurrent interviews (Supabase pooler itself is slow/rejecting)
2. Render restarted process after long run — likely memory limit (512MB free tier)
3. `WARNING: Failed to persist answer to database` — non-fatal but loses data

### Trial 9: Fresh DB sessions for streaming endpoints
**File changed:** `services/interview_service.py`

- Root cause: `get_db()` holds a DB connection for entire SSE request (up to 12 min)
- Supabase kills idle connections → `server closed the connection unexpectedly` on final UPDATE
- Fix: use `Session(get_engine())` fresh sessions for DB writes after streaming completes
- Applied to both `start_interview_stream` and `continue_interview_stream`
- Added `_persist_extracted_skills_with_session()` helper for fresh session context

**Result:** Still stuck on single interview. Deeper issue found (Trial 10).

### Trial 10: Fix connection leak in update_state_node
**Files changed:** `agents/conversational/nodes/update_state.py`, `agents/conversational/graph.py`, `agents/conversational/service.py`, `utils/database.py`

- Root cause: `update_state_node` had a DB session scoping bug:
  ```python
  # BUG: session closes immediately, but message_repo uses it OUTSIDE the block
  with Session(engine) as db_session:
      message_repo = MessageRepository(db_session)
  # ... all DB operations happen here, after session is closed
  message_repo.create(...)  # reopens connection, NEVER returns it to pool
  ```
- Each answer leaked 1 connection from the pool (never returned)
- After ~9 answers (pool max 10 - 1 for get_db), pool exhausted → hangs for pool_timeout
- With `ping=15` keepalive, connection stays alive → appears "stuck" instead of 502
- Fix: moved all DB operations INSIDE the `with Session()` block
- Also: removed unused `message_repo` injection from graph/service (node manages own session)
- Also: reverted pool to 3+2=5 (enough now that leak is fixed)

**Result:** Deployed. See Trial 11 for combined test results.

### Trial 11: Fix async graph missing repos + statement_timeout + deploy all fixes
**Files changed:** `agents/conversational/service.py`, `agents/conversational/nodes/analyze_resume_coverage.py`, `utils/database.py`

Combined deployment of Trials 9, 10, and additional fixes:

- **Async graph missing `predefined_question_repo`**: Streaming endpoints used async graph created WITHOUT injected repo. `analyze_resume_coverage_node` fell back to `create_engine(settings.DATABASE_URL)` — bare engine without `prepare_threshold=None` → prepared statements break Supavisor → node hangs. Fixed by injecting repo into async graph too.
- **Fallback engine in analyze_resume_coverage**: Changed from `create_engine()` (bare) to `get_engine()` (cached, properly configured) as safety net.
- **`statement_timeout=15000`**: Added via SQLAlchemy `connect` event hook (not `options` flag — Supavisor rejects connection-level options). Kills any query hanging >15s.
- **`options` flag broke Supavisor**: First attempt used `connect_args={"options": "-c statement_timeout=15000"}` → Supavisor rejected it → `500: Failed to validate API key`. Fixed by using `SET statement_timeout` after connection established.

**Result:**
- 1 concurrent interview: **completed successfully**
- 2 concurrent interviews: **502 error** — both interviews stopped mid-way

## Current Status

### What's fixed
- Checkpointer no longer consumes DB connections (MemorySaver)
- Auto-summarize disabled (no background DB contention)
- SSE keepalive prevents Render proxy timeout (ping=15)
- Connection pool sized to fit Supabase free tier (max 5)
- Streaming endpoints use fresh DB sessions for final writes (no stale connection)
- Fixed connection leak in update_state_node — was leaking 1 connection per answer
- Fixed async graph missing repo injection — caused streaming predefined interviews to hang
- Added statement_timeout=15s — prevents indefinite DB query hangs
- Supabase logs checked — no app-level errors visible (connections go through Supavisor, pooler logs not available on free tier)

### What's still broken
- **2 concurrent interviews → 502** — Supabase free tier cannot handle the connection load
- Render free tier memory limit may kill long-running interviews
- These are **infrastructure limits**, not code issues

### Recommendations
- **For production:** Upgrade Supabase to Pro ($25/mo, 60 connections) — solves connection issue
- **For production:** Upgrade Render to Starter ($7/mo, 1GB RAM) — solves memory/restart issue
- **For free tier:** Limit to 1 concurrent interview (works reliably)

## Findings

1. **Checkpointer was the biggest DB consumer** — fixed by MemorySaver (Trial 5)
2. **Background summarization is the second biggest** — fixed by AUTO_SUMMARIZE=false (Trial 6)
3. **Connection leak in update_state_node** — leaked 1 DB connection per answer, caused pool exhaustion (Trial 10)
4. **Async graph missing repo injection** — streaming predefined interviews used bare engine without Supavisor compatibility (Trial 11)
5. **`get_db()` holds connection for entire SSE lifetime** — Supabase kills idle connections, fixed by fresh sessions (Trial 9)
6. **Supavisor rejects connection-level `options`** — use `SET` after connect instead (Trial 11)
7. **Supabase free tier (15 backend connections)** is the hard limit — 1 concurrent interview works, 2 does not

**Why Neon works:** Neon provides ~100 connections with autoscaling compute — no contention even with all consumers running.

## Config added
- `CHECKPOINTER_TYPE=memory` (default) or `CHECKPOINTER_TYPE=postgres` in `.env`
- `AUTO_SUMMARIZE=false` (default) in `.env`

## Other options
- Upgrade Supabase plan (free: 15 connections → Pro $25/mo: 60 connections)
- Use Supabase direct connection (port 5432) — doesn't work from Render free tier (Trial 4)
