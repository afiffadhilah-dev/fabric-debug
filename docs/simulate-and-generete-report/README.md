# Simulate Interview and Generate Report

## Prerequisites

- Activate venv
- Make sure Langfuse is enabled in `.env`

```
# Langfuse Observability Configuration
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=true

# Staging (ask petra or teguh for credentials)
LANGFUSE_SECRET_KEY_STG=
LANGFUSE_PUBLIC_KEY_STG=
```

## Step 1: Configure Environment

Decide to simulate in local or staging by editing `./scripts/simulate_interview.py`:

```python
# Staging
DEFAULT_BASE_URL = "https://fabric-api-jxv8.onrender.com"
DEFAULT_QUESTION_SET_ID = "03b84681-2c75-4bbd-89ee-307861ec7b6b"

# Local (uncomment these and comment above)
# DEFAULT_BASE_URL = "http://localhost:8000"
# DEFAULT_QUESTION_SET_ID = ""

DEFAULT_MODE = "predefined_questions"
```

## Step 2: Run API (Local Only)

If simulating locally, start the API:

```sh
make api
```

or

```sh
uvicorn api.main:app --reload
```

## Step 3: Run Simulation

```sh
python .\scripts\simulate_interview.py
```

**Options:**
| Option | Description |
|--------|-------------|
| `--mode` | `predefined_questions` (default) or `dynamic_gap` |
| `--question-set-id` | UUID of question set (required for predefined_questions) |
| `--persona` | `detailed` (default), `concise`, `nervous`, `evasive`, `storyteller` |
| `--max-answers` | Maximum answers before stopping (default: 100) |

**Example output:**
```
============================================================
Starting Interview Simulation
Base URL: https://fabric-api-jxv8.onrender.com
Mode: predefined_questions
Question Set ID: 03b84681-2c75-4bbd-89ee-307861ec7b6b
Persona: Detailed Expert (detailed)
Max Answers: 100
============================================================

Session started: 7491dc8e-c57d-4ad4-95b0-4d8b221aad75

...

============================================================
SIMULATION SUMMARY
============================================================
Session ID: 7491dc8e-c57d-4ad4-95b0-4d8b221aad75
Persona: Detailed Expert
Total Q&A: 13
Completed: True
Termination Reason: None
Elapsed Time: 573.56s
```

## Step 4: Generate Timing Report

Use the session ID from the simulation to generate a Langfuse timing report:

```sh
python .\scripts\langfuse_timing_report.py <session_id>
```

**Options:**
| Option | Description |
|--------|-------------|
| `--output`, `-o` | Custom output file path |
| `--stdout` | Print to stdout instead of saving to file |

The script automatically:
- Detects environment (local/staging) based on where traces are found
- Fetches candidate ID from Langfuse trace metadata

**Output location:** `docs/simulate-and-generete-report/timing-report/langfuse-{local|staging}-{session_id}.txt`
