# Conversational Agent V2 Architecture

## Executive Summary

The current conversational agent has fundamental architectural issues that cause skill extraction failures and state update problems. This document proposes a **multi-agent supervisor architecture** that solves these issues while adding support for predefined question-based interviews.

**Key Changes:**
- ✅ Explicit context passing to tools (eliminates "unknown" skill extraction)
- ✅ Supervisor pattern for mode routing (gap-based vs predefined)
- ✅ Specialized sub-agents with clear responsibilities
- ✅ Support for predefined interview templates (like Fullstack_developer_senior.md)
- ✅ Scalable, testable, maintainable architecture

---

## Current Architecture Problems

### Problem 1: Context Loss in Tools ⚠️ **ROOT CAUSE**

**The Issue:**
When a user answers "3 years" to the question "How long have you worked with Python?", the tool `analyze_technical_skills()` receives:

```python
analyze_technical_skills(
    answer_text="3 years",
    conversation_context="Q: How long have you worked with Python?\nA: 3 years"
)
```

**What the tool DOESN'T receive:**
- `current_gap`: That we're asking about Python duration
- `skill_name`: "Python"
- `attribute_being_asked`: "duration"
- `existing_skill_data`: What we already know about Python

**The Result:**
The LLM inside the tool sees "3 years" and must INFER what skill this refers to from conversation context. This is unreliable and often produces:

```json
{
  "name": "unknown",  // Because "3 years" alone doesn't mention Python!
  "duration": "3 years",
  "depth": "unknown",
  ...
}
```

### Problem 2: Gap Resolution Fails

**File:** `agents/conversational/nodes/update_state.py:277`

The `check_gap_resolved()` function tries to match extracted skills to gaps:

```python
def check_gap_resolved(gap: Gap, new_attributes_added: List[Dict[str, Any]]) -> bool:
    gap_context = gap.get("context", "")  # "Python skill - need: duration"

    for item in new_attributes_added:
        skill_name = item["skill_name"]  # "unknown" ← Problem!

        # This check FAILS if skill_name is "unknown"
        if skill_name.lower() in gap_context.lower():
            return True

    return False
```

**The Result:** Even though we successfully extracted `duration: "3 years"`, the gap remains unresolved because the skill name is "unknown".

### Problem 3: Monolithic Flow

**File:** `agents/conversational/graph.py`

The current graph tries to do everything in one flow:

```
START → identify_gaps → select_gap → generate_response → END
  ↓
agent_node → update_state → select_gap → generate_response → END
```

**Problems:**
- Tight coupling between gap identification, question generation, and answer parsing
- Hard to add new modes (predefined questions)
- Difficult to test individual components
- No separation of concerns

### Problem 4: No Predefined Question Support

The entire architecture is gap-based. There's no mechanism for:
- Loading predefined questions from role templates
- Tracking progress through a question list
- Adapting questions based on context
- Switching between gap-based and guided interview modes

---

## Proposed Architecture: Multi-Agent Supervisor Pattern

### Architecture Overview

```
                        ┌─────────────────────┐
                        │  SupervisorAgent    │
                        │  (Main Orchestrator)│
                        └──────────┬──────────┘
                                   │
                                   ├─ Decides mode (gap vs predefined)
                                   ├─ Manages termination
                                   └─ Persists state
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
  ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
  │  GapAgent   │          │ GuideAgent  │          │ ParseAgent  │
  │ (Gap-based) │          │(Predefined) │          │  (Answer)   │
  └─────────────┘          └─────────────┘          └─────────────┘
         │                         │                         │
         ├─ Identify gaps          ├─ Load template         ├─ Extract skills
         ├─ Select next gap        ├─ Track progress        ├─ Assess engagement
         └─ Track resolution       └─ Branch/skip logic     └─ Update state
                                   │
                  ┌────────────────┴────────────────┐
                  │                                 │
           ┌──────▼──────┐                  ┌──────▼──────┐
           │ Question    │                  │   Tools     │
           │ Generator   │                  │ (Enhanced)  │
           └─────────────┘                  └─────────────┘
                  │                                 │
                  └─────────────────┬───────────────┘
                                    │
                    All components receive EXPLICIT context
```

