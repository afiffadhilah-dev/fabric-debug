# Two-Mode Interview System - Implementation Plan

**Date:** 2026-01-13
**Last Updated:** 2026-01-13 (Enhanced based on technical review)
**Author:** Planning for dual-mode interview system
**Status:** Draft v2 - Ready for Approval

---

## Executive Summary

This document outlines the plan to extend the current conversational interview agent to support two distinct interview modes:

1. **Mode 1: Dynamic Gap-Based Interview** (Already Implemented)
   - Analyzes resume to extract skills with 6 attributes
   - Identifies gaps where attributes are marked as "unknown"
   - Dynamically generates questions to fill gaps
   - Adapts based on user engagement

2. **Mode 2: Structured Predefined Questions Interview** (New)
   - Uses predefined question sets from the database
   - Extracts gaps from the `what_assesses` criteria in each question
   - Attempts to fill gaps from resume before asking
   - Only asks questions where resume cannot provide answers
   - Maintains engagement tracking and adaptive flow

---

## Current System Analysis

### Existing Conversational Agent Architecture

**Components:**
- `agents/conversational/graph.py` - LangGraph workflow (7 nodes, conditional routing)
- `agents/conversational/service.py` - Service layer (DB operations, observability)
- `agents/conversational/state.py` - State definition (`InterviewState` TypedDict)
- `agents/conversational/nodes/` - Individual processing nodes
- `agents/conversational/conditions.py` - Routing conditions
- `agents/conversational/checkpointer.py` - PostgreSQL state persistence

**Current Flow:**
```
START → is_first_run?
  ├─ First run → identify_gaps → select_gap → generate_question → END
  └─ Resume → parse_answer → update_state → should_follow_up?
                                    ├─ Follow up → generate_follow_up → END
                                    └─ Move on → select_gap/finalize
```

**Current Gap Extraction Logic (`identify_gaps_node`):**
1. Calls `extract_skills_from_conversation()` tool
2. For each skill, checks if 6 attributes are "unknown"
3. Creates `Gap` objects for missing attributes
4. Sorts gaps by severity
5. Calculates completeness score

### Predefined Questions System

**Database Models:**
- `PredefinedRole` - Job roles (e.g., "Fullstack Developer", level: "Senior")
- `PredefinedQuestionSet` - Versioned question collections per role
- `PredefinedQuestion` - Individual questions with metadata

**Question Structure:**
```python
{
  "id": UUID,
  "category": str,  # e.g., "LEADERSHIP EXPERIENCE", "MOBILE DEVELOPMENT"
  "question_text": str,  # The actual question
  "what_assesses": List[str],  # Assessment criteria (gaps to evaluate)
  "expected_answer_pattern": Optional[str],  # Expected answer guidance
  "order": int,  # Sequence in the question set
  "is_required": bool  # Whether question must be asked
}
```

**Example Question:**
```json
{
  "category": "LEADERSHIP EXPERIENCE",
  "question_text": "What leadership experience do you have, and how have you led or mentored others?",
  "what_assesses": [
    "People leadership vs. individual contribution",
    "Coaching and decision-making skills"
  ],
  "expected_answer_pattern": "A strong candidate describes mentoring, code/design reviews, how many people they led, decision ownership, conflict resolution, and enabling team performance rather than just holding a title.",
  "order": 1,
  "is_required": true
}
```

---

## Component Reuse Strategy

Understanding which components are shared vs. mode-specific is critical for implementation efficiency.

### Node Reuse Matrix

| Component | Mode 1 (Dynamic) | Mode 2 (Predefined) | Shared? | Notes |
|-----------|------------------|---------------------|---------|-------|
| **identify_gaps_node** | ✅ Used | ❌ Not used | ❌ Mode-specific | Extracts skills from resume |
| **analyze_resume_coverage_node** | ❌ Not used | ✅ Used | ❌ Mode-specific | Analyzes resume vs. questions |
| **select_gap_node** | ✅ Used | ✅ Used | ✅ **Shared** | Works with both gap types |
| **generate_question_node** | ✅ Used | ✅ Used | ✅ **Shared** | Mode-aware (dynamic vs. predefined text) |
| **parse_answer_node** | ✅ Used | ✅ Used | ✅ **Shared** | Extracts skills from answer |
| **update_state_node** | ✅ Used | ✅ Used | ✅ **Shared** | Updates gaps, completeness |
| **generate_follow_up_node** | ✅ Used | ✅ Used | ✅ **Shared** | Generates clarification questions |
| **finalize_node** | ✅ Used | ✅ Used | ✅ **Shared** | Wraps up interview |

**Key Insights:**
- **7 out of 9 nodes** are shared between modes (78% reuse)
- Only **2 mode-specific nodes** needed (gap identification logic)
- Shared nodes require minimal mode-awareness (mostly in `generate_question_node`)

### Condition Function Reuse

| Condition | Mode 1 | Mode 2 | Shared? |
|-----------|--------|--------|---------|
| `is_first_run` | ✅ | ✅ | ✅ Fully shared |
| `should_continue_interview` | ✅ | ✅ | ✅ Fully shared |
| `should_follow_up` | ✅ | ✅ | ✅ Fully shared |
| `route_by_mode` | ❌ | ❌ | ✅ **New** (mode routing) |

### Data Flow Comparison

**Mode 1 (Dynamic Gap-Based):**
```
Resume → extract_skills_from_conversation() → Skill objects with 6 attributes
       → Check for "unknown" attributes → Create Gap objects
       → Sort by severity → Select highest severity gap
       → Generate question dynamically via LLM
```

**Mode 2 (Predefined Questions):**
```
Resume + Question Set ID → Fetch questions from DB → For each question:
                           → analyze_resume_for_question() → is_filled?
                           → Create PredefinedGap objects (resume_filled flag)
                           → Filter out resume_filled=True → Sort by order
                           → Select next unanswered question
                           → Use predefined question_text directly
```

**Convergence Point:** Both modes produce a `current_gap` object that flows through the same downstream nodes.

---

## Design Decisions

### 1. Mode Selection Strategy

**Approach:** Add `mode` field to `InterviewSession` and `InterviewState`

