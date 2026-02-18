# Development Scripts

This directory contains helper scripts for development workflows.

## Files

- **`dev.ps1`**: PowerShell script for Windows users without Make
  - Usage: `.\scripts\dev.ps1 <command>`
  - Run `.\scripts\dev.ps1 help` to see all available commands

- **`init-db.sql`**: PostgreSQL initialization script
  - Automatically enables pgvector extension
  - Used by Docker Compose on first startup

## Usage

### Windows (PowerShell)

```powershell
# Start database
.\scripts\dev.ps1 db-start

# Run migrations
.\scripts\dev.ps1 migrate

# Start API server
.\scripts\dev.ps1 api
```

### Linux/Mac (use Makefile instead)

```bash
make db-start
make migrate
make api
```

The Makefile at the project root is the recommended approach for all platforms.