### Key Principles

1. **Explicit Context Everywhere**: Every tool and agent receives ALL context needed
2. **Mode-Agnostic**: Supervisor routes between gap-based and predefined modes
3. **Specialized Agents**: Each agent has one clear responsibility
4. **Shared Tools**: Tools work for both modes with explicit context
5. **State Machine**: Clear state transitions with conditional routing

---

## Component Design

### 1. SupervisorAgent (Main Orchestrator)

**File:** `agents/conversational/v2/supervisor.py`

**Responsibilities:**
- Determine which mode to use (gap-based or predefined)
- Route to appropriate sub-agent
- Manage interview termination conditions
- Persist final state

**Logic:**
```python
def supervisor_node(state: InterviewStateV2) -> Dict[str, Any]:
    """
    Route to appropriate agent based on interview mode and state.

    Routes:
    - First run + gap mode → gap_agent
    - First run + predefined mode → guide_agent
    - User answered → parse_agent
    - Termination conditions met → finalize
    """
    mode = state["interview_mode"]["mode"]
    messages = state["messages"]

    # Check termination conditions
    if should_terminate(state):
        return {"next": "finalize"}

    # First run - no messages yet
    if not messages:
        if mode == "gap_based":
            return {"next": "gap_agent"}
        else:
            return {"next": "guide_agent"}

    # User just answered - parse it
    last_message = messages[-1]
    if last_message.type == "human":
        return {"next": "parse_agent"}

    # We just asked a question - wait for answer
    return {"next": END}
```

### 2. GapAgent (Gap-Based Interview Logic)

**File:** `agents/conversational/v2/modes/gap/gap_agent.py`

**Responsibilities:**
- Analyze resume to identify skill gaps
- Select next gap to probe (priority-based)
- Build rich question context for generator
- Track gap resolution

**Enhanced Gap Resolution:**
```python
def check_gap_resolved(
    gap: Gap,
    extracted_skills: List[Skill],
    current_question_context: QuestionContext
) -> bool:
    """
    Check if gap is resolved using EXPLICIT skill name from question context.

    NO MORE MATCHING BY NAME - we know exactly which skill was discussed!
    """
    # Get the skill name from question context (EXPLICIT)
    skill_name = current_question_context["targets"]["skill_name"]
    attribute_asked = current_question_context["targets"]["attribute"]

    # Find the skill in extracted_skills
    for skill in extracted_skills:
        if skill["name"].lower() == skill_name.lower():
            # Check if we got the attribute we were asking about
            value = skill.get(attribute_asked)
            if value and value != "unknown":
                # Gap resolved!
                return True

    return False
```

### 3. GuideAgent (Predefined Question Mode)

**File:** `agents/conversational/v2/modes/predefined/guide_agent.py`

**New Component** - Enables structured interviews based on role templates.

**Responsibilities:**
- Load question templates from markdown files (e.g., `docs/Fullstack_developer_senior.md`)
- Track question progress
- Implement skip/branch logic
- Build question context for generator

