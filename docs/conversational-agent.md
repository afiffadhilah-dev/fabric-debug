# Conversational Agent - Technical Interview System

## Overview

The Conversational Agent is a dynamic, AI-powered technical interview system that analyzes resumes and conducts adaptive skill assessments. It uses **LangGraph** for workflow orchestration and operates as a **gap-based interview** - asking questions only about missing information until it reaches sufficient completeness.

**Key Features:**
- Resume analysis to identify skill gaps
- Dynamic question generation based on missing attributes
- Engagement tracking to detect user disinterest
- Autonomous tool calling using ReAct pattern
- Persistent state management with PostgreSQL

---

## Architecture Components

### 1. **Main Agent** (`agent.py`)
The `ConversationalAgent` class provides the public API:

```python
# Start a new interview
agent.start_interview(candidate_id, resume_text)
# Returns: {session_id, thread_id, question}

# Continue with user's answer
agent.continue_interview(thread_id, answer)
# Returns: {question, completed, termination_reason}

# Get extracted skills
agent.get_extracted_skills(session_id)
# Returns: List of skills with 6 attributes
```

### 2. **State Management** (`state.py`)
The `InterviewState` tracks all conversation data:

**Core Data:**
- `session_id`: Database session identifier
- `resume_text`: Candidate's resume
- `messages`: Conversation history (AI questions + user answers)

**Gap Tracking:**
- `identified_gaps`: All gaps found in resume (missing skill attributes)
- `resolved_gaps`: Gaps that have been filled through conversation
- `current_gap`: The gap currently being addressed

**Skills & Engagement:**
- `extracted_skills`: Skills with 6 attributes (duration, depth, autonomy, scale, constraints, production_vs_prototype)
- `engagement_signals`: Track user engagement per answer
- `consecutive_low_quality`: Counter for disengaged answers

**Termination Logic:**
- `completeness_score`: 0.0-1.0 (how complete our understanding is)
- `should_continue`: Flag to continue or stop
- `termination_reason`: Why the interview ended

### 3. **Graph Workflow** (`graph.py`)
Uses LangGraph to orchestrate the interview flow with 6 nodes:

```
START → is_first_run? (conditional entry)
         ├─ Yes (first run) → identify_gaps
         └─ No (resuming) → agent_node
                              ↓
                         update_state
                              ↓
                      should_continue?
         ├─ Yes → select_gap → generate_response → END (wait for user)
         └─ No → finalize → END (interview complete)
```

---

## Interview Flow (Step by Step)

### **Phase 1: Start Interview**

**Step 1:** User calls `start_interview(candidate_id, resume_text)`

**Step 2:** Graph evaluates **is_first_run()** condition → routes to **identify_gaps**
- The conditional entry point checks if `messages` is empty (first run) or has content (resuming)
- Since this is the first run, it routes to **identify_gaps_node**:
  - Analyzes resume using `SkillAnalyzer`
  - Extracts technical skills with 6 attributes
  - Creates gaps for any attribute marked as "unknown"
  - Sorts gaps by severity (high → low)
  - Calculates initial completeness score

**Step 3:** **select_gap** picks highest-severity gap

**Step 4:** **generate_response** creates first question
- Loads prompt template from `prompts/shared/first_question.md`
- Generates natural, conversational opening question
- Saves question to database with metadata

**Step 5:** Returns first question to user

---

### **Phase 2: Continue Interview (User Answers)**

**Step 1:** User calls `continue_interview(thread_id, answer)`

**Step 2:** Graph evaluates **is_first_run()** condition → routes to **agent_node**
- The conditional entry point detects messages exist (resuming), so routes to **agent_node**
- **agent_node** processes the answer:
  - Gets tools from registry (currently: `analyze_technical_skills`)
  - Creates ReAct agent with LLM + tools
  - LLM autonomously decides which tools to call based on the answer
  - Tools extract skills and assess engagement
  - Returns tool results