```python
class InterviewMode(str, Enum):
    DYNAMIC_GAP = "dynamic_gap"  # Current mode: extract skills, identify gaps
    PREDEFINED_QUESTIONS = "predefined_questions"  # New mode: use question sets
```

**Session Creation:**
```python
# Mode 1: Dynamic Gap-Based
service.start_interview(
    candidate_id="123",
    resume_text="...",
    mode="dynamic_gap"
)

# Mode 2: Predefined Questions
service.start_interview(
    candidate_id="123",
    resume_text="...",
    mode="predefined_questions",
    question_set_id="03b84681-2c75-4bbd-89ee-307861ec7b6b"
)
```

**Mode Decision Flow:**

```
                        User/System Request
                               |
                               v
                    ┌──────────────────────┐
                    │ API: POST /interview │
                    │      /start          │
                    └──────────┬───────────┘
                               |
                ┌──────────────┴──────────────┐
                |                             |
                v                             v
    ┌───────────────────────┐    ┌───────────────────────┐
    │ mode="dynamic_gap"    │    │ mode="predefined_     │
    │ (default)             │    │      questions"       │
    └──────────┬────────────┘    └──────────┬────────────┘
               |                            |
               v                            v
    ┌─────────────────────┐    ┌──────────────────────────┐
    │ identify_gaps_node  │    │ Validate question_set_id │
    │ (extract skills)    │    │      exists in DB        │
    └──────────┬──────────┘    └──────────┬───────────────┘
               |                          |
               v                          v
    ┌─────────────────────┐    ┌──────────────────────────┐
    │ Find "unknown"      │    │ analyze_resume_          │
    │ attributes          │    │    coverage_node         │
    └──────────┬──────────┘    └──────────┬───────────────┘
               |                          |
               v                          v
    ┌─────────────────────┐    ┌──────────────────────────┐
    │ Create Gap objects  │    │ Create PredefinedGap     │
    │ (skill-based)       │    │ objects (question-based) │
    └──────────┬──────────┘    └──────────┬───────────────┘
               |                          |
               └──────────┬───────────────┘
                          v
                ┌──────────────────────┐
                │ CONVERGE:            │
                │ select_gap_node      │
                │ (shared downstream)  │
                └──────────────────────┘
```

**Decision Criteria:**

| Factor | Use Dynamic Gap | Use Predefined Questions |
|--------|-----------------|--------------------------|
| **Goal** | Exploratory depth-first skill assessment | Standardized, consistent evaluation |
| **Resume Quality** | Any (adapts to resume) | Better with detailed resumes (more pre-filling) |
| **Evaluation Consistency** | Varies by conversation flow | Identical questions across candidates |
| **Question Count** | Variable (stops at completeness threshold) | Fixed set (can skip if resume fills) |
| **Customization** | Fully adaptive to candidate background | Structured by role/level |
| **Use Case** | Initial screening, skill exploration | Final round, role-specific assessment |

### 2. Gap Extraction for Predefined Questions

**Concept:** Convert `what_assesses` criteria into gap objects

**New Gap Structure for Predefined Mode:**
```python
class PredefinedGap(TypedDict):
    category: str  # From question.category
    question_id: str  # UUID of the predefined question
    question_text: str  # The actual question
    what_assesses: List[str]  # Assessment criteria
    expected_answer_pattern: Optional[str]
    is_required: bool
    order: int
    severity: float  # Based on is_required (1.0 if required, 0.5 if optional)
    resume_filled: bool  # Whether resume already answers this
    resume_evidence: Optional[str]  # Evidence from resume if filled
    probes_attempted: int
    max_probes: int
```

### 3. Resume-Based Answer Filling

**Strategy:** Use LLM to analyze resume against `what_assesses` criteria

**New Node:** `analyze_resume_coverage_node`

**Logic:**
```python
def analyze_resume_coverage_node(state: InterviewState) -> Dict[str, Any]:
    """
    Analyzes resume to determine which predefined questions can be answered
    without asking the candidate.

    For each question:
    1. Check if resume contains evidence for all `what_assesses` criteria
    2. Extract evidence if found
    3. Mark question as resume_filled=True if sufficient evidence exists
    4. Mark as resume_filled=False if evidence is missing/incomplete
    """
    resume_text = state["resume_text"]
    question_set_id = state["question_set_id"]

    # Fetch predefined questions from DB
    questions = fetch_questions_by_set_id(question_set_id)

    gaps = []
    for question in questions:
        # Use LLM to analyze if resume answers this question
        analysis = analyze_resume_for_question(
            resume=resume_text,
            question=question["question_text"],
            what_assesses=question["what_assesses"],
            expected_pattern=question["expected_answer_pattern"]
        )

        gap = {
            "category": question["category"],
            "question_id": str(question["id"]),
            "question_text": question["question_text"],
            "what_assesses": question["what_assesses"],
            "expected_answer_pattern": question["expected_answer_pattern"],
            "is_required": question["is_required"],
            "order": question["order"],
            "severity": 1.0 if question["is_required"] else 0.5,
            "resume_filled": analysis["is_filled"],
            "resume_evidence": analysis.get("evidence"),
            "probes_attempted": 0,
            "max_probes": 2  # Fewer probes for structured questions
        }
        gaps.append(gap)

    # Filter out resume-filled questions (only keep questions we need to ask)
    questions_to_ask = [g for g in gaps if not g["resume_filled"]]

    return {
        "identified_gaps": questions_to_ask,
        "all_predefined_gaps": gaps,  # Keep all for reference
        "completeness_score": calculate_initial_completeness(gaps)
    }
```

