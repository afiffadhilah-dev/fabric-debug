# Code Investigation - Predefined Questions Mode Analysis

## Summary

The `predefined_questions` mode has several incomplete implementations that cause:
1. No skill/criteria extraction (database gets zero ExtractedSkill records)
2. Nonsensical follow-up questions (templates designed for dynamic_gap mode)
3. Overly strict gap resolution (binary: perfect answer or unresolved)
4. Hardcoded completeness threshold (90%) that may be too high

---

## CRITICAL ISSUES

### Issue #1: Missing Criteria Assessment
**File:** `agents/conversational/nodes/parse_answer.py` (lines 79-83)

**Code:**
```python
if mode == "predefined_questions":
    # PREDEFINED MODE: Do NOT extract technical skills
    # Predefined questions assess criteria (leadership, design process, etc.)
    # NOT technical skills with 6 attributes
    print(f"⏭️  Predefined mode: Skipping skill extraction (assessing criteria instead)")
```

**Problem:**
- Comment says "assessing criteria instead" but NO actual criteria assessment code exists
- `skills_list = []` is returned, so no data is extracted
- At end of interview, `service.py:258` persists ZERO ExtractedSkill records
- The entire interview produces no structured output for predefined mode

**Impact:** HIGH - predefined_questions mode produces no usable data

**Action needed:** Either:
1. Implement criteria assessment (extract what_assesses values from answers)
2. Or reuse skill extraction with modified schema for criteria
3. Or create new CriteriaAssessment model/table for predefined mode results

---

### Issue #2: Follow-up Questions Semantically Wrong
**Files:**
- `agents/conversational/nodes/generate_follow_up.py` (lines 44-45, 78-85)
- `agents/conversational/nodes/generate_question.py` (lines 60-61)

**Code in generate_question.py:**
```python
question_context: QuestionContext = {
    "question_id": current_gap.get("question_id", str(uuid.uuid4())),
    "question_text": question_text,
    "skill_name": category,  # Use category as skill_name for predefined mode  ❌
    "attribute": ", ".join(what_assesses),  # Combine what_assesses as attribute  ❌
    "gap_description": question_text
}
```

**Code in generate_follow_up.py:**
```python
skill_name = current_question["skill_name"]  # = "LEADERSHIP EXPERIENCE"
attribute = current_question["attribute"]    # = "People leadership, Decision-making"

system_context = prompt_loader.load(
    "follow_up_probe",
    mode="conversational",
    user_answer=user_answer,
    original_question=original_question,
    attribute=attribute,      # ❌ "People leadership, Decision-making"
    skill_name=skill_name     # ❌ "LEADERSHIP EXPERIENCE"
)
```

**Problem:**
- `skill_name` is set to `category` (e.g., "LEADERSHIP EXPERIENCE")
- `attribute` is set to `what_assesses` joined (e.g., "People leadership, Decision-making")
- Follow-up templates (`follow_up_probe.md`) use these like: "Tell me more about {skill_name}'s {attribute}"
- Result: "Tell me more about LEADERSHIP EXPERIENCE's People leadership, Decision-making"
- This is grammatically and semantically nonsensical

**Impact:** HIGH - follow-up questions don't make sense

**Action needed:**
1. Create separate follow-up templates for predefined mode
2. Or modify QuestionContext to store predefined-specific fields
3. Follow-up should reference the original question and ask for more details/examples

---

### Issue #3: Gap Resolution Too Strict
**File:** `agents/conversational/nodes/update_state.py` (lines 325-346)

**Code:**
```python
if mode == "predefined_questions":
    # PREDEFINED MODE: Resolve current gap if answer was good
    if current_gap:
        if not already_resolved:
            # Resolve if: direct answer, engaged, and sufficient detail
            if (answer_type == "direct_answer" and
                engagement_level == "engaged" and
                detail_score >= 3):                    # ❌ All 3 conditions required
                resolved_gaps.append(current_gap)
            else:
                print(f"  -> ⏳ Current gap still open: {current_gap_id}")
```