**Template Loading:**
```python
class GuideAgent:
    """Manages predefined question-based interviews."""

    def __init__(self, role_template_path: str):
        self.questions = self._load_questions(role_template_path)
        self.current_index = 0

    def _load_questions(self, path: str) -> List[Dict]:
        """
        Parse markdown template into structured questions.

        Template format (Fullstack_developer_senior.md):
        ```markdown
        ## CATEGORY_NAME

        Question
        <The question text>

        What this assesses
        <Assessment criteria>

        Expected answer (in general)
        <Expected answer description>
        ```

        Returns:
        [
            {
                "id": "general_info_1",
                "category": "GENERAL INFORMATION",
                "question": "Can you briefly describe your current role...",
                "assesses": ["Career scope and relevance", ...],
                "expected_answer": "The candidate summarizes...",
                "skip_if": null  # Optional: {"condition": "...", "reason": "..."}
            },
            ...
        ]
        """
        # Implementation: Parse markdown sections
        pass

    def select_next_question(
        self,
        state: InterviewStateV2
    ) -> Optional[QuestionContext]:
        """
        Select next question based on:
        - Current progress
        - Skip conditions
        - Previous answers (for branching)

        Returns rich QuestionContext with all metadata.
        """
        for question in self.questions[self.current_index:]:
            if not state["question_progress"].get(question["id"]):
                # Check skip conditions
                if self._should_skip(question, state):
                    self.current_index += 1
                    continue

                # Build question context
                return {
                    "question_id": question["id"],
                    "question_text": question["question"],
                    "question_type": "predefined",
                    "targets": {
                        "category": question["category"],
                        "assesses": question["assesses"]
                    },
                    "gap": None,  # No gap in predefined mode
                    "template_metadata": {
                        "expected_answer": question["expected_answer"],
                        "index": self.current_index
                    }
                }

        return None  # All questions completed

    def _should_skip(self, question: Dict, state: InterviewStateV2) -> bool:
        """
        Evaluate skip conditions.

        Example: Skip "Have you built an iOS app?" if user already said no mobile experience.
        """
        skip_if = question.get("skip_if")
        if not skip_if:
            return False

        # Evaluate condition against state
        # Could use simple keyword matching or LLM-based evaluation
        pass
```

### 4. ParseAgent (Answer Analysis)

**File:** `agents/conversational/v2/parse_agent.py`

**Responsibilities:**
- Receive answer + question context
- Call tools with EXPLICIT context
- Update state with new information
- Assess engagement

**Key Improvement:** Passes explicit context to tools:

```python
def parse_agent_node(state: InterviewStateV2) -> Dict[str, Any]:
    """
    Parse user answer using tools with EXPLICIT context.

    NO MORE GUESSING - tools know exactly what we asked about!
    """
    current_question = state["current_question"]
    messages = state["messages"]
    last_answer = messages[-1].content

    # Build explicit context for tools
    question_context = {
        "question_id": current_question["question_id"],
        "question_text": current_question["question_text"],
        "targets": current_question["targets"],  # Skill name, attribute, etc.
        "gap": current_question.get("gap"),  # Gap being addressed (if any)
    }

    # Call skill extraction with EXPLICIT context
    if current_question["question_type"] == "gap_based":
        # For gap-based, we know exactly what skill and attribute we're asking about
        skill_name = current_question["targets"]["skill_name"]
        attribute = current_question["targets"]["attribute"]

        # Call tool with explicit instructions
        result = extract_skill_attribute(
            answer=last_answer,
            question_context=json.dumps({
                "skill_name": skill_name,
                "attribute_being_asked": attribute,
                "question": current_question["question_text"],
                "existing_skill_data": get_existing_skill(state, skill_name)
            })
        )
    else:
        # For predefined questions, extract any skills mentioned
        result = extract_skills_from_answer(
            answer=last_answer,
            question_context=json.dumps(question_context)
        )

    # Call engagement assessment
    engagement = assess_answer_engagement(
        question=current_question["question_text"],
        answer=last_answer,
        gap_description=current_question.get("gap", {}).get("description", "")
    )

    # Update state with results
    return update_state_from_tools(state, result, engagement)
```

### 5. Enhanced Tools with Explicit Context

**File:** `tools/v2/extraction_tools.py`

**Key Improvement:** Tools receive structured question context, not just raw text.

