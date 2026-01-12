"""Token usage tracker for rate limit management.

Tracks token usage over a rolling time window to prevent hitting OpenAI rate limits.
"""

import json
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque


@dataclass
class TokenUsage:
    """Record of token usage at a specific time."""
    timestamp: float
    tokens: int


class TokenBudgetTracker:
    """Tracks token usage over a rolling time window.

    Helps prevent rate limit errors by tracking usage and calculating
    required delays before making new API calls.

    Attributes:
        max_tokens_per_minute: Maximum tokens allowed per minute.
        window_seconds: Time window for tracking (default: 60 seconds).
        usage_history: Deque of recent token usage records.
    """

    def __init__(
        self,
        max_tokens_per_minute: int = 30000,
        window_seconds: int = 60,
        safety_margin: float = 0.9,  # Use 90% of limit to be safe
        persist_path: Path | None = None,
    ):
        """Initialize the token budget tracker.

        Args:
            max_tokens_per_minute: Maximum tokens per minute (default: 30K for gpt-4o).
            window_seconds: Rolling window size in seconds (default: 60).
            safety_margin: Use this fraction of max tokens (default: 0.9 = 90%).
            persist_path: Optional path to persist tracker state across runs.
        """
        self.max_tokens = int(max_tokens_per_minute * safety_margin)
        self.window_seconds = window_seconds
        self.persist_path = persist_path
        self.usage_history: Deque[TokenUsage] = deque()

        # Load persisted state if available
        if persist_path and persist_path.exists():
            self._load_state()

    def _clean_old_records(self) -> None:
        """Remove usage records outside the time window."""
        now = time.time()
        cutoff = now - self.window_seconds

        while self.usage_history and self.usage_history[0].timestamp < cutoff:
            self.usage_history.popleft()

    def get_usage_in_window(self) -> int:
        """Get total tokens used in the current window.

        Returns:
            Total tokens used in the rolling window.
        """
        self._clean_old_records()
        return sum(record.tokens for record in self.usage_history)

    def record_usage(self, tokens: int) -> None:
        """Record token usage.

        Args:
            tokens: Number of tokens used.
        """
        self.usage_history.append(TokenUsage(
            timestamp=time.time(),
            tokens=tokens,
        ))
        self._clean_old_records()

        # Persist state if path configured
        if self.persist_path:
            self._save_state()

    def get_wait_time(self, estimated_next_tokens: int = 5000) -> float:
        """Calculate how long to wait before next API call.

        Args:
            estimated_next_tokens: Estimated tokens for next call (default: 5000).

        Returns:
            Seconds to wait before next call (0 if safe to proceed).
        """
        self._clean_old_records()
        current_usage = self.get_usage_in_window()

        # If we'd exceed the limit, calculate wait time
        if current_usage + estimated_next_tokens > self.max_tokens:
            # Find oldest record
            if self.usage_history:
                oldest_timestamp = self.usage_history[0].timestamp
                time_since_oldest = time.time() - oldest_timestamp
                # Wait until oldest record expires plus a small buffer
                return max(0.0, self.window_seconds - time_since_oldest + 2.0)

        return 0.0

    def get_remaining_budget(self) -> int:
        """Get remaining token budget in current window.

        Returns:
            Number of tokens remaining before hitting limit.
        """
        return max(0, self.max_tokens - self.get_usage_in_window())

    def estimate_iteration_tokens(self, num_tool_calls: int = 8) -> int:
        """Estimate tokens for an iteration based on tool calls.

        DeepAgents makes one API call per tool use. Each call includes
        the full conversation history up to that point.

        Args:
            num_tool_calls: Expected number of tool calls (default: 8).

        Returns:
            Estimated total tokens for the iteration.
        """
        # Rough estimate: base context (3K) + incremental per tool call (2K each)
        base_tokens = 3000
        tokens_per_tool = 2000
        return base_tokens + (num_tool_calls * tokens_per_tool)

    def _save_state(self) -> None:
        """Save tracker state to disk."""
        if not self.persist_path:
            return

        try:
            # Convert deque to list of dicts for JSON serialization
            data = {
                "usage_history": [
                    {"timestamp": record.timestamp, "tokens": record.tokens}
                    for record in self.usage_history
                ]
            }

            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            self.persist_path.write_text(json.dumps(data, indent=2))
        except Exception:
            # Silently fail - persistence is nice to have but not critical
            pass

    def _load_state(self) -> None:
        """Load tracker state from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return

        try:
            data = json.loads(self.persist_path.read_text())
            self.usage_history = deque(
                TokenUsage(timestamp=record["timestamp"], tokens=record["tokens"])
                for record in data.get("usage_history", [])
            )
            # Clean old records immediately after loading
            self._clean_old_records()
        except Exception:
            # If loading fails, start fresh
            self.usage_history = deque()