**LLM Analysis Function:**
```python
def analyze_resume_for_question(
    resume: str,
    question: str,
    what_assesses: List[str],
    expected_pattern: Optional[str]
) -> Dict[str, Any]:
    """
    Uses LLM with structured JSON output to determine if resume
    answers the question sufficiently.

    Returns:
    {
        "is_filled": bool,  # Whether resume provides sufficient answer
        "evidence": Optional[str],  # Extracted evidence if is_filled=True
        "missing_criteria": List[str],  # what_assesses items not covered
        "confidence": float  # 0.0-1.0
    }
    """
    system_prompt = """
    You are analyzing a resume to determine if it answers a specific interview question.

    Given:
    - Resume text
    - Interview question
    - Assessment criteria (what_assesses)
    - Expected answer pattern

    Determine if the resume contains sufficient information to answer the question
    without needing to ask the candidate.

    Return JSON with:
    - is_filled: true if resume has sufficient evidence, false otherwise
    - evidence: extracted text from resume if is_filled=true
    - missing_criteria: list of what_assesses items not covered by resume
    - confidence: 0.0-1.0 score

    Be conservative: only mark is_filled=true if resume clearly addresses
    the question. If evidence is vague or incomplete, mark is_filled=false.
    """

    human_prompt = f"""
    Resume:
    {resume}

    Question: {question}

    Assessment Criteria:
    {json.dumps(what_assesses, indent=2)}

    Expected Answer Pattern:
    {expected_pattern or 'No specific pattern provided'}

    Does the resume answer this question sufficiently?
    """

    schema = {
        "type": "object",
        "properties": {
            "is_filled": {"type": "boolean"},
            "evidence": {"type": "string"},
            "missing_criteria": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "required": ["is_filled", "missing_criteria", "confidence"]
    }

    return llm_service.generate_json(
        system_prompt=system_prompt,
        human_prompt=human_prompt,
        schema=schema
    )
```

### 4. State Schema Extensions

**New Fields in `InterviewState`:**
```python
class InterviewState(TypedDict):
    # ... existing fields ...

    # New mode-specific fields
    mode: str  # "dynamic_gap" | "predefined_questions"
    question_set_id: Optional[str]  # UUID for predefined mode
    all_predefined_gaps: Optional[List[PredefinedGap]]  # All questions (asked + resume-filled)
    current_predefined_question: Optional[PredefinedGap]  # Current question being asked
```

### 5. Database Schema Extensions

**Migration: Add mode fields to `InterviewSession`**

```python
# migrations/versions/xxx_add_interview_mode.py

def upgrade():
    # Add mode column (default to existing behavior)
    op.add_column('interview_sessions',
        sa.Column('mode', sa.String(), nullable=False, server_default='dynamic_gap'))

    # Add question_set_id (nullable, only used in predefined mode)
    op.add_column('interview_sessions',
        sa.Column('question_set_id', sa.UUID(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_interview_session_question_set',
        'interview_sessions', 'predefined_question_sets',
        ['question_set_id'], ['id']
    )
```

**Updated `InterviewSession` Model:**
```python
class InterviewSession(SQLModel, table=True):
    # ... existing fields ...

    mode: str = Field(default="dynamic_gap")  # "dynamic_gap" | "predefined_questions"
    question_set_id: Optional[UUID] = Field(default=None, foreign_key="predefined_question_sets.id")

    # Relationships
    question_set: Optional["PredefinedQuestionSet"] = Relationship()
```

### 6. Message Metadata Extensions

**Enhanced Message Storage for Predefined Mode:**

Currently, messages are stored with generic metadata. For predefined mode, we need to track:
- Which predefined question was asked
- Assessment criteria being evaluated
- Resume evidence (if any)

```python
# Example message metadata for predefined mode
{
    "role": "assistant",
    "content": "What leadership experience do you have...",
    "meta": {
        "question_id": "9809e453-32e1-4cbf-9812-07a311c168c8",
        "category": "LEADERSHIP EXPERIENCE",
        "what_assesses": [
            "People leadership vs. individual contribution",
            "Coaching and decision-making skills"
        ],
        "expected_answer_pattern": "...",
        "resume_filled": false,
        "gap_severity": 1.0
    }
}
```

---

## Implementation Plan

### Phase 1: Database & State Extensions (2-3 hours)

**Tasks:**
1. ✅ Create migration to add `mode` and `question_set_id` to `InterviewSession`
2. ✅ Update `InterviewSession` model with new fields
3. ✅ Create `PredefinedGap` TypedDict in state.py
4. ✅ Add mode-specific fields to `InterviewState`
5. ✅ Update `create_initial_state()` to accept mode and question_set_id

**Files to Modify:**
- `migrations/versions/xxx_add_interview_mode.py` (new)
- `models/interview_session.py`
- `agents/conversational/state.py`

**Deliverables:**
- Database migration that can be rolled back
- Updated models with proper type hints
- State schema supporting both modes

---

### Phase 2: Resume Analysis Tool (3-4 hours)

**Tasks:**
1. ✅ Create `tools/resume_analyzer.py` with `analyze_resume_for_question()` function
2. ✅ Create prompt template `prompts/conversational/analyze_resume_coverage.md`
3. ✅ Add JSON schema for structured LLM response
4. ✅ Write unit tests for various resume/question combinations
5. ✅ Test conservative behavior (should default to asking if unclear)

**New Files:**
- `tools/resume_analyzer.py`
- `prompts/conversational/analyze_resume_coverage.md`
- `tests/tools/test_resume_analyzer.py`

**Prompt Template Example:**
```markdown
# Resume Coverage Analysis

You are analyzing whether a resume contains sufficient information to answer an interview question.

## Instructions

1. Carefully read the resume and question
2. Check if resume addresses ALL assessment criteria
3. Extract specific evidence if found
4. Be conservative: only mark as "filled" if evidence is clear and complete

## Assessment Criteria

These are the specific aspects the question aims to evaluate:
{what_assesses}

## Expected Answer Pattern

{expected_answer_pattern}

## Output Format

Return JSON with:
- is_filled: true only if resume clearly addresses ALL criteria
- evidence: specific text from resume (if is_filled=true)
- missing_criteria: list of criteria not covered
- confidence: your confidence score (0.0-1.0)

**Important:** If in doubt, mark is_filled=false. It's better to ask the candidate than to assume from vague resume text.
```

---

### Phase 3: New Graph Node - `analyze_resume_coverage_node` (2-3 hours)

**Tasks:**
1. ✅ Create `agents/conversational/nodes/analyze_resume_coverage.py`
2. ✅ Implement logic to fetch predefined questions from DB
3. ✅ Call `analyze_resume_for_question()` for each question
4. ✅ Create `PredefinedGap` objects
5. ✅ Filter out resume-filled questions
6. ✅ Calculate initial completeness score
7. ✅ Return state updates

