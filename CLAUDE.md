# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A modular AI agent platform with three specialized agents (Conversational, Summarization, RAG) built with FastAPI and Streamlit. Uses LangChain for LLM abstraction and PostgreSQL with pgvector for RAG capabilities.

## Development Commands

### Quick Start (Makefile)
```bash
make help          # Show all available commands
make setup         # Complete setup (install deps, start DB, run migrations)
make dev           # Start development environment (DB + migrations)
make db-start      # Start PostgreSQL
make migrate       # Run migrations
make api           # Run FastAPI server
make ui            # Run Streamlit UI
```

### Windows Alternative (PowerShell)
```powershell
.\scripts\dev.ps1 help     # Show all available commands
.\scripts\dev.ps1 setup    # Complete setup
.\scripts\dev.ps1 db-start # Start PostgreSQL
.\scripts\dev.ps1 api      # Run FastAPI server
```

### Environment Setup
```bash
# Activate virtual environment
venv\Scripts\activate           # Windows
source venv/bin/activate        # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Database Setup

**Local Development (Docker)**:
```bash
# Start PostgreSQL with pgvector
docker-compose up -d

# Verify database is running
docker-compose ps

# Run migrations
alembic upgrade head

# Stop database
docker-compose down

# Stop and remove data (fresh start)
docker-compose down -v
```

**Production (Supabase)**:
1. Create a Supabase project at https://supabase.com
2. pgvector extension is pre-enabled on Supabase
3. Get connection string from Supabase Dashboard > Project Settings > Database
4. Update `DATABASE_URL` in `.env` with Supabase connection string
5. Run migrations: `alembic upgrade head`

### Running the Application
```bash
# Main CLI application
python main.py

# FastAPI server (default: http://127.0.0.1:8000)
uvicorn api.main:app --reload

# Streamlit UI
streamlit run ui/app.py
```

### Database Migrations
```bash
# Run all pending migrations
alembic upgrade head

# Run migrations on staging database (Supabase)
make migrate-stag  # Uses scripts/migrate-stag.ps1

# Rollback one migration
alembic downgrade -1

# Check current migration status
alembic current

# View migration history
alembic history

# Create new migration from model changes
alembic revision --autogenerate -m "description"
make migrate-create MSG="description"  # Alternative

