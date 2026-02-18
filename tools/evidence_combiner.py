"""
Evidence combiner tool for merging cross-gap and direct answer evidence.

When a low-confidence interview_filled gap receives a direct answer,
this tool evaluates whether the new evidence is redundant or complementary
and calculates a combined confidence score.
"""

from typing import Dict, Any, List
from utils.llm_service import LLMService


def evaluate_combined_evidence(
    original_evidence: str,
    new_evidence: str,
    criteria: List[str],
    original_confidence: float = 0.0
) -> Dict[str, Any]:
    """
    Evaluate combined evidence from cross-gap detection and direct answer.

    Determines if the new evidence is redundant or adds new information,
    and calculates a combined confidence score.

    Args:
        original_evidence: Evidence from cross-gap detection
        new_evidence: Evidence from direct answer to the question
        criteria: List of criteria this gap assesses (e.g., ["Architecture ownership", "Scalability"])
        original_confidence: Original confidence from cross-gap detection (0.0-1.0)

    Returns:
        Dictionary with:
        - combined_confidence: float (0.0-1.0) - How well combined evidence covers criteria
        - is_redundant: bool - Whether new evidence mostly repeats original
        - new_information_added: List[str] - What new information was added
        - combined_evidence: str - Merged evidence summary
        - reasoning: str - Explanation of the evaluation
    """
    if not original_evidence or not new_evidence:
        # If either is missing, just use what we have
        if new_evidence and not original_evidence:
            return {
                "combined_confidence": 0.85,  # Direct answer without prior evidence
                "is_redundant": False,
                "new_information_added": ["Direct answer provided"],
                "combined_evidence": new_evidence,
                "reasoning": "Only direct answer available, no prior evidence to combine"
            }
        elif original_evidence and not new_evidence:
            return {
                "combined_confidence": original_confidence,
                "is_redundant": True,
                "new_information_added": [],
                "combined_evidence": original_evidence,
                "reasoning": "No new evidence provided"
            }
        else:
            return {
                "combined_confidence": 0.0,
                "is_redundant": True,
                "new_information_added": [],
                "combined_evidence": "",
                "reasoning": "No evidence available"
            }

    criteria_text = ", ".join(criteria) if criteria else "the topic"

    system_prompt = """You are an evidence evaluator for interview assessments.

Your task is to compare two pieces of evidence about a candidate and determine:
1. Whether the new evidence adds NEW information or is mostly redundant
2. What specific new information was added (if any)
3. How well the COMBINED evidence covers the assessment criteria
4. A merged summary of both pieces of evidence

Be precise and objective. Focus on factual information, not writing style."""

    human_prompt = f"""## Assessment Criteria
This evidence should demonstrate: {criteria_text}

## Original Evidence (from earlier in the interview)
{original_evidence}

## New Evidence (from direct answer to follow-up question)
{new_evidence}

## Your Task
Analyze both pieces of evidence and provide:

1. **Is Redundant**: Does the new evidence mostly repeat what was already said? (true/false)
   - true = 80%+ of new evidence was already covered
   - false = significant new information added

2. **New Information Added**: List specific NEW facts/details not in original evidence
   - Be specific (e.g., "mentioned 10k users scale", "described conflict resolution approach")
   - Empty list if redundant

3. **Combined Confidence**: How well does the COMBINED evidence cover the criteria? (0.0-1.0)
   - 0.9-1.0: Excellent coverage with specific examples and metrics
   - 0.7-0.9: Good coverage with clear examples
   - 0.5-0.7: Partial coverage, missing some aspects
   - Below 0.5: Weak coverage

4. **Combined Evidence**: A concise merged summary (2-3 sentences) capturing key points from BOTH

5. **Reasoning**: Brief explanation of your evaluation"""

    schema = {
        "type": "object",
        "properties": {
            "is_redundant": {
                "type": "boolean",
                "description": "Whether new evidence mostly repeats original (80%+ overlap)"
            },
            "new_information_added": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific new facts/details added"
            },
            "combined_confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "How well combined evidence covers criteria (0.0-1.0)"
            },
            "combined_evidence": {
                "type": "string",
                "description": "Merged summary of both pieces of evidence"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of the evaluation"
            }
        },
        "required": ["is_redundant", "new_information_added", "combined_confidence", "combined_evidence", "reasoning"]
    }

    llm = LLMService()

    try:
        result = llm.generate_json(
            system_prompt=system_prompt,
            human_prompt=human_prompt,
            schema=schema
        )

        if result is None:
            # Fallback: assume complementary if we got here
            return _fallback_evaluation(original_evidence, new_evidence, original_confidence)

        # Ensure confidence doesn't decrease from original
        result["combined_confidence"] = max(
            result.get("combined_confidence", original_confidence),
            original_confidence
        )

        print(f"  -> Evidence evaluation: redundant={result['is_redundant']}, "
              f"confidence={result['combined_confidence']:.2f}, "
              f"new_info={len(result.get('new_information_added', []))} items")

        return result

    except Exception as e:
        print(f"  -> Warning: Evidence evaluation failed: {e}")
        return _fallback_evaluation(original_evidence, new_evidence, original_confidence)


def _fallback_evaluation(
    original_evidence: str,
    new_evidence: str,
    original_confidence: float
) -> Dict[str, Any]:
    """
    Fallback evaluation when LLM fails.

    Uses simple heuristics to estimate if evidence is redundant.
    """
    # Simple heuristic: check word overlap
    original_words = set(original_evidence.lower().split())
    new_words = set(new_evidence.lower().split())

    # Remove common words
    common_words = {"the", "a", "an", "is", "are", "was", "were", "i", "we", "my", "our",
                   "have", "had", "has", "with", "for", "to", "of", "and", "in", "on"}
    original_words -= common_words
    new_words -= common_words

    if not original_words or not new_words:
        return {
            "combined_confidence": max(0.85, original_confidence),
            "is_redundant": False,
            "new_information_added": ["Direct answer provided"],
            "combined_evidence": f"{original_evidence} Additionally: {new_evidence}",
            "reasoning": "Fallback: Unable to evaluate overlap, assuming complementary"
        }

    # Calculate overlap
    overlap = len(original_words & new_words)
    overlap_ratio = overlap / len(new_words) if new_words else 0

    is_redundant = overlap_ratio > 0.6  # 60%+ word overlap = likely redundant

    # Boost confidence based on redundancy
    if is_redundant:
        # Redundant = same info confirmed, small boost
        combined_confidence = min(1.0, original_confidence + 0.05)
    else:
        # New info = bigger boost
        combined_confidence = min(1.0, original_confidence + 0.15)

    return {
        "combined_confidence": combined_confidence,
        "is_redundant": is_redundant,
        "new_information_added": [] if is_redundant else ["New details from direct answer"],
        "combined_evidence": f"{original_evidence} Additionally: {new_evidence}",
        "reasoning": f"Fallback heuristic: {overlap_ratio:.0%} word overlap"
    }


async def evaluate_combined_evidence_async(
    original_evidence: str,
    new_evidence: str,
    criteria: List[str],
    original_confidence: float = 0.0
) -> Dict[str, Any]:
    """Async version of evaluate_combined_evidence."""
    # For now, just call the sync version
    # TODO: Implement true async with generate_json_async
    return evaluate_combined_evidence(
        original_evidence, new_evidence, criteria, original_confidence
    )
