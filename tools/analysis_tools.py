"""
LangChain tools for resume analysis.

Provides on-demand analysis tools that LLM agents can call during conversations
to extract skills, experience, and behavioral indicators.
"""

import json
from typing import List, Dict, Any
from langchain.tools import tool
from tools.skill_analyzer import SkillAnalyzer
from tools.answer_assessor import AnswerAssessor


# Global analyzer instances (singleton pattern for reuse)
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


@tool
def analyze_technical_skills(answer_text: str, conversation_context: str = "") -> str:
    """
    Extract technical skills with detailed attributes from a candidate's answer.

    **IMPORTANT**: This tool analyzes the ANSWER TEXT only, not the full resume.
    The resume is analyzed once at the start - this tool focuses on NEW information from answers.

    Analyzes skills with 6 key attributes:
    - Duration: How long they've used the skill
    - Depth: Complexity level and aspects implemented
    - Autonomy: Ownership level and independence
    - Scale: Impact size (users, traffic, components)
    - Constraints: Limitations or challenges encountered
    - Production vs Prototype: Production-ready or PoC

    Args:
        answer_text: The candidate's answer to analyze (NOT the full resume)
        conversation_context: Recent conversation Q&A for additional context (optional)

    Returns:
        JSON string with extracted skills and their attributes

    Use this tool when:
    - User mentions technical skills in their answer (Python, React, AWS, etc.)
    - User provides new technical details (duration, scale, autonomy, etc.)
    - You want to extract skill attributes from their current answer
    - User elaborates on previously mentioned skills

    **Do NOT** pass the full resume - only pass the current answer text.
    """
    analyzer = get_skill_analyzer()

    # Parse conversation context if provided
    conversation_history = []
    if conversation_context:
        try:
            # Expect format: "Q: question1\nA: answer1\n\nQ: question2\nA: answer2"
            pairs = conversation_context.split("\n\n")
            for pair in pairs:
                if "Q:" in pair and "A:" in pair:
                    parts = pair.split("\nA:")
                    question = parts[0].replace("Q:", "").strip()
                    answer = parts[1].strip() if len(parts) > 1 else ""
                    conversation_history.append({"question": question, "answer": answer})
        except Exception as e:
            print(f"Warning: Failed to parse conversation context: {e}")

    # Extract skills from ANSWER TEXT only (not full resume)
    # This avoids re-extracting all resume skills on every answer
    skills = analyzer.analyze_skill_attributes(answer_text, conversation_history)

    return json.dumps(skills, indent=2)


@tool
def assess_answer_engagement(question: str, answer: str, gap_description: str = "", gap_category: str = "technical_skill") -> str:
    """
    Assess the engagement level and quality of a candidate's answer.

    Evaluates multiple dimensions:
    - Answer type: direct_answer, partial_answer, off_topic, clarification_request
    - Engagement level: engaged or disengaged (CRITICAL for stopping interview)
    - Detail score: 1-5 rating (how detailed the answer is)
    - Relevance score: 0.0-1.0 (how relevant to the question)
    - Enthusiasm: true/false

    Args:
        question: The question that was asked
        answer: The candidate's answer to assess
        gap_description: Description of the skill gap being addressed (optional)
        gap_category: Category of the gap (e.g., "technical_skill", optional)

    Returns:
        JSON string with engagement assessment

    **When to use**:
    - User seems evasive or reluctant to provide details
    - Answer doesn't address the question clearly
    - This is a follow-up and previous answer was also minimal
    - You're uncertain if the user is engaged

    **When NOT to use**:
    - Answer clearly provides the requested information
    - User is enthusiastically explaining (even if brief)
    - Simple expected answer (e.g., "3 years" for duration question)
    """
    assessor = get_answer_assessor()

    # Build gap dict for context
    gap = {
        "description": gap_description or "Additional skill information",
        "category": gap_category or "technical_skill"
    }

    # Assess the answer
    assessment = assessor.assess_answer(question, answer, gap)

    # Normalize detail_score from 1-5 to 0.0-1.0 for consistency
    if "detail_score" in assessment:
        assessment["detail_score"] = assessment["detail_score"] / 5.0

    return json.dumps(assessment, indent=2)


# Placeholder tools for future analyzers
# Uncomment and implement when ExperienceAnalyzer is ready

# @tool
# def analyze_work_experience(resume_text: str, conversation_context: str = "") -> str:
#     """
#     Extract work experience details including companies, roles, tenure, and achievements.
#
#     Args:
#         resume_text: The candidate's resume text
#         conversation_context: Recent conversation Q&A for additional context (optional)
#
#     Returns:
#         JSON string with work experience details
#
#     Use this tool when:
#     - User discusses career history or job changes
#     - You need context about their professional background
#     - User mentions specific companies or roles
#     """
#     # TODO: Implement ExperienceAnalyzer
#     analyzer = ExperienceAnalyzer()
#     experience = analyzer.analyze_experience(resume_text, conversation_history)
#     return json.dumps(experience, indent=2)


# @tool
# def analyze_behavioral_indicators(resume_text: str, conversation_context: str = "") -> str:
#     """
#     Identify behavioral patterns and soft skills (leadership, collaboration, problem-solving).
#
#     Args:
#         resume_text: The candidate's resume text
#         conversation_context: Recent conversation Q&A for additional context (optional)
#
#     Returns:
#         JSON string with behavioral indicators
#
#     Use this tool when:
#     - Assessing soft skills or team fit
#     - User mentions team dynamics or leadership
#     - You need to understand their working style
#     """
#     # TODO: Implement BehaviorAnalyzer
#     analyzer = BehaviorAnalyzer()
#     behavior = analyzer.analyze_behavior(resume_text, conversation_history)
#     return json.dumps(behavior, indent=2)
