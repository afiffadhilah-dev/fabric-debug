"""
Interview graph construction - Clean Workflow Pattern.

Following LangGraph docs:
- Nodes are simple functions (NO nested agents!)
- Direct tool calls with explicit context
- Graph controls flow via conditional edges
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from agents.conversational.state import InterviewState
from agents.conversational.nodes import (
    introduce_node,
    identify_gaps_node,
    analyze_resume_coverage_node,
    update_state_node,
    finalize_node,
    select_gap_node
)
# New nodes following LangGraph pattern
from agents.conversational.nodes.parse_answer import parse_answer_node
from agents.conversational.nodes.generate_question import generate_question_node
from agents.conversational.nodes.generate_follow_up import generate_follow_up_node
from agents.conversational.conditions import (
    should_continue_interview,
    should_follow_up,
    route_entry_point,
    route_after_greet
)


def create_interview_graph(checkpointer: PostgresSaver = None, predefined_question_repo=None):
    """
    Create interview graph following LangGraph clean workflow pattern.

    Supports TWO modes:
    1. Dynamic Gap Mode (mode="dynamic_gap"): Extract skills, identify unknown attributes
    2. Predefined Questions Mode (mode="predefined_questions"): Use question sets, skip resume-filled

    Graph flow:
    START -> route_entry_point (checks messages and questions_asked)
      ├─ No messages, questions_asked==0? -> introduce -> identify_gaps/analyze_resume_coverage -> should_continue? -> select_gap/finalize
      ├─ Messages exist? -> parse_answer (direct tool calls) -> update_state -> should_follow_up?
      │                                                              ├─ Follow up? -> generate_follow_up -> END
      │                                                              └─ Move on? -> should_continue? -> select_gap/finalize
      └─ After introduce, route_after_greet -> identify_gaps/analyze_resume_coverage

    select_gap -> generate_question (direct LLM call or predefined text) -> END (wait for user input)
    finalize -> END

    Key features:
    - Mode-aware routing at entry point
    - 78% component reuse between modes (7 out of 9 nodes shared)
    - Dynamic mode: Skill extraction with 6 attributes
    - Predefined mode: Resume analysis to skip answered questions

    Args:
        checkpointer: Optional PostgreSQL checkpointer for state persistence

    Returns:
        Compiled LangGraph workflow
    """
    # Create workflow
    workflow = StateGraph(InterviewState)

    # Add all nodes (simple functions, no nested agents!)
    workflow.add_node("introduce", introduce_node)
    workflow.add_node("identify_gaps", identify_gaps_node)
    # If a repository is provided, wrap the analyze node so it receives the repo.
    if predefined_question_repo is not None:
        workflow.add_node(
            "analyze_resume_coverage",
            lambda state: analyze_resume_coverage_node(state, predefined_question_repo)
        )
    else:
        workflow.add_node("analyze_resume_coverage", analyze_resume_coverage_node)

    workflow.add_node("update_state", update_state_node)
    workflow.add_node("select_gap", select_gap_node)
    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("generate_follow_up", generate_follow_up_node)
    workflow.add_node("parse_answer", parse_answer_node)
    workflow.add_node("finalize", finalize_node)

    # Set conditional entry point - routes based on first run AND mode
    workflow.set_conditional_entry_point(
        route_entry_point,
        {
            "introduce": "introduce",
            "identify_gaps": "identify_gaps",                      # Dynamic gap mode
            "analyze_resume_coverage": "analyze_resume_coverage",  # Predefined questions mode
            "parse_answer": "parse_answer"                         # Resuming after user answer
        }
    )

    workflow.add_conditional_edges(
        "introduce",
        route_after_greet,
        {
            "identify_gaps": "identify_gaps",
            "analyze_resume_coverage": "analyze_resume_coverage"
        }
    )

    # Add conditional edges from identify_gaps (dynamic gap mode)
    workflow.add_conditional_edges(
        "identify_gaps",
        should_continue_interview,
        {
            "select_gap": "select_gap",
            "finalize": "finalize"
        }
    )

    # Add conditional edges from analyze_resume_coverage (predefined questions mode)
    workflow.add_conditional_edges(
        "analyze_resume_coverage",
        should_continue_interview,
        {
            "select_gap": "select_gap",
            "finalize": "finalize"
        }
    )

    # Add conditional edges from update_state - check if we need follow-up
    # Routes to either generate_follow_up (same gap) or select_gap/finalize (next gap/end)
    workflow.add_conditional_edges(
        "update_state",
        should_follow_up,
        {
            "generate_follow_up": "generate_follow_up",
            "select_gap": "select_gap",
            "finalize": "finalize"
        }
    )

    # Add direct edges
    workflow.add_edge("select_gap", "generate_question")
    workflow.add_edge("generate_question", END) 
    workflow.add_edge("generate_follow_up", END)  
    workflow.add_edge("parse_answer", "update_state")
    workflow.add_edge("finalize", END)

    # Compile workflow
    return workflow.compile(checkpointer=checkpointer)
