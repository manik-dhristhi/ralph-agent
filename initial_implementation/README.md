# Initial Implementation (v1)

This directory contains the original Ralph Agent implementation (v1).

## Overview

The initial implementation had a ~5000 token system prompt which caused:
- High token usage per iteration
- Increased API costs
- Slower response times

The minimal implementation (`ralph_minimal/`) solves these issues.

## Files

- `agent_factory.py`: Original agent factory with large system prompt
- `ralph_loop.py`: Original loop logic with comprehensive token tracking
- `main.py`: Original entry point

## Running Initial Implementation

```bash
# From project root
python initial_implementation/main.py "Your task here"
```

## Key Differences from v2

| Feature | v1 (this version) | v2 (ralph_minimal) |
|---------|-------------------|-------------------|
| System Prompt | ~5000 tokens | ~200 tokens |
| Skills Source | `input/SKILL.md` | `skills/SKILL.md` |
| Skills Injection | In prompt | In filesystem |
| Token Tracking | Comprehensive | Basic |
| Rate Limiting | Automatic (65s) | Manual |

**Note**: This implementation is maintained for reference and comparison. Use `ralph_minimal/` for production.