# Create empty migration
alembic revision -m "description"
```

### Database Inspection (Makefile helpers)
```bash
make db-status   # Check database container status
make db-tables   # Show all database tables
make db-schema   # Show candidatechunk table schema
make db-connect  # Open psql shell
```

## Architecture

### Multi-Provider LLM Service (utils/llm_service.py)

The `LLMService` class provides a unified interface across multiple LLM providers:

- **Supported Providers**: OpenAI, OpenRouter, Gemini, Ollama (local)
- **Provider Selection**: Configured via `LLM_PROVIDER` and `LLM_MODEL` in `.env`
- **Response Modes**:
  - `generate()` / `generate_async()`: Plain text responses
  - `generate_json()` / `generate_json_async()`: Structured JSON output with schema validation
- **Async Support**: All methods have async variants for parallel LLM calls

The service automatically handles provider-specific differences (e.g., OpenAI/OpenRouter support `response_format` for JSON mode, while Gemini/Ollama rely on system prompt enforcement).

### Conversational Agent (LangGraph-based Interview System)

The **Conversational Agent** is a fully implemented LangGraph workflow for conducting dynamic technical interviews. See `docs/conversational-agent.md` for complete documentation.

**Key Architecture**:
- **graph.py**: Defines LangGraph workflow with 6 nodes (identify_gaps, select_gap, generate_response, agent_node, update_state, finalize)
- **service.py**: Application service layer (`ConversationalInterviewService` class) that handles database operations, observability, and invokes the graph
- **state.py**: `InterviewState` TypedDict defining all data flowing through the graph
- **conditions.py**: Routing logic (`is_first_run`, `should_continue_interview`)
- **nodes/**: Individual processing nodes (each modifies state)
- **checkpointer.py**: PostgreSQL-based state persistence (enables resume/pause interviews)

**Flow Pattern**:
1. Each user interaction = one `graph.invoke()` call
2. Graph runs through nodes until reaching `END`
3. Checkpointer persists state between invocations using `thread_id`
4. State accumulates conversation history, gaps, skills, engagement metrics

**Interview Logic**:
- **Gap-based**: Analyzes resume to find missing skill attributes (duration, depth, autonomy, scale, constraints, production_vs_prototype)
- **Adaptive**: Asks questions only about identified gaps
- **Engagement-aware**: Tracks user engagement and stops if disengaged (3+ consecutive low-quality answers)
- **Completeness-driven**: Terminates when 60% completeness reached or no gaps remain
- **Agentic**: Uses ReAct pattern where LLM autonomously decides when to call tools

**Database Models**:
- `InterviewSession`: Tracks interview metadata (status, metrics, thread_id)
- `ExtractedSkill`: Stores skills with 6 attributes extracted during interview
- `Message`: Stores Q&A pairs with rich metadata (engagement, gap info, etc.)

**Summarization Agent** (`agents/summarization/`):
- **orchestrator.py**: Main LangGraph workflow that coordinates skill and behavior extraction
- **state.py**: `SummarizationState` TypedDict defining data flow
- **nodes/**: Processing nodes (load_session_data, skill_node, behavior_node)
- **Sub-agents**: Resume extractor, conversation extractor, analyze agent, skill scorer, extracted skills merger
- **Flow**: load_session_data → skill_node → behavior_node → END
- **Purpose**: Post-interview analysis to extract structured skills and behavioral observations
- **Entry point**: `summarize_session(session_id, mode="SELF_REPORT")`

**RAG Agent**: `agents/rag/agent.py` (stub)

### Prompt Management (utils/prompt_loader.py)

The `PromptLoader` class loads markdown-based prompts from `prompts/`:

```python
loader = PromptLoader()
prompt = loader.load("system", mode="conversational")
# or use convenience methods
prompt = loader.load_project_mode("first_question", project_name="MyApp")
```

- Supports variable substitution using Python `.format()` syntax
- Organizes prompts by mode: `prompts/{mode}/{template_name}.md`
- Modes seen in code: `conversational`, `summarization`, `rag`, `project_mode`, `resume_mode`, `shared`

### Database Models (models/)

Using SQLModel (combines SQLAlchemy + Pydantic):

**Interview System Models**:
- **InterviewSession** (`models/interview_session.py`): Tracks interview state
  - Fields: `id`, `candidate_id`, `resume_text`, `status`, `termination_reason`, `questions_asked`, `completeness_score`, `thread_id`, timestamps

- **ExtractedSkill** (`models/extracted_skill.py`): Stores skills with 6 attributes
  - Fields: `id`, `session_id`, `name`, `confidence_score`, `duration`, `depth`, `autonomy`, `scale`, `constraints`, `production_vs_prototype`, `evidence`

- **Message** (`models/message.py`): Stores conversation Q&A pairs
  - Fields: `id`, `session_id`, `role` (user/assistant), `content`, `meta` (JSON metadata for engagement, gaps, etc.)

**RAG System Models**:
- **Candidate** (`models/candidate.py`): Stores candidate information
  - Fields: `id` (str, PK), `created_at` (datetime)

- **CandidateChunk** (`models/candidate_chunk.py`): Stores chunked content with vector embeddings for RAG
  - Fields: `id` (UUID, PK), `candidate_id` (FK), `chunk_index` (int), `content` (str), `embedding` (Vector[1536]), `created_at` (datetime)
  - Uses pgvector extension for similarity search
  - Default embedding dimension: 1536 (OpenAI standard)

**Important**: All SQLModel models must be imported in `migrations/env.py` for Alembic autogenerate to detect schema changes.

### Tool Registry (tools/registry.py)

The `ToolRegistry` class manages reusable tools that agents can use:

```python
from tools.registry import get_tool_registry

