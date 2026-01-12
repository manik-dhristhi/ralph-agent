"""Configuration for Ralph Agent."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class RalphConfig:
    """Configuration for Ralph Agent.

    Attributes:
        model_name: LLM model to use (default: gpt-4o)
        max_iterations: Maximum loop iterations (0 = unlimited)
        max_todos_per_iteration: Number of todos per iteration (default: 1)
        workspace_dir: Working directory for files
        state_file: Name of state file
        output_dir: Name of output directory
        auto_create_workspace: Whether to create workspace if missing
        verbose: Whether to print detailed output
    """

    # Model settings (OpenAI)
    model_name: str = field(
        default_factory=lambda: os.environ.get(
            "RALPH_MODEL", "gpt-4o"
        )
    )

    # Loop settings
    max_iterations: int = field(
        default_factory=lambda: int(os.environ.get("RALPH_MAX_ITERATIONS", "0"))
    )
    max_todos_per_iteration: int = 1  # One focused task per iteration

    # Path settings
    workspace_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("RALPH_WORKSPACE", "./workspace")
        )
    )
    state_file: str = "state.md"
    output_dir: str = "output"

    # Behavior settings
    auto_create_workspace: bool = True
    verbose: bool = True

    def __post_init__(self) -> None:
        """Ensure workspace_dir is a Path object."""
        if isinstance(self.workspace_dir, str):
            self.workspace_dir = Path(self.workspace_dir)

    @property
    def state_path(self) -> Path:
        """Full path to state.md file."""
        return self.workspace_dir / self.state_file

    @property
    def output_path(self) -> Path:
        """Full path to output directory."""
        return self.workspace_dir / self.output_dir

    def ensure_workspace(self) -> None:
        """Create workspace directory structure if it doesn't exist."""
        if self.auto_create_workspace:
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            self.output_path.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        """Validate configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        if self.max_todos_per_iteration < 1:
            raise ValueError("max_todos_per_iteration must be at least 1")
        if self.max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")
