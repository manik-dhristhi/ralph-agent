"""Minimal agent factory - matches official DeepAgents pattern.

Key insight: Don't inject massive prompts. Keep it simple.
"""

from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from src.tools import get_ralph_tools


# MINIMAL system prompt - let the agent figure out the rest
RALPH_MINIMAL_PROMPT = """You are Ralph, an autonomous agent working iteratively.

CRITICAL RULES (MUST FOLLOW):
1. FIRST: Read state.md to see what's been done
2. Do EXACTLY ONE focused task - create OR edit ONE file in output/
3. LAST: Update state.md before finishing

STRICT LIMIT: Create/edit MAX 1 FILE per iteration. Do NOT create multiple files.

EFFICIENCY: You have limited steps (recursion_limit=40). Be efficient:
- Don't overthink or plan excessively
- Don't re-read files you already read
- Read state.md → create/edit ONE file → update state.md → DONE
- Aim for 5-8 tool calls maximum per iteration
- Stop immediately after updating state.md

QUALITY: Generate detailed, useful content:
- Add real substance, not just outlines
- Include examples, code snippets, explanations
- Make each lesson comprehensive and valuable
- Don't create shallow placeholders

GOOD examples (ONE task):
- Create lesson_01.md with detailed introduction (code examples, exercises)
- Edit course_outline.md to add module details
- Create exercises_week1.md with practice problems

BAD examples (NEVER do this):
- Create outline.md AND lesson_01.md (multiple files)
- Create 5 different outline files
- Create shallow content with just bullet points
- Overthink and use 20+ tool calls

state.md format:
```
## Iteration
[increment the number]

## Completed Work
- [x] [what you just did]

## Files Created
- [list all files in output/]
```

Your memory is ONLY in files. Update state.md or next iteration won't know what you did."""


def create_ralph_agent_minimal(
    workspace_dir: Path,
    model_name: str = "gpt-4o-mini",
) -> CompiledStateGraph:
    """Create a DeepAgent with MINIMAL prompt to avoid token bloat.

    Key difference from previous version:
    - System prompt: ~100 tokens (was ~5000 tokens!)
    - No skills injection (put in filesystem instead)
    - No state format injection (agent figures it out)
    - Task passed in user message, not system prompt (saves tokens)

    Args:
        workspace_dir: Path to the workspace directory.
        model_name: Name of the OpenAI model to use.

    Returns:
        A compiled DeepAgent ready for execution.
    """
    # Ultra-minimal system prompt - task and iteration passed via user message
    system_prompt = RALPH_MINIMAL_PROMPT

    # Create the OpenAI model with reasonable token limits and streaming enabled
    model = ChatOpenAI(
        model=model_name,
        max_tokens=4000,  # Reduced from 16000 to prevent rate limit issues
        streaming=True,  # Enable streaming for real-time output
        model_kwargs={"stream_options": {"include_usage": True}},  # Track actual token usage
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
