from agents.summarization.resume.domain_agent import ResumeDomainAgent
from agents.summarization.conversation.domain_agent import ConversationDomainAgent
from agents.summarization.merger.merge_extracted import merge_domains


def domain_node(state):
    cid = state["interview_session"].candidate_id

    resume = ResumeDomainAgent().analyze(
        state.get("resume_text", ""),
        cid
    )

    convo = ConversationDomainAgent().analyze(
        state.get("answers", []),
        cid
    )

    merged = merge_domains(resume, convo)

    # merged already contains structured rows with confidence + evidence
    return {
        **state,
        "domain_contexts": merged.get("domain_contexts", []),
    }