```python
@tool
def extract_skill_attribute(answer: str, question_context: str) -> str:
    """
    Extract skill attribute with EXPLICIT context about what we're asking.

    This tool receives JSON context with:
    {
        "skill_name": "Python",
        "attribute_being_asked": "duration",
        "question": "How long have you worked with Python?",
        "existing_skill_data": {
            "duration": null,
            "depth": "unknown",
            ...
        }
    }

    This ensures we KNOW what skill and attribute we're extracting.
    NO MORE "unknown" skill names!

    Args:
        answer: User's answer text
        question_context: JSON string with explicit context

    Returns:
        JSON string with extracted skill data
    """
    context = json.loads(question_context)

    # Build highly specific prompt
    schema = {
        "type": "object",
        "properties": {
            "skill_name": {"type": "string"},  # Will be filled from context
            context["attribute_being_asked"]: {"type": "string"},
            "confidence": {"type": "number"},
            "evidence": {"type": "string"}
        },
        "required": ["skill_name", context["attribute_being_asked"]]
    }

    system_prompt = f"""
    Extract the {context['attribute_being_asked']} for {context['skill_name']} from the candidate's answer.

    Question asked: {context['question']}
    Candidate answer: {answer}

    We are SPECIFICALLY asking about the {context['attribute_being_asked']} attribute for {context['skill_name']}.

    IMPORTANT: The skill_name is "{context['skill_name']}" - use this exact name, NOT "unknown".

    Return JSON with:
    - skill_name: "{context['skill_name']}"
    - {context['attribute_being_asked']}: extracted value from the answer
    - confidence: 0.0-1.0
    - evidence: quote from answer supporting this
    """

    llm_service = LLMService()
    result = llm_service.generate_json(
        system_prompt=system_prompt,
        human_prompt="",
        schema=schema
    )

    # Ensure skill_name is correct (defensive)
    result["skill_name"] = context["skill_name"]

    return json.dumps(result)


@tool
def extract_skills_from_answer(answer: str, question_context: str) -> str:
    """
    Extract any technical skills mentioned in answer.

    Used for predefined questions where we don't know in advance what skills will be mentioned.

    Args:
        answer: User's answer
        question_context: JSON with question metadata

    Returns:
        JSON list of skills with attributes
    """
    context = json.loads(question_context)

    system_prompt = f"""
    Extract technical skills from the candidate's answer.

    Question asked: {context['question_text']}
    Candidate answer: {answer}

    For each skill mentioned, extract as many of these 6 attributes as possible:
    - duration: How long they've used it
    - depth: What level/aspects they've implemented
    - autonomy: How independently they worked
    - scale: Impact (users, traffic, size)
    - constraints: Limitations/challenges
    - production_vs_prototype: Production-ready or PoC

    Return JSON array of skills with these attributes.
    """

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "duration": {"type": "string"},
                "depth": {"type": "string"},
                "autonomy": {"type": "string"},
                "scale": {"type": "string"},
                "constraints": {"type": "string"},
                "production_vs_prototype": {"type": "string"},
                "confidence_score": {"type": "number"},
                "evidence": {"type": "string"}
            },
            "required": ["name"]
        }
    }

    llm_service = LLMService()
    result = llm_service.generate_json(
        system_prompt=system_prompt,
        human_prompt="",
        schema=schema
    )

    return json.dumps(result)
```

---

## State Schema V2

**File:** `agents/conversational/v2/state.py`