# Get global registry instance
registry = get_tool_registry()

# Register a new tool
registry.register_tool("tool_name", tool_function, agents=["conversational"])

# Get tools for specific agent
tools = registry.get_tools_for_agent("conversational")
```

- **Tool Registration**: Register tools with specific agent assignments
- **Agent Assignment**: Control which agents can access which tools
- **Singleton Pattern**: Use `get_tool_registry()` for global access
- Tools are defined in `tools/` directory and registered at application startup

### Configuration (config/settings.py)

Uses `pydantic-settings` to load configuration from `.env`:

- **LLM Settings**: `LLM_PROVIDER`, `LLM_MODEL`, provider-specific API keys
- **Database**: `DATABASE_URL` (PostgreSQL with pgvector)
- **Server**: `API_HOST`, `API_PORT`

Settings are accessed via singleton: `from config.settings import settings`

## Key Implementation Patterns

### Adding a New LangGraph Agent

For complex workflows like the Conversational Agent, use LangGraph:

1. **Create graph structure** (`agents/{agent_name}/graph.py`):
```python
from langgraph.graph import StateGraph, END

def create_my_graph(checkpointer=None):
    workflow = StateGraph(MyState)
    workflow.add_node("node1", node1_func)
    workflow.add_node("node2", node2_func)
    workflow.set_conditional_entry_point(routing_func, {...})
    workflow.add_edge("node1", "node2")
    return workflow.compile(checkpointer=checkpointer)
```

2. **Define state** (`agents/{agent_name}/state.py`):
```python
class MyState(TypedDict):
    session_id: str
    messages: Annotated[List[BaseMessage], add_messages]
    # ... other state fields
```

3. **Create nodes** (`agents/{agent_name}/nodes/`):
- Each node is a function: `def node_name(state: MyState) -> Dict[str, Any]`
- Nodes receive state, perform work, return state updates
- Keep nodes focused on single responsibility

4. **Define conditions** (`agents/{agent_name}/conditions.py`):
- Pure functions that read state and return routing path
- Example: `def should_continue(state) -> Literal["continue", "stop"]`

5. **Create service wrapper** (`agents/{agent_name}/service.py`):
- Application service layer that invokes the graph
- Handles database operations and observability
- Manages checkpointer for state persistence

**Naming Convention: `service.py` vs `agent.py`**:
- Use `service.py` for LangGraph workflows (the graph IS the agent, service wraps it)
- The conversational agent uses this pattern: `graph.py` contains the workflow, `service.py` handles app concerns
- For simple non-workflow agents, you can still use `agent.py` if it directly contains agent logic

**Service Layer Pattern**:
```python
# agents/conversational/service.py
class ConversationalInterviewService:
    """Application service wrapping the interview graph."""

    def __init__(self, llm_service, prompt_loader, db_session):
        self.db_session = db_session
        self.checkpointer = get_postgres_checkpointer()
        self.graph = create_interview_graph(checkpointer=self.checkpointer)

    def start_interview(self, candidate_id, resume_text):
        # Create DB session
        # Build initial state
        # Invoke graph with config
        # Extract and return results
```

This separates concerns:
- **graph.py** = Workflow logic (nodes, edges, conditions)
- **service.py** = Application integration (DB, observability, API)
- **API layer** = HTTP concerns (validation, serialization, auth)

### Adding a Simple Agent

**Note**: For simple request-response agents without complex workflows, you can use a simpler pattern without LangGraph.

For simple request-response agents without workflows:

1. Create agent class in `agents/{agent_name}/agent.py` (or `service.py` if it's a service wrapper):
```python
class MyAgent:
    def __init__(self, llm_service: LLMService, prompt_loader: PromptLoader):
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader

    def process(self, input: str) -> str:
        system_prompt = self.prompt_loader.load("system", mode="my_agent")
        return self.llm_service.generate(input, system_prompt)
