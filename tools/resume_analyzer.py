"""
Resume analysis tool for predefined questions mode.

Analyzes whether a resume provides sufficient evidence to answer
interview questions without needing to ask the candidate.
"""

from asyncio.log import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
import json

from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader


def analyze_resume_for_question(
    resume: str,
    question: str,
    what_assesses: List[str],
    expected_pattern: Optional[str] = None,
    llm_service: Optional[LLMService] = None,
    prompt_loader: Optional[PromptLoader] = None
) -> Dict[str, Any]:
    """
    Analyze whether a resume contains sufficient information to answer a question.

    Uses LLM with structured JSON output to determine if resume provides
    clear evidence for all assessment criteria.

    Args:
        resume: Full resume text
        question: Interview question text
        what_assesses: List of assessment criteria the question evaluates
        expected_pattern: Optional guidance on expected answer format
        llm_service: Optional LLMService instance (creates new if None)
        prompt_loader: Optional PromptLoader instance (creates new if None)

    Returns:
        Dictionary with:
        - is_filled (bool): Whether resume provides sufficient answer
        - evidence (str | None): Extracted text from resume if is_filled=True
        - missing_criteria (List[str]): Assessment items not covered by resume
        - confidence (float): 0.0-1.0 confidence score

    Example:
        >>> result = analyze_resume_for_question(
        ...     resume="Led a team of 5 engineers...",
        ...     question="What leadership experience do you have?",
        ...     what_assesses=["People leadership", "Decision-making skills"]
        ... )
        >>> result['is_filled']
        True
        >>> result['confidence']
        0.85
    """
    # Initialize services if not provided
    if llm_service is None:
        llm_service = LLMService()

    if prompt_loader is None:
        prompt_loader = PromptLoader()

    # Load and format system prompt with assessment criteria and expected pattern
    system_prompt = prompt_loader.load(
        "analyze_resume_coverage",
        mode="conversational",
        what_assesses=json.dumps(what_assesses, indent=2),
        expected_answer_pattern=expected_pattern or "No specific pattern provided"
    )

    # Build human prompt with resume and question
    human_prompt = f"""## Resume

{resume}

## Interview Question

{question}

## Assessment Criteria

{json.dumps(what_assesses, indent=2)}

---

Does the resume answer this question sufficiently? Return your analysis as JSON.
"""

    # Define JSON schema for structured output
    schema = {
        "type": "object",
        "properties": {
            "is_filled": {
                "type": "boolean",
                "description": "True if resume clearly addresses ALL assessment criteria"
            },
            "evidence": {
                "type": ["string", "null"],
                "description": "Exact text extracted from resume (if is_filled=true)"
            },
            "missing_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of what_assesses items not covered by resume"
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confidence score between 0.0 and 1.0"
            }
        },
        "required": ["is_filled", "missing_criteria", "confidence"]
    }

    # Call LLM with JSON schema enforcement
    result = llm_service.generate_json(
        system_prompt=system_prompt,
        human_prompt=human_prompt,
        schema=schema
    )

    # Post-processing: Apply confidence threshold
    # Only mark as filled if confidence >= 0.8 (as per conservative approach)
    if result.get("is_filled") and result.get("confidence", 0) < 0.8:
        result["is_filled"] = False
        result["missing_criteria"].append("Low confidence (< 0.8)")

    return result


def analyze_resume_for_all_questions_batch(
    resume: str,
    questions: List[Dict[str, Any]],
    llm_service: Optional[LLMService] = None,
    prompt_loader: Optional[PromptLoader] = None
) -> List[Dict[str, Any]]:
    """
    Analyze resume against ALL questions in a SINGLE LLM call (batch mode).

    MUCH more efficient than looping through questions one by one.
    Instead of 34 LLM calls, this makes 1 call with all questions as context.

    Args:
        resume: Full resume text
        questions: List of question dictionaries with keys:
            - id (str): Question ID
            - question_text (str)
            - what_assesses (List[str])
            - expected_answer_pattern (Optional[str])
            - category (str)
        llm_service: Optional LLMService instance (creates new if None)
        prompt_loader: Optional PromptLoader instance (creates new if None)

    Returns:
        List of analysis results, one per question

    Example:
        >>> questions = [
        ...     {
        ...         "id": "q1",
        ...         "question_text": "What leadership experience do you have?",
        ...         "what_assesses": ["People leadership", "Decision-making"],
        ...         "category": "LEADERSHIP EXPERIENCE"
        ...     },
        ...     # ... 33 more questions
        ... ]
        >>> results = analyze_resume_for_all_questions_batch(resume, questions)
        >>> len(results)  # Same as input
        34
    """
    # Initialize services
    if llm_service is None:
        llm_service = LLMService()

    if prompt_loader is None:
        prompt_loader = PromptLoader()

    # Build comprehensive prompt with ALL questions organized by category
    categories_text = _build_questions_by_category(questions)

    system_prompt = prompt_loader.load(
        "analyze_resume_system",
        mode="shared",
    )

    human_prompt = system_prompt = prompt_loader.load(
        "analyze_resume_human",
        mode="shared",
        resume=resume,
        categories_text=categories_text,
        question_amount=len(questions)
    )

    # Define schema for batch response
    schema = {
        "type": "object",
        "properties": {
            "analyses": {
                "type": "array",
                "description": "Analysis for each question",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_id": {
                            "type": "string",
                            "description": "ID of the question being analyzed"
                        },
                        "is_filled": {
                            "type": "boolean",
                            "description": "True if resume clearly addresses ALL assessment criteria"
                        },
                        "evidence": {
                            "type": ["string", "null"],
                            "description": "Exact text extracted from resume (if is_filled=true)"
                        },
                        "missing_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of assessment items not covered by resume"
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Confidence score between 0.0 and 1.0"
                        }
                    },
                    "required": ["question_id", "is_filled", "missing_criteria", "confidence"]
                }
            }
        },
        "required": ["analyses"]
    }

    # Single LLM call for all questions
    result = llm_service.generate_json(
        system_prompt=system_prompt,
        human_prompt=human_prompt,
        schema=schema
    )

    # Post-process results
    analyses = result.get("analyses", [])

    # Create lookup for easy access
    analyses_by_id = {a["question_id"]: a for a in analyses}

    # Build final results matching input order and adding metadata
    final_results = []
    for q in questions:
        q_id = str(q.get("id"))
        analysis = analyses_by_id.get(q_id, {
            "is_filled": False,
            "evidence": None,
            "missing_criteria": ["Analysis not returned by LLM"],
            "confidence": 0.0
        })

        # Apply confidence threshold (conservative approach)
        if analysis.get("is_filled") and analysis.get("confidence", 0) < 0.8:
            analysis["is_filled"] = False
            analysis["missing_criteria"].append("Low confidence (< 0.8)")

        # Add question metadata
        analysis["question_id"] = q_id
        analysis["question_text"] = q["question_text"]
        analysis["category"] = q.get("category", "Uncategorized")

        final_results.append(analysis)

    return final_results

