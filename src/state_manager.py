"""State management for Ralph Agent.

This module handles reading and writing the state.md file that tracks
progress across iterations.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RalphState:
    """Represents the current state of a Ralph task.

    Attributes:
        iteration: Current iteration number (starts at 1)
        task: The original task description
        status: Current status ('in_progress' or 'completed')
        completed_items: List of completed work items
        files_created: List of files created so far
        notes: Notes for the next iteration
        last_updated: ISO 8601 timestamp of last update
    """

    iteration: int
    task: str
    status: str = "in_progress"
    completed_items: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    notes: str = ""
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def create_initial_state(task: str) -> RalphState:
    """Create initial state for a new task.

    Args:
        task: The task description.

    Returns:
        A new RalphState with iteration 1.
    """
    return RalphState(
        iteration=1,
        task=task,
        status="in_progress",
        completed_items=[],
        files_created=[],
        notes="This is the first iteration. Start by understanding the task and creating a plan.",
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


def state_to_markdown(state: RalphState) -> str:
    """Convert RalphState to markdown string.

    Args:
        state: The state to convert.

    Returns:
        Markdown formatted string.
    """
    # Format completed items
    completed_str = ""
    if state.completed_items:
        completed_str = "\n".join(f"- [x] {item}" for item in state.completed_items)
    else:
        completed_str = "- [ ] No items completed yet"

    # Format files created
    files_str = ""
    if state.files_created:
        files_str = "\n".join(f"- {f}" for f in state.files_created)
    else:
        files_str = "- No files created yet"

    return f"""# Ralph State

## Task
{state.task}

## Iteration
{state.iteration}

## Status
{state.status}

## Completed Work
{completed_str}

## Files Created
{files_str}

## Notes for Next Iteration
{state.notes}

## Last Updated
{state.last_updated}
"""


def markdown_to_state(content: str) -> RalphState:
    """Parse markdown string to RalphState.

    Args:
        content: The markdown content to parse.

    Returns:
        Parsed RalphState.

    Raises:
        ValueError: If required fields are missing.
    """
    # Extract task
    task_match = re.search(r"## Task\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    task = task_match.group(1).strip() if task_match else ""

    # Extract iteration
    iteration_match = re.search(r"## Iteration\n(\d+)", content)
    iteration = int(iteration_match.group(1)) if iteration_match else 1

    # Extract status
    status_match = re.search(r"## Status\n(\w+)", content)
    status = status_match.group(1).strip() if status_match else "in_progress"

    # Extract completed items
    completed_items = []
    completed_match = re.search(
        r"## Completed Work\n(.+?)(?=\n## |\Z)", content, re.DOTALL
    )
    if completed_match:
        completed_section = completed_match.group(1)
        # Find all checked items: - [x] item
        items = re.findall(r"- \[x\] (.+?)(?=\n|$)", completed_section)
        completed_items = [item.strip() for item in items]

    # Extract files created
    files_created = []
    files_match = re.search(r"## Files Created\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if files_match:
        files_section = files_match.group(1)
        # Find all file paths: - /path/to/file
        files = re.findall(r"- (/\S+)", files_section)
        files_created = [f.strip() for f in files]

    # Extract notes
    notes_match = re.search(
        r"## Notes for Next Iteration\n(.+?)(?=\n## |\Z)", content, re.DOTALL
    )
    notes = notes_match.group(1).strip() if notes_match else ""

    # Extract last updated
    updated_match = re.search(r"## Last Updated\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
    last_updated = (
        updated_match.group(1).strip()
        if updated_match
        else datetime.now(timezone.utc).isoformat()
    )

    if not task:
        raise ValueError("Could not parse task from state.md")

    return RalphState(
        iteration=iteration,
        task=task,
        status=status,
        completed_items=completed_items,
        files_created=files_created,
        notes=notes,
        last_updated=last_updated,
    )


def read_state(workspace_dir: Path) -> RalphState | None:
    """Read state from state.md file.

    Args:
        workspace_dir: Path to the workspace directory.

    Returns:
        RalphState if file exists and is valid, None otherwise.
    """
    state_path = workspace_dir / "state.md"

    if not state_path.exists():
        return None

    try:
        content = state_path.read_text(encoding="utf-8")
        return markdown_to_state(content)
    except (OSError, ValueError) as e:
        # Log error but return None to allow fresh start
        print(f"Warning: Could not read state.md: {e}")
        return None


def write_state(workspace_dir: Path, state: RalphState) -> None:
    """Write state to state.md file.

    Args:
        workspace_dir: Path to the workspace directory.
        state: The state to write.
    """
    state_path = workspace_dir / "state.md"

    # Update timestamp
    state.last_updated = datetime.now(timezone.utc).isoformat()

    content = state_to_markdown(state)
    state_path.write_text(content, encoding="utf-8")