**Problem:**
- Resolution requires ALL THREE conditions: direct_answer AND engaged AND detail_score >= 3
- If user gives a decent but brief answer (detail_score = 2), gap stays unresolved
- This triggers follow-up → but follow-up templates are broken (Issue #2)
- User may answer the same question multiple times with no resolution

**Impact:** MEDIUM - interviews take too long, poor user experience

**Action needed:**
1. Lower threshold for predefined mode (e.g., detail_score >= 2)
2. Or make resolution progressive (partial → resolved after 2 attempts)
3. Or track partial resolution with scoring

---

## MEDIUM ISSUES

### Issue #4: Hardcoded Completeness Threshold
**File:** `agents/conversational/state.py` (line 285 or state defaults)
**File:** `agents/conversational/conditions.py` (line 47)

**Code in conditions.py:**
```python
minimum_completeness = state.get("minimum_completeness", 0.6)  # Default 0.6 but...
```

**Problem:**
- Default `minimum_completeness` may be 0.9 (90%) based on investigation
- For a 34-question set, user must answer 31 questions to reach 90%
- No way to configure threshold per question set
- Early termination at 60% may cut interview short

**Impact:** MEDIUM - interview length not controllable

**Action needed:**
1. Make minimum_completeness configurable per question_set
2. Or add to StartInterviewRequest parameters
3. Consider different defaults for predefined (e.g., 0.7) vs dynamic (0.6)

---

### Issue #5: Empty Resume Not Handled Gracefully
**File:** `agents/conversational/nodes/analyze_resume_coverage.py`

**Current behavior:**
- If resume_text is empty/"N/A", LLM analyzes "" against all questions
- Result: All questions marked as NOT answered by resume
- All questions added to `identified_gaps`
- Interview proceeds with all questions sequentially by severity

**Problem:**
- No warning logged that resume is empty
- No adjustment to interview strategy
- Could skip resume analysis entirely for empty resume (save 1 LLM call)

**Impact:** LOW - works correctly but not optimized

**Action needed:**
1. Add early check for empty resume
2. Skip batch LLM call if resume empty (all questions → gaps)
3. Optionally log warning or adjust completeness calculation

---

### Issue #6: No Criteria Tracking in Database
**Current state:**
- `ExtractedSkill` model has 6 attributes: duration, depth, autonomy, scale, constraints, production_vs_prototype
- These are for dynamic_gap mode skill extraction
- Predefined questions assess different criteria: leadership, design process, communication, etc.
- No model exists to store predefined question assessment results

**Impact:** HIGH for predefined mode usefulness

**Action needed:**
1. Create `CriteriaAssessment` model or reuse `ExtractedSkill` with different semantics
2. Define what data to extract from predefined question answers
3. Update parse_answer.py to populate this data

---

## FLOW DIAGRAM: Predefined Questions Mode

```
START
  │
  ▼
┌─────────────────────────────────┐
│ is_first_run()                  │
│ mode == "predefined_questions"  │
│ && messages.empty?              │
└─────────────────────────────────┘
  │ YES
  ▼
┌─────────────────────────────────┐
│ analyze_resume_coverage_node    │
│ • Fetch all questions from DB   │
│ • Batch LLM: which answered?    │
│ • Create PredefinedGap objects  │
│ • Filter to unanswered only     │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ select_gap_node                 │
│ • Sort by severity              │
│ • Pick highest priority gap     │
│ • Set current_gap               │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ generate_question_node          │
│ • mode == predefined?           │
│   → Use question_text directly  │  ✅ Works
│ • Save QuestionContext          │
│   → skill_name = category       │  ❌ Wrong field mapping
│   → attribute = what_assesses   │  ❌ Wrong field mapping
└─────────────────────────────────┘
  │
  ▼
  END (wait for user answer)

=== User answers ===

  │
  ▼
┌─────────────────────────────────┐
│ parse_answer_node               │
│ • assess_answer_engagement()    │  ✅ Works
│ • mode == predefined?           │
│   → Skip skill extraction       │  ❌ No criteria assessment
│   → skills_list = []            │  ❌ No data extracted
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ update_state_node               │
│ • Check gap resolution          │
│   → Requires: direct_answer     │
│   → AND engaged                 │
│   → AND detail_score >= 3       │  ❌ Too strict
│ • Calculate completeness        │  ✅ Works
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ should_follow_up()              │
│ • answer_type == clarification? │
│   → generate_follow_up          │
│ • detail_score < 3 && !resolved?│
│   → generate_follow_up          │  ❌ Uses wrong templates
│ • else → should_continue_interview│
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ should_continue_interview()     │
│ • consecutive_low_quality >= 3? │
│   → finalize                    │  ✅ Works
│ • completeness >= threshold?    │
│   → finalize                    │  ⚠️ Threshold hardcoded
│ • no available gaps?            │
│   → finalize                    │  ✅ Works
│ • else → select_gap             │
└─────────────────────────────────┘
```

---

## FILES TO MODIFY

| Priority | File | Changes Needed |
|----------|------|----------------|
| P0 | `nodes/parse_answer.py` | Add criteria assessment for predefined mode |
| P0 | `nodes/generate_follow_up.py` | Add mode-aware template selection |
| P0 | `prompts/conversational/` | Create predefined-specific follow-up templates |
| P1 | `nodes/update_state.py` | Relax gap resolution for predefined mode |
| P1 | `nodes/generate_question.py` | Fix QuestionContext field mapping |
| P2 | `state.py` | Add configurable minimum_completeness |
| P2 | `nodes/analyze_resume_coverage.py` | Handle empty resume gracefully |
| P3 | `models/` | Consider CriteriaAssessment model |

---

## RECOMMENDED SOLUTIONS

### Solution #1: Criteria Assessment (for Issue #1)

**Approach: Score-based extraction with evidence snippets**

Create new `assess_criteria()` tool in `extraction_tools.py` that extracts:

```python
{
    "answer_quality": 4,  # 1-5 overall score
    "criteria_assessed": [
        {"criterion": "People leadership", "demonstrated": true, "evidence": "Led team of 5..."},
        {"criterion": "Decision-making", "demonstrated": true, "evidence": "Chose to prioritize..."}
    ]
}
```

**Why this approach:**
- Reuses existing `assess_answer_engagement()` pattern (already does LLM scoring)
- Captures structured data for each `what_assesses` criterion
- Evidence snippets allow human review without re-reading full transcript
- No new database model needed - store in `Message.meta` (already used for engagement data)

---

### Solution #2: Follow-up Questions (for Issue #2)

**Approach: Simple mode-aware templates**

For predefined mode, follow-ups should be generic probes, not skill-attribute based:

| Scenario | Follow-up Template |
|----------|-------------------|
| Vague answer | "Could you give me a specific example?" |
| Brief answer | "Can you tell me more about that experience?" |
| Clarification request | Answer the clarification, then re-ask |

**Why:**
- Predefined questions are already well-crafted - no need to generate new questions
- Simple probes work universally across all question categories
- Avoids the semantic mismatch with `skill_name`/`attribute`

---

### Solution #3: Gap Resolution (for Issue #3)

**Approach: Progressive resolution with attempt-based fallback**

```python
# In update_state.py for predefined mode:
if mode == "predefined_questions":
    probes_attempted = current_gap.get("probes_attempted", 0)

    # Resolve if: good answer OR we've tried enough
    should_resolve = (
        (answer_quality >= 3) or                    # Good enough answer
        (probes_attempted >= 2 and answer_quality >= 2) or  # Decent after 2 tries
        (probes_attempted >= max_probes)            # Max attempts reached
    )
```

**Why:**
- Prevents infinite loops on the same question
- Respects user's time - move on after reasonable attempts
- Still captures the data even if answer wasn't perfect

---

### Solution #4: Database Storage (for Issue #6)

**Approach: Use existing `Message.meta` - no new model**

The `Message` model already stores rich metadata per Q&A pair. Just add criteria assessment:

```python
meta = {
    # ... existing fields ...
    "criteria_assessed": criteria_result,  # Add this for predefined mode
}
```

**Why:**
- No migration needed
- Data stays with the answer it came from
- Easy to query per-session with existing MessageRepository

---

## UNIFIED IMPLEMENTATION PLAN

### Phase 0: Immediate Fixes (Prerequisites)

These fixes make predefined_questions mode work correctly. Required before stage flow.

| Step | Task | File(s) | Effort |
|------|------|---------|--------|
| 0.1 | Create `assess_criteria()` tool | `tools/extraction_tools.py` | Medium |
| 0.2 | Update `parse_answer.py` to call `assess_criteria()` | `nodes/parse_answer.py` | Low |
| 0.3 | Create predefined-specific follow-up templates | `prompts/conversational/` | Low |
| 0.4 | Add mode check in `generate_follow_up.py` | `nodes/generate_follow_up.py` | Low |
| 0.5 | Update gap resolution logic (relax for predefined) | `nodes/update_state.py` | Low |
| 0.6 | Fix `QuestionContext` field mapping | `nodes/generate_question.py` | Low |
| 0.7 | Store criteria in `Message.meta` | `nodes/update_state.py` | Low |

### Phase 1-5: Stage-Based Flow (Enhancement)

Adds full flow control system. See "STAGE-BASED INTERVIEW FLOW" section below for details.

---

## DESIGN DECISIONS (Confirmed)

| Aspect | Decision |
|--------|----------|
| **Criteria Assessment** | Extract `answer_quality` (1-5) + per-criterion `{demonstrated, evidence}` |
| **Follow-ups** | Simple generic probes: "Can you give an example?" |
| **Gap Resolution** | Resolve after good answer OR 2 attempts with decent answer |
| **Storage** | Use `Message.meta` - no new model needed |
| **Completeness Threshold** | Keep 0.6 default but make configurable via API |

---

## STAGE-BASED INTERVIEW FLOW (Option B - Full Implementation)

### Overview

Implement a stage-based conversation flow system similar to lead generation agents, giving full control over interview pacing, tone, and question prioritization.

### Stage Definitions

```python
from enum import Enum

class InterviewStage(str, Enum):
    WARM_UP = "warm_up"       # Build rapport, easy questions
    DEEP_DIVE = "deep_dive"   # Core questions, full probing
    WRAP_UP = "wrap_up"       # Final critical questions
    CLOSING = "closing"       # Thank candidate, next steps
```

### Stage Characteristics

| Stage | Purpose | Tone | Probe Limit | Question Priority |
|-------|---------|------|-------------|-------------------|
| **WARM_UP** | Build rapport, ease in | Friendly, casual | 1 | Low priority first |
| **DEEP_DIVE** | Core assessment | Professional, probing | 3 | High priority |
| **WRAP_UP** | Cover remaining critical | Efficient, focused | 1 | Required only |
| **CLOSING** | End gracefully | Grateful, encouraging | 0 | N/A |

### Stage-Specific System Prompts

```
prompts/conversational/
├── system.md                    # Base system prompt
├── stage_warm_up.md             # Friendly, build rapport
├── stage_deep_dive.md           # Professional, probe deeply
├── stage_wrap_up.md             # Efficient, respect time
└── stage_closing.md             # Grateful, next steps
```

**Example: stage_warm_up.md**
```markdown
You are conducting the opening of an interview. Your goal is to:
- Make the candidate comfortable
- Ask easier, rapport-building questions
- Keep responses warm and encouraging
- Don't probe too deeply yet - save that for later

Tone: Friendly, conversational, welcoming
```

**Example: stage_deep_dive.md**
```markdown
You are in the core assessment phase. Your goal is to:
- Ask critical questions about key competencies
- Probe for specific examples and details
- Challenge vague answers with follow-ups
- Extract concrete evidence for each criterion

Tone: Professional, curious, thorough
```

### Interview Configuration Schema

```python
class StageConfig(TypedDict):
    """Configuration for a single interview stage."""
    question_range: Tuple[int, int]      # e.g., (1, 3) = questions 1-3
    priority_filter: str                  # "low", "medium", "high", "required"
    probe_limit: int                      # Max follow-ups per question
    system_prompt: str                    # Prompt template name
    triggers: Optional[List[StageTrigger]]  # Auto-transition triggers


class StageTrigger(TypedDict):
    """Trigger condition for automatic stage transition."""
    type: str       # "time_elapsed", "completeness", "question_count", "low_engagement"
    value: float    # Threshold value
    operator: str   # ">=", "<=", "=="


class InterviewConfig(TypedDict):
    """Full interview configuration with stages."""
    target_duration_minutes: int          # e.g., 45
    max_questions: int                    # e.g., 20
    stages: Dict[str, StageConfig]        # Stage configurations
    default_stage: str                    # Starting stage
```

### Example Configuration

```python
STANDARD_45_MIN_CONFIG: InterviewConfig = {
    "target_duration_minutes": 45,
    "max_questions": 20,

    "stages": {
        "warm_up": {
            "question_range": (1, 3),
            "priority_filter": "low",
            "probe_limit": 1,
            "system_prompt": "stage_warm_up",
            "triggers": None  # No auto-trigger, ends after question 3
        },
        "deep_dive": {
            "question_range": (4, 15),
            "priority_filter": "high",
            "probe_limit": 3,
            "system_prompt": "stage_deep_dive",
            "triggers": [
                {"type": "time_elapsed", "value": 35, "operator": ">="},
                {"type": "completeness", "value": 0.7, "operator": ">="},
                {"type": "low_engagement", "value": 2, "operator": ">="}
            ]
        },
        "wrap_up": {
            "question_range": (16, 20),
            "priority_filter": "required",
            "probe_limit": 1,
            "system_prompt": "stage_wrap_up",
            "triggers": [
                {"type": "question_count", "value": 20, "operator": ">="},
                {"type": "time_elapsed", "value": 43, "operator": ">="}
            ]
        },
        "closing": {
            "question_range": (0, 0),  # No questions
            "priority_filter": None,
            "probe_limit": 0,
            "system_prompt": "stage_closing",
            "triggers": None  # Always auto-triggered at end
        }
    },

    "default_stage": "warm_up"
}
```

### Updated State Schema

```python
# Add to InterviewState in state.py:

class InterviewState(TypedDict):
    # ... existing fields ...

    # ============================================================================
    # STAGE-BASED FLOW CONTROL
    # ============================================================================
    current_stage: str
    """Current interview stage: warm_up, deep_dive, wrap_up, closing"""

    interview_config: InterviewConfig
    """Stage configuration for this interview"""

    stage_start_time: Optional[float]
    """Timestamp when current stage started (for time-based triggers)"""

    interview_start_time: float
    """Timestamp when interview started"""

    stage_question_count: int
    """Questions asked in current stage"""
```

### Updated Graph Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGE-AWARE INTERVIEW GRAPH                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  START                                                                      │
│    │                                                                        │
│    ▼                                                                        │
│  ┌─────────────────┐                                                        │
│  │ is_first_run?   │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│     ┌─────┴─────┐                                                          │
│     ▼           ▼                                                          │
│  ┌──────────┐ ┌─────────────────────┐                                      │
│  │ init_gaps│ │ parse_answer        │◄──────────────────────┐              │
│  └────┬─────┘ └──────────┬──────────┘                       │              │
│       │                  │                                   │              │
│       │                  ▼                                   │              │
│       │         ┌─────────────────┐                          │              │
│       │         │ update_state    │                          │              │
│       │         └────────┬────────┘                          │              │
│       │                  │                                   │              │
│       │                  ▼                                   │              │
│       │         ┌─────────────────┐                          │              │
│       │         │ check_stage_    │  ◄── NEW: Stage          │              │
│       │         │ transition      │      transition logic    │              │
│       │         └────────┬────────┘                          │              │
│       │                  │                                   │              │
│       ▼                  ▼                                   │              │
│  ┌────────────────────────────────┐                          │              │
│  │      should_continue?          │                          │              │
│  └──────────────┬─────────────────┘                          │              │
│                 │                                            │              │
│      ┌──────────┼──────────┐                                 │              │
│      ▼          ▼          ▼                                 │              │
│  ┌───────┐ ┌─────────┐ ┌─────────┐                          │              │
│  │select │ │ closing │ │finalize │                          │              │
│  │ _gap  │ │ _node   │ │         │                          │              │
│  └───┬───┘ └────┬────┘ └────┬────┘                          │              │
│      │          │           │                                │              │
│      ▼          │           │                                │              │
│  ┌────────────┐ │           │                                │              │
│  │ generate_  │ │           │                                │              │
│  │ question   │ │           │                                │              │
│  │ (stage-    │ │           │                                │              │
│  │  aware)    │ │           │                                │              │
│  └─────┬──────┘ │           │                                │              │
│        │        │           │                                │              │
│        ▼        ▼           ▼                                │              │
│      END ◄──────┴───────────┘                                │              │
│        │                                                     │              │
│        │ (User answers)                                      │              │
│        └─────────────────────────────────────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### New/Modified Nodes

#### 1. `check_stage_transition_node` (NEW)

```python
def check_stage_transition_node(state: InterviewState) -> Dict[str, Any]:
    """
    Check if stage transition triggers are met and update stage.

    Evaluates triggers:
    - time_elapsed: Minutes since interview start
    - completeness: Current completeness score
    - question_count: Total questions asked
    - low_engagement: Consecutive disengaged answers

    Returns:
        State updates with new current_stage if transition needed
    """
    config = state.get("interview_config")
    current_stage = state.get("current_stage")
    current_config = config["stages"][current_stage]

    # Check question range (stage ends when max reached)
    questions_asked = state.get("questions_asked", 0)
    question_range = current_config["question_range"]

    if questions_asked >= question_range[1]:
        return transition_to_next_stage(state, config)

    # Check triggers
    triggers = current_config.get("triggers", [])
    for trigger in triggers:
        if evaluate_trigger(state, trigger):
            return transition_to_next_stage(state, config)

    return {}  # No transition
```

#### 2. `select_gap_node` (MODIFIED)

```python
def select_gap_node(state: InterviewState) -> Dict[str, Any]:
    """
    Select next gap based on current stage priority filter.

    Stage-aware selection:
    - WARM_UP: Pick low-priority questions first
    - DEEP_DIVE: Pick high-priority questions
    - WRAP_UP: Pick required questions only
    """
    current_stage = state.get("current_stage")
    config = state.get("interview_config")
    stage_config = config["stages"][current_stage]

    priority_filter = stage_config["priority_filter"]

    # Filter gaps by priority
    available_gaps = filter_gaps_by_priority(
        state.get("identified_gaps", []),
        state.get("resolved_gaps", []),
        priority_filter
    )

    # Sort by severity within priority
    available_gaps.sort(key=lambda g: g.get("severity", 0), reverse=True)

    if not available_gaps:
        return {"current_gap": None}

    return {"current_gap": available_gaps[0]}
```

#### 3. `generate_question_node` (MODIFIED)

```python
def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate question using stage-specific system prompt.
    """
    current_stage = state.get("current_stage")
    config = state.get("interview_config")
    stage_config = config["stages"][current_stage]

    # Load stage-specific system prompt
    prompt_name = stage_config["system_prompt"]
    system_prompt = prompt_loader.load(prompt_name, mode="conversational")

    # ... rest of question generation with stage-aware prompt
```

#### 4. `closing_node` (NEW)

```python
def closing_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate closing message and end interview gracefully.

    - Thanks candidate for their time
    - Summarizes what was discussed (optional)
    - Provides next steps information
    """
    prompt_loader = PromptLoader()
    llm = LLMService()

    system_prompt = prompt_loader.load("stage_closing", mode="conversational")

    closing_context = prompt_loader.load(
        "closing_message",
        mode="conversational",
        questions_asked=state.get("questions_asked", 0),
        completeness=state.get("completeness_score", 0),
        duration_minutes=calculate_duration(state)
    )

    closing_message = llm.generate(
        prompt=closing_context,
        system_prompt=system_prompt
    )

    return {
        "messages": [AIMessage(content=closing_message)],
        "current_stage": "closing",
        "termination_reason": "complete"
    }
```

### Stage Transition Condition

```python
def should_continue_or_transition(state: InterviewState) -> Literal[
    "select_gap", "closing", "finalize"
]:
    """
    Determine next step based on stage and triggers.

    Returns:
        - "select_gap": Continue with next question
        - "closing": Transition to closing stage
        - "finalize": End immediately (disengaged)
    """
    current_stage = state.get("current_stage")

    # Check for disengagement (immediate finalize)
    if state.get("consecutive_low_quality", 0) >= 3:
        return "finalize"

    # Check if we should move to closing
    if current_stage == "wrap_up":
        if no_more_required_questions(state):
            return "closing"

    # Check completeness
    if state.get("completeness_score", 0) >= state.get("minimum_completeness", 0.6):
        return "closing"

    # Check if no gaps available for current stage
    if no_gaps_for_stage(state):
        if current_stage == "closing":
            return "finalize"
        return "closing"  # Transition to closing

    return "select_gap"
```

### Database Changes

#### Add to `InterviewSession` model:

```python
class InterviewSession(SQLModel, table=True):
    # ... existing fields ...

    # Stage tracking
    current_stage: Optional[str] = Field(default="warm_up")
    interview_config: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    started_at: datetime = Field(default_factory=datetime.utcnow)
```

#### Add to `QuestionSet` model (or create if not exists):

```python
class QuestionSet(SQLModel, table=True):
    # ... existing fields ...

    # Default interview config for this question set
    default_config: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    target_duration_minutes: int = Field(default=45)
```

### API Changes

#### Update `StartInterviewRequest`:

```python
class StartInterviewRequest(BaseModel):
    candidate_id: str
    resume_text: str
    mode: InterviewMode = InterviewMode.DYNAMIC_GAP
    question_set_id: Optional[UUID] = None

    # NEW: Stage configuration
    interview_config: Optional[InterviewConfig] = None  # Override question set default
    target_duration_minutes: Optional[int] = None       # Quick override
```

### Priority Tags for Questions

Add `priority` field to `PredefinedQuestion` model:

```python
class QuestionPriority(str, Enum):
    LOW = "low"           # Warm-up questions
    MEDIUM = "medium"     # Standard questions
    HIGH = "high"         # Critical questions
    REQUIRED = "required" # Must-ask questions


class PredefinedQuestion(SQLModel, table=True):
    # ... existing fields ...

    priority: str = Field(default="medium")  # QuestionPriority value
```

### Implementation Order

| Phase | Tasks | Files |
|-------|-------|-------|
| **Phase 1: Foundation** | | |
| 1.1 | Add stage fields to `InterviewState` | `state.py` |
| 1.2 | Add `InterviewConfig` types | `state.py` |
| 1.3 | Add `current_stage` to `InterviewSession` model | `models/interview_session.py` |
| 1.4 | Create migration for new fields | `migrations/` |
| **Phase 2: Stage Logic** | | |
| 2.1 | Create `check_stage_transition_node` | `nodes/check_stage_transition.py` |
| 2.2 | Create `closing_node` | `nodes/closing.py` |
| 2.3 | Modify `select_gap_node` for priority filter | `nodes/select_gap.py` |
| 2.4 | Modify `generate_question_node` for stage prompts | `nodes/generate_question.py` |
| **Phase 3: Prompts** | | |
| 3.1 | Create `stage_warm_up.md` | `prompts/conversational/` |
| 3.2 | Create `stage_deep_dive.md` | `prompts/conversational/` |
| 3.3 | Create `stage_wrap_up.md` | `prompts/conversational/` |
| 3.4 | Create `stage_closing.md` | `prompts/conversational/` |
| **Phase 4: Graph** | | |
| 4.1 | Update `graph.py` with new nodes | `graph.py` |
| 4.2 | Add stage transition edges | `graph.py` |
| 4.3 | Update conditions | `conditions.py` |
| **Phase 5: API** | | |
| 5.1 | Update `StartInterviewRequest` | `api/routes/interview.py` |
| 5.2 | Update service layer | `service.py` |
| 5.3 | Add priority to questions | `models/predefined_question.py` |

### Default Configurations

```python
# configs/interview_configs.py

QUICK_SCREEN_30_MIN = {
    "target_duration_minutes": 30,
    "max_questions": 12,
    "stages": {
        "warm_up": {"question_range": (1, 2), "priority_filter": "low", "probe_limit": 1},
        "deep_dive": {"question_range": (3, 10), "priority_filter": "high", "probe_limit": 2},
        "wrap_up": {"question_range": (11, 12), "priority_filter": "required", "probe_limit": 1},
        "closing": {"question_range": (0, 0), "priority_filter": None, "probe_limit": 0}
    },
    "default_stage": "warm_up"
}

STANDARD_45_MIN = {
    "target_duration_minutes": 45,
    "max_questions": 20,
    "stages": {
        "warm_up": {"question_range": (1, 3), "priority_filter": "low", "probe_limit": 1},
        "deep_dive": {"question_range": (4, 15), "priority_filter": "high", "probe_limit": 3},
        "wrap_up": {"question_range": (16, 20), "priority_filter": "required", "probe_limit": 1},
        "closing": {"question_range": (0, 0), "priority_filter": None, "probe_limit": 0}
    },
    "default_stage": "warm_up"
}

DEEP_DIVE_60_MIN = {
    "target_duration_minutes": 60,
    "max_questions": 25,
    "stages": {
        "warm_up": {"question_range": (1, 4), "priority_filter": "low", "probe_limit": 1},
        "deep_dive": {"question_range": (5, 20), "priority_filter": "high", "probe_limit": 3},
        "wrap_up": {"question_range": (21, 25), "priority_filter": "required", "probe_limit": 2},
        "closing": {"question_range": (0, 0), "priority_filter": None, "probe_limit": 0}
    },
    "default_stage": "warm_up"
}
```