**Step 3:** **update_state** consolidates results
- Merges new skills with existing skills
- Updates skill attributes (fills in "unknown" values)
- Tracks which attributes were newly added
- Checks if current gap is resolved
- Recalculates completeness score
- Updates engagement counter

**Step 4:** **should_continue_interview** checks termination conditions
- **Stop if:** 3+ consecutive disengaged answers
- **Stop if:** Completeness ≥ 60% (configurable)
- **Stop if:** No more gaps to explore
- **Continue:** Select next gap

**Step 5a (Continue):** **select_gap → generate_response**
- Picks next highest-severity unresolved gap
- Detects user intent (normal, clarification, example request, partial answer)
- Generates appropriate response type
- Returns next question

**Step 5b (Complete):** **finalize**
- Generates completion message
- Marks interview as complete
- Persists extracted skills to database
- Returns completion message

---

## Key Nodes Explained

### **identify_gaps_node** (agents/conversational/nodes/identify_gaps.py)
- Runs on first invocation only
- Uses `extract_skills_from_conversation()` to analyze resume
- Creates a `Gap` for each "unknown" skill attribute
- Returns: `{identified_gaps, extracted_skills, completeness_score}`

### **agent_node** (agents/conversational/nodes/agent_node.py)
- **Agentic Tool Calling** - LLM autonomously selects tools
- Builds conversation context from message history
- Creates ReAct agent with available tools
- LLM decides when to call `analyze_technical_skills`
- Parses tool results and validates with Pydantic
- Returns: `{tool_results, extracted_skills}`

### **update_state_node** (agents/conversational/nodes/update_state.py)
- Merges new skills with existing skills (smart merge)
- Detects which attributes are NEW information
- Checks if current gap is resolved
- Recalculates completeness score
- Updates engagement counter based on answer type
- Persists answer to database with metadata
- Returns: `{extracted_skills, engagement_signals, resolved_gaps, completeness_score, consecutive_low_quality}`

### **generate_response_node** (agents/conversational/nodes/generate_response.py)
- Detects user intent from conversation history
- Generates 4 types of responses:
  - **Question:** Normal interview question
  - **Explanation:** User confused, clarify question
  - **Example:** User asks for example
  - **Follow-up:** User gave partial/short answer
- Loads appropriate prompt template
- Increments gap probe counter
- Persists question to database
- Returns: `{messages, questions_asked, current_gap}`

### **finalize_node** (agents/conversational/nodes/finalize.py)
- Generates completion message based on termination reason
- Returns: `{should_continue: false, messages}`

### **select_gap_node** (agents/conversational/nodes/helpers.py)
- Selects next highest-severity unresolved gap that hasn't exceeded max probes
- Filters out resolved gaps and gaps that have been probed too many times
- Sorts remaining gaps by severity (highest first)
- Returns: `{current_gap: selected_gap}`

---

## Conditions (Routing Logic)

### **is_first_run** (conditions.py)
```python
if messages is empty:
    return "identify_gaps"  # First run - analyze resume
else:
    return "agent_node"     # Resuming - process answer
```

### **should_continue_interview** (conditions.py)
```python
if consecutive_low_quality >= 3:
    return "finalize"  # User disengaged
elif completeness_score >= minimum_completeness:
    return "finalize"  # Reached 60% completeness
elif no unresolved gaps:
    return "finalize"  # Nothing left to ask
else:
    return "select_gap"  # Continue interview
```

---

## Tools System

### **Tool Registry** (tools/registry.py)
Centralized registry for agent tools with agent-specific assignments.

### **Available Tools:**

**1. analyze_technical_skills** (tools/analysis_tools.py)
- **Purpose:** Extract skills with 6 attributes from candidate's answer
- **Input:** `answer_text`, `conversation_context`
- **Output:** JSON with skills array
- **Assigned to:** Conversational agent

Uses `SkillAnalyzer` which calls LLM with structured JSON schema to extract:
- Skill name
- 6 attributes: duration, depth, autonomy, scale, constraints, production_vs_prototype
- Evidence from text

