# Conversational Agent Refactoring Plan

## Problem Summary

1. **Context Loss**: Tools don't receive explicit skill name/attribute, causing "unknown" skills
2. **Nested Agent Anti-Pattern**: Using `create_agent()` inside LangGraph nodes
3. **No Predefined Question Support**: Only gap-based interviews

## Solution: Clean LangGraph Workflow Pattern

### Core Principles (from LangGraph docs)

1. **Nodes are simple functions** - no nested agents
2. **Direct tool calls** - call tools explicitly, don't use ReAct pattern
3. **Direct LLM calls** - invoke LLM directly for generation
4. **Graph controls flow** - use conditional edges, not agent loops
5. **Explicit context** - pass all context to tools

---

## New Architecture

### State Schema

```python
class QuestionContext(TypedDict):
    """Explicit context for every question - KEY to solving context loss"""
    question_id: str
    question_text: str
    targets: Dict[str, Any]
    # For gap-based: {"skill_name": "Python", "attribute": "duration"}
    # For predefined: {"category": "Backend", "assesses": [...]}
    gap: Optional[Gap]  # The gap being addressed
```

### Unified Gap Model

Treat predefined questions as gaps too:

```python
class Gap(TypedDict):
    source: Literal["resume", "template"]
    category: str
    description: str
    severity: float

    # Resume gaps
    skill_name: Optional[str]
    attribute: Optional[str]

    # Template gaps
    question_id: Optional[str]
    template_metadata: Optional[Dict]
```

---

## Changes by File

### 1. `agents/conversational/state.py`

**Add:**
- `QuestionContext` TypedDict
- `current_question: Optional[QuestionContext]` to state
- Unified `Gap` with `source` field

### 2. `agents/conversational/nodes/parse_answer.py` ⭐ **CRITICAL**

**Before (WRONG):**
```python
def agent_node(state):
    agent = create_agent(llm, tools)  # ❌ Nested agent
    result = agent.invoke(...)
    return parse_result(result)
```

**After (CORRECT):**
```python
def parse_answer_node(state: InterviewState) -> Dict[str, Any]:
    """Parse answer - NO agent, direct tool calls with explicit context"""

    current_question = state["current_question"]
    answer = state["messages"][-1].content
    question = state["messages"][-2].content

    # Build EXPLICIT context
    gap_context = {
        "skill_name": current_question["targets"]["skill_name"],
        "attribute": current_question["targets"]["attribute"],
        "question": question,
        "answer": answer
    }

    # Direct tool call (not via agent!)
    skills = extract_skill_attribute(
        answer=answer,
        gap_context=json.dumps(gap_context)
    )

    engagement = assess_answer_engagement(
        question=question,
        answer=answer,
        gap_description=current_question["gap"]["description"]
    )

    return {
        "tool_results": {
            "skills": json.loads(skills),
            "engagement": json.loads(engagement)
        }
    }
```

### 3. `agents/conversational/nodes/generate_question.py` ⭐ **CRITICAL**

**Before (WRONG):**
```python
def generate_response_node(state):
    # Direct LLM call, but doesn't save question context
    response = llm.generate(prompt)
    return {"messages": [AIMessage(content=response)]}
```

**After (CORRECT):**
```python
def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """Generate question - direct LLM call, save question context"""

    current_gap = state["current_gap"]

    # Build question context BEFORE generating
    question_context = {
        "question_id": f"{current_gap['category']}_{uuid.uuid4()}",
        "targets": {
            "skill_name": current_gap["skill_name"],
            "attribute": current_gap["attribute"]
        },
        "gap": current_gap
    }

    # Generate question
    prompt = f"Ask about {current_gap['skill_name']}'s {current_gap['attribute']}"
    question_text = llm.generate(prompt)

    # Save BOTH question and context
    question_context["question_text"] = question_text

    return {
        "messages": [AIMessage(content=question_text)],
        "current_question": question_context  # ⭐ Save context!
    }
```

### 4. `agents/conversational/nodes/identify_gaps.py`

**Change:**
- Support loading gaps from resume OR template
- Unified gap format with `source` field

```python
def identify_gaps_node(state: InterviewState) -> Dict[str, Any]:
    """Load gaps from resume analysis OR predefined template"""

    mode = state.get("interview_mode", "gap_based")
    gaps = []

    # Resume gaps
    if mode in ["gap_based", "hybrid"]:
        resume_gaps = analyze_resume(state["resume_text"])
        for gap in resume_gaps:
            gap["source"] = "resume"
        gaps.extend(resume_gaps)

    # Template gaps
    if mode in ["predefined", "hybrid"]:
        template_gaps = load_template_gaps(state["role_template"])
        for gap in template_gaps:
            gap["source"] = "template"
        gaps.extend(template_gaps)

    return {"identified_gaps": gaps}
```

### 5. `agents/conversational/graph.py`

