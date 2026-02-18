"""
Tool Registry for managing reusable agent tools.

This registry provides a centralized way to:
- Register and discover available tools
- Assign tools to specific agents
- Manage tool dependencies and configurations
"""

from typing import List, Dict, Callable, Optional


class ToolRegistry:
    """
    Central registry for all available tools that can be used by agents.

    Tools are reusable functions that agents can call to perform specific tasks
    such as web search, calculations, database queries, API calls, etc.

    Usage:
        registry = ToolRegistry()
        tools = registry.get_tools_for_agent("conversational")
        # Pass tools to your agent
    """

    def __init__(self):
        """Initialize the tool registry with available tools."""
        self._tools: Dict[str, Callable] = {}
        self._agent_tool_mapping: Dict[str, List[str]] = {
            "conversational": [],
            "summarization": [],
            "rag": [],
        }

    def register_tool(
        self,
        name: str,
        func: Callable,
        agents: Optional[List[str]] = None
    ) -> None:
        """
        Register a new tool in the registry.

        Args:
            name: Unique identifier for the tool
            func: The tool function to register
            agents: List of agent types that can use this tool.
                   If None, tool is available to all agents.

        Example:
            def my_tool(query: str) -> str:
                return "result"

            registry.register_tool("my_tool", my_tool, ["conversational"])
        """
        self._tools[name] = func

        # If specific agents specified, add to their mappings
        if agents:
            for agent_type in agents:
                if agent_type in self._agent_tool_mapping:
                    if name not in self._agent_tool_mapping[agent_type]:
                        self._agent_tool_mapping[agent_type].append(name)
        else:
            # Available to all agents
            for agent_type in self._agent_tool_mapping:
                if name not in self._agent_tool_mapping[agent_type]:
                    self._agent_tool_mapping[agent_type].append(name)

    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Retrieve a specific tool by name.

        Args:
            name: The tool name

        Returns:
            The tool function or None if not found
        """
        return self._tools.get(name)

    def get_tools_for_agent(self, agent_type: str) -> List[Callable]:
        """
        Get all tools available for a specific agent type.

        Args:
            agent_type: Type of agent ("conversational", "summarization", "rag")

        Returns:
            List of tool functions available for this agent

        Example:
            tools = registry.get_tools_for_agent("conversational")
            # Use tools with LangChain agent
        """
        if agent_type not in self._agent_tool_mapping:
            return []

        tool_names = self._agent_tool_mapping[agent_type]
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_all_tools(self) -> List[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def list_tools_for_agent(self, agent_type: str) -> List[str]:
        """
        List tool names available for a specific agent.

        Args:
            agent_type: Type of agent

        Returns:
            List of tool names
        """
        return self._agent_tool_mapping.get(agent_type, [])


# Global registry instance (singleton pattern)
_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance (singleton).

    Returns:
        The global ToolRegistry instance

    Example:
        from tools.registry import get_tool_registry

        registry = get_tool_registry()
        tools = registry.get_tools_for_agent("conversational")
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance
