# Ralph Minimal - Token-Optimized Implementation

This is the recommended implementation of Ralph Agent with optimized token usage.

## Key Improvements

- **System prompt**: ~200 tokens (down from ~5000 tokens)
- **10x fewer tokens** per iteration
- Skills placed in filesystem instead of injected into prompt
- Agent discovers context organically through file reading

## Usage

```bash
# From project root
python ralph_minimal/main_minimal.py "Your task here"

# Or interactively
python ralph_minimal/main_minimal.py
```

## How It Works

1. Creates a workspace in the current directory
2. Copies SKILL.md to workspace for agent reference
3. Agent reads state.md and SKILL.md from filesystem
4. Runs in autonomous loop until Ctrl+C

## Files

- `agent_factory_minimal.py`: Creates the DeepAgent with minimal prompt
- `main_minimal.py`: Entry point and main loop logic

## Configuration

The agent uses shared configuration from `src/config.py` and utilities from:
- `src/state_manager.py`: State persistence
- `src/tools.py`: Tool definitions
- `src/token_tracker.py`: Token usage tracking