```python
from typing import TypedDict, Annotated, Optional, List, Any, Dict, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class InterviewMode(TypedDict):
    """Interview mode configuration."""
    mode: Literal["gap_based", "predefined"]
    role_template: Optional[str]  # Path to role template for predefined mode
    question_set: Optional[List[Dict]]  # Loaded questions for predefined mode


class QuestionContext(TypedDict):
    """
    Rich context for every question asked.

    This is the KEY to solving context loss - every question carries
    EXPLICIT information about what we're trying to learn.
    """
    question_id: str  # Unique ID for this question
    question_text: str  # The actual question
    question_type: Literal["gap_based", "predefined"]

    # What we're trying to learn (EXPLICIT)
    targets: Dict[str, Any]
    # For gap_based: {"skill_name": "Python", "attribute": "duration"}
    # For predefined: {"category": "Backend", "assesses": ["Languages", "Architecture"]}

    # Gap-based specific
    gap: Optional[Gap]  # The gap being addressed (if gap_based)

    # Predefined specific
    template_metadata: Optional[Dict]  # Expected answer, category, etc.


class Skill(TypedDict):
    """Technical skill with 6 attributes."""
    name: str
    confidence_score: float
    duration: Optional[str]
    depth: Optional[str]
    autonomy: Optional[str]
    scale: Optional[str]
    constraints: Optional[str]
    production_vs_prototype: Optional[str]
    evidence: str


class Gap(TypedDict):
    """Gap in skill information."""
    category: str
    description: str
    severity: float
    context: str
    probes_attempted: int
    max_probes: int


class EngagementSignal(TypedDict):
    """Engagement assessment for an answer."""
    answer_length: int
    relevance_score: float
    detail_score: float
    enthusiasm_detected: bool
    engagement_level: str


class InterviewStateV2(TypedDict):
    """
    V2 state schema supporting both gap-based and predefined interview modes.
    """

    # ========================================================================
    # SESSION
    # ========================================================================
    session_id: str
    resume_text: str
    messages: Annotated[List[BaseMessage], add_messages]

    # ========================================================================
    # MODE CONFIGURATION
    # ========================================================================
    interview_mode: InterviewMode

    # ========================================================================
    # CURRENT QUESTION (Rich Context!)
    # ========================================================================
    current_question: Optional[QuestionContext]
    """
    CRITICAL: This carries EXPLICIT context about what we're asking.
    Tools use this to know exactly what skill/attribute to extract.
    """

    # ========================================================================
    # PROGRESS TRACKING
    # ========================================================================
    questions_asked: int
    questions_answered: int

    # ========================================================================
    # EXTRACTED DATA
    # ========================================================================
    extracted_skills: List[Skill]

    # ========================================================================
    # GAP-BASED MODE SPECIFIC
    # ========================================================================
    identified_gaps: List[Gap]
    resolved_gaps: List[Gap]

    # ========================================================================
    # PREDEFINED MODE SPECIFIC
    # ========================================================================
    question_progress: Dict[str, bool]  # question_id -> completed

    # ========================================================================
    # ENGAGEMENT
    # ========================================================================
    engagement_signals: List[EngagementSignal]
    consecutive_low_quality: int

    # ========================================================================
    # TERMINATION
    # ========================================================================
    should_continue: bool
    termination_reason: Optional[str]
    completeness_score: float
    minimum_completeness: float


def create_initial_state_v2(
    session_id: str,
    resume_text: str,
    mode: Literal["gap_based", "predefined"],
    role_template: Optional[str] = None
) -> InterviewStateV2:
    """
    Create initial state for V2 architecture.

    Args:
        session_id: Database session ID
        resume_text: Resume text to analyze
        mode: Interview mode ("gap_based" or "predefined")
        role_template: Path to role template (required for predefined mode)

    Returns:
        Fresh InterviewStateV2
    """
    return {
        # Session
        "session_id": session_id,
        "resume_text": resume_text,
        "messages": [],

        # Mode
        "interview_mode": {
            "mode": mode,
            "role_template": role_template,
            "question_set": None  # Will be loaded by GuideAgent if predefined
        },

        # Current question
        "current_question": None,

        # Progress
        "questions_asked": 0,
        "questions_answered": 0,

        # Extracted data
        "extracted_skills": [],

        # Gap-based
        "identified_gaps": [],
        "resolved_gaps": [],

        # Predefined
        "question_progress": {},

        # Engagement
        "engagement_signals": [],
        "consecutive_low_quality": 0,

        # Termination
        "should_continue": True,
        "termination_reason": None,
        "completeness_score": 0.0,
        "minimum_completeness": 0.6
    }
```

---

## Graph Structure V2

**File:** `agents/conversational/v2/graph.py`