### **Supporting Classes:**

**SkillAnalyzer** (tools/skill_analyzer.py)
- Uses `llm_service.generate_json()` for structured extraction
- Validates output against skill schema
- Returns list of skills with attributes

**AnswerAssessor** (tools/answer_assessor.py)
- Assesses answer engagement (currently NOT registered as tool)
- Used internally by nodes if needed
- Returns: answer_type, engagement_level, detail_score, relevance_score

---

## Database Persistence

### **State Checkpointing** (checkpointer.py)
- Uses LangGraph's `PostgresSaver` for state persistence
- Stores entire graph state in PostgreSQL
- Enables resume/pause conversations
- Singleton pattern for efficient connection pooling

### **Interview Data** (agent.py)
- **InterviewSession:** Stores session metadata, status, metrics
- **ExtractedSkill:** Persists final skills with all 6 attributes
- **Message:** Stores Q&A pairs with rich metadata (via MessageRepository)

---

## Configuration

### **Prompts** (prompts/conversational/ & prompts/shared/)
- `prompts/conversational/agent_analysis.md`: System prompt for agent_node
- `prompts/shared/first_question.md`: Opening question template
- `prompts/shared/question_generation.md`: Follow-up question template
- `prompts/shared/explanation.md`: Clarification template
- Uses `PromptLoader` for variable substitution

### **Settings**
- **Minimum Completeness:** 0.6 (60%) - configurable in state
- **Max Probes per Gap:** 3 attempts before giving up
- **Disengagement Threshold:** 3 consecutive low-quality answers

---

## Termination Conditions

The interview ends when ANY of these conditions is met:

1. **Disengaged:** 3+ consecutive disengaged answers
2. **Complete:** Completeness score ≥ 60%
3. **No Gaps:** All gaps resolved or exhausted max probes

---

## Example Flow Diagram

```
User: start_interview("candidate_123", resume_text)
  ↓
[identify_gaps_node]
  → Analyze resume
  → Find 5 skills: Python, React, AWS, Docker, PostgreSQL
  → Identify 12 gaps (missing attributes)
  → Completeness: 40%
  ↓
[select_gap]
  → Select: "Missing duration, scale for Python"
  ↓
[generate_response]
  → Question: "Hi! I see you have Python experience. How long have you been working with it?"
  ↓
Return to User ─────────────────────────────────┐
                                                 │
User: continue_interview(thread_id, answer) ←────┘
  "I've been using Python for 3 years professionally..."
  ↓
[agent_node]
  → LLM autonomously calls: analyze_technical_skills(answer)
  → Extracted: {name: "Python", duration: "3 years", scale: "enterprise-level", ...}
  ↓
[update_state]
  → Merge: Python.duration = "3 years" (was "unknown")
  → Merge: Python.scale = "enterprise-level" (was "unknown")
  → Gap RESOLVED ✓
  → Completeness: 55%
  → Engagement: "engaged"
  ↓
[should_continue_interview]
  → 55% < 60% → Continue
  → 11 gaps remaining
  ↓
[select_gap]
  → Select: "Missing depth, autonomy for React"
  ↓
[generate_response]
  → Question: "Great! What aspects of React have you worked with?"
  ↓
Return to User ─────────────────────────────────┐
                                                 │
... (continues until completeness ≥ 60% or disengaged)
```

---

## Summary

The Conversational Agent is a **smart, adaptive interview system** that:

1. **Analyzes** resumes to find skill gaps
2. **Asks** targeted questions to fill those gaps
3. **Adapts** to user engagement and completeness
4. **Extracts** structured skill data with 6 key attributes
5. **Stops** automatically when it has enough information

It uses LangGraph for orchestration, ReAct agents for autonomous tool calling, and PostgreSQL for state persistence. The result is a natural, efficient interview that respects the user's time while gathering comprehensive skill assessments.
