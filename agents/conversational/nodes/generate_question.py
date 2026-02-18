"""
Generate question node - following LangGraph workflow pattern.

Direct LLM call, saves explicit QuestionContext.
"""

from typing import Dict, Any, List
import uuid
from langchain_core.messages import AIMessage
from agents.conversational.state import InterviewState, QuestionContext
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from utils.transition_tracker import (
    extract_transition_phrase,
    update_recent_transitions,
    format_transitions_for_prompt
)
from agents.conversational.nodes.generate_follow_up import generate_followup_for_prefilled


def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate question for current gap with EXPLICIT context saving.

    MODE-AWARE:
    - Dynamic Gap Mode: Generates question dynamically using LLM
    - Predefined Questions Mode: Uses predefined question_text directly

    From LangGraph docs: "Nodes are simple functions" - direct LLM call,
    NOT creating an agent.

    Args:
        state: Current interview state

    Returns:
        State updates with:
        - messages: [AIMessage] with question
        - current_question: QuestionContext with EXPLICIT skill/attribute
        - questions_asked: incremented
    """

    current_gap = state.get("current_gap")
    mode = state.get("mode", "dynamic_gap")
    questions_asked = state.get("questions_asked", 0)
    introduction_text = state.get("introduction_text", "")
    language = state.get("language")

    if not current_gap:
        # No gap - shouldn't happen
        return {}

    print(f"\n=== GENERATE QUESTION NODE ({mode}) ===")
    print(f"Gap: {current_gap.get('description', current_gap.get('question_text'))}")

    # MODE-SPECIFIC QUESTION GENERATION
    if mode == "predefined_questions":
        # PREDEFINED MODE: Use question_text directly from current_gap (which is a PredefinedGap)
        base_question_text = current_gap.get("question_text", "Can you tell me more?")
        category = current_gap.get("category", "General")
        what_assesses = current_gap.get("what_assesses", [])

        print(f"Category: {category}")
        print(f"What Assesses: {', '.join(what_assesses)}")

        # Check if this gap was pre-filled by a previous answer (cross-gap detection)
        is_interview_filled = current_gap.get("interview_filled", False)
        interview_evidence = current_gap.get("interview_evidence", "")

        messages = state.get("messages", [])
        questions_asked = state.get("questions_asked", 0)

        if is_interview_filled and interview_evidence:
            # Gap was already partially covered - generate follow-up instead of full question
            recent_transitions = state.get("recent_transitions", [])
            question_text = generate_followup_for_prefilled(
                evidence=interview_evidence,
                original_question=base_question_text,
                category=category,
                what_assesses=what_assesses,
                recent_transitions=recent_transitions,
                language=language
            )
            print(f"✅ Generated follow-up for pre-filled gap (evidence: {interview_evidence[:50]}...)")
        elif questions_asked > 0 and len(messages) >= 2:
            # Generate contextual question with transition using LLM
            recent_transitions = state.get("recent_transitions", [])
            question_text = _generate_contextual_question(
                messages=messages,
                next_question=base_question_text,
                category=category,
                recent_transitions=recent_transitions,
                language=language
            )
            print(f"✅ Generated contextual question with transition")
        elif language and language.lower() != "en":
            # First question + non-English: translate directly via langcode
            # Don't use _generate_contextual_question here — it assumes prior
            # conversation exists and will hallucinate an acknowledgment.
            llm = LLMService()
            question_text = llm.generate(
                prompt=f"Deliver this interview question to the candidate:\n\n{base_question_text}",
                system_prompt="You are a friendly interviewer. Output only the question, nothing else.",
                langcode=language
            ).strip() or base_question_text
            print(f"✅ Translated first question to target language")
        else:
            # First question - use as-is
            question_text = base_question_text
            print(f"✅ Using predefined question (first question)")

        # Build question context for predefined mode
        # - skill_name/attribute: None (not applicable for predefined mode)
        # - category/what_assesses: From PredefinedGap
        question_context: QuestionContext = {
            "question_id": current_gap.get("question_id", str(uuid.uuid4())),
            "question_text": question_text,
            "gap_description": base_question_text,  # Keep original for gap tracking
            # Dynamic gap fields - None for predefined mode
            "skill_name": None,
            "attribute": None,
            # Predefined mode fields
            "category": category,
            "what_assesses": what_assesses,
        }

        print(f"Question: {question_text[:80]}...")

    else:
        # DYNAMIC GAP MODE: Generate question dynamically using LLM
        skill_name, attribute = parse_gap_context(current_gap)

        print(f"Skill: {skill_name}")
        print(f"Attribute: {attribute}")

        # Build EXPLICIT question context BEFORE generating question
        question_context: QuestionContext = {
            "question_id": f"{skill_name}_{attribute}_{uuid.uuid4().hex[:8]}",
            "question_text": "",  # Will be filled after generation
            "gap_description": current_gap["description"],
            # Dynamic gap fields - EXPLICIT!
            "skill_name": skill_name,
            "attribute": attribute,
            # Predefined mode fields - None for dynamic_gap mode
            "category": None,
            "what_assesses": None,
        }

        # Generate question using direct LLM call
        llm = LLMService()
        prompt_loader = PromptLoader()

        system_prompt = prompt_loader.load("system", mode="conversational")

        # Check if we're switching skills (for conversational transitions)
        previous_question = state.get("current_question")
        previous_skill = previous_question.get("skill_name") if previous_question else None

        # Detect skill switch
        skill_switched = (previous_skill is not None and
                         previous_skill != skill_name and
                         previous_skill.lower() != skill_name.lower())

        # Check if multiple gaps were resolved in previous answer (for acknowledgment)
        gaps_resolved_last_turn = state.get("gaps_resolved_this_turn", 0)

        # Check if we're RETURNING to a previously-asked gap (contextual follow-up)
        probes_attempted = current_gap.get("probes_attempted", 0)
        returning_to_gap = probes_attempted >= 1

        transition_context = ""
        acknowledgment_context = ""
        returning_context = ""

        if skill_switched:
            transition_context = f"The previous question was about {previous_skill}. Now we're asking about {skill_name}. Add a brief transition phrase to acknowledge the topic switch, such as 'Thanks for those details about {previous_skill}. Now let's discuss {skill_name}...' or 'Great! Moving on to {skill_name}...'"
            print(f"🔄 Skill switch detected: {previous_skill} → {skill_name}")

        if gaps_resolved_last_turn >= 2:
            acknowledgment_context = f"\n\nIMPORTANT: The user's previous answer covered {gaps_resolved_last_turn} different requirements at once! Start your question by acknowledging this: 'Great! You've covered multiple aspects...' or 'Excellent! That answered several requirements...'"
            print(f"🎯 Multi-gap acknowledgment: {gaps_resolved_last_turn} gaps resolved")

        if returning_to_gap:
            returning_context = f"\n\nCONTEXTUAL RETURN: We asked about {skill_name} {attribute} earlier (probe {probes_attempted + 1}/{current_gap.get('max_probes', 3)}). Acknowledge we're circling back: 'Coming back to {skill_name}...' or 'Earlier you mentioned {skill_name}. Let me ask more specifically...' This makes re-asking feel natural, not repetitive."
            print(f"🔁 Returning to gap: {skill_name} - {attribute} (probe {probes_attempted + 1}/{current_gap.get('max_probes', 3)})")

        # Load dynamic question prompt
        combined_context = transition_context + acknowledgment_context + returning_context
        question_prompt = prompt_loader.load(
            "dynamic_question",
            mode="conversational",
            skill_name=skill_name,
            attribute=attribute,
            gap_description=current_gap['description'],
            transition_context=combined_context
        )

        # Direct LLM call (no agent!)
        question_text = llm.generate(
            prompt=question_prompt,
            system_prompt=system_prompt,
            langcode=language
        ).strip()

        # Save question text in context
        question_context["question_text"] = question_text

        print(f"✅ Generated: {question_text}")
        print(f"✅ Saved context: {skill_name} - {attribute}")

    # Increment probe attempts for this gap
    updated_gap = dict(current_gap)
    updated_gap["probes_attempted"] = updated_gap.get("probes_attempted", 0) + 1

    print(f"  Probe attempts: {updated_gap['probes_attempted']}/{updated_gap['max_probes']}")

    # Update the gap in identified_gaps list as well
    from agents.conversational.conditions import get_gap_identifier
    identified_gaps = list(state.get("identified_gaps", []))
    gap_id = get_gap_identifier(current_gap)

    for i, gap in enumerate(identified_gaps):
        if get_gap_identifier(gap) == gap_id:
            identified_gaps[i] = updated_gap
            break
            
    # Extract and track transition phrase from generated question
    current_transitions = state.get("recent_transitions", [])
    new_transition = extract_transition_phrase(question_text)
    updated_transitions = update_recent_transitions(current_transitions, new_transition)
    
    if new_transition:
        print(f"📝 Tracked transition: \"{new_transition}\"")
    
    # Prepend introduction to first question if available
    if introduction_text and questions_asked == 0:
        question_text = f"{introduction_text}\n\n{question_text}"
        print(f"Prepended introduction to question")

    # Return state updates
    return {
        "messages": [AIMessage(content=question_text)],
        "current_question": question_context,  # ⭐ KEY: Save explicit context!
        "current_gap": updated_gap,  # Update gap with incremented probes
        "identified_gaps": identified_gaps,  # Update gaps list
        "questions_asked": state.get("questions_asked", 0) + 1,
        "recent_transitions": updated_transitions  # Track transitions to avoid repetition
    }


def parse_gap_context(gap: Dict[str, Any]) -> tuple[str, str]:
    """
    Parse skill name and attribute from gap context.

    Gap context format: "Python skill - missing duration"
                        "JavaScript skill - need depth"
                        etc.

    Returns:
        (skill_name, attribute)
    """
    context = gap.get("context", "")
    description = gap.get("description", "")

    # Try to extract from context first
    # Format: "Python skill - missing duration" or "Python skill - need: duration, scale"
    if " skill - " in context:
        parts = context.split(" skill - ")
        skill_name = parts[0].strip()

        # Extract attribute(s)
        attr_part = parts[1].strip()

        # Handle "missing" format
        if "missing" in attr_part:
            attr_part = attr_part.replace("missing", "").strip()
        # Handle "need:" format (with colon)
        elif "need:" in attr_part:
            attr_part = attr_part.split("need:")[1].strip()
        # Handle "need" format (without colon)
        elif "need" in attr_part:
            attr_part = attr_part.replace("need", "").strip()

        # If multiple attributes (comma-separated), take the first one
        if "," in attr_part:
            attribute = attr_part.split(",")[0].strip()
        else:
            attribute = attr_part.strip()

        return skill_name, attribute

    # Fallback: try to parse from description
    # This is less reliable, might need improvement
    for attr in ["duration", "depth", "autonomy", "scale", "constraints", "production_vs_prototype"]:
        if attr in description.lower() or attr in context.lower():
            # Try to extract skill name (first word usually)
            skill_name = context.split()[0] if context else "unknown"
            return skill_name, attr

    # Last resort
    return "unknown", "general_info"


def _generate_contextual_question(
    messages: list,
    next_question: str,
    category: str,
    recent_transitions: List[str] = None,
    language: str = None
) -> str:
    """
    Generate a contextual question with natural transition based on conversation history.

    Uses LLM to:
    1. Acknowledge what the user shared in their previous answer
    2. Create a natural bridge to the next question
    3. Optionally connect to relevant context from their answer
    4. Avoid using recently-used transition phrases

    Args:
        messages: Conversation history (list of BaseMessage)
        next_question: The predefined question to ask next
        category: Category of the next question (e.g., "LEADERSHIP EXPERIENCE")
        recent_transitions: List of recently used transition phrases to avoid

    Returns:
        Contextual question with transition
    """
    from utils.llm_service import LLMService

    # Get recent conversation context (last 2-4 messages)
    recent_messages = messages[-4:] if len(messages) > 4 else messages

    # Format conversation for prompt
    conversation_text = ""
    for msg in recent_messages:
        role = "Interviewer" if msg.type == "ai" else "Candidate"
        content = msg.content[:300] if len(msg.content) > 300 else msg.content
        conversation_text += f"{role}: {content}\n"

    # Build transition avoidance context
    transition_context = format_transitions_for_prompt(recent_transitions or [])

    # Load prompts from template files
    prompt_loader = PromptLoader()
    
    system_prompt = prompt_loader.load(
        "contextual_question_system",
        mode="conversational",
        transition_context=transition_context
    )
    
    human_prompt = prompt_loader.load(
        "contextual_question_human",
        mode="conversational",
        conversation_text=conversation_text,
        category=category,
        next_question=next_question
    )

    llm = LLMService()

    # Fallback transitions to use when LLM fails
    fallback_transitions = [
        "I see.",
        "Got it.",
        "Understood.",
        "Thanks.",
        "",  # No transition - go directly to question
    ]
    
    try:
        result = llm.generate(
            prompt=human_prompt,
            system_prompt=system_prompt,
            langcode=language
        ).strip()

        # Ensure the result contains the core question intent
        # If LLM output is too short or doesn't include question, fall back
        if len(result) < 20 or "?" not in result:
            # Pick a fallback that wasn't recently used
            for fallback in fallback_transitions:
                if fallback.lower() not in [t.lower() for t in (recent_transitions or [])]:
                    if fallback:
                        return f"{fallback} {next_question}"
                    return next_question
            return next_question  # No transition if all were used

        return result

    except Exception as e:
        print(f"  -> Warning: Failed to generate contextual question: {e}")
        # Fallback - pick one that wasn't recently used
        for fallback in fallback_transitions:
            if fallback.lower() not in [t.lower() for t in (recent_transitions or [])]:
                if fallback:
                    return f"{fallback} {next_question}"
                return next_question
        return next_question