```python
from langgraph.graph import StateGraph, END
from agents.conversational.v2.state import InterviewStateV2
from agents.conversational.v2.nodes import (
    supervisor_node,
    gap_agent_node,
    guide_agent_node,
    parse_agent_node,
    question_generator_node,
    finalize_node
)
from agents.conversational.v2.conditions import route_by_supervisor


def create_interview_graph_v2(checkpointer=None):
    """
    Create V2 interview graph with supervisor pattern.

    Flow:
    START → supervisor
      ├─ gap_based → gap_agent → question_generator → END (wait for answer)
      ├─ predefined → guide_agent → question_generator → END (wait for answer)
      ├─ parse → parse_agent → supervisor (loop)
      └─ finalize → END

    User answer triggers: supervisor → parse_agent → supervisor → [gap/guide]_agent → question_generator
    """
    workflow = StateGraph(InterviewStateV2)

    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("gap_agent", gap_agent_node)
    workflow.add_node("guide_agent", guide_agent_node)
    workflow.add_node("parse_agent", parse_agent_node)
    workflow.add_node("question_generator", question_generator_node)
    workflow.add_node("finalize", finalize_node)

    # Entry point
    workflow.set_entry_point("supervisor")

    # Supervisor routes to appropriate agent
    workflow.add_conditional_edges(
        "supervisor",
        route_by_supervisor,
        {
            "gap_agent": "gap_agent",
            "guide_agent": "guide_agent",
            "parse_agent": "parse_agent",
            "finalize": "finalize"
        }
    )

    # Both agents generate questions
    workflow.add_edge("gap_agent", "question_generator")
    workflow.add_edge("guide_agent", "question_generator")

    # Question generator outputs and waits for answer
    workflow.add_edge("question_generator", END)

    # Parse agent loops back to supervisor
    workflow.add_edge("parse_agent", "supervisor")

    # Finalize ends the interview
    workflow.add_edge("finalize", END)

    return workflow.compile(checkpointer=checkpointer)
```

---

## Implementation Plan

### Phase 1: Core Refactor (Week 1)

**Goal:** Implement supervisor pattern and new state schema

1. **Create V2 directory structure:**
   ```
   agents/conversational/v2/
   ├── __init__.py
   ├── state.py                    # New state schema
   ├── graph.py                    # New graph with supervisor
   ├── agent.py                    # Public API (ConversationalAgentV2)
   ├── nodes/
   │   ├── supervisor.py           # Supervisor node
   │   ├── parse_agent.py          # Answer parsing node
   │   ├── question_generator.py  # Question generation node
   │   └── finalize.py            # Finalize node
   ├── conditions.py              # Routing logic
   └── modes/
       ├── gap/
       │   └── gap_agent.py       # Gap-based logic
       └── predefined/
           ├── guide_agent.py     # Predefined question logic
           └── template_parser.py # Parse role templates
   ```

2. **Implement state schema** (`state.py`)
   - Define `InterviewStateV2` with mode support
   - Define `QuestionContext` for explicit context
   - Create `create_initial_state_v2()`

3. **Implement supervisor node** (`nodes/supervisor.py`)
   - Route based on mode and state
   - Implement termination checks
   - Handle state transitions

4. **Implement graph** (`graph.py`)
   - Create workflow with supervisor pattern
   - Add conditional routing
   - Set up checkpointer

### Phase 2: Enhanced Tools (Week 2)

**Goal:** Add explicit context to tools

1. **Create V2 tools:**
   ```
   tools/v2/
   ├── extraction_tools.py
   │   ├── extract_skill_attribute()    # NEW: Explicit context
   │   └── extract_skills_from_answer() # For predefined mode
   ├── analysis_tools.py
   │   └── assess_answer_engagement()   # Enhanced
   └── registry.py                       # Updated registry
   ```

2. **Implement `extract_skill_attribute()`**
   - Receives JSON question context
   - Explicitly knows skill name and attribute
   - Returns structured skill data

3. **Update tool registry**
   - Register V2 tools for "conversational_v2" agent
   - Keep V1 tools for backward compatibility

### Phase 3: Gap Agent (Week 2)

**Goal:** Migrate gap-based logic to new architecture

1. **Implement `GapAgent`** (`modes/gap/gap_agent.py`)
   - Port `identify_gaps_node` logic
   - Enhanced gap resolution with explicit context
   - Build rich `QuestionContext` for each gap

2. **Implement `gap_agent_node`**
   - Call `GapAgent` methods
   - Return state updates
   - Track gap progress