```

2. Create system prompt: `prompts/{agent_name}/system.md`
3. Export agent in `agents/{agent_name}/__init__.py`

### Composite Agent Pattern (Sub-agents)

For complex agents that coordinate multiple specialized sub-agents (like Summarization Agent):

1. **Create orchestrator** (`agents/{agent_name}/orchestrator.py`):
```python
from langgraph.graph import StateGraph, END
from agents.my_agent.state import MyState
from agents.my_agent.nodes import node1, node2

def build_graph():
    graph = StateGraph(MyState)
    graph.add_node("node1", node1)
    graph.add_node("node2", node2)
    graph.set_entry_point("node1")
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", END)
    return graph.compile()

GRAPH = build_graph()

def process_workflow(input_id: str):
    final_state = GRAPH.invoke({"input_id": input_id})
    return final_state
```

2. **Create specialized sub-agents** in subdirectories:
```
agents/my_agent/
├── orchestrator.py        # Main workflow coordinator
├── state.py               # Shared state definition
├── nodes/                 # Graph nodes
│   ├── node1.py
│   └── node2.py
├── resume/                # Sub-agent: resume processing
│   ├── resume_agent.py
│   └── resume_extractor.py
├── conversation/          # Sub-agent: conversation analysis
│   ├── conversation_agent.py
│   └── conversation_extractor.py
└── skill_scoring/         # Sub-agent: skill scoring
    └── score_skills.py
```

3. **Use base agent pattern** for shared logic:
```python
# agents/my_agent/base_agent.py
class BaseAgent:
    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_loader = PromptLoader()

    def extract(self, text: str, prompt_name: str, schema: dict):
        prompt = self.prompt_loader.load(prompt_name, mode="my_agent")
        return self.llm_service.generate_json(
            system_prompt=prompt,
            human_prompt=text,
            schema=schema
        )

# agents/my_agent/resume/resume_agent.py
from agents.my_agent.base_agent import BaseAgent

class ResumeAgent(BaseAgent):
    def extract_skills(self, resume: str):
        return self.extract(resume, "resume_skills", SKILL_SCHEMA)
```

**When to use**:
- Multiple extraction/processing steps with different concerns
- Specialized logic that's easier to maintain separately
- Orchestration of multiple LLM calls with different purposes
- See `agents/summarization/` for production example

### Adding a New Tool (LangChain @tool)

Tools enable agents to perform specific actions autonomously (used with ReAct pattern).

1. Create tool file in `tools/{tool_name}.py`:
```python
from langchain.tools import tool
import json

@tool
def my_tool(input: str) -> str:
    """
    Tool description shown to the LLM.

    Explain what the tool does, when to use it, and what it returns.
    LLM reads this to decide when to call the tool.

    Args:
        input: Description of input parameter

    Returns:
        JSON string with results
    """
    # Implementation
    result = {"key": "value"}
    return json.dumps(result)
```

2. Register tool in `tools/__init__.py`:
```python
from tools.registry import get_tool_registry
from tools.my_tool import my_tool

