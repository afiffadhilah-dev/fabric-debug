from tools.registry import ToolRegistry, get_tool_registry
from tools.analysis_tools import analyze_technical_skills, assess_answer_engagement

# Initialize and register tools
registry = get_tool_registry()

# Register analysis tools
registry.register_tool(
    "analyze_technical_skills",
    analyze_technical_skills,
    agents=["conversational", "rag"]  # Available to conversational and RAG agents
)

# Register engagement assessment tool
registry.register_tool(
    "assess_answer_engagement",
    assess_answer_engagement,
    agents=["conversational"]  # Critical for tracking user disengagement
)

__all__ = ["ToolRegistry", "get_tool_registry"]