**New Files:**
- `agents/conversational/nodes/analyze_resume_coverage.py`

**Pseudo-code:**
```python
def analyze_resume_coverage_node(state: InterviewState) -> Dict[str, Any]:
    """Analyze which predefined questions can be answered from resume."""

    # Only run in predefined mode
    if state["mode"] != "predefined_questions":
        raise ValueError("This node should only run in predefined_questions mode")

    resume_text = state["resume_text"]
    question_set_id = state["question_set_id"]

    # Fetch predefined questions (ordered by order field)
    questions = db_fetch_questions(question_set_id)

    all_gaps = []
    questions_to_ask = []

    for q in questions:
        # Analyze resume
        analysis = analyze_resume_for_question(
            resume=resume_text,
            question=q["question_text"],
            what_assesses=q["what_assesses"],
            expected_pattern=q["expected_answer_pattern"]
        )

        gap = {
            "category": q["category"],
            "question_id": str(q["id"]),
            "question_text": q["question_text"],
            "what_assesses": q["what_assesses"],
            "expected_answer_pattern": q["expected_answer_pattern"],
            "is_required": q["is_required"],
            "order": q["order"],
            "severity": 1.0 if q["is_required"] else 0.5,
            "resume_filled": analysis["is_filled"],
            "resume_evidence": analysis.get("evidence"),
            "probes_attempted": 0,
            "max_probes": 2
        }

        all_gaps.append(gap)

        # Only add to questions_to_ask if NOT filled by resume
        if not analysis["is_filled"]:
            questions_to_ask.append(gap)

    # Calculate completeness
    total_questions = len(all_gaps)
    filled_questions = sum(1 for g in all_gaps if g["resume_filled"])
    completeness_score = filled_questions / total_questions if total_questions > 0 else 0.0

    print(f"Resume filled {filled_questions}/{total_questions} questions")
    print(f"Need to ask {len(questions_to_ask)} questions")

    return {
        "identified_gaps": questions_to_ask,  # Only questions we need to ask
        "all_predefined_gaps": all_gaps,  # All questions for reference
        "completeness_score": completeness_score
    }
```

---

### Phase 4: Mode-Aware Graph Modifications (3-4 hours)

**Tasks:**
1. ✅ Add mode-aware entry point condition
2. ✅ Modify `identify_gaps_node` to route based on mode
3. ✅ Update `select_gap_node` to handle predefined gaps
4. ✅ Update `generate_question_node` to use predefined question text
5. ✅ Update `parse_answer_node` to extract based on what_assesses
6. ✅ Update `update_state_node` to handle predefined mode
7. ✅ Update completeness calculation

**Files to Modify:**
- `agents/conversational/graph.py`
- `agents/conversational/conditions.py`
- `agents/conversational/nodes/identify_gaps.py`
- `agents/conversational/nodes/select_gap.py`
- `agents/conversational/nodes/generate_question.py`
- `agents/conversational/nodes/parse_answer.py`
- `agents/conversational/nodes/update_state.py`

**Updated Graph Flow:**
```
START → is_first_run?
  ├─ First run → check_mode?
  │              ├─ dynamic_gap → identify_gaps (existing) → select_gap → ...
  │              └─ predefined_questions → analyze_resume_coverage → select_gap → ...
  │
  └─ Resume → parse_answer → update_state → should_follow_up?
                                    ├─ Follow up → generate_follow_up → END
                                    └─ Move on → should_continue? → select_gap/finalize
```

**New Condition Function:**
```python
def route_by_mode(state: InterviewState) -> str:
    """Route to appropriate gap identification node based on mode."""
    mode = state.get("mode", "dynamic_gap")

    if mode == "dynamic_gap":
        return "identify_gaps"
    elif mode == "predefined_questions":
        return "analyze_resume_coverage"
    else:
        raise ValueError(f"Unknown mode: {mode}")
```

**Modified `select_gap_node`:**
```python
def select_gap_node(state: InterviewState) -> Dict[str, Any]:
    """Select next gap to address (works for both modes)."""

    identified_gaps = state["identified_gaps"]
    resolved_gaps = state["resolved_gaps"]

    # Filter out resolved gaps
    remaining_gaps = [
        g for g in identified_gaps
        if g not in resolved_gaps and g.get("probes_attempted", 0) < g.get("max_probes", 3)
    ]

    if not remaining_gaps:
        return {
            "current_gap": None,
            "should_continue": False,
            "termination_reason": "no_gaps"
        }

    # Select highest severity gap
    current_gap = max(remaining_gaps, key=lambda g: g["severity"])

    # For predefined mode, also set current_predefined_question
    updates = {"current_gap": current_gap}

    if state.get("mode") == "predefined_questions":
        updates["current_predefined_question"] = current_gap

    return updates
```

**Modified `generate_question_node`:**
```python
def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """Generate question based on current gap (mode-aware)."""

    mode = state.get("mode", "dynamic_gap")
    current_gap = state["current_gap"]

    if mode == "predefined_questions":
        # Use predefined question text directly
        question_text = current_gap["question_text"]

        # Add conversational wrapper if needed
        question = f"{question_text}"

    else:  # dynamic_gap mode
        # Generate question dynamically (existing logic)
        question = generate_dynamic_question(current_gap, state)

    # Create message
    message = AIMessage(content=question)

    # Save question context
    question_context = {
        "question_id": str(uuid.uuid4()),
        "question_text": question,
        "gap_description": current_gap["description"] if mode == "dynamic_gap" else current_gap["question_text"],
        # Mode-specific metadata
        "mode": mode,
        "category": current_gap["category"],
        "what_assesses": current_gap.get("what_assesses", []),
    }

    return {
        "messages": [message],
        "current_question": question_context,
        "questions_asked": state["questions_asked"] + 1
    }
```

---

### Phase 5: Service Layer Updates (2 hours)

**Tasks:**
1. ✅ Update `start_interview()` to accept `mode` and `question_set_id`
2. ✅ Add validation for predefined mode (question_set_id required)
3. ✅ Update `create_initial_state()` calls with new parameters
4. ✅ Update database session creation with new fields

