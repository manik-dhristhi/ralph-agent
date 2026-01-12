"""Tools for Ralph Agent.

This module provides additional tools beyond the default filesystem tools
that come with DeepAgents.
"""

import os
from langchain_community.tools.tavily_search import TavilySearchResults


def get_search_tool() -> TavilySearchResults:
    """Get Tavily search tool for web searching.

    Requires TAVILY_API_KEY environment variable to be set.

    Returns:
        TavilySearchResults tool instance.

    Raises:
        ValueError: If TAVILY_API_KEY is not set.
    """
    if not os.environ.get("TAVILY_API_KEY"):
        raise ValueError(
            "TAVILY_API_KEY environment variable is required for web search. "
            "Get your API key at https://tavily.com"
        )

    return TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
    )


def get_ralph_tools() -> list:
    """Get all tools for Ralph agent.

    Returns:
        List of tool instances.
    """
    tools = []

    # Add Tavily search if API key is available
    try:
        search_tool = get_search_tool()
        tools.append(search_tool)
    except ValueError as e:
        print(f"Warning: {e}")
        print("Web search will not be available.")

    return tools
