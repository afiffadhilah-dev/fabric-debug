"""
Graph nodes for the interview system.

Clean Workflow Pattern (following LangGraph best practices):
- Nodes are simple functions 
- Direct tool calls with explicit context
- Direct LLM calls for question generation
- Natural conversation flow with follow-ups
"""

from agents.conversational.nodes.introduce import introduce_node
from agents.conversational.nodes.identify_gaps import identify_gaps_node
from agents.conversational.nodes.analyze_resume_coverage import analyze_resume_coverage_node
from agents.conversational.nodes.parse_answer import parse_answer_node
from agents.conversational.nodes.generate_question import generate_question_node
from agents.conversational.nodes.generate_follow_up import generate_follow_up_node
from agents.conversational.nodes.update_state import update_state_node
from agents.conversational.nodes.finalize import finalize_node
from agents.conversational.nodes.select_gap import select_gap_node

__all__ = [
    "introduce_node",
    "identify_gaps_node",
    "analyze_resume_coverage_node",
    "parse_answer_node",
    "generate_question_node",
    "generate_follow_up_node",
    "update_state_node",
    "finalize_node",
    "select_gap_node"
]
