"""Task execution wrapper with token tracking and rate limiting.

This module provides a wrapper around agent execution that handles:
- Token usage tracking
- Rate limit enforcement
- Streaming output
- Error handling
"""

from typing import Any, Dict, Optional
from rich.console import Console

from src.token_tracker import TokenBudgetTracker


console = Console()


def _extract_action_description(output_data: dict, call_number: int) -> str:
    """Extract a description of what the LLM is doing from the output data."""
    # Check if it's an AIMessage object with tool_calls attribute
    if hasattr(output_data, "tool_calls") and output_data.tool_calls:
        tool_name = output_data.tool_calls[0].get("name", "unknown")
        return f"Call #{call_number}: {tool_name}"

    # Try dict format
    if isinstance(output_data, dict) and "tool_calls" in output_data:
        tool_calls = output_data["tool_calls"]
        if tool_calls and len(tool_calls) > 0:
            tool_name = tool_calls[0].get("name", "unknown")
            return f"Call #{call_number}: {tool_name}"

    # Check for content in AIMessage
    if hasattr(output_data, "content"):
        content = output_data.content
        if content and len(str(content)) > 40:
            return f"Call #{call_number}: Thinking"
        elif content:
            return f"Call #{call_number}: Response"

    # Try dict content
    if isinstance(output_data, dict):
        content = output_data.get("content", "")
        if content and len(str(content)) > 40:
            return f"Call #{call_number}: Thinking"
        elif content:
            return f"Call #{call_number}: Response"

    return f"Call #{call_number}"


async def execute_task(
    prompt: str,
    agent: Any,
    token_tracker: TokenBudgetTracker,
    config: Optional[Dict] = None,
    verbose: bool = True,
    debug_events: bool = False,
) -> int:
    """Execute a task with the agent, handling rate limits and token tracking.

    Args:
        prompt: The prompt/task to execute
        agent: The compiled agent graph
        token_tracker: TokenBudgetTracker instance
        config: Optional configuration dict (e.g., recursion_limit)
        verbose: Whether to print streaming output

    Returns:
        Total tokens used in this execution
    """
    # Estimate tokens needed for this iteration
    estimated_tokens = token_tracker.estimate_iteration_tokens(num_tool_calls=8)

    # Check rate limit before starting
    wait_time = token_tracker.get_wait_time(estimated_tokens)
    if wait_time > 0:
        if verbose:
            console.print(
                f"[yellow]Rate limit protection: waiting {wait_time:.1f}s "
                f"(current usage: {token_tracker.get_usage_in_window():,} tokens)[/yellow]"
            )
        import time
        time.sleep(wait_time)

    # Set default config
    if config is None:
        config = {"recursion_limit": 100}

    # Execute with streaming and track tokens
    total_tokens_this_run = 0
    llm_call_count = 0

    try:
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
            version="v2",
        ):
            # Debug: print all events to understand structure
            if debug_events:
                console.print(f"[dim]Event: {event.get('event')}[/dim]")
                if event.get("event") == "on_llm_end":
                    console.print(f"[dim yellow]LLM End Data: {event.get('data', {})}[/dim yellow]")

            # Track token usage from LLM completions
            # Try multiple ways to extract token usage
            if event.get("event") == "on_llm_end":
                llm_call_count += 1
                output_data = event.get("data", {}).get("output", {})
                action_desc = _extract_action_description(output_data, llm_call_count)

                # Method 1: usage_metadata (new format)
                usage = output_data.get("usage_metadata")
                if usage:
                    tokens_used = usage.get("total_tokens", 0)
                    if tokens_used > 0:
                        total_tokens_this_run += tokens_used
                        token_tracker.record_usage(tokens_used)
                        if verbose:
                            console.print(f"[dim cyan]  [{action_desc}] +{tokens_used} tokens[/dim cyan]")

                # Method 2: llm_output (old format)
                if not usage:
                    llm_output = output_data.get("llm_output")
                    if llm_output and "token_usage" in llm_output:
                        token_usage = llm_output["token_usage"]
                        tokens_used = token_usage.get("total_tokens", 0)
                        if tokens_used > 0:
                            total_tokens_this_run += tokens_used
                            token_tracker.record_usage(tokens_used)
                            if verbose:
                                console.print(f"[dim cyan]  [{action_desc}] +{tokens_used} tokens[/dim cyan]")

            # Stream content to console if verbose
            if verbose and event.get("event") == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", {})

                # Check for usage data in the streaming chunk (OpenAI format)
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    tokens_used = chunk.usage_metadata.get("total_tokens", 0)
                    if tokens_used > 0:
                        total_tokens_this_run += tokens_used
                        token_tracker.record_usage(tokens_used)
                        if verbose:
                            console.print(f"\n[dim cyan]  +{tokens_used} tokens[/dim cyan]")

                # Print content
                if hasattr(chunk, "content") and chunk.content:
                    console.print(chunk.content, end="", style="dim")

        if verbose:
            console.print()  # New line after streaming

    except Exception as e:
        # Re-raise but ensure we still print newline
        if verbose:
            console.print()
        raise e

    # If we didn't track any tokens, estimate from the error
    # (This shouldn't happen, but better than showing 0)
    if total_tokens_this_run == 0 and verbose:
        console.print("[yellow]Warning: Token tracking didn't capture usage. Check streaming events.[/yellow]")

    return total_tokens_this_run