**Files to Modify:**
- `agents/conversational/service.py`

**Updated `start_interview()` Signature:**
```python
def start_interview(
    self,
    candidate_id: str,
    resume_text: str,
    mode: str = "dynamic_gap",
    question_set_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start a new interview session.

    Args:
        candidate_id: ID of the candidate
        resume_text: Resume text to analyze
        mode: "dynamic_gap" or "predefined_questions"
        question_set_id: Required if mode="predefined_questions"

    Returns:
        Dictionary with session_id, thread_id, question
    """
    # Validate mode
    if mode == "predefined_questions" and not question_set_id:
        raise ValueError("question_set_id is required for predefined_questions mode")

    # Validate question_set exists
    if question_set_id:
        question_set = self.db_session.get(PredefinedQuestionSet, question_set_id)
        if not question_set:
            raise ValueError(f"Question set {question_set_id} not found")

    # Create session with mode
    thread_id = f"thread_{uuid.uuid4()}"
    session = InterviewSession(
        candidate_id=candidate_id,
        resume_text=resume_text,
        thread_id=thread_id,
        status="active",
        mode=mode,
        question_set_id=question_set_id
    )
    # ... rest of implementation
```

---

### Phase 6: API Endpoint Updates (1-2 hours)

**Tasks:**
1. ✅ Update `POST /interview/start` to accept mode and question_set_id
2. ✅ Add request schema validation
3. ✅ Update API documentation

**Files to Modify:**
- `api/routes/interview.py`
- `api/models/interview_schemas.py`

**Updated Request Schema:**
```python
class InterviewStartRequest(BaseModel):
    candidate_id: str
    resume_text: str
    mode: str = Field(default="dynamic_gap", pattern="^(dynamic_gap|predefined_questions)$")
    question_set_id: Optional[UUID] = None

    @validator("question_set_id")
    def validate_question_set_required(cls, v, values):
        if values.get("mode") == "predefined_questions" and v is None:
            raise ValueError("question_set_id is required when mode is predefined_questions")
        return v
```

**Updated Endpoint:**
```python
@router.post("/start")
def start_interview(
    request: InterviewStartRequest,
    service: ConversationalInterviewService = Depends(get_interview_service)
):
    """
    Start a new interview session.

    Supports two modes:
    - dynamic_gap: Analyzes resume and generates questions for skill gaps
    - predefined_questions: Uses predefined question set, skips questions answered by resume
    """
    result = service.start_interview(
        candidate_id=request.candidate_id,
        resume_text=request.resume_text,
        mode=request.mode,
        question_set_id=request.question_set_id
    )
    return result
```

---

### Phase 7: Testing & Validation (3-4 hours)

**Tasks:**
1. ✅ Write integration test for Mode 1 (dynamic_gap) - ensure nothing broke
2. ✅ Write integration test for Mode 2 (predefined_questions)
3. ✅ Test resume-filling logic with various resume qualities
4. ✅ Test edge cases (all questions filled, no questions filled)
5. ✅ Test engagement tracking in both modes
6. ✅ Test completeness calculation in both modes
7. ✅ Test mode switching (start new session with different mode)

**New Test Files:**
- `tests/conversational/test_two_mode_interview.py`
- `tests/conversational/test_resume_coverage_analysis.py`

**Test Scenarios:**

**Scenario 1: Dynamic Gap Mode (Existing Behavior)**
```python
def test_dynamic_gap_mode():
    """Test that dynamic gap mode works as before."""
    result = service.start_interview(
        candidate_id="test_123",
        resume_text=SAMPLE_RESUME,
        mode="dynamic_gap"
    )

    assert result["question"] is not None
    assert "session_id" in result
    # Verify gaps were identified from skills
```

**Scenario 2: Predefined Questions - All Resume Filled**
```python
def test_predefined_all_filled():
    """Test when resume answers all questions."""
    comprehensive_resume = load_fixture("comprehensive_senior_fullstack.txt")

    result = service.start_interview(
        candidate_id="test_456",
        resume_text=comprehensive_resume,
        mode="predefined_questions",
        question_set_id=FULLSTACK_QUESTION_SET_ID
    )

    # Should complete immediately or ask very few questions
    assert result.get("completed") or result["questions_asked"] < 5
```

**Scenario 3: Predefined Questions - Partial Resume Coverage**
```python
def test_predefined_partial_coverage():
    """Test when resume answers some but not all questions."""
    partial_resume = load_fixture("mid_level_backend.txt")

    result = service.start_interview(
        candidate_id="test_789",
        resume_text=partial_resume,
        mode="predefined_questions",
        question_set_id=FULLSTACK_QUESTION_SET_ID
    )

    # Should ask questions about missing areas (e.g., frontend, mobile)
    assert result["question"] is not None
    # Should have pre-filled some questions
    # Verify via database query or state inspection
```

**Scenario 4: Predefined Questions - Minimal Resume**
```python
def test_predefined_minimal_resume():
    """Test when resume is very sparse."""
    minimal_resume = "Software Engineer with 2 years experience in Python."

    result = service.start_interview(
        candidate_id="test_999",
        resume_text=minimal_resume,
        mode="predefined_questions",
        question_set_id=FULLSTACK_QUESTION_SET_ID
    )

    # Should ask most/all questions
    # Verify first question is from the question set
    assert result["question"] in [q["question_text"] for q in EXPECTED_QUESTIONS]
```

---

### Phase 8: Documentation (1-2 hours)

**Tasks:**
1. ✅ Update `docs/conversational-agent.md` with two-mode explanation
2. ✅ Add mode comparison table
3. ✅ Document API changes
4. ✅ Add examples for both modes
5. ✅ Update CLAUDE.md with new patterns

**Documentation Sections to Add:**

**Mode Comparison Table:**
```markdown
| Aspect | Dynamic Gap Mode | Predefined Questions Mode |
|--------|------------------|---------------------------|
| Gap Source | Extract skills, identify unknown attributes | Use `what_assesses` from predefined questions |
| Question Generation | LLM-generated based on gap context | Use predefined `question_text` |
| Resume Pre-filling | Not applicable | LLM analyzes if resume answers question |
| Completeness | Based on skill attribute coverage | Based on % of questions answered |
| Flexibility | Highly adaptive, follows conversation | Follows structured question sequence |
| Use Case | Exploratory, depth-first skill probing | Standardized, consistent evaluation |
```

