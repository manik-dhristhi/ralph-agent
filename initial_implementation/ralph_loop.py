"""Main loop controller for Ralph Agent.

This module implements the core Ralph loop that orchestrates
the autonomous agent execution across iterations.
"""

import asyncio
import signal
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.agent_factory import create_ralph_agent
from src.config import RalphConfig
from src.state_manager import (
    RalphState,
    create_initial_state,
    read_state,
    state_to_markdown,
    write_state,
)
from src.token_tracker import TokenBudgetTracker

console = Console()

# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum: int, frame) -> None:
    """Handle interrupt signals for graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    console.print("\n[yellow]Shutdown requested. Finishing current iteration...[/yellow]")


async def ralph_loop(
    task: str,
    config: RalphConfig,
) -> None:
    """Run the main Ralph loop.

    This function orchestrates the autonomous agent execution:
    1. Sets up the workspace and initial files
    2. Loops through iterations, each with fresh agent context
    3. Handles graceful shutdown on Ctrl+C
    4. Prints summary on exit

    Args:
        task: The task description (WHAT to do).
        config: Configuration settings.
    """
    global _shutdown_requested
    _shutdown_requested = False

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Validate configuration
    config.validate()

    # Ensure workspace exists
    config.ensure_workspace()

    # Print startup banner
    console.print(Panel(
        f"[bold blue]Ralph Mode[/bold blue]\n\n"
        f"[bold]Task:[/bold] {task}\n"
        f"[bold]Workspace:[/bold] {config.workspace_dir.absolute()}\n"
        f"[bold]Max Iterations:[/bold] {config.max_iterations or 'Unlimited'}\n"
        f"[bold]Model:[/bold] {config.model_name}",
        title="Starting Ralph Agent",
        border_style="blue",
    ))

    # Load or create initial state
    state = read_state(config.workspace_dir)
    if state is None:
        state = create_initial_state(task)
        write_state(config.workspace_dir, state)
        console.print("[green]Created initial state.md[/green]")
    else:
        console.print(f"[cyan]Resuming from iteration {state.iteration}[/cyan]")

    # Load skills from input/SKILL.md
    skills_path = Path(__file__).parent.parent / "input" / "SKILL.md"
    if not skills_path.exists():
        console.print(f"[red]Error: SKILL.md not found at {skills_path}[/red]")
        console.print("[yellow]Please create input/SKILL.md with your execution skills.[/yellow]")
        sys.exit(1)

    try:
        skills_content = skills_path.read_text(encoding="utf-8")
        console.print(f"[green]Loaded skills from {skills_path.name}[/green]")
    except OSError as e:
        console.print(f"[red]Error reading SKILL.md: {e}[/red]")
        sys.exit(1)

    # Initialize token budget tracker with persistence
    # gpt-4o has 30K tokens/minute limit
    token_tracker = TokenBudgetTracker(
        max_tokens_per_minute=30000,
        safety_margin=0.85,  # Use 85% of limit to be safe
        persist_path=config.workspace_dir / ".ralph_tokens.json",
    )

    # Show initial budget status
    current_usage = token_tracker.get_usage_in_window()
    if current_usage > 0:
        console.print(
            f"[cyan]Token budget tracker initialized (25.5K/min limit)[/cyan]\n"
            f"[yellow]⚠️  Found {current_usage:,} tokens used in last 60s from previous runs[/yellow]"
        )
    else:
        console.print("[cyan]Token budget tracker initialized (25.5K/min limit)[/cyan]")

    # Main loop
    iteration = state.iteration

    # Track when each iteration starts (persist to handle restarts)
    iteration_time_file = config.workspace_dir / ".ralph_last_iteration_time"
    last_iteration_start_time = None

    # Load last iteration time if available
    if iteration_time_file.exists():
        try:
            last_iteration_start_time = float(iteration_time_file.read_text().strip())
            elapsed_since_last = time.time() - last_iteration_start_time
            if elapsed_since_last < 65:
                console.print(
                    f"[yellow]Last iteration was {elapsed_since_last:.1f}s ago "
                    f"(need 65s for rate limit window)[/yellow]"
                )
        except (ValueError, OSError):
            pass  # Ignore invalid/unreadable files

    while True:
        # Check shutdown flag
        if _shutdown_requested:
            console.print("[yellow]Shutting down gracefully...[/yellow]")
            break

        # Check iteration limit
        if config.max_iterations > 0 and iteration > config.max_iterations:
            console.print(f"[green]Reached maximum iterations ({config.max_iterations})[/green]")
            break

        # CRITICAL: Ensure 65 seconds between iteration starts for rate limit window
        # Each iteration uses ~25-30K tokens, and limit is 30K/minute (60s window)
        if last_iteration_start_time is not None:
            elapsed = time.time() - last_iteration_start_time
            rate_limit_window = 65.0  # 60s window + 5s buffer

            if elapsed < rate_limit_window:
                wait_time = rate_limit_window - elapsed
                console.print(
                    f"[yellow]⏳ Rate limit window protection: waiting {wait_time:.1f}s[/yellow]\n"
                    f"[dim]   Each iteration uses ~25-30K tokens (limit: 30K/minute)[/dim]\n"
                    f"[dim]   Must wait {rate_limit_window:.0f}s between iterations[/dim]"
                )
                await asyncio.sleep(wait_time)

        # Record iteration start time and persist it
        last_iteration_start_time = time.time()
        try:
            iteration_time_file.write_text(str(last_iteration_start_time))
        except OSError:
            pass  # Persist is nice-to-have, don't fail if it errors

        # Print iteration header
        console.print(Panel(
            f"[bold]Iteration {iteration}[/bold]\n"
            f"[dim]Token budget: {token_tracker.get_remaining_budget():,} / {token_tracker.max_tokens:,} available[/dim]",
            border_style="cyan",
        ))

        try:
            # Ensure state.md exists (agent will read it)
            state = read_state(config.workspace_dir)
            if state is None:
                state = create_initial_state(task)
                write_state(config.workspace_dir, state)
                console.print("[dim]Created initial state.md for agent to read[/dim]")

            # Create fresh agent for this iteration
            # Agent will read state.md from filesystem (keeping context small!)
            if config.verbose:
                console.print("[dim]Creating fresh agent instance...[/dim]")

            agent = create_ralph_agent(
                task=task,
                iteration=iteration,
                skills_content=skills_content,
                workspace_dir=config.workspace_dir,
                model_name=config.model_name,
            )

            # Execute the agent with retry on rate limits
            max_retries = 5
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                        transient=True,
                    ) as progress:
                        progress.add_task(description="Agent working...", total=None)

                        # Invoke the agent with the task as user message
                        result = await agent.ainvoke({
                            "messages": [{"role": "user", "content": task}]
                        })
                    break  # Success!

                except Exception as e:
                    error_str = str(e).lower()
                    if "rate" in error_str and "limit" in error_str or "429" in str(e):
                        if attempt < max_retries - 1:
                            console.print(f"[yellow]⚠️  Rate limit hit. Waiting {retry_delay:.1f}s before retry {attempt+2}/{max_retries}...[/yellow]")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                    # Re-raise if not rate limit or max retries reached
                    raise

            # Print completion message and record token usage
            messages = result.get("messages", [])

            # Estimate tokens used this iteration
            total_chars = sum(len(str(m)) for m in messages)
            estimated_tokens_used = total_chars // 4  # Rough estimate

            # Record usage in tracker
            token_tracker.record_usage(estimated_tokens_used)

            if config.verbose:
                # DEBUG: Print message count and token usage
                console.print(f"[dim]Total messages in iteration: {len(messages)}[/dim]")
                console.print(f"[dim]Estimated tokens used: {estimated_tokens_used:,}[/dim]")
                console.print(f"[dim]Total usage in last minute: {token_tracker.get_usage_in_window():,}[/dim]")

                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, "content"):
                        content = last_msg.content
                        if isinstance(content, str) and len(content) > 500:
                            content = content[:500] + "..."
                        console.print(Panel(
                            str(content),
                            title=f"Iteration {iteration} Complete",
                            border_style="green",
                        ))

            console.print(f"[green]✓ Iteration {iteration} completed ({estimated_tokens_used:,} tokens)[/green]\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error in iteration {iteration}: {e}[/red]")
            if config.verbose:
                console.print_exception()
            # Continue to next iteration despite errors
            console.print("[yellow]Continuing to next iteration...[/yellow]")

        # Increment iteration counter
        iteration += 1

        # No fixed delay - token tracker handles rate limiting intelligently

    # Print final summary
    _print_summary(config, iteration)


def _print_summary(config: RalphConfig, final_iteration: int) -> None:
    """Print final summary after loop ends.

    Args:
        config: Configuration settings.
        final_iteration: The last iteration number.
    """
    # Read final state
    state = read_state(config.workspace_dir)

    console.print("\n")
    console.print(Panel(
        f"[bold]Completed Iterations:[/bold] {final_iteration - 1}\n"
        f"[bold]Workspace:[/bold] {config.workspace_dir.absolute()}\n"
        f"[bold]Files Created:[/bold] {len(state.files_created) if state else 0}\n\n"
        f"[dim]Check {config.workspace_dir / 'output'} for generated files[/dim]",
        title="Ralph Session Complete",
        border_style="green",
    ))

    # List created files if any
    if state and state.files_created:
        console.print("\n[bold]Files Created:[/bold]")
        for f in state.files_created[:20]:  # Limit to first 20
            console.print(f"  - {f}")
        if len(state.files_created) > 20:
            console.print(f"  ... and {len(state.files_created) - 20} more")


def run_ralph(task: str, config: RalphConfig | None = None) -> None:
    """Synchronous wrapper to run the Ralph loop.

    Args:
        task: The task description.
        config: Optional configuration (uses defaults if not provided).
    """
    if config is None:
        config = RalphConfig()

    asyncio.run(ralph_loop(task, config))