3. **Test gap-based interviews**
   - Resume analysis
   - Gap identification
   - Question generation
   - Gap resolution

### Phase 4: Predefined Questions (Week 3)

**Goal:** Add support for structured role-based interviews

1. **Implement template parser** (`modes/predefined/template_parser.py`)
   - Parse markdown templates (e.g., `Fullstack_developer_senior.md`)
   - Extract questions, categories, expected answers
   - Build structured question list

2. **Implement `GuideAgent`** (`modes/predefined/guide_agent.py`)
   - Load questions from template
   - Select next question
   - Implement skip/branch logic
   - Track progress

3. **Implement `guide_agent_node`**
   - Call `GuideAgent` methods
   - Build `QuestionContext` for predefined questions
   - Return state updates

4. **Create template examples:**
   - Port `Fullstack_developer_senior.md` to structured format
   - Create parser unit tests

### Phase 5: Parse Agent (Week 3)

**Goal:** Unified answer parsing with explicit context

1. **Implement `ParseAgent`** (`nodes/parse_agent.py`)
   - Receive `current_question` from state
   - Call tools with explicit context
   - Update state with extracted info
   - Assess engagement

2. **Implement state update logic:**
   - Merge skills intelligently
   - Mark questions as answered
   - Update gap resolution
   - Track engagement

3. **Test with both modes:**
   - Gap-based answer parsing
   - Predefined question answer parsing

### Phase 6: Question Generator (Week 4)

**Goal:** Generate questions from question context

1. **Implement `QuestionGenerator`** (`nodes/question_generator.py`)
   - Receive `QuestionContext` from state
   - Generate appropriate question based on type
   - Handle follow-ups, clarifications, examples
   - Persist to database

2. **Migrate prompt templates:**
   - Port existing prompts to work with `QuestionContext`
   - Add predefined question prompts

### Phase 7: Migration & Testing (Week 4)

**Goal:** Migrate existing data and deploy

1. **Database migration:**
   - No schema changes needed (same models)
   - Add migration for V2 compatibility

2. **API compatibility layer:**
   - Keep `ConversationalAgent` (V1) for existing integrations
   - Add `ConversationalAgentV2` for new interviews
   - Deprecation notices

3. **Integration testing:**
   - Full gap-based interview flow
   - Full predefined interview flow
   - Mode switching
   - State persistence

4. **Performance testing:**
   - Latency comparison with V1
   - Tool call optimization
   - Checkpointer performance

---

## Benefits of V2 Architecture

### 1. ✅ Solves "Unknown" Skill Problem

**Before:**
```python
# Tool receives just the answer
analyze_technical_skills(answer="3 years")
# → Extracts: {"name": "unknown", "duration": "3 years"}
```

**After:**
```python
# Tool receives explicit context
extract_skill_attribute(
    answer="3 years",
    question_context='{"skill_name": "Python", "attribute_being_asked": "duration"}'
)
# → Extracts: {"name": "Python", "duration": "3 years"}  ✅
```

### 2. ✅ Reliable Gap Resolution

**Before:**
- Matched skills by name string matching
- Failed when name was "unknown"

**After:**
- Use explicit skill name from question context
- Always know which skill was discussed
- Gap resolution is deterministic

### 3. ✅ Support for Predefined Questions

**Before:**
- Only gap-based interviews
- No structured role templates

**After:**
- Load questions from role templates
- Track progress through question list
- Adaptive branching based on answers

### 4. ✅ Scalable Multi-Agent Design

**Before:**
- Monolithic flow
- Hard to add new features

**After:**
- Supervisor coordinates specialized agents
- Easy to add new modes (e.g., "hybrid" mode)
- Each agent testable independently

### 5. ✅ Clean Separation of Concerns

**Before:**
- Nodes mixed gap logic, question generation, parsing

**After:**
- **GapAgent**: Only gap logic
- **GuideAgent**: Only predefined question logic
- **ParseAgent**: Only answer parsing
- **QuestionGenerator**: Only question generation
- **Supervisor**: Only routing

---