def chunk_questions(questions: List[Dict[str, Any]], chunk_size: int):
    for i in range(0, len(questions), chunk_size):
        yield questions[i:i + chunk_size]


def analyze_resume_for_all_questions_batched(
    resume: str,
    questions: List[Dict[str, Any]],
    llm_service: LLMService,
    prompt_loader: PromptLoader,
    batch_size: int = 5,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    final_results = []

    batches = list(chunk_questions(questions, batch_size))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {
            executor.submit(
                analyze_resume_for_all_questions_batch,
                resume=resume,
                questions=batch,
                llm_service=llm_service,
                prompt_loader=prompt_loader
            ): batch
            for batch in batches
        }

        for future in as_completed(future_to_batch):
            batch = future_to_batch[future]
            try:
                batch_results = future.result()
                final_results.extend(batch_results)
            except Exception as e:
                # Log the failure with enough context to debug
                logger.exception(
                    "Resume analysis batch failed",
                    extra={
                        "batch_size": len(batch),
                        "question_ids": [q.get("id") for q in batch]
                    }
                )

    return final_results


def _build_questions_by_category(questions: List[Dict[str, Any]]) -> str:
    """
    Build formatted text with questions organized by category.

    This helps LLM process related questions together for efficiency.
    """
    # Group questions by category
    by_category = {}
    for q in questions:
        category = q.get("category", "Uncategorized")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(q)

    # Build formatted output
    lines = []
    for category, qs in by_category.items():
        lines.append(f"\n### {category}\n")
        for q in qs:
            lines.append(f"**Question ID:** {q.get('id')}")
            lines.append(f"**Question:** {q['question_text']}")
            lines.append(f"**Assesses:** {', '.join(q['what_assesses'])}")
            if q.get("expected_answer_pattern"):
                lines.append(f"**Expected Pattern:** {q['expected_answer_pattern']}")
            lines.append("")

    return "\n".join(lines)


def analyze_resume_for_multiple_questions(
    resume: str,
    questions: List[Dict[str, Any]],
    llm_service: Optional[LLMService] = None,
    prompt_loader: Optional[PromptLoader] = None
) -> List[Dict[str, Any]]:
    """
    Analyze resume against multiple questions in batch.

    DEPRECATED: Use analyze_resume_for_all_questions_batch() instead for better performance.
    This function loops through questions one-by-one (N LLM calls).
    The batch function makes only 1 LLM call for all questions.

    More efficient than calling analyze_resume_for_question() repeatedly
    as it reuses the same LLMService and PromptLoader instances.

    Args:
        resume: Full resume text
        questions: List of question dictionaries with keys:
            - question_text (str)
            - what_assesses (List[str])
            - expected_answer_pattern (Optional[str])
        llm_service: Optional LLMService instance (creates new if None)
        prompt_loader: Optional PromptLoader instance (creates new if None)

    Returns:
        List of analysis results, one per question

    Example:
        >>> questions = [
        ...     {
        ...         "question_text": "What leadership experience do you have?",
        ...         "what_assesses": ["People leadership", "Decision-making"],
        ...         "expected_answer_pattern": "Mentions team size, responsibilities"
        ...     },
        ...     # ... more questions
        ... ]
        >>> results = analyze_resume_for_multiple_questions(resume, questions)
        >>> len(results)
        34
    """
    # Initialize services once for all questions
    if llm_service is None:
        llm_service = LLMService()

    if prompt_loader is None:
        prompt_loader = PromptLoader()

    results = []

    for q in questions:
        result = analyze_resume_for_question(
            resume=resume,
            question=q["question_text"],
            what_assesses=q["what_assesses"],
            expected_pattern=q.get("expected_answer_pattern"),
            llm_service=llm_service,
            prompt_loader=prompt_loader
        )

        # Add question metadata to result
        result["question_id"] = q.get("id")
        result["question_text"] = q["question_text"]
        result["category"] = q.get("category")

        results.append(result)

    return results
