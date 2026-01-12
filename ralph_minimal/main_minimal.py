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
        f"[green]Token optimization: System prompt ~200 tokens (was ~5000!)[/green]",
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

    # Put SKILL.md in workspace for agent to read (don't inject into prompt!)
    skills_source = Path(__file__).parent.parent / "skills" / "SKILL.md"
    if skills_source.exists():
        skills_dest = config.workspace_dir / "SKILL.md"
        if not skills_dest.exists():
            skills_dest.write_text(skills_source.read_text())
            console.print("[dim]Copied SKILL.md to workspace for agent reference[/dim]")

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
            # Create fresh agent with MINIMAL prompt
            agent = create_ralph_agent_minimal(
                task=task,
                iteration=iteration,
                workspace_dir=config.workspace_dir,
                model_name=config.model_name,
            )

            # Simple user message (task already in system prompt)
            console.print("[dim]Agent working...[/dim]")
            result = await agent.ainvoke({
                "messages": [{"role": "user", "content": f"Continue working on iteration {iteration}."}]
            })

            # Show completion
            messages = result.get("messages", [])
            total_chars = sum(len(str(m)) for m in messages)
            estimated_tokens = total_chars // 4

            console.print(f"[green]✓ Iteration {iteration} completed[/green]")
            console.print(f"[dim]Estimated tokens: {estimated_tokens:,} (much lower!)[/dim]\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error in iteration {iteration}: {e}[/red]")
            if config.verbose:
                console.print_exception()
            console.print("[yellow]Continuing to next iteration...[/yellow]")

        iteration += 1
        await asyncio.sleep(1)  # Brief pause between iterations

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
