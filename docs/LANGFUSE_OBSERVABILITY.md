# Langfuse Observability Guide

Complete guide for implementing Langfuse observability in agents and tools.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Implementation Patterns](#implementation-patterns)
  - [LangGraph Agents](#langgraph-agents)
  - [Simple Agents](#simple-agents-non-langgraph)
  - [Standalone Tools](#standalone-tools)
  - [LangChain Tools](#langchain-tools)
- [Best Practices](#best-practices)
- [Viewing Traces](#viewing-traces)
- [Troubleshooting](#troubleshooting)

## Overview

[Langfuse](https://langfuse.com) is an open-source LLM observability platform that helps you:
- **Trace** LLM calls across your application
- **Monitor** performance, costs, and token usage
- **Debug** prompts and responses
- **Analyze** user sessions and behavior
- **Evaluate** output quality

This project uses Langfuse to automatically trace all LLM operations in agents and tools.

## How It Works

**Auto-Initialization Architecture**:

```
1. Application starts (main.py, api/main.py, ui/app.py)
   ↓
2. config/settings.py loads .env → os.environ (via python-dotenv)
   ↓
3. Any module imports utils/langfuse_config.py
   ↓
4. Langfuse singleton initializes (reads credentials from os.environ)
   ↓
5. CallbackHandler() can be used anywhere without passing credentials!
```

**Key Files**:
- `config/settings.py` - Defines Langfuse settings, loads .env
- `utils/langfuse_config.py` - Auto-initializes Langfuse singleton, provides `is_langfuse_enabled()`
- `agents/conversational/agent.py` - Example implementation in LangGraph agent

## Configuration

### 1. Get Langfuse Credentials

**Option A: Cloud (Recommended for most users)**
1. Sign up at [cloud.langfuse.com](https://cloud.langfuse.com)
2. Create a new project
3. Go to **Project Settings** → **API Keys**
4. Copy your **Public Key** and **Secret Key**

**Option B: Self-Hosted**
1. Follow [Langfuse self-hosting guide](https://langfuse.com/docs/deployment/self-host)
2. Use your self-hosted URL as `LANGFUSE_HOST`

### 2. Configure Environment Variables

Add to `.env`:

```bash
# Langfuse Observability
LANGFUSE_PUBLIC_KEY=pk-lf-1234567890abcdef
LANGFUSE_SECRET_KEY=sk-lf-0987654321fedcba
LANGFUSE_HOST=https://cloud.langfuse.com  # Or your self-hosted URL
LANGFUSE_ENABLED=true                     # Set to false to disable
```

### 3. Verify Setup

Run any application entry point:

```bash
python main.py
# or
uvicorn api.main:app --reload
# or
streamlit run ui/app.py
```

**Expected Output**:
- ✅ Success: `✅ Langfuse initialized (host: https://cloud.langfuse.com)`
- ⚠️ Missing credentials: `⚠️ LANGFUSE_ENABLED=true but credentials missing in .env`
- ℹ️ Disabled: `ℹ️ Langfuse observability disabled`

## Implementation Patterns

### LangGraph Agents

For agents using LangGraph (like `ConversationalAgent`), use the **CallbackHandler pattern**.

#### Complete Example

```python
from typing import Optional
from langfuse.langchain import CallbackHandler
from utils.langfuse_config import is_langfuse_enabled
from agents.my_agent.graph import create_my_graph

class MyAgent:
    def __init__(self, llm_service, prompt_loader, db_session):
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader
        self.db_session = db_session
        self.graph = create_my_graph()

    def _get_langfuse_handler(self) -> Optional[CallbackHandler]:
        """
        Get Langfuse callback handler if observability is enabled.

        Returns:
            CallbackHandler if enabled, None otherwise
        """
        if not is_langfuse_enabled():
            return None

        try:
            # CallbackHandler auto-discovers credentials from os.environ
            # No args needed - python-dotenv loaded them globally
            return CallbackHandler()
        except Exception as e:
            print(f"⚠️  Failed to create Langfuse handler: {e}")
            return None

    def start_session(self, user_id: str, session_id: str, input: str) -> dict:
        """
        Start a new session with Langfuse tracing.

        Args:
            user_id: User identifier (for per-user analytics)
            session_id: Session identifier (groups related traces)
            input: User input

        Returns:
            Result from graph execution
        """
        # Get Langfuse handler if enabled
        langfuse_handler = self._get_langfuse_handler()

        # Configure LangGraph with callbacks and metadata
        config = {
            "configurable": {"thread_id": f"thread_{session_id}"},
            "callbacks": [langfuse_handler] if langfuse_handler else [],
            "metadata": {
                # Session ID groups all traces in this session
                "langfuse_session_id": session_id,

                # User ID enables per-user analytics
                "langfuse_user_id": user_id,

                # Tags for filtering in Langfuse UI
                "langfuse_tags": ["my_agent", "production", "start"]
            }
        }

        # Invoke graph - all operations automatically traced!
        result = self.graph.invoke({"messages": [input]}, config)
        return result

    def continue_session(self, session_id: str, user_id: str, input: str) -> dict:
        """Continue existing session with Langfuse tracing."""
        langfuse_handler = self._get_langfuse_handler()

        config = {
            "configurable": {"thread_id": f"thread_{session_id}"},
            "callbacks": [langfuse_handler] if langfuse_handler else [],
            "metadata": {
                "langfuse_session_id": session_id,
                "langfuse_user_id": user_id,
                "langfuse_tags": ["my_agent", "production", "continue"]
            }
        }

        result = self.graph.invoke({"messages": [input]}, config)
        return result
```

#### Key Points

1. **Handler Creation**: Use `_get_langfuse_handler()` helper that checks `is_langfuse_enabled()`
2. **Config Structure**: Pass handler in `config["callbacks"]` list (not as separate parameter)
3. **Metadata Fields**:
   - `langfuse_session_id`: Groups all traces in a session (e.g., entire interview)
   - `langfuse_user_id`: Tracks per-user metrics and costs
   - `langfuse_tags`: Array of tags for filtering (environment, agent type, operation)
4. **Automatic Tracing**: Handler automatically traces all LangChain operations in the graph

#### Real-World Example

See `agents/conversational/agent.py:62-82` and `agents/conversational/agent.py:119-132` for production implementation.

### Simple Agents (Non-LangGraph)

For simple request-response agents not using LangGraph, use the **@observe decorator**.

#### Complete Example

```python
from langfuse.decorators import observe, langfuse_context
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader

class SimpleSummarizerAgent:
    def __init__(self, llm_service: LLMService, prompt_loader: PromptLoader):
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader

    @observe(as_type="generation")
    def summarize(self, text: str, user_id: str = None, session_id: str = None) -> str:
        """
        Summarize text with Langfuse tracing.

        Args:
            text: Text to summarize
            user_id: Optional user identifier
            session_id: Optional session identifier

        Returns:
            Summary text
        """
        # Update trace with session/user metadata
        langfuse_context.update_current_trace(
            session_id=session_id,
            user_id=user_id,
            tags=["summarizer", "production"]
        )

        # Load prompt
        system_prompt = self.prompt_loader.load("system", mode="summarization")

        # LLM call (automatically traced by @observe decorator)
        summary = self.llm_service.generate(
            system_prompt=system_prompt,
            human_prompt=f"Summarize the following text:\n\n{text}"
        )

        return summary

    @observe(name="multi-step-analysis", as_type="span")
    def analyze_and_summarize(self, text: str, user_id: str = None) -> dict:
        """
        Multi-step operation with nested tracing.

        The @observe decorator creates a parent span,
        and the summarize() call creates a child generation.
        """
        langfuse_context.update_current_trace(
            user_id=user_id,
            tags=["analyzer", "production"]
        )

        # Step 1: Extract key points (child trace)
        key_points = self._extract_key_points(text)

        # Step 2: Summarize (child trace)
        summary = self.summarize(text, user_id=user_id)

        return {
            "key_points": key_points,
            "summary": summary
        }

    @observe(as_type="generation")
    def _extract_key_points(self, text: str) -> list:
        """Private method also traced."""
        # This creates a nested trace under analyze_and_summarize()
        result = self.llm_service.generate_json(
            system_prompt="Extract key points as JSON array.",
            human_prompt=text,
            schema={
                "type": "array",
                "items": {"type": "string"}
            }
        )
        return result
```

#### Key Points

1. **@observe Decorator Types**:
   - `as_type="generation"`: For LLM calls (shows in UI as generations)
   - `as_type="span"`: For general operations (default)
   - `name="custom-name"`: Optional custom name in traces

2. **Metadata Updates**:
   - `langfuse_context.update_current_trace()`: Sets session/user/tags for entire trace
   - `langfuse_context.update_current_observation()`: Logs inputs/outputs for current operation

3. **Nested Tracing**: Decorated methods automatically create child traces when called from other decorated methods

### Standalone Tools

For tools that use LLMs but are called **outside of an agent** (no LangGraph).

#### Complete Example

```python
from langfuse.decorators import observe, langfuse_context
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from typing import Dict, Any
import json

class AnswerAssessor:
    """
    Standalone tool that assesses answer quality using LLM.

    Used by: agents/conversational/nodes/agent_node.py
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_loader = PromptLoader()

    @observe(name="assess-answer", as_type="generation")
    def assess_answer(
        self,
        question: str,
        answer: str,
        gap: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess answer quality with Langfuse tracing.

        Args:
            question: The question asked
            answer: User's answer
            gap: Gap being addressed

        Returns:
            Assessment results dictionary
        """
        # Log inputs to Langfuse
        langfuse_context.update_current_observation(
            input={
                "question": question,
                "answer": answer,
                "gap_category": gap.get("category")
            },
            metadata={
                "tool": "answer_assessor",
                "version": "2.0"
            }
        )

        # Load prompt
        human_prompt = self.prompt_loader.load(
            "answer_assessment",
            mode="shared",
            question=question,
            answer=answer,
            gap_description=gap.get('description', 'Additional skill information')
        )

        # Define schema
        schema = {
            "type": "object",
            "properties": {
                "answer_type": {"type": "string", "enum": ["direct_answer", "partial_answer", "off_topic"]},
                "engagement_level": {"type": "string", "enum": ["engaged", "disengaged"]},
                "detail_score": {"type": "integer", "minimum": 1, "maximum": 5},
                "relevance_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reasoning": {"type": "string"}
            }
        }

        # LLM call (automatically traced)
        response = self.llm_service.generate_json(
            system_prompt="",
            human_prompt=human_prompt,
            schema=schema
        )

        # Log output to Langfuse
        langfuse_context.update_current_observation(
            output=response,
            metadata={
                "answer_length": len(answer),
                "answer_type": response.get("answer_type")
            }
        )

        return response

    @observe(name="assess-answer-async", as_type="generation")
    async def assess_answer_async(self, question: str, answer: str, gap: Dict[str, Any]) -> Dict[str, Any]:
        """ASYNC version with same Langfuse tracing."""
        langfuse_context.update_current_observation(
            input={"question": question, "answer": answer}
        )

        # Async LLM call
        response = await self.llm_service.generate_json_async(...)

        langfuse_context.update_current_observation(output=response)
        return response
```

#### Key Points

1. **Input/Output Logging**: Use `update_current_observation()` to log inputs and outputs
2. **Metadata**: Add tool name, version, and other context in metadata
3. **Works Standalone**: Traces appear even when tool is called outside an agent
4. **Async Support**: Use same pattern in async methods

#### Real-World Example

See `tools/answer_assessor.py` for production implementation (note: currently doesn't use `@observe`, but should be added as shown above).

### LangChain Tools

For tools registered with `@tool` decorator (used in LangGraph agents with ReAct pattern).

#### Complete Example

```python
from langchain.tools import tool
from langfuse.decorators import observe, langfuse_context
from utils.llm_service import LLMService
import json

@tool
@observe(name="analyze-skill", as_type="generation")
def analyze_skill(skill_data: str) -> str:
    """
    Analyze a technical skill using LLM.

    This tool is called by LangGraph agents using ReAct pattern.
    When called from an agent with CallbackHandler, this trace
    appears as a child of the agent's trace.

    Args:
        skill_data: JSON string with skill information
            Example: {"skill_name": "Python", "experience": "5 years"}

    Returns:
        JSON string with analysis results
    """
    llm_service = LLMService()

    # Parse input
    data = json.loads(skill_data)

    # Log input to Langfuse
    langfuse_context.update_current_observation(
        input=data,
        metadata={
            "tool_type": "skill_analyzer",
            "skill_name": data.get("skill_name")
        }
    )

    # LLM call
    schema = {
        "type": "object",
        "properties": {
            "depth": {"type": "string", "enum": ["beginner", "intermediate", "advanced", "expert"]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reasoning": {"type": "string"}
        }
    }

    result = llm_service.generate_json(
        system_prompt="You are a technical skill analyzer. Assess the depth of expertise.",
        human_prompt=f"Analyze this skill: {data['skill_name']} with {data.get('experience', 'unknown')} experience",
        schema=schema
    )

    # Log output to Langfuse
    langfuse_context.update_current_observation(
        output=result,
        metadata={
            "depth_assessed": result.get("depth"),
            "confidence": result.get("confidence")
        }
    )

    return json.dumps(result)


@tool
@observe(name="extract-skills-from-resume", as_type="generation")
def extract_skills_from_resume(resume_text: str) -> str:
    """
    Extract technical skills from resume text.

    Args:
        resume_text: Resume content as string

    Returns:
        JSON string with array of extracted skills
    """
    llm_service = LLMService()

    # Log input (truncate long text in metadata)
    langfuse_context.update_current_observation(
        input={"resume_length": len(resume_text)},
        metadata={"tool_type": "skill_extractor"}
    )

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"},
                "years_experience": {"type": "number"},
                "proficiency": {"type": "string"}
            }
        }
    }

    result = llm_service.generate_json(
        system_prompt="Extract technical skills from resumes.",
        human_prompt=f"Extract all technical skills:\n\n{resume_text}",
        schema=schema
    )

    # Log output
    langfuse_context.update_current_observation(
        output={"skills_count": len(result)},
        metadata={"extracted_skills": [s["skill_name"] for s in result]}
    )

    return json.dumps(result)
```

#### Key Points

1. **Decorator Order**: Stack `@tool` first, then `@observe()` below it
2. **Agent Integration**: When agent with `CallbackHandler` calls this tool:
   - Tool trace appears as child of agent trace
   - Creates hierarchical trace structure
3. **JSON Input/Output**: Tools must use JSON strings (LangChain requirement)
4. **Logging**: Use `update_current_observation()` to log parsed inputs/outputs

#### Integration with Agent

```python
from tools.registry import get_tool_registry
from langfuse.langchain import CallbackHandler

# In agent initialization
registry = get_tool_registry()
tools = registry.get_tools_for_agent("my_agent")

# In agent execution
langfuse_handler = CallbackHandler()

config = {
    "callbacks": [langfuse_handler],
    "metadata": {
        "langfuse_session_id": session_id,
        "langfuse_tags": ["my_agent"]
    }
}

# Agent calls tool - both traces appear in Langfuse
result = graph.invoke(input, config)
```

#### Tool Registration

```python
# tools/__init__.py
from tools.registry import get_tool_registry
from tools.skill_analyzer import analyze_skill

registry = get_tool_registry()
registry.register_tool(
    "analyze_skill",
    analyze_skill,
    agents=["conversational", "rag"]  # Which agents can use it
)
```

## Best Practices

### 1. Session Grouping

Use consistent `langfuse_session_id` for all related interactions:

```python
# Good: Same session_id for entire interview
session_id = str(uuid.uuid4())

# Start interview
config = {"metadata": {"langfuse_session_id": session_id, ...}}
result1 = graph.invoke(input1, config)

# Continue interview (same session_id)
result2 = graph.invoke(input2, config)

# Complete interview (same session_id)
result3 = graph.invoke(input3, config)
```

**Benefit**: View entire session as one trace in Langfuse UI.

### 2. User Tracking

Always set `langfuse_user_id` for per-user analytics:

```python
config = {
    "metadata": {
        "langfuse_session_id": session_id,
        "langfuse_user_id": user_id,  # Critical for analytics
        ...
    }
}
```

**Benefit**: Track costs, usage, and behavior per user.

### 3. Tagging Strategy

Use consistent tags to enable filtering:

```python
# Environment tags
tags = ["production"]  # or ["staging"], ["development"]

# Agent type tags
tags = ["conversational", "interview"]  # or ["rag"], ["summarizer"]

# Operation tags
tags = ["start"]  # or ["continue"], ["finalize"], ["error"]

# Combined
config = {
    "metadata": {
        "langfuse_tags": ["production", "conversational", "start"]
    }
}
```

**Benefit**: Filter traces by environment, agent, or operation in Langfuse UI.

### 4. Conditional Tracing

Always check if Langfuse is enabled to prevent errors:

```python
def _get_langfuse_handler(self) -> Optional[CallbackHandler]:
    """Get handler only if enabled."""
    if not is_langfuse_enabled():
        return None

    try:
        return CallbackHandler()
    except Exception as e:
        print(f"⚠️  Failed to create Langfuse handler: {e}")
        return None
```

**Benefit**: App continues working even if Langfuse is misconfigured.

### 5. Error Handling

Wrap Langfuse operations in try-except:

```python
try:
    langfuse_handler = CallbackHandler()
except Exception as e:
    print(f"⚠️  Langfuse error: {e}")
    langfuse_handler = None  # Continue without tracing

config = {
    "callbacks": [langfuse_handler] if langfuse_handler else []
}
```

**Benefit**: Langfuse failures don't break your application.

### 6. Environment Separation (Development vs Production)

Use **separate Langfuse projects** with different API keys for dev and prod environments.

**Setup**:

1. **Create two Langfuse projects** at [cloud.langfuse.com](https://cloud.langfuse.com):
   - `my-app-development` → Get dev API keys
   - `my-app-production` → Get prod API keys

2. **Local Development** - Use dev credentials in `.env`:

```bash
# .env (local development)
LANGFUSE_PUBLIC_KEY=pk-lf-dev-1234567890abcdef
LANGFUSE_SECRET_KEY=sk-lf-dev-0987654321fedcba
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=true  # Set to false to disable tracing in dev
```

3. **Production Deployment** - Use prod credentials:

**Option A: Environment Variables (Docker/Kubernetes)**
```bash
# In Dockerfile or docker-compose.yml
ENV LANGFUSE_PUBLIC_KEY=pk-lf-prod-abcdef1234567890
ENV LANGFUSE_SECRET_KEY=sk-lf-prod-fedcba0987654321
ENV LANGFUSE_ENABLED=true
```

**Option B: Production `.env` (VM/Server)**
```bash
# On production server, create .env with prod keys
LANGFUSE_PUBLIC_KEY=pk-lf-prod-abcdef1234567890
LANGFUSE_SECRET_KEY=sk-lf-prod-fedcba0987654321
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
```

**Benefits**:
- ✅ **Complete isolation**: Dev traces in separate project from prod
- ✅ **Separate billing**: Dev usage doesn't affect prod quota
- ✅ **Clean analytics**: Production data is pristine
- ✅ **Can disable dev**: Set `LANGFUSE_ENABLED=false` in local `.env`

**Alternative: Same Project with Tags**

If you prefer a single Langfuse project, add tags to differentiate environments:

```python
config = {
    "metadata": {
        "langfuse_tags": [
            "production",      # or "development"
            "conversational",
            "v2.0"
        ]
    }
}
```

Then filter by tags in Langfuse UI. Simpler setup but dev traces clutter prod analytics.

### 7. Input/Output Logging

Log structured data in tools:

```python
@observe(as_type="generation")
def my_tool(data: dict) -> dict:
    # Log input
    langfuse_context.update_current_observation(
        input=data,
        metadata={"tool": "my_tool", "version": "1.0"}
    )

    # Process
    result = process(data)

    # Log output
    langfuse_context.update_current_observation(
        output=result,
        metadata={"result_type": result.get("type")}
    )

    return result
```

**Benefit**: Inspect exact inputs/outputs in Langfuse for debugging.

## Viewing Traces

### Navigate to Langfuse Dashboard

1. Go to [cloud.langfuse.com](https://cloud.langfuse.com)
2. Select your project
3. Click **Traces** in sidebar

### Filter Traces

**By Session**:
- Click on a `Session ID` in the traces list
- View all traces in that session grouped together

**By User**:
- Click on a `User ID` in the traces list
- See all traces for that user across all sessions

**By Tags**:
- Use tag filters at top of traces page
- Filter by environment (`production`), agent type (`conversational`), etc.

**By Date/Time**:
- Use date picker to narrow down time range

### Inspect Trace Details

Click on any trace to view:

1. **Overview**: Total duration, cost, tokens used
2. **Trace Timeline**: Hierarchical view of all operations
   - Agent invocation (parent)
   - Node executions (children)
   - Tool calls (grandchildren)
   - LLM calls (leaf nodes)
3. **LLM Calls**: For each generation:
   - Prompt (system + user messages)
   - Response
   - Model used
   - Tokens (input/output/total)
   - Cost
   - Latency
4. **Metadata**: Session ID, user ID, tags, custom metadata
5. **Input/Output**: Full inputs and outputs for each operation

### Analyze Performance

**Token Usage**:
- View tokens per session, user, or time period
- Identify heavy users or sessions

**Cost Analysis**:
- Track costs per user or session
- Estimate monthly spending

**Latency**:
- Find slow operations
- Optimize bottlenecks

**Error Tracking**:
- Filter by error status
- Debug failed operations

## Troubleshooting

### Problem: `⚠️ LANGFUSE_ENABLED=true but credentials missing in .env`

**Cause**: Langfuse is enabled but API keys are not configured.

**Solution**:
1. Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to `.env`
2. Get keys from [cloud.langfuse.com](https://cloud.langfuse.com) → Project Settings → API Keys
3. Restart application

### Problem: No traces appear in Langfuse dashboard

**Cause**: Multiple possible issues.

**Solution**:

1. **Verify `LANGFUSE_ENABLED=true`**:
   ```bash
   # Check .env
   cat .env | grep LANGFUSE_ENABLED
   ```

2. **Check credentials are correct**:
   - Copy-paste keys carefully (no extra spaces)
   - Verify they match project in Langfuse dashboard

3. **Ensure handler is in callbacks**:
   ```python
   # Correct
   config = {"callbacks": [langfuse_handler]}

   # Wrong (won't trace)
   config = {"langfuse": langfuse_handler}
   ```

4. **Verify network connectivity**:
   ```bash
   curl https://cloud.langfuse.com
   # Should return HTML (not error)
   ```

5. **Check application output**:
   - Look for: `✅ Langfuse initialized`
   - If not present, Langfuse isn't loading

6. **Wait for traces to appear**:
   - Traces may take 10-30 seconds to appear in UI
   - Refresh dashboard

### Problem: Traces missing for certain operations

**Cause**: Operations aren't using LangChain components or `@observe` decorator.

**Solution**:

1. **For LLM calls**: Ensure they use LangChain LLMs (passed via CallbackHandler)
2. **For custom operations**: Add `@observe()` decorator:
   ```python
   @observe(as_type="generation")
   def my_operation(input: str) -> str:
       # Now traced
       return process(input)
   ```

3. **For tools**: Stack decorators correctly:
   ```python
   @tool
   @observe(as_type="generation")  # Must be below @tool
   def my_tool(input: str) -> str:
       return result
   ```

### Problem: `Failed to create Langfuse handler: <error>`

**Cause**: Error during CallbackHandler initialization.

**Solution**:

1. **Check error message** for specific issue
2. **Verify credentials format**:
   - Public key starts with `pk-lf-`
   - Secret key starts with `sk-lf-`
3. **Check network**: Ensure you can reach `LANGFUSE_HOST`
4. **Update Langfuse SDK**:
   ```bash
   pip install --upgrade langfuse
   ```

### Problem: Traces are incomplete or cut off

**Cause**: Application crashed or operation timed out.

**Solution**:

1. **Check application logs** for errors
2. **Increase timeouts** if operations are slow
3. **Ensure graceful shutdown**: Let traces flush before app exits

### Problem: Too many traces in development

**Cause**: Langfuse enabled during local development.

**Solution**:

1. **Disable in development**:
   ```bash
   # .env
   LANGFUSE_ENABLED=false
   ```

2. **Or use separate Langfuse projects**:
   - Use dev project keys in local `.env`
   - Use prod project keys in production deployment
   - See [Environment Separation](#6-environment-separation-development-vs-production)

## Advanced Topics

### Custom Trace Names

```python
@observe(name="custom-operation-name", as_type="span")
def my_function():
    # Appears as "custom-operation-name" in traces
    pass
```

### Scoring Traces

```python
from langfuse import Langfuse

langfuse = Langfuse()
langfuse.score(
    trace_id="trace-id",
    name="quality",
    value=0.9,
    comment="High quality response"
)
```

### Manual Trace Creation

```python
from langfuse.decorators import langfuse_context

# Start manual trace
trace = langfuse_context.get_current_trace()

# Add custom data
trace.update(
    metadata={"custom_field": "value"},
    tags=["manual", "custom"]
)
```

## Resources

- **Langfuse Docs**: [langfuse.com/docs](https://langfuse.com/docs)
- **Python SDK**: [langfuse.com/docs/sdk/python](https://langfuse.com/docs/sdk/python)
- **LangChain Integration**: [langfuse.com/docs/integrations/langchain](https://langfuse.com/docs/integrations/langchain)
- **Example Code**: See `agents/conversational/agent.py` and `tools/answer_assessor.py` in this project