**API Usage Examples:**
```python
# Mode 1: Dynamic Gap-Based Interview
POST /interview/start
{
  "candidate_id": "123",
  "resume_text": "Senior Python Developer...",
  "mode": "dynamic_gap"
}

# Mode 2: Predefined Questions Interview
POST /interview/start
{
  "candidate_id": "456",
  "resume_text": "Fullstack Engineer...",
  "mode": "predefined_questions",
  "question_set_id": "03b84681-2c75-4bbd-89ee-307861ec7b6b"
}
```

---

## Implementation Timeline

**Total Estimated Time: 17-24 hours**

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| 1. Database & State | Schema changes, model updates | 2-3 hours |
| 2. Resume Analysis | Tool creation, prompt engineering | 3-4 hours |
| 3. Resume Coverage Node | New node implementation | 2-3 hours |
| 4. Graph Modifications | Mode-aware routing and processing | 3-4 hours |
| 5. Service Layer | Public API updates | 2 hours |
| 6. API Endpoints | REST API changes | 1-2 hours |
| 7. Testing | Integration and edge case tests | 3-4 hours |
| 8. Documentation | Docs and examples | 1-2 hours |

**Recommended Implementation Order:**
1. Phase 1 (Foundation) → Phase 2 (Tool) → Phase 3 (Node) → Phase 4 (Graph)
2. Phase 5 (Service) → Phase 6 (API)
3. Phase 7 (Testing) → Phase 8 (Documentation)

---

## Risk Assessment & Mitigation

### Risk 1: Resume Analysis Too Lenient (False Positives)

**Risk:** LLM marks questions as "filled" when resume has vague/partial information

**Impact:** Skip important questions, reduce interview quality

**Mitigation:**
- Use conservative prompt engineering ("if in doubt, mark as not filled")
- Add confidence threshold (only mark filled if confidence > 0.8)
- Include "missing_criteria" field to track partial coverage
- Add human override in UI to force ask specific questions

### Risk 2: Resume Analysis Too Strict (False Negatives)

**Risk:** LLM marks questions as "not filled" when resume has sufficient evidence

**Impact:** Ask redundant questions, annoy candidates

**Mitigation:**
- Test with diverse resume samples
- Tune prompt based on test results
- Allow candidates to say "I already mentioned this in my resume" (follow-up detection)
- Track resume evidence in metadata for human review

### Risk 3: Backward Compatibility

**Risk:** Breaking existing interviews or API consumers

**Impact:** Production issues, data loss

**Mitigation:**
- Default mode to "dynamic_gap" for backward compatibility
- Add migration with safe defaults
- Version API endpoints if needed
- Comprehensive testing of existing flows

### Risk 4: Performance Degradation

**Risk:** Analyzing 30+ questions against resume takes too long

**Impact:** Slow interview start, poor UX

**Mitigation:**
- Batch LLM calls if possible
- Use faster model (Haiku) for resume analysis
- Cache analysis results per resume hash
- Consider async processing for large question sets

### Risk 5: Question Set Quality Variation

**Risk:** Poorly designed predefined questions don't translate well to gaps

**Impact:** Confusing interviews, poor candidate experience

**Mitigation:**
- Document best practices for question set design
- Add validation for `what_assesses` field (non-empty, specific)
- Create sample question sets as templates
- User testing with multiple question sets

---

## Edge Cases & Fallback Scenarios

Understanding and handling edge cases is critical for robust implementation.

### Edge Case 1: All Questions Resume-Filled (Predefined Mode)

**Scenario:** Resume comprehensively answers all predefined questions

**Example:**
```python
# 34 questions in Fullstack Senior question set
# Comprehensive resume provides evidence for all 34 questions
```

**Handling Strategy:**

```python
def analyze_resume_coverage_node(state: InterviewState) -> Dict[str, Any]:
    # ... analyze all questions ...

    questions_to_ask = [g for g in all_gaps if not g["resume_filled"]]

    if not questions_to_ask:
        # All questions answered by resume - complete immediately
        return {
            "identified_gaps": [],
            "all_predefined_gaps": all_gaps,
            "completeness_score": 1.0,
            "should_continue": False,
            "termination_reason": "complete",
            "completion_message": "Your resume comprehensively addressed all assessment areas!"
        }

    # Normal flow: some questions need asking
    return {
        "identified_gaps": questions_to_ask,
        "all_predefined_gaps": all_gaps,
        "completeness_score": initial_score
    }
```

**Expected Behavior:**
- Interview completes on first invocation (no questions asked)
- Returns completion message acknowledging resume quality
- `questions_asked = 0` is valid
- All questions marked as `resume_filled=True` in metadata

### Edge Case 2: No Questions Resume-Filled (Predefined Mode)

**Scenario:** Minimal resume with no evidence for any question

**Example:**
```python
resume = "Software Engineer, 2 years experience"
# No specific skills, projects, or details
```

**Handling Strategy:**

```python
def analyze_resume_coverage_node(state: InterviewState) -> Dict[str, Any]:
    # ... analyze all questions ...

    questions_to_ask = [g for g in all_gaps if not g["resume_filled"]]

    if len(questions_to_ask) == len(all_gaps):
        # No questions filled - ask all questions in order
        print(f"Resume sparse: asking all {len(questions_to_ask)} questions")

    return {
        "identified_gaps": questions_to_ask,
        "all_predefined_gaps": all_gaps,
        "completeness_score": 0.0  # Nothing known yet
    }
```

**Expected Behavior:**
- Interview proceeds through all questions sequentially
- Follows `order` field from database
- Standard engagement tracking applies
- May terminate early if candidate becomes disengaged

### Edge Case 3: Question Set Not Found

**Scenario:** Invalid `question_set_id` provided

**Handling Strategy:**

