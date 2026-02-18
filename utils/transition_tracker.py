"""
Transition phrase tracking utility.

Tracks transition phrases used in interview questions to avoid repetitive openings
like "Good start", "Thanks for sharing", etc.
"""

import re
from typing import List, Optional


# Configuration: How many recent transitions to track
MAX_RECENT_TRANSITIONS = 7


def extract_transition_phrase(text: str) -> Optional[str]:
    """
    Extract the transition/opening phrase from a question.
    
    Looks for the opening phrase before the main question content.
    Common patterns:
    - "That's a good start—could you tell me..." → "That's a good start"
    - "Thanks for sharing that. Now..." → "Thanks for sharing that"
    - "Building on that, ..." → "Building on that"
    - "I see. What about..." → "I see"
    
    Args:
        text: The full question text
        
    Returns:
        Extracted transition phrase, or None if no clear transition found
    """
    if not text or len(text) < 10:
        return None
    
    # Normalize text - convert curly apostrophes to straight
    text = text.strip()
    text_normalized = text.replace("’", "'").replace("'", "'")
    
    # Pattern 1: Look for phrase before em-dash (— or --)
    if "—" in text:
        phrase = text.split("—")[0].strip()
        if 3 <= len(phrase) <= 60:
            return phrase
    
    # Pattern 2: Look for phrase before common transition punctuation
    # Split on period, exclamation, or comma followed by transition words
    transition_markers = [
        r'^([^.!?]+[.!])\s*(?:Now|So|Let|Can|Could|Would|I\'d|Moving|Speaking|Regarding)',
        r'^([^.!?]+[.!])\s+[A-Z]',  # Sentence followed by capital letter
    ]
    
    for pattern in transition_markers:
        match = re.match(pattern, text_normalized)
        if match:
            phrase = match.group(1).strip().rstrip('.!?')
            if 3 <= len(phrase) <= 60:
                return phrase
    
    # Pattern 3: Common short transition patterns at start
    short_patterns = [
        r'^(That\'s (?:a )?(?:good|great|nice|helpful|excellent|useful|clear)[^.!,—]*)',
        r'^(Thanks?(?: for)?[^.!,—]*)',
        r'^(Good (?:start|point|to know|overview|context|background)[^.!,—]*)',
        r'^(Great[^.!,—]*)',
        r'^(Nice[^.!,—]*)',
        r'^(I see[^.!,—]*)',
        r'^(Interesting[^.!,—]*)',
        r'^(Got it[^.!,—]*)',
        r'^(Understood[^.!,—]*)',
        r'^(Building on (?:that|what you|your)[^.!,—]*)',
        r'^(Speaking of[^.!,—]*)',
        r'^(Moving on[^.!,—]*)',
        r'^(Regarding[^.!,—]*)',
        r'^(That gives[^.!,—]*)',
        r'^(That helps[^.!,—]*)',
        r'^(Helpful[^.!,—]*)',
        r'^(Good to (?:know|hear)[^.!,—]*)',
    ]
    
    for pattern in short_patterns:
        match = re.match(pattern, text_normalized, re.IGNORECASE)
        if match:
            phrase = match.group(1).strip()
            if 3 <= len(phrase) <= 60:
                return phrase
    
    # Pattern 4: First sentence if it's short (likely a transition)
    first_sentence_match = re.match(r'^([^.!?]+[.!?])', text_normalized)
    if first_sentence_match:
        first_sentence = first_sentence_match.group(1).strip()
        # Only count as transition if short and doesn't contain a question
        if len(first_sentence) <= 50 and '?' not in first_sentence:
            return first_sentence.rstrip('.!?')
    
    return None


def update_recent_transitions(
    current_transitions: List[str],
    new_transition: Optional[str],
    max_count: int = MAX_RECENT_TRANSITIONS
) -> List[str]:
    """
    Update the list of recent transitions with a new one.
    
    Maintains a rolling window of the most recent transitions.
    
    Args:
        current_transitions: Current list of tracked transitions
        new_transition: New transition to add (can be None)
        max_count: Maximum number of transitions to keep
        
    Returns:
        Updated list of transitions
    """
    if not new_transition:
        return current_transitions
    
    # Normalize for comparison (lowercase, strip)
    normalized_new = new_transition.lower().strip()
    
    # Don't add duplicates (check normalized versions)
    for existing in current_transitions:
        if existing.lower().strip() == normalized_new:
            return current_transitions
    
    # Add new transition and trim to max
    updated = list(current_transitions)
    updated.append(new_transition)
    
    # Keep only the most recent max_count
    if len(updated) > max_count:
        updated = updated[-max_count:]
    
    return updated


def format_transitions_for_prompt(transitions: List[str]) -> str:
    """
    Format the list of recent transitions for inclusion in LLM prompt.
    
    Args:
        transitions: List of recent transition phrases
        
    Returns:
        Formatted string for prompt, or empty string if no transitions
    """
    if not transitions:
        return ""
    
    transitions_list = "\n".join(f"- \"{t}\"" for t in transitions)
    
    return f"""
These transition phrases have already been used:
{transitions_list}

Try varying with different ones, or go directly to the question without a transition.
"""