## Migration Strategy

### Option 1: Parallel Deployment (Recommended)

1. Deploy V2 alongside V1
2. Create new interviews with V2
3. Keep existing interviews on V1
4. Gradually migrate after testing

**Pros:**
- No disruption to existing interviews
- Safe rollback if issues
- Test in production with new sessions

**Cons:**
- Maintain two codebases temporarily

### Option 2: Full Migration

1. Migrate all existing interviews to V2 format
2. Deprecate V1 immediately

**Pros:**
- Clean cut, no legacy code

**Cons:**
- Risky - might break existing interviews
- Need migration script for in-progress interviews

### Recommended: Parallel Deployment

**Timeline:**
- **Week 1-4:** Implement V2
- **Week 5:** Deploy V2, start new interviews with V2
- **Week 6-8:** Monitor and fix issues
- **Week 9:** Migrate existing interviews (if possible)
- **Week 10:** Deprecate V1

---

## Example: Gap-Based Interview Flow (V2)

```python
# User starts interview
session = ConversationalAgentV2.start_interview(
    candidate_id="cand_123",
    resume_text="...",
    mode="gap_based"
)

# Graph flow:
# 1. supervisor → gap_agent
#    - GapAgent analyzes resume
#    - Identifies: {"skill_name": "Python", "attribute": "duration"} gap
#    - Builds QuestionContext
# 2. gap_agent → question_generator
#    - Generates: "How long have you worked with Python?"
#    - Persists QuestionContext in state
# 3. question_generator → END (wait for answer)

# User answers: "3 years"
session = ConversationalAgentV2.continue_interview(
    thread_id=session["thread_id"],
    answer="3 years"
)

# Graph flow:
# 1. supervisor → parse_agent
#    - ParseAgent receives QuestionContext from state
#    - Calls extract_skill_attribute(answer="3 years", context={"skill_name": "Python", "attribute": "duration"})
#    - Tool extracts: {"name": "Python", "duration": "3 years"}  ✅
#    - Updates state: skill "Python" now has duration filled
#    - Marks gap as resolved
# 2. parse_agent → supervisor
# 3. supervisor → gap_agent
#    - Selects next gap
# 4. gap_agent → question_generator → END
```

---

## Example: Predefined Interview Flow (V2)

```python
# User starts predefined interview
session = ConversationalAgentV2.start_interview(
    candidate_id="cand_456",
    resume_text="...",
    mode="predefined",
    role_template="docs/Fullstack_developer_senior.md"
)

# Graph flow:
# 1. supervisor → guide_agent
#    - GuideAgent loads template
#    - Selects first question: "Can you briefly describe your current role..."
#    - Builds QuestionContext with template metadata
# 2. guide_agent → question_generator
#    - Generates question (potentially adapts based on resume)
# 3. question_generator → END

# User answers
session = ConversationalAgentV2.continue_interview(
    thread_id=session["thread_id"],
    answer="I'm a senior fullstack engineer at..."
)

# Graph flow:
# 1. supervisor → parse_agent
#    - ParseAgent extracts skills mentioned in answer
#    - Marks question as answered
#    - Assesses engagement
# 2. parse_agent → supervisor
# 3. supervisor → guide_agent
#    - Selects next question from template
# 4. guide_agent → question_generator → END
```

---

## Conclusion

The V2 architecture solves all identified problems:

1. **✅ Context Loss**: Explicit `QuestionContext` passed everywhere
2. **✅ Unknown Skills**: Tools receive skill name explicitly
3. **✅ Gap Resolution**: Deterministic matching using explicit context
4. **✅ Predefined Questions**: `GuideAgent` + template parser
5. **✅ Scalability**: Multi-agent supervisor pattern

**Next Steps:**
1. Review this architecture proposal
2. Approve implementation plan
3. Begin Phase 1 implementation
4. Test gap-based mode
5. Implement predefined mode
6. Deploy V2 in parallel with V1

This is a complete architectural overhaul that requires 4 weeks of focused development but delivers a robust, scalable, and maintainable interview system.
