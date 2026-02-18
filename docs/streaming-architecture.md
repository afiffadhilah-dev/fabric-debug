# Streaming Architecture

This document explains how streaming is implemented in the conversational agent.

## Streaming Happens at TWO Levels

### 1. Graph-Level Streaming (ALL nodes - automatic)

In `service.py`, we use LangGraph's `astream()` with multiple modes:

```python
stream_mode=["messages", "updates", "custom"]
```

This gives **automatic streaming for all nodes**:

| Stream Mode | What It Does | Applies To |
|------------|--------------|------------|
| `"updates"` | Emits node completion events | **ALL nodes** (identify_gaps, select_gap, etc.) |
| `"messages"` | Streams LLM tokens in real-time | Nodes using LLM (generate_question, generate_follow_up) |
| `"custom"` | Custom events via `get_stream_writer()` | Only nodes that explicitly use it |

### 2. Node-Level Custom Streaming (only parse_answer)

`parse_answer` is the **only node that needs custom progress events** because it has **4 sequential slow operations**:

1. `assess_answer_engagement`
2. `extract_all_skills_from_answer` (or `assess_criteria`)
3. `analyze_cross_gap_coverage`

Other nodes don't need custom streaming because:

- **identify_gaps, select_gap, update_state, finalize** → Single operation, fast
- **generate_question, generate_follow_up** → Already stream tokens via `"messages"` mode

## Node Streaming Summary

| Node | Graph-level "updates" | Graph-level "messages" (tokens) | Custom "progress" events |
|------|----------------------|--------------------------------|-------------------------|
| identify_gaps | ✅ | ❌ | ❌ (single op) |
| select_gap | ✅ | ❌ | ❌ (single op) |
| parse_answer | ✅ | ❌ | ✅ (4 tool calls) |
| update_state | ✅ | ❌ | ❌ (single op) |
| generate_question | ✅ | ✅ | ❌ (tokens already stream) |
| generate_follow_up | ✅ | ✅ | ❌ (tokens already stream) |
| finalize | ✅ | ❌ | ❌ (single op) |

## SSE Event Types

The streaming endpoints emit these Server-Sent Events:

| Event | Description | Example |
|-------|-------------|---------|
| `session` | Session created (start only) | `{"session_id": "uuid"}` |
| `status` | Human-readable status message | `{"message": "Analyzing resume...", "node": "identify_gaps"}` |
| `node` | Node completion | `{"node": "identify_gaps", "status": "complete"}` |
| `token` | LLM token (question generation) | `{"content": "What"}` |
| `progress` | Custom progress from parse_answer | `{"stage": "skills_extracted", "detail": "3 skill(s)"}` |
| `complete` | Interview turn complete | `{"session_id": "...", "question": "...", "completed": false}` |
| `error` | Error occurred | `{"detail": "error message"}` |

## Implementation Details

### Adding Custom Streaming to a Node

If you need to add custom progress events to another node:

```python
def _get_stream_writer():
    """Get stream writer for custom progress events."""
    try:
        from langgraph.config import get_stream_writer
        return get_stream_writer()
    except Exception:
        return lambda x: None  # No-op fallback

def my_node(state: InterviewState) -> Dict[str, Any]:
    writer = _get_stream_writer()

    # Emit progress event
    writer({"stage": "step_1", "detail": "Starting..."})

    # Do work...

    writer({"stage": "step_2", "detail": "Done"})

    return {"result": "..."}
```

### Why Only parse_answer Has Custom Streaming

`parse_answer` is unique because:
1. It makes **multiple LLM tool calls** sequentially
2. Each call can take several seconds
3. Users benefit from knowing which extraction step is running

Other nodes either:
- Complete quickly (single operation)
- Already stream via `"messages"` mode (LLM token streaming)