**Before (WRONG):**
```python
workflow.add_node("agent", agent_node)  # ❌ Confused name
workflow.add_edge("agent", "update_state")
```

**After (CORRECT):**
```python
workflow = StateGraph(InterviewState)

# Clear functional nodes
workflow.add_node("identify_gaps", identify_gaps_node)
workflow.add_node("parse_answer", parse_answer_node)
workflow.add_node("update_state", update_state_node)
workflow.add_node("select_gap", select_gap_node)
workflow.add_node("generate_question", generate_question_node)
workflow.add_node("finalize", finalize_node)

# Entry point
workflow.set_conditional_entry_point(is_first_run, {
    "first": "identify_gaps",
    "resume": "parse_answer"
})

# Clean edges
workflow.add_edge("identify_gaps", "select_gap")
workflow.add_edge("parse_answer", "update_state")
workflow.add_edge("update_state", "select_gap")
workflow.add_conditional_edges("select_gap", has_unresolved_gaps, {
    "yes": "generate_question",
    "no": "finalize"
})
workflow.add_edge("generate_question", END)
workflow.add_edge("finalize", END)
```

### 6. `tools/extraction_tools.py`

**Enhance with explicit context:**

```python
@tool
def extract_skill_attribute(answer: str, gap_context: str) -> str:
    """
    Extract skill attribute with EXPLICIT context.

    Args:
        answer: User's answer
        gap_context: JSON with {"skill_name", "attribute", "question", "answer"}

    Returns:
        JSON with skill data
    """
    context = json.loads(gap_context)

    # Now we KNOW the skill name!
    schema = {
        "type": "object",
        "properties": {
            "skill_name": {"type": "string"},
            context["attribute"]: {"type": "string"},
            "confidence": {"type": "number"},
            "evidence": {"type": "string"}
        }
    }

    system_prompt = f"""
    Extract {context['attribute']} for {context['skill_name']}.

    Question: {context['question']}
    Answer: {context['answer']}

    The skill_name is "{context['skill_name']}" - use this EXACTLY.
    """

    llm = LLMService()
    result = llm.generate_json(
        system_prompt=system_prompt,
        human_prompt="",
        schema=schema
    )

    # Ensure skill_name is correct
    result["skill_name"] = context["skill_name"]

    return json.dumps(result)
```

---

## Migration Steps

### Phase 1: State Schema (Week 1)
1. ✅ Add `QuestionContext` to state.py
2. ✅ Add `current_question: Optional[QuestionContext]` field
3. ✅ Update `Gap` to support both sources

### Phase 2: Nodes Refactor (Week 1)
1. ✅ Refactor `parse_answer_node` - remove agent, direct tool calls
2. ✅ Refactor `generate_question_node` - save question context
3. ✅ Update `identify_gaps_node` - support both sources

### Phase 3: Tools Enhancement (Week 1)
1. ✅ Add `gap_context` parameter to `extract_skill_attribute`
2. ✅ Update tool to use explicit skill name from context
3. ✅ Test with both gap types

### Phase 4: Graph Update (Week 2)
1. ✅ Update graph structure
2. ✅ Remove agent_node references
3. ✅ Test flow end-to-end

### Phase 5: Testing (Week 2)
1. ✅ Test gap-based interview
2. ✅ Test predefined question interview
3. ✅ Verify context is preserved
4. ✅ Verify "unknown" skills are fixed

---

## Success Criteria

✅ **No "unknown" skills** - All extracted skills have correct names
✅ **No nested agents** - Only direct tool/LLM calls in nodes
✅ **Support predefined questions** - Can load questions from template
✅ **Clean graph structure** - Clear workflow pattern from docs
✅ **Explicit context everywhere** - All tools receive full context

---

## Key Files to Change

Priority order:

1. **agents/conversational/state.py** - Add QuestionContext
2. **agents/conversational/nodes/parse_answer.py** - Remove agent, add direct calls
3. **agents/conversational/nodes/generate_question.py** - Save question context
4. **tools/extraction_tools.py** - Add gap_context parameter
5. **agents/conversational/graph.py** - Clean workflow structure
6. **agents/conversational/nodes/identify_gaps.py** - Support both sources

---

## Testing Plan

```python
# Test 1: Gap-based interview
session = ConversationalAgent.start_interview(
    candidate_id="test_1",
    resume_text="3 years Python experience",
    mode="gap_based"
)
# Should ask: "How long have you worked with Python?"

# User answers
session = ConversationalAgent.continue_interview(
    thread_id=session["thread_id"],
    answer="3 years"
)
# Should extract: {"skill_name": "Python", "duration": "3 years"} ✅
# NOT: {"skill_name": "unknown", "duration": "3 years"} ❌

# Test 2: Predefined questions
session = ConversationalAgent.start_interview(
    candidate_id="test_2",
    resume_text="...",
    mode="predefined",
    role_template="docs/Fullstack_developer_senior.md"
)
# Should ask first question from template
```