```python
def start_interview(self, candidate_id, resume_text, mode, question_set_id):
    if mode == "predefined_questions":
        # Validate question_set exists
        question_set = self.db_session.get(PredefinedQuestionSet, question_set_id)
        if not question_set:
            raise ValueError(
                f"Question set {question_set_id} not found. "
                "Please verify the question set ID or create it first."
            )

        # Validate question set has questions
        questions_count = len(question_set.questions)
        if questions_count == 0:
            raise ValueError(
                f"Question set {question_set_id} has no questions. "
                "Please add questions before starting interview."
            )
```

**Expected Behavior:**
- Fail fast with clear error message
- Do NOT create interview session
- Return HTTP 404 or 400 to API caller

### Edge Case 4: All Gaps Exhausted Mid-Interview

**Scenario:** All identified gaps resolved or max probes reached

**Handling Strategy:**

```python
def select_gap_node(state: InterviewState) -> Dict[str, Any]:
    identified_gaps = state["identified_gaps"]
    resolved_gaps = state["resolved_gaps"]

    # Filter out resolved gaps and exhausted probes
    remaining_gaps = [
        g for g in identified_gaps
        if g not in resolved_gaps and g.get("probes_attempted", 0) < g.get("max_probes", 3)
    ]

    if not remaining_gaps:
        # No more gaps to address - complete interview
        return {
            "current_gap": None,
            "should_continue": False,
            "termination_reason": "no_gaps",
            "completion_message": "We've covered all the key areas. Thank you!"
        }

    # Continue with next gap
    current_gap = max(remaining_gaps, key=lambda g: g["severity"])
    return {"current_gap": current_gap}
```

**Expected Behavior:**
- Graceful termination when work is done
- Appropriate completion message
- Works for both modes

### Edge Case 5: Candidate References Resume During Interview

**Scenario:** Candidate says "I already mentioned this in my resume"

**Example:**
```
Q: "What leadership experience do you have?"
A: "I already covered this in my resume - I led a team of 5 engineers."
```

**Handling Strategy:**

```python
def parse_answer_node(state: InterviewState) -> Dict[str, Any]:
    answer = state["messages"][-1].content

    # Detect resume references
    resume_references = [
        "already mentioned in my resume",
        "covered this in my resume",
        "as stated in my resume",
        "my resume shows"
    ]

    if any(phrase in answer.lower() for phrase in resume_references):
        # Mark as low-quality answer, but don't penalize too much
        # Allow follow-up to probe for more details
        engagement = {
            "engagement_level": "neutral",  # Not disengaged, just redundant
            "needs_follow_up": True,
            "follow_up_reason": "Candidate referenced resume - probe for deeper details"
        }
    else:
        # Normal engagement analysis
        engagement = analyze_engagement(answer)

    return {
        "tool_results": {
            "engagement": engagement,
            # ... other results
        }
    }
```

**Expected Behavior:**
- Don't count as disengagement
- Generate follow-up asking for more details beyond resume
- Example: "I see that in your resume - can you tell me more about the specific challenges you faced?"

### Edge Case 6: Empty or Invalid Resume Text

**Scenario:** Resume text is empty, null, or just whitespace

**Handling Strategy:**

```python
def start_interview(self, candidate_id, resume_text, mode, question_set_id):
    # Validate resume
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text cannot be empty")

    if len(resume_text.strip()) < 50:
        # Warn but allow (some resumes are minimal)
        print(f"⚠️  Warning: Resume is very short ({len(resume_text)} chars)")

    # Continue with interview
    # ...
```

**Expected Behavior:**
- Reject completely empty resumes
- Allow short resumes but warn
- For predefined mode: will likely mark all questions as not filled

### Fallback Decision Matrix

| Edge Case | Mode 1 (Dynamic) | Mode 2 (Predefined) | Severity | Auto-Handle? |
|-----------|------------------|---------------------|----------|--------------|
| All gaps filled | N/A (always finds gaps) | Complete immediately | Low | ✅ Yes |
| No gaps filled | Asks about all skills | Asks all questions | Low | ✅ Yes |
| Invalid question_set_id | N/A | Fail fast with error | High | ✅ Yes |
| Empty resume | Creates minimal gaps | Marks all questions unfilled | Medium | ✅ Yes (warn) |
| Candidate disengaged | Terminate early | Terminate early | Medium | ✅ Yes |
| All probes exhausted | Move to next gap | Move to next question | Low | ✅ Yes |
| Resume reference | Generate follow-up | Generate follow-up | Low | ✅ Yes |

**Key Principle:** All edge cases should be handled automatically without manual intervention. The system should degrade gracefully and provide clear feedback.

---

## Success Criteria

### Functional Requirements

✅ **FR1:** System supports both dynamic_gap and predefined_questions modes
✅ **FR2:** Predefined mode skips questions answered by resume
✅ **FR3:** Engagement tracking works in both modes
✅ **FR4:** Completeness calculation adapts to mode
✅ **FR5:** Existing dynamic_gap mode continues to work unchanged
✅ **FR6:** API accepts mode parameter with validation
✅ **FR7:** Database stores mode and question_set_id

### Non-Functional Requirements

✅ **NFR1:** Resume analysis completes in < 5 seconds for 30 questions
✅ **NFR2:** No breaking changes to existing API contracts
✅ **NFR3:** Code maintains LangGraph clean workflow pattern
✅ **NFR4:** Comprehensive test coverage (>80%) for new code
✅ **NFR5:** Documentation explains both modes clearly

### Acceptance Tests

**Test 1: Mode 1 Still Works**
```
GIVEN an existing interview flow
WHEN I start an interview without specifying mode
THEN it should default to dynamic_gap mode
AND work exactly as before
```

**Test 2: Mode 2 Skips Resume-Covered Questions**
```
GIVEN a comprehensive senior fullstack resume
AND a predefined question set for "Senior Fullstack"
WHEN I start an interview in predefined_questions mode
THEN at least 50% of questions should be marked as resume-filled
AND interview should only ask about gaps not in resume
```

**Test 3: Mode 2 Asks All Questions for Sparse Resume**
```
GIVEN a minimal resume with only job title and years
AND a predefined question set
WHEN I start an interview in predefined_questions mode
THEN most questions should be marked as not filled
AND interview should ask questions in order
```

