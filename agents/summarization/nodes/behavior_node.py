from agents.summarization.resume.behaviors_extractor import extract_behaviors_from_resume
from agents.summarization.conversation.behaviors_extractor import extract_behaviors_from_conversation
from agents.summarization.behavior_tools import merge_extracted_behaviors, score_behaviors


def behavior_node(state):
    interview = state.get("interview_session")
    candidate_id = interview.candidate_id if interview is not None else None

    answers = state.get("answers", [])
    resume_text = state.get("resume_text", "")

    resume_beh = extract_behaviors_from_resume(resume_text, candidate_id)
    convo_beh = extract_behaviors_from_conversation(answers, candidate_id)

    merged = merge_extracted_behaviors(resume_beh, convo_beh)
    scored = score_behaviors(merged)

    return {
        **state,
        "behavior_observations": scored,
    }
