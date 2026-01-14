#!/usr/bin/env python3
"""Ralph Mode with minimal prompts - fixed token usage.

Key fix: System prompt reduced from 5000 → 200 tokens
Result: ~10x fewer tokens per iteration
"""
import sys
import asyncio
import signal
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from src.config import RalphConfig
from src.state_manager import create_initial_state, read_state, write_state
from src.token_tracker import TokenBudgetTracker
from src.execution import execute_task
from ralph_minimal.agent_factory_minimal import create_ralph_agent_minimal

console = Console()
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    console.print("\n[yellow]Shutdown requested. Finishing current iteration...[/yellow]")


async def ralph_minimal(task: str, config: RalphConfig):
    """Run Ralph with minimal token usage."""
    global shutdown_requested

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    config.validate()
    config.ensure_workspace()

    console.print(Panel(
        f"[bold blue]Ralph Mode (Minimal Prompts)[/bold blue]\n\n"
        f"[bold]Task:[/bold] {task}\n"
        f"[bold]Workspace:[/bold] {config.workspace_dir.absolute()}\n"
        f"[bold]Max Iterations:[/bold] {config.max_iterations or 'Unlimited'}\n"
        f"[bold]Model:[/bold] {config.model_name}\n\n"
        f"[green]Using gpt-4o-mini: 150K TPM (5x rate limit) + 20x cheaper![/green]",
        title="Starting Ralph Agent",
        border_style="blue",
    ))

    # Load or create state
    state = read_state(config.workspace_dir)
    if state is None:
        state = create_initial_state(task)
        write_state(config.workspace_dir, state)
        console.print("[green]Created initial state.md[/green]")
    else:
        console.print(f"[cyan]Resuming from iteration {state.iteration}[/cyan]")

    # NOTE: We don't copy SKILL.md to workspace anymore
    # The agent works purely from the minimal system prompt
    # SKILL.md is kept in skills/ directory for future deepagent-cli integration

    # Initialize token tracker for rate limiting
    token_tracker = TokenBudgetTracker(
        max_tokens_per_minute=150000,  # OpenAI GPT-4o-mini limit (5x higher than gpt-4o!)
        safety_margin=0.9,  # Use 90% of limit for safety
    )

    iteration = state.iteration

    while True:
        if shutdown_requested:
            console.print("[yellow]Shutting down gracefully...[/yellow]")
            break

        if config.max_iterations > 0 and iteration > config.max_iterations:
            console.print(f"[green]Reached maximum iterations ({config.max_iterations})[/green]")
            break

        console.print(Panel(
            f"[bold]Iteration {iteration}[/bold]",
            border_style="cyan",
        ))

        try:
            # Create FRESH agent each iteration (Ralph pattern: fresh context every loop)
            console.print("[dim]Creating fresh agent for this iteration...[/dim]")
            agent = create_ralph_agent_minimal(
                workspace_dir=config.workspace_dir,
                model_name=config.model_name,
            )

            # Execute task with rate limiting and token tracking
            console.print("[dim]Agent working (streaming enabled)...[/dim]\n")

            # Build user message with task and iteration context
            user_message = f"""## Iteration {iteration}

TASK: {task}

STRICT INSTRUCTIONS:
1. Read state.md ONCE (shows what's been completed)
2. Do EXACTLY ONE task: Create OR edit ONE file in output/
3. Update state.md (increment iteration, add what you did)
4. STOP IMMEDIATELY after updating state.md

EFFICIENCY RULES:
- You have recursion_limit=40, don't waste steps
- Don't re-read files, don't overthink, don't validate
- Workflow: read → create/edit → update → STOP
- MAX 1 file operation per iteration

Your memory is ONLY in files. If you don't update state.md, next iteration won't know what you did."""

            total_tokens_used = await execute_task(
                prompt=user_message,
                agent=agent,
                token_tracker=token_tracker,
                config={"recursion_limit": 80},  # Real limit (agent told 40 for psychological pressure)
                verbose=True,
            )

            # Show completion stats
            stats = token_tracker.get_stats()
            console.print(f"[green]✓ Iteration {iteration} completed[/green]")
            console.print(f"[cyan]Tokens this iteration: {total_tokens_used:,}[/cyan]")
            console.print(f"[dim]Total tokens: {stats['total_tokens']:,} | "
                         f"Window usage: {stats['current_window_usage']:,}/{stats['limit']:,} "
                         f"({stats['utilization_pct']:.1f}%)[/dim]\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error in iteration {iteration}: {e}[/red]")
            if config.verbose:
                console.print_exception()
            console.print("[yellow]Continuing to next iteration...[/yellow]")

        iteration += 1

        # Small delay between iterations (rate limiting is handled by token tracker)
        if not shutdown_requested:
            await asyncio.sleep(1)  # Just a brief pause for UI clarity

    # Print final summary
    state = read_state(config.workspace_dir)
    console.print(Panel(
        f"[bold]Completed Iterations:[/bold] {iteration - 1}\n"
        f"[bold]Workspace:[/bold] {config.workspace_dir.absolute()}\n"
        f"[bold]Files Created:[/bold] {len(state.files_created) if state else 0}",
        title="Ralph Session Complete",
        border_style="green",
    ))


def main():
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = input("Enter your task: ").strip()
        if not task:
            print("Error: Task cannot be empty")
            sys.exit(1)

    config = RalphConfig(
        workspace_dir=Path.cwd(),
        verbose=True,
        max_iterations=0,
    )

    print(f"\n🚀 Starting Ralph Mode (Minimal Prompts)")
    print(f"Task: {task}")
    print(f"Workspace: {config.workspace_dir}")
    print(f"Press Ctrl+C to stop\n")

    asyncio.run(ralph_minimal(task, config))


if __name__ == "__main__":
    main()