**Test 4: Engagement Tracking in Mode 2**
```
GIVEN an interview in predefined_questions mode
WHEN candidate gives 3 consecutive low-quality answers
THEN interview should terminate with "disengaged" reason
```

**Test 5: Completeness in Mode 2**
```
GIVEN an interview in predefined_questions mode
WHEN candidate answers enough questions to reach threshold
THEN interview should complete with "complete" reason
AND completeness_score should be >= minimum_completeness
```

---

## Open Questions

1. **Question Ordering in Predefined Mode:**
   - Should we always follow the `order` field strictly?
   - Or allow re-ordering based on resume analysis (ask hardest gaps first)?
   - **Recommendation:** Follow order field initially, can add "adaptive ordering" later

2. **Follow-up Questions in Predefined Mode:**
   - Should follow-ups be generated dynamically?
   - Or should we support predefined follow-up questions?
   - **Recommendation:** Generate dynamically using `expected_answer_pattern` as guide

3. **Hybrid Mode:**
   - Should we support a hybrid mode (start with predefined, then dynamic gaps)?
   - **Recommendation:** Implement as separate mode in future if needed

4. **Resume Analysis Caching:**
   - Should we cache resume analysis results?
   - Key by resume hash + question_set_id?
   - **Recommendation:** Add caching in Phase 2.1 if performance issues arise

5. **Question Set Versioning:**
   - How to handle question set updates mid-interview?
   - **Recommendation:** Snapshot question set at interview start (store in state)

---

## Future Enhancements

### Phase 2.1: Performance Optimization (Post-MVP)
- Add caching for resume analysis
- Batch LLM calls for resume analysis
- Use Haiku for resume analysis (faster, cheaper)
- Async resume analysis for large question sets

### Phase 2.2: Advanced Features
- Hybrid mode (start predefined, then dynamic)
- Adaptive question ordering based on resume analysis
- Question difficulty rating
- Skip entire categories if resume has strong evidence

### Phase 2.3: Analytics & Reporting
- Compare candidate answers vs resume claims
- Identify resume exaggerations/gaps
- Track question effectiveness (which questions get best signal)
- Resume completeness score

### Phase 2.4: UI Enhancements
- Show which questions were resume-filled in interview review
- Allow interviewer to override resume-filling
- Suggest questions to ask based on role requirements

---

## Appendices

### Appendix A: Example Resume Analysis Response

```json
{
  "question_id": "9809e453-32e1-4cbf-9812-07a311c168c8",
  "question_text": "What leadership experience do you have, and how have you led or mentored others?",
  "what_assesses": [
    "People leadership vs. individual contribution",
    "Coaching and decision-making skills"
  ],
  "analysis": {
    "is_filled": true,
    "confidence": 0.85,
    "evidence": "Resume states: 'Led a team of 5 engineers, conducted weekly 1:1s, mentored 2 junior developers on React best practices, made architecture decisions for the authentication system.'",
    "missing_criteria": []
  }
}
```

### Appendix B: State Transition Diagram

```
[START]
   |
   v
[is_first_run?] ──Yes──> [check_mode?]
   |                          ├──dynamic_gap──> [identify_gaps] ──> [select_gap]
   |                          └──predefined──> [analyze_resume_coverage] ──> [select_gap]
   |
   No
   |
   v
[parse_answer] ──> [update_state] ──> [should_follow_up?]
                                          ├──Yes──> [generate_follow_up] ──> [END]
                                          └──No──> [should_continue?]
                                                      ├──Yes──> [select_gap] ──> [generate_question] ──> [END]
                                                      └──No──> [finalize] ──> [END]
```

### Appendix C: Database Schema Diagram

```
┌─────────────────────────┐
│   InterviewSession      │
├─────────────────────────┤
│ id (PK)                 │
│ candidate_id            │
│ resume_text             │
│ status                  │
│ mode ◄─────────────────┼── NEW: "dynamic_gap" | "predefined_questions"
│ question_set_id (FK) ◄─┼── NEW: References PredefinedQuestionSet
│ thread_id               │
│ completeness_score      │
│ ...                     │
└─────────────────────────┘
            │
            │ 1:N
            v
┌─────────────────────────┐
│   ExtractedSkill        │
├─────────────────────────┤
│ id (PK)                 │
│ session_id (FK)         │
│ name                    │
│ duration                │
│ depth                   │
│ autonomy                │
│ scale                   │
│ constraints             │
│ production_vs_prototype │
│ ...                     │
└─────────────────────────┘

┌─────────────────────────┐
│ PredefinedQuestionSet   │
├─────────────────────────┤
│ id (PK)                 │
│ role_id (FK)            │
│ name                    │
│ version                 │
│ is_active               │
└─────────────────────────┘
            │
            │ 1:N
            v
┌─────────────────────────┐
│  PredefinedQuestion     │
├─────────────────────────┤
│ id (PK)                 │
│ question_set_id (FK)    │
│ category                │
│ question_text           │
│ what_assesses (JSON)    │
│ expected_answer_pattern │
│ order                   │
│ is_required             │
└─────────────────────────┘
```

---

## Conclusion

This implementation plan outlines a comprehensive approach to extending the conversational interview agent with two distinct modes:

1. **Dynamic Gap-Based Mode** (existing) - Exploratory, depth-first skill probing
2. **Predefined Questions Mode** (new) - Structured, standardized evaluation with resume pre-filling

The design maintains backward compatibility, follows established LangGraph patterns, and introduces smart resume analysis to reduce redundant questions.

**Next Steps:**
1. Review and approve this plan
2. Create implementation tasks in project management tool
3. Begin Phase 1 (Database & State Extensions)
4. Iterate based on testing feedback

**Key Benefits:**
- ✅ Maintains existing dynamic interview capabilities
- ✅ Adds structured interview mode for standardization
- ✅ Reduces candidate friction with resume pre-filling
- ✅ Preserves engagement tracking and adaptive flow
- ✅ Scales to handle multiple question sets per role

---

**Document Version:** 1.0
**Last Updated:** 2026-01-13
**Status:** Draft - Awaiting Approval
