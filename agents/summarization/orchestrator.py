from langgraph.graph import StateGraph, END
from sqlmodel import Session
from utils.database import get_engine

from config.settings import settings
from agents.summarization.state import SummarizationState
from agents.summarization.nodes.load_session import LoadSessionNode
from agents.summarization.nodes.skill_node import skill_node
from agents.summarization.nodes.behavior_node import behavior_node
from agents.summarization.nodes.persist_summary import persist_summary_node
from agents.summarization.nodes.infra_node import infra_node
from agents.summarization.nodes.domain_node import domain_node

DEFAULT_MODE = "SELF_REPORT"


# -------------------------
# Utility node
# -------------------------

def load_session_data(state: SummarizationState) -> SummarizationState:
    engine = get_engine()
    with Session(engine) as db:
        node = LoadSessionNode(db)
        # The node.run() method loads and formats the data
        # But we need to extract raw data for Q/A processing
        from agents.summarization.nodes.load_session import get_all_data_for_session
        data = get_all_data_for_session(state["session_id"], db)

    interview = data.get("interview_session")
    candidate = data.get("candidate")
    messages = data.get("messages") or []

    if not interview:
        raise ValueError(f"Interview session not found: {state['session_id']}")

    candidate_id = interview.candidate_id or (candidate.id if candidate else None)

    # Normalize conversation into Q/A pairs
    answers = []
    last_assistant = None

    for m in messages:
        if m.role == "assistant":
            last_assistant = m
            continue

        answers.append({
            "answer": m.content,
            "question": last_assistant.content if last_assistant else "",
            "datetime": m.created_at,
            "meta": getattr(m, "meta", {}),
        })

    return {
        **state,
        "interview_session": interview,
        "resume_text": getattr(interview, "resume_text", None),
        "messages": messages,
        "answers": answers,
        "candidate_id": candidate_id,
    }



# -------------------------
# Graphs
# -------------------------

def build_graph():
    graph = StateGraph(SummarizationState)
    graph.add_node("load_session_data", load_session_data)
    graph.add_node("skill_node", skill_node)
    graph.add_node("behavior_node", behavior_node)
    graph.add_node("infra_node", infra_node)
    graph.add_node("domain_node", domain_node)
    graph.add_node("persist_summary", persist_summary_node)
    graph.set_entry_point("load_session_data")
    graph.add_edge("load_session_data", "skill_node")
    graph.add_edge("skill_node", "behavior_node")
    graph.add_edge("behavior_node", "infra_node")
    graph.add_edge("infra_node", "domain_node")
    graph.add_edge("domain_node", "persist_summary")
    graph.add_edge("persist_summary", END)
    return graph.compile()

def build_profile_summary_graph():
    graph = StateGraph(SummarizationState)
    graph.add_node("load_session_data", load_session_data)
    graph.add_node("skill_node", skill_node)
    graph.add_node("behavior_node", behavior_node)
    graph.add_node("infra_node", infra_node)
    graph.add_node("domain_node", domain_node)
    graph.set_entry_point("load_session_data")
    graph.add_edge("load_session_data", "skill_node")
    graph.add_edge("skill_node", "behavior_node")
    graph.add_edge("behavior_node", "infra_node")
    graph.add_edge("infra_node", "domain_node")
    graph.add_edge("domain_node", END)
    return graph.compile()

GRAPH = build_graph()
PROFILE_SUMMARY_GRAPH = build_profile_summary_graph()


# -------------------------
# Public API
# -------------------------


def summarize_session(session_id: str, mode: str = DEFAULT_MODE):
    """
    Orchestrate summarization and persistence for a session.
    """
    final_state = GRAPH.invoke({
        "session_id": session_id,
        "mode": mode,
    })
    return {
        "session_id": session_id,
        "mode": mode,
        "skills": final_state.get("skills"),
        "behavior_observations": final_state.get("behavior_observations"),
        "infra_contexts": final_state.get("infra_contexts"),
        "domain_contexts": final_state.get("domain_contexts"),
    }

def summarize_session_profile_context(session_id: str, mode: str = DEFAULT_MODE):
    """
    Run the summarization graph up to domain_node (no DB persistence of skills/contexts), returning all context for profile summary.
    """
    final_state = PROFILE_SUMMARY_GRAPH.invoke({
        "session_id": session_id,
        "mode": mode,
    })
    return final_state
