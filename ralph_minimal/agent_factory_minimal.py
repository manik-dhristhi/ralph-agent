"""Minimal agent factory - matches official DeepAgents pattern.

Key insight: Don't inject massive prompts. Keep it simple.
"""

import sys
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

# Add deepagents to path
DEEPAGENTS_PATH = Path(__file__).parent.parent / "deepagents" / "libs" / "deepagents"
if str(DEEPAGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(DEEPAGENTS_PATH))

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from src.tools import get_ralph_tools


# MINIMAL system prompt - let the agent figure out the rest
RALPH_MINIMAL_PROMPT = """You are Ralph, an autonomous agent working iteratively on a task.

Your previous work is in the filesystem. Check what exists using ls and read_file.
Continue making progress on the task.

Important:
- Read state.md to see what you've completed
- Update state.md with your progress before finishing
- Focus on one concrete task per iteration
- All files go in the output/ directory

Available filesystem tools: ls, read_file, write_file, edit_file, glob, grep
Planning tool: write_todos (create exactly 1 todo for this iteration)
Research tool: tavily_search_results_json

You'll be called again after this iteration completes."""


def create_ralph_agent_minimal(
    task: str,
    iteration: int,
    workspace_dir: Path,
    model_name: str = "gpt-4o",
) -> CompiledStateGraph:
    """Create a DeepAgent with MINIMAL prompt to avoid token bloat.

    Key difference from previous version:
    - System prompt: ~200 tokens (was ~5000 tokens!)
    - No skills injection (put in filesystem instead)
    - No state format injection (agent figures it out)
    - Task in user message, not system prompt

    Args:
        task: The task description.
        iteration: Current iteration number.
        workspace_dir: Path to the workspace directory.
        model_name: Name of the OpenAI model to use.

    Returns:
        A compiled DeepAgent ready for execution.
    """
    # Simple system prompt with iteration context
    system_prompt = f"""{RALPH_MINIMAL_PROMPT}

Current iteration: {iteration}

Task: {task}"""

    # Create the OpenAI model
    model = ChatOpenAI(
        model=model_name,
        max_tokens=16000,
    )

    # Create filesystem backend
    backend = FilesystemBackend(
        root_dir=workspace_dir,
        virtual_mode=True,
    )

    # Get tools (Tavily search, etc.)
    tools = get_ralph_tools()

    # Create the agent
    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        backend=backend,
    )

    return agent
