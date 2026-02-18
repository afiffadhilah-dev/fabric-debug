"""
State schema for the interview graph.

Defines the data structure that flows through the LangGraph nodes during interviews.
"""

from typing import TypedDict, Annotated, Optional, List, Any, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class QuestionContext(TypedDict):
    """
    Explicit context for every question asked.

    Carries context about what we asked, so downstream nodes can process
    answers correctly based on the mode.

    Dynamic Gap Mode:
        - skill_name: The skill being asked about (e.g., "Python")
        - attribute: The specific attribute (e.g., "duration", "depth")
        - category/what_assesses: None

    Predefined Questions Mode:
        - skill_name/attribute: None
        - category: Question category (e.g., "LEADERSHIP EXPERIENCE")
        - what_assesses: Assessment criteria from database
    """
    question_id: str
    question_text: str
    gap_description: str

    # DYNAMIC GAP MODE fields (None for predefined mode)
    skill_name: Optional[str]  # e.g., "Python"
    attribute: Optional[str]   # e.g., "duration", "depth", "autonomy"

    # PREDEFINED MODE fields (None for dynamic_gap mode)
    category: Optional[str]           # e.g., "LEADERSHIP EXPERIENCE"
    what_assesses: Optional[List[str]]  # e.g., ["People leadership", "Decision-making"]


class Gap(TypedDict):
    """
    Represents a gap in skill information that needs to be addressed.

    Gaps are identified when skill attributes are marked as "unknown".
    """
    category: str  # "technical_skill"
    description: str  # Human-readable description of what's missing
    severity: float  # 0.0-1.0, higher = more important to resolve
    context: str  # Context about the skill this gap relates to
    probes_attempted: int  # How many times we've asked about this
    max_probes: int  # Maximum times to ask before giving up
    probe_history: List[str]  # History of answer_types for this gap: ["partial_answer", "clarification_request", ...]


class PredefinedGap(TypedDict):
    """
    Represents a predefined question that needs to be asked.

    Used in predefined_questions mode. Converted from database PredefinedQuestion.

    A gap can be filled in three ways:
    1. resume_filled: Resume already answers the question (detected at start)
    2. interview_filled: A previous answer covered this question (cross-gap detection)
    3. Resolved through direct Q&A (probes_attempted > 0 and marked resolved)
    """
    category: str  # From question.category (e.g., "LEADERSHIP EXPERIENCE")
    question_id: str  # UUID of the predefined question
    question_text: str  # The actual question
    what_assesses: List[str]  # Assessment criteria
    expected_answer_pattern: Optional[str]
    is_required: bool
    order: int
    severity: float  # Based on is_required (1.0 if required, 0.5 if optional)

    # Resume coverage (detected at interview start)
    resume_filled: bool  # Whether resume already answers this
    resume_evidence: Optional[str]  # Evidence from resume if filled

    # Interview coverage (detected via cross-gap analysis)
    interview_filled: bool  # Whether a previous answer already covered this
    interview_evidence: Optional[str]  # Evidence from the answer that covered it
    coverage_confidence: float  # 0.0-1.0 how well it was covered

    # Probing state
    probes_attempted: int
    max_probes: int

    # User skip state
    skipped: bool              # User explicitly skipped
    skip_reason: Optional[str] # Reason for skipping, if any


class EngagementSignal(TypedDict):
    """
    Tracks user engagement for a single answer.

    Used to detect when the user becomes disengaged and stop the interview.
    """
    answer_length: int  # Character count
    relevance_score: float  # 0.0-1.0
    detail_score: float  # 0.0-1.0
    enthusiasm_detected: bool
    engagement_level: str  # "engaged" | "disengaged"


class Skill(TypedDict):
    """
    A technical skill with 6 key attributes.

    Attributes can be "unknown" if not yet determined through interview.
    """
    name: str
    confidence_score: float
    # 6 skill attributes
    duration: Optional[str]  # e.g., "3 years", "6 months"
    depth: Optional[str]  # e.g., "basic CRUD", "advanced optimization"
    autonomy: Optional[str]  # e.g., "solo project", "led team of 5"
    scale: Optional[str]  # e.g., "10M users", "enterprise-scale"
    constraints: Optional[str]  # e.g., "legacy system", "tight deadlines"
    production_vs_prototype: Optional[str]  # "production" | "prototype" | "PoC"
    evidence: str  # Supporting text from resume/conversation


