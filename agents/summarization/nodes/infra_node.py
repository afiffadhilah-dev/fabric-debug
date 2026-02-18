from agents.summarization.resume.infra_agent import ResumeInfraAgent
from agents.summarization.conversation.infra_agent import ConversationInfraAgent
from agents.summarization.merger.merge_extracted import merge_infra


def infra_node(state):
    cid = state["interview_session"].candidate_id

    resume = ResumeInfraAgent().analyze(
        state.get("resume_text", ""),
        cid
    )

    convo = ConversationInfraAgent().analyze(
        state.get("answers", []),
        cid
    )

    merged = merge_infra(resume, convo)

    return {
        **state,
        "infra_contexts": merged.get("infra_contexts", []),
    }
