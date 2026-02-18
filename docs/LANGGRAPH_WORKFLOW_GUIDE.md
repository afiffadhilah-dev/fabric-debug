# LangGraph Workflow Guide

Complete guide to understanding and extending the conversational agent's LangGraph architecture.

---

## Table of Contents

1. [Current Workflow Architecture](#current-workflow-architecture)
2. [Detailed Node Flow](#detailed-node-flow)
3. [State Persistence](#state-persistence)
4. [How to Add New Tools](#how-to-add-new-tools)
5. [How to Add New Nodes](#how-to-add-new-nodes)
6. [How to Add Conditional Logic](#how-to-add-conditional-logic)
7. [Session Resume](#session-resume)
8. [State Lifecycle](#state-lifecycle)
9. [Quick Reference](#quick-reference)

---

## Current Workflow Architecture

### High-Level Flow

```
┌──────────────────────────────────────────────────────────┐
│  START → router → identify_gaps OR agent_node           │
│             ├─ First run? → identify_gaps               │
│             └─ Resume?    → agent_node                   │
│                                                           │
│  identify_gaps → should_continue? → select_gap/finalize │
│  agent_node → update_state → should_continue?           │
│                                                           │
│  select_gap → generate_response → END (wait for user)   │
│  finalize → END (interview complete)                     │
└──────────────────────────────────────────────────────────┘
```

### Graph Structure

**File**: `agents/conversational/graph.py:25-100`

```python
workflow = StateGraph(InterviewState)

# Nodes
workflow.add_node("router", router_node)              # Entry point
workflow.add_node("identify_gaps", identify_gaps_node)  # Analyze resume
workflow.add_node("select_gap", select_gap_node)       # Pick next question
workflow.add_node("generate_response", generate_response_node)  # Ask question
workflow.add_node("agent_node", agent_node)            # Process answer (ReAct)
workflow.add_node("update_state", update_state_node)   # Update skills/gaps
workflow.add_node("finalize", finalize_node)           # End interview

# Edges
workflow.set_entry_point("router")

workflow.add_conditional_edges("router", is_first_run, {...})
workflow.add_conditional_edges("identify_gaps", should_continue_interview, {...})
workflow.add_conditional_edges("update_state", should_continue_interview, {...})

workflow.add_edge("select_gap", "generate_response")
workflow.add_edge("generate_response", END)
workflow.add_edge("agent_node", "update_state")
workflow.add_edge("finalize", END)

graph = workflow.compile(checkpointer=get_postgres_checkpointer())
```

---

## Detailed Node Flow

### 1. First Invocation (Start Interview)

**Entry Point**: `agents/conversational/agent.py:60-115`

```python
result = graph.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
```

**Execution Flow**:

```
START
  ↓
router_node (no-op pass-through)
  ↓
is_first_run() → "identify_gaps" (because messages == [])
  ↓
identify_gaps_node:
  - Extracts skills from resume using SkillAnalyzer
  - Identifies gaps (missing skill attributes)
  - Calculates initial completeness score
  - Returns: identified_gaps, extracted_skills, completeness_score
  ↓
should_continue_interview() → "select_gap"
  - Checks if gaps exist
  - Checks completeness threshold
  ↓
select_gap_node:
  - Filters unresolved gaps with remaining probes
  - Picks highest-severity gap
  - Returns: current_gap
  ↓
generate_response_node:
  - Generates first question using PromptLoader
  - Persists question to database
  - Returns: messages=[AIMessage(question)], questions_asked=1
  ↓
END (graph pauses, state checkpointed, waits for user input)
```

**State Checkpoint**: ✅ Saved to PostgreSQL with `thread_id` as key

---

### 2. Subsequent Invocations (Continue Interview)

**Entry Point**: `agents/conversational/agent.py:117-194`

```python
result = graph.invoke(
    {"messages": [HumanMessage(content=answer)]},
    config={"configurable": {"thread_id": thread_id}}
)
```

**Execution Flow**:

```
START (loads checkpoint from PostgreSQL using thread_id)
  ↓
router_node (no-op)
  ↓
is_first_run() → "agent_node" (because messages exist)
  ↓
agent_node (Agentic Tool Calling):
  - Creates ReAct agent with registered tools
  - Builds system prompt from templates
  - LLM autonomously decides to call analyze_technical_skills
  - Parses tool results with Pydantic validation
  - Returns: tool_results = {skills: [...], engagement: {...}}
  ↓
update_state_node:
  - Merges new skills with existing skills
  - Updates engagement metrics
  - Checks if current gap is resolved
  - Recalculates completeness score
  - Persists answer to database
  - Returns: extracted_skills, resolved_gaps, completeness_score, consecutive_low_quality
  ↓
should_continue_interview():
  - Check disengagement: consecutive_low_quality >= 3?
  - Check completeness: score >= minimum_completeness (60%)?
  - Check remaining gaps: any unresolved gaps left?
  - Returns: "select_gap" OR "finalize"
  ↓
If "select_gap":
  select_gap_node → generate_response_node → END
If "finalize":
  finalize_node → END (interview complete, skills persisted)
```

**State Checkpoint**: ✅ Saved to PostgreSQL after each node execution

---

## State Persistence

### PostgreSQL Checkpointer

**File**: `agents/conversational/checkpointer.py:14-52`

```python
def get_postgres_checkpointer() -> PostgresSaver:
    """Singleton PostgreSQL checkpointer for state persistence."""
    global _checkpointer_instance

    if _checkpointer_instance is None:
        connection_pool = ConnectionPool(
            conninfo=settings.DATABASE_URL,
            autocommit=True,
            row_factory=dict_row
        )
        _checkpointer_instance = PostgresSaver(conn=connection_pool)
        _checkpointer_instance.setup()  # Creates checkpoint tables

    return _checkpointer_instance
```

### What's Persisted

- ✅ Full `InterviewState` (messages, gaps, skills, completeness, etc.)
- ✅ All conversation history (Q&A pairs)
- ✅ Graph position (which node to resume from)
- ✅ Channel versions (for time-travel debugging)
- ✅ Metadata (timestamps, checkpoint IDs)

### Database Tables

**Auto-created by LangGraph**:

| Table | Purpose |
|-------|---------|
| `checkpoints` | Full state snapshots at each step |
| `checkpoint_writes` | Incremental state updates |
| `checkpoint_blobs` | Large binary data (if needed) |

### Resume Mechanism

```python
# The thread_id is the key to resume sessions
config = {"configurable": {"thread_id": "thread_abc123"}}

# Continue from exact same state
result = graph.invoke({"messages": [HumanMessage("new answer")]}, config)
# ↑ PostgresSaver automatically loads state from database
```

**Session can be resumed**:
- ✅ After browser refresh
- ✅ After server restart
- ✅ Days/weeks later
- ✅ From different machines (same DB)

---

## How to Add New Tools

Tools are used by the ReAct agent to extract information from user answers.

### Step 1: Create Tool File

**File**: `tools/personality_analyzer.py` (example)

```python
from langchain.tools import tool
import json
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader

@tool
def analyze_personality_traits(answer_text: str, conversation_context: str = "") -> str:
    """
    Analyze personality traits from candidate's answer.

    Extracts communication style, confidence level, and problem-solving approach
    to understand soft skills and working style.

    Args:
        answer_text: The candidate's current answer
        conversation_context: Previous Q&A for additional context

    Returns:
        JSON string with personality insights

    Use this tool when:
    - User describes how they work with teams
    - User explains their approach to problems
    - You want to assess communication style
    """
    llm = LLMService()
    prompt_loader = PromptLoader()

    # Load system prompt from templates
    system_prompt = prompt_loader.load("personality_analysis", mode="shared")

    # Define JSON schema for validation
    schema = {
        "type": "object",
        "properties": {
            "communication_style": {
                "type": "string",
                "description": "How they communicate (clear, verbose, concise, etc.)"
            },
            "confidence_level": {
                "type": "string",
                "enum": ["low", "medium", "high"]
            },
            "problem_solving_approach": {
                "type": "string",
                "description": "Their approach (analytical, creative, systematic, etc.)"
            },
            "reasoning": {
                "type": "string",
                "description": "Explanation of assessment"
            }
        },
        "required": ["communication_style", "confidence_level", "problem_solving_approach"]
    }

    # Use generate_json for structured output with validation
    result = llm.generate_json(
        system_prompt=system_prompt,
        human_prompt=f"""Answer: {answer_text}

Conversation context: {conversation_context}

Analyze the personality traits from this answer.""",
        schema=schema
    )

    return json.dumps(result, indent=2)
```

### Step 2: Register Tool

**File**: `tools/__init__.py`

```python
from tools.analysis_tools import analyze_technical_skills
from tools.personality_analyzer import analyze_personality_traits  # NEW
from tools.registry import get_tool_registry

# Register at module load
registry = get_tool_registry()

# Existing tool
registry.register_tool(
    "analyze_technical_skills",
    analyze_technical_skills,
    agents=["conversational"]
)

# NEW: Register personality tool
registry.register_tool(
    "analyze_personality_traits",
    analyze_personality_traits,
    agents=["conversational"]  # Make available to conversational agent
)
```

### Step 3: Create Prompt Template

**File**: `prompts/shared/personality_analysis.md`

```markdown
# Personality Trait Analysis

Analyze the candidate's personality traits from their answer.

## Focus Areas

1. **Communication Style**: How do they express themselves?
   - Clear and structured
   - Verbose with examples
   - Concise and to-the-point
   - Technical and precise

2. **Confidence Level**: How confident do they seem?
   - Low: Uncertain, hedging ("I think", "maybe", "probably")
   - Medium: Balanced, some uncertainty
   - High: Assertive, definitive statements

3. **Problem-Solving Approach**: How do they approach challenges?
   - Analytical: Data-driven, methodical
   - Creative: Innovative, thinking outside the box
   - Systematic: Process-oriented, step-by-step
   - Collaborative: Team-focused, seeking input

## Output

Return structured JSON with your assessment and reasoning.
No commentary, just the analysis.
```

### Step 4: Update State (Optional)

If you need to store personality data in state:

**File**: `agents/conversational/state.py`

```python
class PersonalityTrait(TypedDict):
    """Personality assessment result."""
    communication_style: str
    confidence_level: str  # "low" | "medium" | "high"
    problem_solving_approach: str
    reasoning: str

class InterviewState(TypedDict):
    # ... existing fields ...

    # NEW: Add personality traits
    personality_traits: Optional[PersonalityTrait]
```

**File**: `agents/conversational/nodes/update_state.py`

Add parsing logic in `update_state_node`:

```python
def update_state_node(state: InterviewState) -> Dict[str, Any]:
    """Update state based on tool execution results."""
    tool_results = state.get("tool_results", {})

    # ... existing skill processing ...

    # NEW: Process personality analysis results
    if "personality" in tool_results:
        personality_data = tool_results["personality"]

        personality_trait: PersonalityTrait = {
            "communication_style": personality_data.get("communication_style", "unknown"),
            "confidence_level": personality_data.get("confidence_level", "medium"),
            "problem_solving_approach": personality_data.get("problem_solving_approach", "unknown"),
            "reasoning": personality_data.get("reasoning", "")
        }

        updates["personality_traits"] = personality_trait
        print(f"  -> Assessed personality: {personality_trait['communication_style']}")

    return updates
```

### Step 5: Test

**Done!** The ReAct agent will now:
1. See the new tool in its available tools list
2. Read the tool's docstring to understand when to use it
3. Autonomously call it when the user's answer warrants personality analysis
4. Parse and validate the JSON response
5. Store results in state

**No changes needed to agent_node.py** - the ReAct pattern handles it automatically!

---

## How to Add New Nodes

Nodes are the building blocks of the graph. Each node performs a specific task.

### Example: Add Email Draft Node

**Step 1: Create Node File**

**File**: `agents/conversational/nodes/draft_email.py`

```python
"""
Draft email node - generates follow-up email after interview completion.
"""

from typing import Dict, Any
from agents.conversational.state import InterviewState
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader


def draft_email_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate a professional follow-up email draft based on interview.

    Uses conversation history and extracted skills to create a personalized
    email thanking the candidate and outlining next steps.

    Args:
        state: Current interview state

    Returns:
        Dictionary with updates:
        - email_draft: str (the drafted email)
    """
    print(f"\n{'='*60}")
    print(f"NODE: draft_email_node")

    extracted_skills = state.get("extracted_skills", [])
    messages = state.get("messages", [])
    termination_reason = state.get("termination_reason", "complete")

    llm = LLMService()
    prompt_loader = PromptLoader()

    # Build skill summary
    skill_names = [s['name'] for s in extracted_skills]
    skill_summary = ", ".join(skill_names[:5])  # Top 5 skills

    # Load email template prompt
    try:
        prompt = prompt_loader.load(
            "email_draft",
            mode="shared",
            skill_summary=skill_summary,
            conversation_length=len(messages) // 2,  # Number of Q&A pairs
            termination_reason=termination_reason
        )
    except Exception as e:
        print(f"  -> Warning: Could not load email template: {e}")
        prompt = f"""Draft a professional follow-up email to the candidate.

Skills discussed: {skill_summary}
Interview length: {len(messages) // 2} questions

Include:
1. Thank you for their time
2. Brief summary of skills discussed
3. Next steps in the process
4. Timeline expectations

Keep it warm, professional, and under 150 words."""

    email_draft = llm.generate(prompt).strip()

    print(f"  -> Drafted email ({len(email_draft)} characters)")

    return {"email_draft": email_draft}
```

**Step 2: Update State Schema**

**File**: `agents/conversational/state.py`

```python
class InterviewState(TypedDict):
    # ... existing fields ...

    # NEW: Email draft
    email_draft: Optional[str]
    """Auto-generated follow-up email draft"""
```

**Step 3: Add to Graph**

**File**: `agents/conversational/graph.py`

```python
from agents.conversational.nodes import (
    identify_gaps_node,
    generate_response_node,
    agent_node,
    update_state_node,
    finalize_node,
    router_node,
    select_gap_node,
    draft_email_node  # NEW
)

def create_interview_graph(checkpointer: PostgresSaver = None):
    """Create the interview graph workflow with agentic tool calling."""
    workflow = StateGraph(InterviewState)

    # Add all nodes
    workflow.add_node("router", router_node)
    workflow.add_node("identify_gaps", identify_gaps_node)
    workflow.add_node("select_gap", select_gap_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("update_state", update_state_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("draft_email", draft_email_node)  # NEW

    # ... existing edges ...

    # NEW: After finalize, draft email
    workflow.add_edge("finalize", "draft_email")
    workflow.add_edge("draft_email", END)

    # REMOVE: workflow.add_edge("finalize", END)

    return workflow.compile(checkpointer=checkpointer)
```

**Step 4: Export Node**

**File**: `agents/conversational/nodes/__init__.py`

```python
from agents.conversational.nodes.identify_gaps import identify_gaps_node
from agents.conversational.nodes.generate_response import generate_response_node
from agents.conversational.nodes.agent_node import agent_node
from agents.conversational.nodes.update_state import update_state_node
from agents.conversational.nodes.finalize import finalize_node
from agents.conversational.nodes.helpers import router_node, select_gap_node
from agents.conversational.nodes.draft_email import draft_email_node  # NEW

__all__ = [
    "identify_gaps_node",
    "generate_response_node",
    "agent_node",
    "update_state_node",
    "finalize_node",
    "router_node",
    "select_gap_node",
    "draft_email_node"  # NEW
]
```

**Step 5: Create Prompt Template (Optional)**

**File**: `prompts/shared/email_draft.md`

```markdown
# Follow-Up Email Draft

Generate a professional follow-up email to the candidate after their interview.

## Context

- Skills discussed: {skill_summary}
- Interview length: {conversation_length} questions
- Completion reason: {termination_reason}

## Email Structure

1. **Opening**: Thank them for their time
2. **Summary**: Briefly mention key skills discussed
3. **Next Steps**: Outline what happens next in the process
4. **Timeline**: When they can expect to hear back
5. **Closing**: Professional sign-off

## Tone

- Warm and professional
- Encouraging but not overpromising
- Clear about next steps
- Under 150 words

## Output

Return only the email text, no subject line or signatures.
```

**Done!** Now the graph flow is:

```
... → finalize → draft_email → END
```

---

## How to Add Conditional Logic

Conditional edges allow dynamic routing based on state.

### Example: Route Based on Skill Level

**Step 1: Create Condition Function**

**File**: `agents/conversational/conditions.py`

```python
def route_by_skill_level(state: InterviewState) -> Literal["advanced_interview", "beginner_interview"]:
    """
    Route to different interview paths based on detected skill level.

    Analyzes extracted skills to determine if candidate is senior-level
    or beginner-level, then routes to appropriate question set.

    Args:
        state: Current interview state

    Returns:
        "advanced_interview" if senior-level skills detected
        "beginner_interview" otherwise
    """
    extracted_skills = state.get("extracted_skills", [])

    # Check for senior-level indicators
    senior_keywords = ["senior", "lead", "architect", "principal", "staff"]

    for skill in extracted_skills:
        autonomy = skill.get("autonomy", "").lower()

        # Check if any senior keyword is in autonomy description
        if any(keyword in autonomy for keyword in senior_keywords):
            print(f"  -> Detected senior-level: {skill['name']} ({skill['autonomy']})")
            return "advanced_interview"

        # Check for team leadership
        if "team" in autonomy and ("lead" in autonomy or "manage" in autonomy):
            print(f"  -> Detected team leadership: {skill['name']}")
            return "advanced_interview"

        # Check for architectural work
        depth = skill.get("depth", "").lower()
        if "architecture" in depth or "design" in depth or "system" in depth:
            print(f"  -> Detected architectural work: {skill['name']}")
            return "advanced_interview"

    print(f"  -> No senior indicators found, routing to beginner interview")
    return "beginner_interview"
```

**Step 2: Create Different Interview Paths**

**File**: `agents/conversational/nodes/advanced_questions.py`

```python
"""Advanced interview questions for senior-level candidates."""

from typing import Dict, Any
from agents.conversational.state import InterviewState
from utils.llm_service import LLMService

def advanced_interview_node(state: InterviewState) -> Dict[str, Any]:
    """
    Ask architecture and system design questions.

    Focuses on:
    - System design and scalability
    - Technical leadership
    - Architectural decisions
    - Trade-offs and constraints
    """
    current_gap = state.get("current_gap")

    llm = LLMService()

    # Advanced question prompt
    prompt = f"""Generate an advanced technical question about: {current_gap['description']}

Focus on:
- System design and architecture
- Scalability and performance trade-offs
- Technical leadership and decision-making
- Complex problem-solving

Keep it conversational but technical."""

    question = llm.generate(prompt).strip()

    return {
        "messages": [AIMessage(content=question)],
        "questions_asked": state.get("questions_asked", 0) + 1
    }
```

**File**: `agents/conversational/nodes/beginner_questions.py`

```python
"""Beginner interview questions for early-career candidates."""

from typing import Dict, Any
from agents.conversational.state import InterviewState
from utils.llm_service import LLMService

def beginner_interview_node(state: InterviewState) -> Dict[str, Any]:
    """
    Ask foundational and practical questions.

    Focuses on:
    - Practical experience
    - Learning approach
    - Basic technical concepts
    - Hands-on projects
    """
    current_gap = state.get("current_gap")

    llm = LLMService()

    # Beginner-friendly question prompt
    prompt = f"""Generate a beginner-friendly question about: {current_gap['description']}

Focus on:
- Practical, hands-on experience
- Learning journey and growth
- Specific examples from projects
- Foundational understanding

Keep it encouraging and conversational."""

    question = llm.generate(prompt).strip()

    return {
        "messages": [AIMessage(content=question)],
        "questions_asked": state.get("questions_asked", 0) + 1
    }
```

**Step 3: Add Conditional Edge to Graph**

**File**: `agents/conversational/graph.py`

```python
from agents.conversational.conditions import (
    should_continue_interview,
    is_first_run,
    route_by_skill_level  # NEW
)

from agents.conversational.nodes import (
    # ... existing nodes ...
    advanced_interview_node,  # NEW
    beginner_interview_node   # NEW
)

def create_interview_graph(checkpointer: PostgresSaver = None):
    workflow = StateGraph(InterviewState)

    # Add nodes
    # ... existing nodes ...
    workflow.add_node("advanced_interview", advanced_interview_node)  # NEW
    workflow.add_node("beginner_interview", beginner_interview_node)  # NEW

    # NEW: After identify_gaps, route based on skill level
    workflow.add_conditional_edges(
        "identify_gaps",
        route_by_skill_level,
        {
            "advanced_interview": "advanced_interview",
            "beginner_interview": "beginner_interview"
        }
    )

    # Both paths continue to should_continue check
    workflow.add_conditional_edges(
        "advanced_interview",
        should_continue_interview,
        {"select_gap": "select_gap", "finalize": "finalize"}
    )

    workflow.add_conditional_edges(
        "beginner_interview",
        should_continue_interview,
        {"select_gap": "select_gap", "finalize": "finalize"}
    )

    return workflow.compile(checkpointer=checkpointer)
```

**Updated Flow**:

```
identify_gaps
    ↓
route_by_skill_level()
    ├─ Senior detected → advanced_interview
    └─ Beginner → beginner_interview
        ↓
should_continue_interview()
    ├─ Continue → select_gap
    └─ Finish → finalize
```

---

## Session Resume

### How Resume Works

**Key Insight**: The `thread_id` is the unique identifier for a conversation session.

**File**: `agents/conversational/agent.py:60-115`

```python
# Starting a new interview
def start_interview(self, candidate_id: str, resume_text: str):
    # Create unique thread_id
    thread_id = f"thread_{uuid.uuid4()}"

    # Create database session record
    session = InterviewSession(
        candidate_id=candidate_id,
        resume_text=resume_text,
        thread_id=thread_id,
        status="active"
    )
    self.db_session.add(session)
    self.db_session.commit()

    # Run graph with thread_id
    config = {"configurable": {"thread_id": thread_id}}
    result = self.graph.invoke(initial_state, config)

    return {
        "session_id": session.id,
        "thread_id": thread_id,  # ← Store this!
        "question": question
    }
```

**File**: `agents/conversational/agent.py:117-194`

```python
# Continuing an interview (works even after restart!)
def continue_interview(self, thread_id: str, answer: str):
    # Load session from database
    session = db.query(InterviewSession).filter_by(thread_id=thread_id).first()

    # Resume from exact checkpoint
    config = {"configurable": {"thread_id": thread_id}}
    result = self.graph.invoke(
        {"messages": [HumanMessage(content=answer)]},
        config  # ← LangGraph loads full state from PostgreSQL
    )

    # State is automatically restored!
    # - All previous messages
    # - All extracted skills
    # - All gaps (resolved and unresolved)
    # - Completeness score
    # - Engagement history
    # - Graph position (which node to execute next)
```

### Example Usage

```python
from agents.conversational.agent import ConversationalAgent

# Day 1: Start interview
agent = ConversationalAgent(llm_service, prompt_loader, db_session)

result = agent.start_interview(
    candidate_id="candidate_123",
    resume_text="Senior Python Developer with 5 years..."
)

thread_id = result["thread_id"]  # Save this!
# Output: "thread_a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# User answers first question
agent.continue_interview(thread_id, "I worked with Python for 5 years")

# User answers second question
agent.continue_interview(thread_id, "I led a team of 4 developers")

# User closes browser
# ... wait 2 days ...

# Day 3: User returns (browser closed, server restarted, doesn't matter)
# Just need the thread_id!
agent.continue_interview(thread_id, "I also have experience with Docker")
# ✅ Continues from exact same state!
```

### What Gets Restored

When resuming via `thread_id`, LangGraph restores:

```python
InterviewState {
    session_id: "abc-123",
    resume_text: "Senior Python Developer...",
    messages: [
        AIMessage("Question 1..."),
        HumanMessage("I worked with Python for 5 years"),
        AIMessage("Question 2..."),
        HumanMessage("I led a team of 4 developers"),
        # ... all previous Q&A
    ],
    extracted_skills: [
        {name: "Python", duration: "5 years", autonomy: "led team of 4", ...},
        # ... all previously extracted skills
    ],
    identified_gaps: [...],
    resolved_gaps: [...],
    current_gap: {description: "Missing scale for Python", ...},
    completeness_score: 0.45,
    questions_asked: 2,
    # ... everything!
}
```

### Time-Travel Debugging

LangGraph also supports going back in time:

```python
# Get all checkpoints for a thread
checkpoints = []
for checkpoint in graph.get_state_history(config):
    checkpoints.append({
        "step": checkpoint.config["configurable"]["checkpoint_id"],
        "timestamp": checkpoint.values.get("timestamp"),
        "questions_asked": checkpoint.values.get("questions_asked")
    })

# Resume from a specific past checkpoint
past_checkpoint_id = checkpoints[2]["step"]
time_travel_config = {
    "configurable": {
        "thread_id": thread_id,
        "checkpoint_id": past_checkpoint_id  # ← Go back to this point
    }
}

result = graph.invoke(
    {"messages": [HumanMessage("Let's try a different answer")]},
    config=time_travel_config
)
```

---

## State Lifecycle

### Visual Representation

```
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL Database (checkpoints table)                     │
│                                                              │
│  ┌──────────────┬──────┬────────────────────────────┐      │
│  │ thread_id    │ step │ state_json                 │      │
│  ├──────────────┼──────┼────────────────────────────┤      │
│  │ thread_123   │ 0    │ {initial_state}            │      │
│  │ thread_123   │ 1    │ {after identify_gaps}      │      │
│  │ thread_123   │ 2    │ {after select_gap}         │      │
│  │ thread_123   │ 3    │ {after generate_response}  │ ← Current │
│  │ thread_123   │ 4    │ {after agent_node}         │      │
│  │ thread_123   │ 5    │ {after update_state}       │      │
│  └──────────────┴──────┴────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                         ↓
        graph.invoke({...}, config={"thread_id": "thread_123"})
                         ↓
              Loads step 3, continues execution
                         ↓
              Saves step 4, 5, 6... as graph runs
```

### State Update Pattern

Every node can return a dictionary of state updates:

```python
def my_node(state: InterviewState) -> Dict[str, Any]:
    """Node that updates multiple state fields."""

    # Read from state
    current_value = state.get("some_field", default_value)

    # Compute updates
    new_value = compute_something(current_value)

    # Return updates (will be merged into state)
    return {
        "some_field": new_value,
        "another_field": "new data",
        "messages": [AIMessage(content="Generated message")]
        # messages will be appended (not replaced) due to add_messages reducer
    }
```

**Important**: State updates are **shallow merged** unless a reducer is specified:

```python
# In state.py
class InterviewState(TypedDict):
    # Without reducer: replacement
    completeness_score: float

    # With add reducer: append
    messages: Annotated[List[BaseMessage], add_messages]

    # With custom reducer: custom logic
    extracted_skills: Annotated[List[Skill], merge_skills]
```

---

## Quick Reference

### File Locations

| Component | File Path |
|-----------|-----------|
| **Graph Definition** | `agents/conversational/graph.py` |
| **State Schema** | `agents/conversational/state.py` |
| **Nodes** | `agents/conversational/nodes/*.py` |
| **Conditions** | `agents/conversational/conditions.py` |
| **Tools** | `tools/*.py` |
| **Tool Registry** | `tools/registry.py` |
| **Checkpointer** | `agents/conversational/checkpointer.py` |
| **Agent Interface** | `agents/conversational/agent.py` |
| **Prompts** | `prompts/conversational/*.md`, `prompts/shared/*.md` |

### Extension Checklist

| To Add | Files to Modify |
|--------|-----------------|
| **New Tool** | 1. Create `tools/my_tool.py`<br>2. Register in `tools/__init__.py`<br>3. Add prompt in `prompts/shared/` |
| **New Node** | 1. Create `nodes/my_node.py`<br>2. Export in `nodes/__init__.py`<br>3. Add to graph in `graph.py`<br>4. Update `state.py` if needed |
| **New Condition** | 1. Add function in `conditions.py`<br>2. Use in `graph.py` with `add_conditional_edges()` |
| **New State Field** | 1. Update `InterviewState` in `state.py`<br>2. Update nodes that read/write it |

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Node** | A function that reads state, performs work, returns updates |
| **Edge** | Connection between nodes (direct or conditional) |
| **State** | TypedDict holding all conversation data |
| **Checkpointer** | PostgreSQL-backed persistence layer |
| **thread_id** | Unique identifier for a conversation session |
| **Reducer** | Function that controls how state fields are updated (replace vs append vs custom) |
| **Tool** | Function available to ReAct agent for information extraction |
| **ReAct Pattern** | LLM autonomously decides which tools to call |

### Common Operations

**Get current state**:
```python
config = {"configurable": {"thread_id": thread_id}}
snapshot = graph.get_state(config)
print(snapshot.values)  # Current state
print(snapshot.next)    # Next node to execute
```

**List all threads**:
```python
# Query database directly
sessions = db.query(InterviewSession).all()
for session in sessions:
    print(f"Thread: {session.thread_id}, Status: {session.status}")
```

**Clear/delete a thread**:
```python
# Not built-in to LangGraph, but you can delete from DB
# This will make the thread unresumable
db.query(Checkpoint).filter_by(thread_id=thread_id).delete()
db.commit()
```

---

## Best Practices

### 1. State Design

✅ **DO**:
- Keep state flat when possible
- Use TypedDict for type safety
- Add Optional[] for nullable fields
- Use reducers for list fields (add_messages)

❌ **DON'T**:
- Store large binary data in state (use database instead)
- Put functions or non-serializable objects in state
- Create deeply nested structures

### 2. Node Design

✅ **DO**:
- Keep nodes focused (single responsibility)
- Return only changed fields
- Print debug info for observability
- Handle errors gracefully

❌ **DON'T**:
- Mutate state directly (return updates instead)
- Make nodes too complex (split into multiple nodes)
- Forget to handle None/empty cases

### 3. Tool Design

✅ **DO**:
- Use `generate_json()` for structured output
- Define clear JSON schemas
- Write detailed docstrings (LLM reads them!)
- Return JSON strings from tools

❌ **DON'T**:
- Return complex objects (stick to JSON)
- Re-analyze full resume on every call
- Forget to handle LLM failures

### 4. Prompt Design

✅ **DO**:
- Use PromptLoader for reusability
- Keep prompts in templates (`prompts/`)
- Use `.format()` for variable substitution
- Test prompts independently

❌ **DON'T**:
- Hardcode prompts in Python code
- Forget to escape special characters
- Make prompts too long (cost!)

---

## Troubleshooting

### Issue: State not persisting

**Check**:
1. Is checkpointer passed to `compile()`?
2. Is `thread_id` provided in config?
3. Is PostgreSQL running?
4. Are checkpoint tables created? (Run `checkpointer.setup()`)

### Issue: Graph stuck in infinite loop

**Check**:
1. Does every path lead to `END`?
2. Are conditional edges properly defined?
3. Is `should_continue` flag being updated?

### Issue: Tool not being called

**Check**:
1. Is tool registered in `tools/__init__.py`?
2. Does tool docstring clearly describe when to use it?
3. Is tool assigned to correct agent?
4. Check agent_node logs for available tools

### Issue: Resume fails after code changes

**Solution**:
- LangGraph requires state schema to match
- If you change `InterviewState`, old checkpoints may fail
- For development: Delete checkpoints table
- For production: Write migration or version state

---

## Additional Resources

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangChain Tools**: https://python.langchain.com/docs/modules/agents/tools/
- **PostgresSaver**: https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.PostgresSaver

---

**Last Updated**: 2026-01-02
**Version**: 1.0
