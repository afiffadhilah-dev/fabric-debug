"""
Extraction tools for LangGraph nodes.

Provides wrapper functions for skill extraction and engagement assessment
that can be called from graph nodes.
"""

import time
from typing import List, Dict, Any
import json
from tools.skill_analyzer import SkillAnalyzer
from tools.answer_assessor import AnswerAssessor
from utils.llm_service import LLMService


# Global tool instances (reused across calls)
_skill_analyzer = None
_answer_assessor = None


def get_skill_analyzer() -> SkillAnalyzer:
    """Get or create global SkillAnalyzer instance."""
    global _skill_analyzer
    if _skill_analyzer is None:
        _skill_analyzer = SkillAnalyzer()
    return _skill_analyzer


def get_answer_assessor() -> AnswerAssessor:
    """Get or create global AnswerAssessor instance."""
    global _answer_assessor
    if _answer_assessor is None:
        _answer_assessor = AnswerAssessor()
    return _answer_assessor


# Tool functions for nodes


def extract_skills_from_conversation(
    resume_text: str,
    conversation_history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extract skills from resume and conversation.

    Args:
        resume_text: Resume text
        conversation_history: List of Q&A dicts

    Returns:
        List of skill dicts with 6 attributes
    """
    analyzer = get_skill_analyzer()
    return analyzer.analyze_skill_attributes(resume_text, conversation_history)


async def extract_skills_from_conversation_async(
    resume_text: str,
    conversation_history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """ASYNC version of extract_skills_from_conversation."""
    analyzer = get_skill_analyzer()
    return await analyzer.analyze_skill_attributes_async(resume_text, conversation_history)


def assess_answer_engagement(
    question: str,
    answer: str,
    gap_description: str,
    what_assesses: List[str],
    category: str = "predefined_questions",
    mode: str = "shared"
) -> str:
    """
    Comprehensively assess a user answer.

    Returns answer type, engagement level, detail score, relevance, and enthusiasm.

    Args:
        question: Question asked
        answer: User's answer
        gap_description: Description of what we're trying to learn

    Returns:
        JSON string with:
        - answer_type: direct_answer, partial_answer, or off_topic
        - engagement_level: engaged or disengaged
        - detail_score: 1-5
        - relevance_score: 0.0-1.0
        - enthusiasm_detected: true/false
        - reasoning: explanation
    """
    # Create a simple gap dict for backward compatibility
    gap = {"description": gap_description}
    assessor = get_answer_assessor()
    result = assessor.assess_answer(question, answer, gap, what_assesses=what_assesses, category=category, mode=mode)
    return result


async def assess_answer_engagement_async(
    question: str,
    answer: str,
    gap: Dict[str, Any]
) -> Dict[str, Any]:
    """ASYNC version of assess_answer_engagement."""
    assessor = get_answer_assessor()
    return await assessor.assess_answer_async(question, answer, gap)


def extract_skill_attribute(answer: str, gap_context: str) -> str:
    """
    Extract skill attribute with EXPLICIT context.

    This is the KEY fix for the "unknown skill" problem!

    Args:
        answer: User's answer text
        gap_context: JSON string with explicit context:
            {
                "skill_name": "Python",  # EXPLICIT!
                "attribute": "duration",  # EXPLICIT!
                "question": "How long have you worked with Python?",
                "answer": "3 years",
                "gap_description": "Python skill - missing duration"
            }

    Returns:
        JSON string with extracted skill data
    """
    context = json.loads(gap_context)

    # Build schema dynamically based on attribute being asked
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            context["attribute"]: {"type": "string"},
            "confidence_score": {"type": "number"},
            "evidence": {"type": "string"}
        },
        "required": ["name", context["attribute"]]
    }

    system_prompt = f"""
Extract the {context['attribute']} for {context['skill_name']} from the candidate's answer.

Question asked: {context['question']}
Candidate answer: {context['answer']}

We are SPECIFICALLY asking about the "{context['attribute']}" attribute for "{context['skill_name']}".

IMPORTANT: The skill name is "{context['skill_name']}" - use this EXACTLY, NOT "unknown".

Return JSON with:
- name: "{context['skill_name']}" (use this exact value!)
- {context['attribute']}: extracted value from the answer
- confidence_score: 0.0-1.0 (how confident you are in the extraction)
- evidence: quote from answer supporting this extraction
"""

    llm = LLMService()
    result = llm.generate_json(
        system_prompt=system_prompt,
        human_prompt="",
        schema=schema
    )

    # Ensure name is correct (defensive programming)
    result["name"] = context["skill_name"]

    return json.dumps(result)


def assess_criteria(
    question: str,
    answer: str,
    what_assesses: List[str],
    category: str = "General"
) -> Dict[str, Any]:
    """
    Assess which criteria were demonstrated in an answer to a predefined question.

    Used in predefined_questions mode to evaluate answers against specific criteria
    (e.g., leadership, decision-making, communication) rather than extracting
    technical skill attributes.

    Args:
        question: The predefined question that was asked
        answer: User's answer
        what_assesses: List of criteria this question assesses
                       (e.g., ["People leadership", "Decision-making skills"])
        category: Question category (e.g., "LEADERSHIP EXPERIENCE")

    Returns:
        Dictionary with structure:
        {
            "answer_quality": 1-5,  # Overall answer quality
            "criteria_assessed": [
                {
                    "criterion": "People leadership",
                    "demonstrated": true/false,
                    "evidence": "Led team of 5 engineers..."
                },
                ...
            ],
            "reasoning": "Explanation of assessment"
        }
    """
    from utils.prompt_loader import PromptLoader

    # Build criteria list for the prompt
    criteria_list = "\n".join([f"- {c}" for c in what_assesses])

    prompt_loader = PromptLoader()
    system_prompt = prompt_loader.load(
        "criteria_assessment",
        mode="shared",
        category=category,
        question=question,
        criteria_list=criteria_list,
        answer=answer
    )


    schema = {
        "type": "object",
        "properties": {
            "answer_quality": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5
            },
            "criteria_assessed": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "criterion": {"type": "string"},
                        "demonstrated": {"type": "boolean"},
                        "evidence": {"type": "string"}
                    },
                    "required": ["criterion", "demonstrated", "evidence"]
                }
            },
            "reasoning": {"type": "string"}
        },
        "required": ["answer_quality", "criteria_assessed", "reasoning"]
    }

    llm = LLMService()

    try:
        result = llm.generate_json(
            system_prompt=system_prompt,
            human_prompt="",
            schema=schema
        )

        if result is None:
            print("  -> WARNING: LLM returned None for criteria assessment - using fallback")
            return _basic_criteria_fallback(answer, what_assesses)
        
        criteria = result.get("criteria_assessed", [])
        demonstrated = sum(1 for c in criteria if c.get("demonstrated"))

        # Debug output
        print(f"  -> Criteria Assessment LLM Response:")
        print(f"     answer_quality: {result.get('answer_quality')}")
        print(f"     criteria_assessed: {demonstrated}/{len(criteria)} demonstrated")
        print(f"     reasoning: {result.get('reasoning', '')[:100]}...")

        return result

    except Exception as e:
        print(f"  -> ERROR in criteria assessment: {e}")
        return _basic_criteria_fallback(answer, what_assesses)


def _basic_criteria_fallback(answer: str, what_assesses: List[str]) -> Dict[str, Any]:
    """
    Basic fallback when LLM criteria assessment fails.

    Uses simple heuristics based on answer length.
    """
    word_count = len(answer.split())

    # Simple quality based on length
    if word_count < 10:
        quality = 1
    elif word_count < 30:
        quality = 2
    elif word_count < 60:
        quality = 3
    elif word_count < 100:
        quality = 4
    else:
        quality = 5

    # Mark all criteria as not demonstrated (conservative fallback)
    criteria_assessed = [
        {
            "criterion": c,
            "demonstrated": False,
            "evidence": "Unable to assess - LLM fallback"
        }
        for c in what_assesses
    ]

    return {
        "answer_quality": quality,
        "criteria_assessed": criteria_assessed,
        "reasoning": "Fallback heuristic assessment due to LLM error"
    }


def analyze_cross_gap_coverage(
    answer: str,
    remaining_gaps: List[Dict[str, Any]],
    current_gap_id: str
) -> List[Dict[str, Any]]:
    """
    Analyze if an answer covers OTHER predefined gaps besides the current one.

    Used in predefined_questions mode to detect when a detailed answer
    addresses multiple questions at once, so we can skip or modify
    subsequent questions.

    Args:
        answer: The user's answer to the current question
        remaining_gaps: List of PredefinedGap dicts that haven't been resolved yet
        current_gap_id: ID of the current gap being answered (to exclude from analysis)

    Returns:
        List of coverage results:
        [
            {
                "question_id": "uuid",
                "question_text": "What leadership experience...",
                "category": "LEADERSHIP EXPERIENCE",
                "covered": True/False,
                "confidence": 0.0-1.0,
                "evidence": "User mentioned leading team of 5..."
            }
        ]
    """
    # Filter out current gap and already-filled gaps
    gaps_to_check = [
        g for g in remaining_gaps
        if g.get("question_id") != current_gap_id
        and not g.get("resume_filled")
        and not g.get("interview_filled")
    ]

    if not gaps_to_check:
        return []

    # Build batch prompt for efficiency (single LLM call for all gaps)
    questions_text = ""
    for i, gap in enumerate(gaps_to_check, 1):
        what_assesses = ", ".join(gap.get("what_assesses", []))
        questions_text += f"""
{i}. Question ID: {gap["question_id"]}
   Category: {gap["category"]}
   Question: {gap["question_text"]}
   Assesses: {what_assesses}
"""

    system_prompt = f"""You are analyzing a candidate's interview answer to determine if it ALSO answers other questions.

## Candidate's Answer
{answer}

## Other Questions to Check
Determine if the answer above provides information that would answer these questions:
{questions_text}

## Instructions
For EACH question, determine:
1. **covered**: Does the answer provide meaningful information that addresses this question? (true/false)
   - true: The answer contains specific, relevant information for this question
   - false: The answer does not address this question, or only tangentially mentions it
2. **confidence**: How confident are you? (0.0-1.0)
   - 0.9+: Answer clearly and thoroughly addresses the question
   - 0.7-0.9: Answer provides good coverage but might benefit from follow-up
   - 0.5-0.7: Answer partially addresses it, follow-up recommended
   - <0.5: Answer barely touches on this topic
3. **evidence**: If covered, quote or summarize the specific part that addresses this question

Be conservative - only mark as "covered" if there's substantial, relevant information.
A passing mention is NOT enough to mark as covered.
"""

    schema = {
        "type": "object",
        "properties": {
            "coverage_results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_id": {"type": "string"},
                        "covered": {"type": "boolean"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "evidence": {"type": "string"}
                    },
                    "required": ["question_id", "covered", "confidence"]
                }
            }
        },
        "required": ["coverage_results"]
    }

    llm = LLMService()

    try:
        result = llm.generate_json(
            system_prompt=system_prompt,
            human_prompt="",
            schema=schema
        )

        if result is None:
            print("  -> WARNING: Cross-gap analysis returned None")
            return []

        coverage_results = result.get("coverage_results", [])

        # Enrich results with question metadata
        gap_lookup = {g["question_id"]: g for g in gaps_to_check}
        enriched_results = []

        for cr in coverage_results:
            q_id = cr.get("question_id")
            if q_id in gap_lookup:
                gap = gap_lookup[q_id]
                enriched_results.append({
                    "question_id": q_id,
                    "question_text": gap["question_text"],
                    "category": gap["category"],
                    "covered": cr.get("covered", False),
                    "confidence": cr.get("confidence", 0.0),
                    "evidence": cr.get("evidence", "")
                })

        # Log results
        covered_count = sum(1 for r in enriched_results if r["covered"])
        print(f"  -> Cross-gap analysis: {covered_count}/{len(gaps_to_check)} other gaps covered by this answer")

        for r in enriched_results:
            if r["covered"]:
                print(f"     📝 {r['category']}: confidence={r['confidence']:.2f}")

        return enriched_results

    except Exception as e:
        print(f"  -> ERROR in cross-gap analysis: {e}")
        return []


def extract_all_skills_from_answer(
    answer: str,
    question: str,
    known_skills: List[Dict[str, Any]],
    current_context: Dict[str, Any],
    conversation_messages: List[Any] = None
) -> List[Dict[str, Any]]:
    """
    Extract ALL skills and attributes from a conversational answer.

    This handles dynamic conversation where user might:
    - Answer multiple attributes at once
    - Mention different skills than asked
    - Provide information for multiple gaps
    - Reference previous answers (e.g., "same like python")

    Args:
        answer: User's answer text
        question: Question that was asked
        known_skills: List of skills we already know about from resume
        current_context: Context of what we asked about (skill_name, attribute)
        conversation_messages: Full conversation history for co-reference resolution

    Returns:
        List of skill dicts with ALL extracted information
    """
    from utils.prompt_loader import PromptLoader

    # Build list of known skill names for context
    skill_names = [s["name"] for s in known_skills]

    # Format conversation history for context
    conversation_text = ""
    if conversation_messages:
        conversation_text = "\n## Previous Conversation\n\n"
        for msg in conversation_messages[:-1]:  # Exclude current answer
            role = "Interviewer" if msg.type == "ai" else "Candidate"
            conversation_text += f"{role}: {msg.content}\n"
        conversation_text += "\n"

    # Load the existing skill extraction template
    prompt_loader = PromptLoader()
    base_prompt = prompt_loader.load("skill_attributes_extraction", mode="shared")

    # Add conversational context
    contextual_prompt = f"""
{base_prompt}
{conversation_text}
## Current Question & Answer

Interviewer asked: {question}
Candidate answered: {answer}

We specifically asked about: {current_context.get('skill_name', 'skills')} - {current_context.get('attribute', 'general info')}

Known skills from resume: {', '.join(skill_names) if skill_names else 'None yet'}

## Task

**EXTRACT ALL information mentioned, even if not directly asked!**

IMPORTANT - Handle conversational references:
- If user says "same like [skill]" or "similar to [skill]", look at the previous conversation to find that skill's attributes
- If user references a previous answer, resolve it using the conversation history above
- User might answer multiple attributes at once (e.g., "3 years in production with 50K users")
- User might mention skills we didn't ask about

Examples:
- Q: "How long with Python?" A: "3 years" → Extract Python: duration="3 years"
- Q: "How long with React?" A: "same like python" → Look at previous Python answer, apply same attributes to React
- A: "Both Python and React for 2 years" → Extract both skills with duration="2 years"

Analyze the current answer and extract all skills with their attributes. Resolve any references to previous answers.
"""

    schema = {
        "type": "object",
        "properties": {
            "skills": {
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
        },
        "required": ["skills"]
    }

    llm = LLMService()
    result = llm.generate_json(
        system_prompt=contextual_prompt,
        human_prompt="",
        schema=schema
    )

    return result.get("skills", [])