registry = get_tool_registry()
registry.register_tool(
    "my_tool",
    my_tool,
    agents=["conversational", "rag"]  # Specify which agents can use it
)
```

3. Tool is automatically available when agent calls:
```python
tools = registry.get_tools_for_agent("conversational")
# Pass tools to ReAct agent or LangChain agent executor
```

**Best Practices**:
- Return JSON strings for structured data (parse with `json.loads()`)
- Use `llm_service.generate_json()` inside tools for LLM-based extraction (ensures schema validation)
- Keep tool descriptions clear - LLM uses them to decide when to call
- Tools run synchronously in agent execution - avoid long-running operations

### Adding a New Database Model

1. Create model in `models/{model_name}.py` inheriting from `SQLModel`
2. Export model in `models/__init__.py`
3. Import model in `migrations/env.py` at the top (critical for autogenerate)
4. Run `alembic revision --autogenerate -m "add {model_name}"`
5. Review generated migration, then `alembic upgrade head`

### Vector Embeddings

When working with embeddings:
- Default dimension is 1536 (OpenAI standard)
- To change: update `Vector(1536)` in model and create migration
- pgvector extension is:
  - **Local Docker**: Automatically enabled via `init-db.sql`
  - **Supabase**: Pre-enabled by default

## LangGraph Workflow Patterns

### Graph Components

LangGraph workflows consist of 5 main components:

1. **Nodes**: Functions that do work (transform state)
   - Signature: `def node_name(state: StateType) -> Dict[str, Any]`
   - Return dict with state updates (merged into state)
   - Keep focused on single responsibility

2. **Edges**: Connections between nodes
   - **Direct edges**: Always go from A → B (`workflow.add_edge("a", "b")`)
   - **Conditional edges**: Route based on state (`workflow.add_conditional_edges(...)`)

3. **Entry Points**: Where execution starts
   - Direct: `workflow.set_entry_point("node_name")`
   - Conditional: `workflow.set_conditional_entry_point(condition_func, {...})`

4. **State**: Data structure flowing through nodes (TypedDict)
   - Use `Annotated[List, add_messages]` for message accumulation
   - State updates from nodes are automatically merged

5. **Conditions**: Pure routing functions
   - Read state, return which path to take
   - Example: `def route(state) -> Literal["path1", "path2"]`
   - **Don't create router nodes** - use condition functions directly

### Invocation Model

**Each user interaction = one `graph.invoke()` call that runs until END**:

```python
# First invocation (start interview)
result = graph.invoke(initial_state, config={"configurable": {"thread_id": "abc"}})
# Runs: START → identify_gaps → select_gap → generate_response → END

# Second invocation (user answers)
result = graph.invoke({"messages": [HumanMessage("answer")]}, config={"configurable": {"thread_id": "abc"}})
# Checkpointer loads previous state, merges new message
# Runs: START → agent_node → update_state → select_gap → generate_response → END
```

**Key points**:
- Graph doesn't pause mid-execution for user input
- User interaction happens between invocations
- `thread_id` in config enables state persistence via checkpointer
- Each invocation runs multiple nodes until reaching END

### Checkpointer Pattern

Use `PostgresSaver` for persistent state across invocations:

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Create singleton checkpointer
checkpointer = PostgresSaver(conn=connection_pool)
checkpointer.setup()  # Creates checkpoint tables

# Use in graph
graph = workflow.compile(checkpointer=checkpointer)

# Each invoke with same thread_id loads/saves state
graph.invoke(state, config={"configurable": {"thread_id": "thread_123"}})
```

**Benefits**:
- Resume conversations after interruption
- Preserve state across application restarts
- Enable multi-turn conversations with state accumulation

### When to Add Nodes

**Add a node when you need**:
- Distinct processing step with different logic
- Conditional branching requiring state transformation
- External API calls or database operations
- Heavy computation that produces state updates

**Don't add a node for**:
- Simple routing logic (use condition functions)
- Setting a single variable (do it in another node)
- No-op pass-through (routing is handled by conditions)

## Testing

### Integration Tests

Integration tests run against real database and LLM to verify end-to-end workflows:

```python
# tests/summarization/orchestrator.py
from agents.summarization.orchestrator import summarize_session

# Run summarization workflow
result = summarize_session(SESSION_ID)

# Result contains:
# - skills: Structured skill data
# - behavior_observations: Behavioral analysis
```

**Running integration tests**:
```bash
# Ensure database is running
make db-start

# Run test script
python tests/summarization/orchestrator.py

# Output written to: tests/summarization/output/orchestrator.json
```

### Test Patterns

**Database setup for tests**:
```python
from sqlmodel import create_engine, Session
from config.settings import settings

# Import all models (required for SQLAlchemy relationships)
import importlib
import pkgutil
import models

for _, name, _ in pkgutil.iter_modules(models.__path__):
    importlib.import_module(f"models.{name}")

engine = create_engine(settings.DATABASE_URL)
with Session(engine) as db:
    # Run test
    result = test_function(db)
```

**Important**: Always import all model modules before creating sessions to ensure SQLAlchemy relationships are properly registered.