class InterviewState(TypedDict):
    """
    The complete state of an interview conversation.

    This is a dynamic, gap-based interview system - no fixed question counts!
    The conversation continues based on:
    1. Identified gaps in skill information
    2. User engagement level
    3. Completeness threshold (default: 60%)
    """

    # ============================================================================
    # SESSION IDENTIFICATION
    # ============================================================================
    session_id: str
    """Database session UUID"""

    resume_text: str
    """Full resume text provided by user"""

    # ============================================================================
    # INTERVIEW MODE (Mode selection)
    # ============================================================================
    mode: str
    """Interview mode: "dynamic_gap" or "predefined_questions" """

    question_set_id: Optional[str]
    """UUID of predefined question set (required if mode="predefined_questions")"""

    all_predefined_gaps: Optional[List[PredefinedGap]]
    """All predefined questions (both asked and resume-filled) - only used in predefined mode"""

    current_predefined_question: Optional[PredefinedGap]
    """Current predefined question being asked - only used in predefined mode"""

    # ============================================================================
    # INTRODUCTION (One-time introduction message on first interaction)
    # ============================================================================
    introduction_text: str
    """One-time introduction message, set by introduce_node and prepended to first question"""

    # ============================================================================
    # MESSAGES (LangGraph built-in pattern)
    # ============================================================================
    messages: Annotated[List[BaseMessage], add_messages]
    """
    Conversation messages (questions and answers).

    The 'add_messages' reducer automatically appends new messages
    instead of replacing the list.
    """

    # ============================================================================
    # DYNAMIC GAP TRACKING (Core of dynamic behavior)
    # ============================================================================
    identified_gaps: List[Gap]
    """All gaps found during resume analysis - sorted by severity"""

    resolved_gaps: List[Gap]
    """Gaps that have been clarified through conversation"""

    current_gap: Optional[Gap]
    """The gap we're currently asking about (None if between questions)"""

    current_question: Optional[QuestionContext]
    """
    CRITICAL: Explicit context for the current question.

    This carries ALL context about what we asked, so tools can extract
    skills correctly with explicit skill_name and attribute.
    """

    gaps_resolved_this_turn: int
    """
    Number of gaps resolved in the most recent answer (for acknowledgment).

    Used to detect when a single answer covers multiple requirements,
    so we can acknowledge: "Great! You've covered Python duration, scale, AND production..."
    Reset to 0 after acknowledgment is generated.
    """

    # ============================================================================
    # ENGAGEMENT TRACKING (Detect disinterest)
    # ============================================================================
    engagement_signals: List[EngagementSignal]
    """History of engagement metrics for each answer"""

    consecutive_low_quality: int
    """
    Count of consecutive disengaged answers (assessed by LLM).
    Triggers early termination if >= 3.
    """

    # ============================================================================
    # EXTRACTED DATA (Builds up over conversation)
    # ============================================================================
    extracted_skills: List[Skill]
    """Skills extracted from resume + conversation with 6 attributes"""

    # ============================================================================
    # COMPLETENESS (Not question count!)
    # ============================================================================
    completeness_score: float
    """
    0.0-1.0: How complete is our understanding?

    Calculated based on:
    - Number of resolved gaps
    - Quality of extracted data
    - Coverage of key skills
    """

    minimum_completeness: float
    """Threshold to stop (e.g., 0.6 = 60% complete is enough)"""

    # ============================================================================
    # TERMINATION CONDITIONS
    # ============================================================================
    should_continue: bool
    """Flag: should we keep asking questions?"""

    termination_reason: Optional[str]
    """
    Why did we stop?
    - "complete": Reached completeness threshold
    - "disengaged": User lost interest
    - "no_gaps": No more gaps to explore
    - None: Still ongoing
    """

    # ============================================================================
    # AGENT-DRIVEN PROCESSING (for answer analysis)
    # ============================================================================
    answer_text: Optional[str]
    """Current answer text being processed"""

    tool_results: Optional[Dict[str, Any]]
    """
    Results from tool execution:
    - skills: List[Skill]
    - engagement: EngagementSignal
    """

    feedback: Optional[str]
    """Feedback text generated for the most recent answer (human-facing)."""

    # ============================================================================
    # METADATA
    # ============================================================================
    questions_asked: int
    """Count of questions asked (for logging/analytics)"""

    # ============================================================================
    # TRANSITION TRACKING (Avoid repetitive phrases)
    # ============================================================================
    recent_transitions: List[str]
    """
    Recent transition phrases used in questions.

    Tracked to avoid repetitive openings like "Good start", "Thanks for sharing".
    Passed to LLM so it can vary its transitions.
    """

    # ============================================================================
    # LANGUAGE (Optional target language for user-facing output)
    # ============================================================================
    language: Optional[str]
    """
    ISO 639-1 language code (e.g. "id", "es", "fr").

    When set (and not "en"), user-facing output (questions, follow-ups,
    greetings, completion messages) will be generated in this language.
    Internal extraction (skills, engagement) always stays in English.
    None or "en" means English (default).
    """


def create_initial_state(
    session_id: str,
    resume_text: str,
    mode: str = "dynamic_gap",
    question_set_id: Optional[str] = None,
    language: Optional[str] = None
) -> InterviewState:
    """
    Create initial state for a new interview session.

    Args:
        session_id: Database session UUID
        resume_text: Resume text to analyze
        mode: Interview mode ("dynamic_gap" or "predefined_questions")
        question_set_id: UUID of predefined question set (required if mode="predefined_questions")
        language: ISO 639-1 language code for user-facing output (e.g. "id", "es"). None or "en" = English.

    Returns:
        Fresh InterviewState ready to start
    """
    return {
        # Session
        "session_id": session_id,
        "resume_text": resume_text,
        "messages": [],

        # Interview mode
        "mode": mode,
        "question_set_id": question_set_id,
        "all_predefined_gaps": None,
        "current_predefined_question": None,

        # Introduction
        "introduction_text": "",

        # Gaps (will be populated by identify_gaps_node or analyze_resume_coverage_node)
        "identified_gaps": [],
        "resolved_gaps": [],
        "current_gap": None,
        "current_question": None,
        "gaps_resolved_this_turn": 0,

        # Engagement
        "engagement_signals": [],
        "consecutive_low_quality": 0,

        # Extracted data
        "extracted_skills": [],

        # Completeness
        "completeness_score": 0.0,
        "minimum_completeness": 0.9 if mode == "dynamic_gap" else 0.6,

        # Termination
        "should_continue": True,
        "termination_reason": None,

        # Agent-driven processing
        "answer_text": None,
        "tool_results": None,
        "feedback": None,

        # Metadata
        "questions_asked": 0,

        # Transition tracking
        "recent_transitions": [],

        # Language
        "language": language
    }
