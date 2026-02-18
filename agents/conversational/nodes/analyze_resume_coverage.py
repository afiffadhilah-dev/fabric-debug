"""
Analyze resume coverage node - for predefined_questions mode.

This node fetches predefined questions from the database and analyzes
which questions the resume already answers, so we only ask about gaps.
"""

from typing import Dict, Any, List, Optional
import hashlib
import cachetools
from sqlmodel import Session, select
from uuid import UUID

from agents.conversational.state import InterviewState, PredefinedGap
from models.predefined_question import PredefinedQuestion
from repositories import PredefinedQuestionRepository
from tools.resume_analyzer import analyze_resume_for_all_questions_batch, analyze_resume_for_all_questions_batched
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from config.settings import settings
from utils.database import get_engine as get_cached_engine

# Cache for resume analyses with TTL to prevent memory leak in long-running servers
# TTLCache: maxsize=128 entries, ttl=3600 seconds (1 hour)
_resume_analysis_cache = cachetools.TTLCache(maxsize=128, ttl=3600)


def analyze_resume_coverage_node(
    state: InterviewState,
    predefined_question_repo: Optional[PredefinedQuestionRepository] = None
) -> Dict[str, Any]:
    """
    Analyze which predefined questions can be answered from resume.

    This node runs ONLY in predefined_questions mode. It:
    1. Fetches all questions from the question_set_id
    2. Analyzes resume against each question using LLM
    3. Creates PredefinedGap objects (with resume_filled flag)
    4. Filters out questions where resume provides sufficient answers
    5. Calculates initial completeness score

    Args:
        state: Current interview state (must have mode="predefined_questions")

    Returns:
        Dictionary with state updates:
        - identified_gaps: List[PredefinedGap] - Questions that need asking
        - all_predefined_gaps: List[PredefinedGap] - All questions (for reference)
        - completeness_score: float - Initial completeness (0.0-1.0)

    Raises:
        ValueError: If mode is not "predefined_questions" or question_set_id is missing
    """
    # Validate mode
    mode = state.get("mode")
    if mode != "predefined_questions":
        raise ValueError(
            f"analyze_resume_coverage_node should only run in predefined_questions mode, "
            f"got mode='{mode}'"
        )

    # Get required data from state
    resume_text = state["resume_text"] or ""
    question_set_id = state.get("question_set_id")

    if not question_set_id:
        raise ValueError("question_set_id is required for predefined_questions mode")

    # Initialize services: choose model/provider from env via settings (with sensible fallbacks)
    llm_provider = settings.RESUME_ANALYZER_PROVIDER
    llm_model = settings.RESUME_ANALYZER_MODEL
    llm_service = LLMService(provider=llm_provider, model_name=llm_model)
    prompt_loader = PromptLoader()

    # Fetch questions: prefer injected repository, fall back to local session
    if predefined_question_repo is not None:
        questions = predefined_question_repo.get_by_question_set(UUID(question_set_id))
    else:
        # Backwards-compat fallback: use cached engine (has prepare_threshold, connect_timeout)
        engine = get_cached_engine()
        with Session(engine) as db:
            statement = (
                select(PredefinedQuestion)
                .where(PredefinedQuestion.question_set_id == UUID(question_set_id))
                .order_by(PredefinedQuestion.order)
            )
            questions = db.exec(statement).all()

    if not questions:
        raise ValueError(
            f"No questions found for question_set_id: {question_set_id}. "
            "Please ensure the question set exists and has questions."
        )

    print(f"📋 Analyzing resume against {len(questions)} predefined questions...")

    # Prepare questions for batch analysis
    questions_list = [
        {
            "id": str(q.id),
            "question_text": q.question_text,
            "what_assesses": q.what_assesses,
            "expected_answer_pattern": q.expected_answer_pattern,
            "category": q.category
        }
        for q in questions
    ]

    # BATCH ANALYSIS: Single LLM call for ALL questions (much more efficient!)
    # Using full resume text to avoid oversimplification from filtering
    # Build cache key from resume + question_set_id to avoid repeated LLM calls
    resume_hash = hashlib.sha256(resume_text.encode()).hexdigest()
    cache_key = f"{resume_hash}:{question_set_id}"

    print(f"⚡ Using batch analysis (1 LLM call instead of {len(questions)} calls)...")

    # Check cache first
    if cache_key in _resume_analysis_cache:
        print(f"✨ Cache hit! Returning cached analysis for this resume+question_set.")
        analyses = _resume_analysis_cache[cache_key]
    else:
        # Call LLM and cache the result
        if resume_text.strip() != "":
            analyses = analyze_resume_for_all_questions_batched(
                resume=resume_text,
                questions=questions_list,
                llm_service=llm_service,
                prompt_loader=prompt_loader,
                batch_size=settings.ANALYZE_RESUME_BATCH_SIZE,  # Larger batch size for better efficiency
                max_workers=settings.MAX_WORKER_THREADS  # Use multiple threads for concurrent LLM calls
            )
        else:
            analyses = []
        _resume_analysis_cache[cache_key] = analyses
        print(f"💾 Cached analysis result for future use.")

    # Create lookup for easy access
    analyses_by_id = {a["question_id"]: a for a in analyses}

    # Build gaps from questions and analyses
    all_gaps: List[PredefinedGap] = []
    questions_to_ask: List[PredefinedGap] = []

    for q in questions:
        q_id = str(q.id)
        analysis = analyses_by_id.get(q_id, {
            "is_filled": False,
            "evidence": None,
            "confidence": 0.0
        })

        # Create PredefinedGap object
        gap: PredefinedGap = {
            "category": q.category,
            "question_id": q_id,
            "question_text": q.question_text,
            "what_assesses": q.what_assesses,
            "expected_answer_pattern": q.expected_answer_pattern,
            "is_required": q.is_required,
            "order": q.order,
            "severity": 1.0 if q.is_required else 0.5,  # Required questions = high severity
            # Resume coverage
            "resume_filled": analysis["is_filled"],
            "resume_evidence": analysis.get("evidence"),
            # Interview coverage (will be updated during interview via cross-gap detection)
            "interview_filled": False,
            "interview_evidence": None,
            "coverage_confidence": 0.0,
            # Probing state
            "probes_attempted": 0,
            "max_probes": 2,  # Fewer probes for structured questions
            # User skip state
            "skipped": False,
            "skip_reason": None
        }

        all_gaps.append(gap)

        # Only add to questions_to_ask if NOT filled by resume
        if not analysis["is_filled"]:
            questions_to_ask.append(gap)

    # Calculate initial completeness score
    total_questions = len(all_gaps)
    filled_questions = sum(1 for g in all_gaps if g["resume_filled"])
    completeness_score = filled_questions / total_questions if total_questions > 0 else 0.0

    # Log summary
    print(f"✅ Resume filled {filled_questions}/{total_questions} questions "
          f"({completeness_score:.1%} completeness)")
    print(f"❓ Need to ask {len(questions_to_ask)} questions")

    # Check edge case: All questions filled by resume
    if not questions_to_ask:
        print("🎉 Resume comprehensively answers all questions!")
        return {
            "identified_gaps": [],
            "all_predefined_gaps": all_gaps,
            "completeness_score": 1.0,
            "should_continue": False,
            "termination_reason": "complete"
        }

    # Normal flow: Some questions need asking
    return {
        "identified_gaps": questions_to_ask,  # Only questions we need to ask
        "all_predefined_gaps": all_gaps,      # All questions for reference
        "completeness_score": completeness_score
    }
