#!/usr/bin/env python3
"""
Ralph Agent - Main Entry Point

Run Ralph in autonomous looping mode using local src/ implementation.
"""
import sys
from pathlib import Path

from src.config import RalphConfig
from src.ralph_loop import run_ralph


def main():
    """Main entry point for Ralph Agent."""
    # Get task from command line or prompt user
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = input("Enter your task: ").strip()
        if not task:
            print("Error: Task cannot be empty")
            sys.exit(1)

    # Create configuration
    # Workspace will be current directory or RALPH_WORKSPACE env var
    config = RalphConfig(
        workspace_dir=Path.cwd(),  # Use current directory
        verbose=True,
        max_iterations=0,  # Unlimited (until Ctrl+C)
    )

    # Run Ralph!
    print(f"\n🚀 Starting Ralph Mode")
    print(f"Task: {task}")
    print(f"Workspace: {config.workspace_dir}")
    print(f"Press Ctrl+C to stop\n")

    run_ralph(task, config)


if __name__ == "__main__":
    main()
