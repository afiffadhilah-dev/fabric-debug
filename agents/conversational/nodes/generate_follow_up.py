"""
Generate follow-up question for natural conversation flow.

Handles:
- Clarification requests (provide examples)
- Vague answers (probe for more detail)
- Yes/no answers (ask for elaboration)
- Partial information (ask specific follow-up)
"""

from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from agents.conversational.state import InterviewState
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from utils.transition_tracker import (
    extract_transition_phrase,
    update_recent_transitions,
    format_transitions_for_prompt
)


def generate_follow_up_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate a follow-up question to get more information on the SAME gap.

    This maintains natural conversation flow when:
    - User asks for clarification
    - Answer was too vague/brief
    - User gave yes/no without elaboration

    Args:
        state: Current interview state

    Returns:
        State updates with:
        - messages: [AIMessage] with follow-up question
        - current_gap: Updated with incremented probes_attempted
    """
    current_question = state.get("current_question")
    current_gap = state.get("current_gap")
    tool_results = state.get("tool_results", {})
    engagement_data = tool_results.get("engagement", {})
    mode = state.get("mode", "dynamic_gap")
    language = state.get("language")

    if not current_question or not current_gap:
        print("WARNING: Missing current_question or current_gap for follow-up!")
        return {}

    original_question = current_question["question_text"]
    answer_type = engagement_data.get("answer_type", "")
    detail_score = engagement_data.get("detail_score", 0)

    # Get the user's last answer
    messages = state.get("messages", [])
    user_answer = messages[-1].content if messages else ""

    print(f"\n=== GENERATE FOLLOW-UP NODE ({mode}) ===")
    print(f"Answer type: {answer_type}, Detail score: {detail_score}")
    print(f"User said: {user_answer[:100]}")

    # Build follow-up prompt based on mode and answer type
    prompt_loader = PromptLoader()

    if mode == "predefined_questions":
        # PREDEFINED MODE: Use criteria-based templates
        # Get from current_question (populated in generate_question) or fallback to current_gap
        what_assesses = current_question.get("what_assesses") or current_gap.get("what_assesses", [])
        criteria_list = ", ".join(what_assesses) if what_assesses else "general competency"

        print(f"Criteria: {criteria_list}")

        if answer_type == "clarification_request":
            follow_up_type = "clarification"
            system_context = prompt_loader.load(
                "follow_up_predefined_clarification",
                mode="conversational",
                original_question=original_question,
                user_answer=user_answer,
                criteria_list=criteria_list
            )
        else:
            follow_up_type = "probe"
            system_context = prompt_loader.load(
                "follow_up_predefined_probe",
                mode="conversational",
                original_question=original_question,
                user_answer=user_answer,
                criteria_list=criteria_list
            )

        # Simple prompt for predefined mode
        prompt = system_context

    else:
        # DYNAMIC GAP MODE: Use skill_name/attribute templates
        skill_name = current_question.get("skill_name", "unknown")
        attribute = current_question.get("attribute", "general")

        print(f"Skill: {skill_name}, Attribute: {attribute}")

        if answer_type == "clarification_request":
            follow_up_type = "clarification"

            # Check if user provided partial information before clarifying
            extracted_skills = tool_results.get("skills", [])
            extracted_info = summarize_extracted_info(extracted_skills)

            system_context = prompt_loader.load(
                "follow_up_clarification",
                mode="conversational",
                original_question=original_question,
                extracted_info=extracted_info
            )
        else:
            # Vague/minimal answer - probe for more detail
            follow_up_type = "probe"
            system_context = prompt_loader.load(
                "follow_up_probe",
                mode="conversational",
                user_answer=user_answer,
                original_question=original_question,
                attribute=attribute,
                skill_name=skill_name
            )

        prompt = prompt_loader.load(
            "follow_up_wrapper",
            mode="conversational",
            follow_up_type=follow_up_type,
            attribute=attribute,
            skill_name=skill_name,
            original_question=original_question,
            user_answer=user_answer,
            system_context=system_context
        )

    system_prompt = prompt_loader.load("follow_up_system", mode="conversational")
    
    # Add transition avoidance context
    recent_transitions = state.get("recent_transitions", [])
    transition_context = format_transitions_for_prompt(recent_transitions)
    if transition_context:
        system_prompt = system_prompt + "\n" + transition_context

    llm = LLMService()
    follow_up_text = llm.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        langcode=language
    ).strip()

    print(f"✅ Generated {follow_up_type} follow-up")
    print(f"Preview: {follow_up_text[:100]}...")

    # Extract and track transition phrase
    new_transition = extract_transition_phrase(follow_up_text)
    updated_transitions = update_recent_transitions(recent_transitions, new_transition)
    
    if new_transition:
        print(f"📝 Tracked transition: \"{new_transition}\"")

    # Increment probe attempts on gap
    updated_gap = dict(current_gap)
    updated_gap["probes_attempted"] = updated_gap.get("probes_attempted", 0) + 1

    # Update question context with new question text
    updated_question = dict(current_question)
    updated_question["question_text"] = follow_up_text

    print(f"  Probe attempts: {updated_gap['probes_attempted']}/{updated_gap['max_probes']}")

    # Update the gap in identified_gaps list as well
    from agents.conversational.conditions import get_gap_identifier
    identified_gaps = list(state.get("identified_gaps", []))
    gap_id = get_gap_identifier(current_gap)

    for i, gap in enumerate(identified_gaps):
        if get_gap_identifier(gap) == gap_id:
            identified_gaps[i] = updated_gap
            print(f"  Updated gap in identified_gaps list")
            break

    # Return state updates
    return {
        "messages": [AIMessage(content=follow_up_text)],
        "current_gap": updated_gap,
        "current_question": updated_question,
        "identified_gaps": identified_gaps,  # Update gaps list
        "questions_asked": state.get("questions_asked", 0) + 1,
        "recent_transitions": updated_transitions  # Track transitions to avoid repetition
    }


def summarize_extracted_info(skills: list) -> str:
    """
    Summarize what information was extracted from a partial answer.

    Used to acknowledge partial information when generating follow-ups.
    Example: "3 years" → "You mentioned 3 years of experience."

    Args:
        skills: List of extracted skills from tool_results

    Returns:
        Human-readable summary of extracted info, or empty string if nothing extracted
    """
    if not skills:
        return ""

    summaries = []
    for skill in skills:
        skill_name = skill.get("name", "")
        attributes = []

        # Check each attribute
        if skill.get("duration"):
            attributes.append(f"duration: {skill['duration']}")
        if skill.get("depth"):
            attributes.append(f"depth: {skill['depth']}")
        if skill.get("autonomy"):
            attributes.append(f"autonomy: {skill['autonomy']}")
        if skill.get("scale"):
            attributes.append(f"scale: {skill['scale']}")
        if skill.get("production_vs_prototype"):
            attributes.append(f"production: {skill['production_vs_prototype']}")
        if skill.get("constraints"):
            attributes.append(f"constraints: {skill['constraints']}")

        if attributes:
            # Create readable summary
            attr_text = ", ".join(attributes)
            summaries.append(f"{skill_name}: {attr_text}")

    if summaries:
        return "You mentioned: " + "; ".join(summaries) + "."
    else:
        return ""

def generate_followup_for_prefilled(
    evidence: str,
    original_question: str,
    category: str,
    what_assesses: list,
    recent_transitions: List[str] = None,
    language: str = None
) -> str:
    """
    Generate a follow-up question for a gap that was pre-filled by a previous answer.

    Instead of asking the full question, acknowledges what was already said and
    asks for additional details or clarification.

    Args:
        evidence: What the candidate already mentioned about this topic
        original_question: The original predefined question
        category: Question category (e.g., "LEADERSHIP EXPERIENCE")
        what_assesses: List of criteria this question assesses
        recent_transitions: List of recently used transition phrases to avoid

    Returns:
        A follow-up question that acknowledges prior information
    """
    from utils.llm_service import LLMService

    print("\n=== GENERATE FOLLOW-UP FOR PREFILLED ===")

    criteria_text = ", ".join(what_assesses) if what_assesses else "this topic"
    
    # Build transition avoidance context
    transition_context = format_transitions_for_prompt(recent_transitions or [])

    # Load prompts from template files
    prompt_loader = PromptLoader()
    
    system_prompt = prompt_loader.load(
        "followup_prefilled_system",
        mode="conversational",
        transition_context=transition_context
    )
    
    human_prompt = prompt_loader.load(
        "followup_prefilled_human",
        mode="conversational",
        evidence=evidence,
        category=category,
        original_question=original_question,
        criteria_text=criteria_text
    )

    llm = LLMService()

    try:
        result = llm.generate(
            prompt=human_prompt,
            system_prompt=system_prompt,
            langcode=language
        ).strip()

        # Ensure result is a question
        if len(result) < 15 or "?" not in result:
            return f"You mentioned {evidence[:50]}... Could you elaborate on that?"

        return result

    except Exception as e:
        print(f"  -> Warning: Failed to generate follow-up for prefilled: {e}")
        # Fallback
        return f"You mentioned something about {category.lower()} earlier. Could you tell me more about that?"