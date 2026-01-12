# Project Structure Guide

This document explains the organization of the Ralph Agent project.

## Overview

The project contains three implementations:
1. **v2 (ralph_minimal/)**: Recommended production implementation
2. **v1 (initial_implementation/)**: Legacy implementation for reference
3. **DeepAgent CLI (.deepagents/)**: Integration with DeepAgent command-line tool

## Directory Structure

### Core Implementations

#### `ralph_minimal/` - v2 Implementation (Recommended)
The token-optimized implementation with minimal prompts.

```
ralph_minimal/
├── agent_factory_minimal.py  # Creates DeepAgent with ~200 token prompt
├── main_minimal.py            # Entry point and main loop
├── __init__.py                # Package initialization
└── README.md                  # v2 specific documentation
```

**Uses:**
- `skills/SKILL.md` for agent reference (placed in workspace)
- `src/` modules for shared functionality

**Key Features:**
- System prompt: ~200 tokens
- Skills in filesystem, not injected
- 10x token efficiency vs v1

#### `initial_implementation/` - v1 Implementation (Legacy)
The original implementation with comprehensive system prompts.

```
initial_implementation/
├── agent_factory.py   # Creates DeepAgent with ~5000 token prompt
├── ralph_loop.py      # Main loop with token tracking
├── main.py            # Entry point
├── __init__.py        # Package marker
└── README.md          # Legacy documentation
```

**Uses:**
- `input/SKILL.md` for skills (injected into prompt)
- `src/` modules for shared functionality

**Key Features:**
- System prompt: ~5000 tokens (includes full skills)
- Comprehensive token tracking
- Rate limit protection

### Shared Modules

#### `src/` - Core Functionality
Shared by both v1 and v2 implementations.

```
src/
├── __init__.py           # Package initialization
├── config.py             # RalphConfig class
├── state_manager.py      # State persistence (state.md)
├── tools.py              # Tool definitions (Tavily, todos)
└── token_tracker.py      # Token usage tracking
```

**Key Modules:**
- `config.py`: Configuration management, workspace setup
- `state_manager.py`: Read/write state.md, track progress
- `tools.py`: Web search, todo management tools
- `token_tracker.py`: Token budget tracking and rate limiting

### Skills and Input

#### `skills/` - v2 Skills Directory
Contains skill definitions for the minimal implementation.

```
skills/
└── SKILL.md   # Ralph mode execution patterns (v2)
```

**Usage:**
- Copied to workspace by `ralph_minimal/main_minimal.py`
- Agent reads from filesystem, not injected into prompt
- Reduces token usage significantly

#### `input/` - v1 Skills Directory
Contains skill definitions for the legacy implementation.

```
input/
├── SKILL.md    # Ralph mode execution patterns (v1)
└── README.md   # Input directory documentation
```

**Usage:**
- Read by `initial_implementation/ralph_loop.py` at startup (line 91)
- Injected into agent system prompt
- Required for v1 to function

**Important:** Both skill directories contain similar content but are used differently:
- `input/SKILL.md` → injected into v1 prompt
- `skills/SKILL.md` → placed in v2 workspace for agent to read

### Documentation

#### `docs/` - Project Documentation
Contains architecture and design documentation.

```
docs/
├── ARCHITECTURE_PLAN.md   # Original architecture document
└── STRUCTURE.md           # This file
```

### DeepAgent CLI Integration

#### `.deepagents/` - CLI Integration
Integration with the DeepAgent command-line tool.

```
.deepagents/
├── AGENTS.md                      # Agent definitions
└── skills/
    └── ralph-mode/
        └── SKILL.md               # Ralph skill for CLI
```

**Usage:**
```bash
deepagent --agent ralph-mode "Your task"
```

## Shared vs Separate Files

### Shared Between v1 and v2
- `src/*.py` - All core modules
- `.env` - API keys and configuration
- `pyproject.toml` - Python package configuration

### Version-Specific
- `ralph_minimal/*.py` - v2 only
- `initial_implementation/*.py` - v1 only
- `skills/SKILL.md` - v2 only
- `input/SKILL.md` - v1 only

### Why Two SKILL.md Files?

The skills content is similar, but used differently:

**v1 Approach (input/SKILL.md):**
- Read at startup
- Injected into system prompt (~5000 tokens)
- Sent to API every iteration
- High token usage

**v2 Approach (skills/SKILL.md):**
- Copied to workspace
- Agent discovers and reads when needed
- Not in system prompt
- Low token usage (~200 tokens)

## Running Different Versions

### v2 (Recommended)
```bash
python ralph_minimal/main_minimal.py "Your task"
```
Reads from: `skills/SKILL.md`

### v1 (Legacy)
```bash
python initial_implementation/main.py "Your task"
```
Reads from: `input/SKILL.md`

### DeepAgent CLI
```bash
deepagent --agent ralph-mode "Your task"
```
Reads from: `.deepagents/skills/ralph-mode/SKILL.md`

## File Dependencies

### v1 Dependencies
```
initial_implementation/main.py
  └─> initial_implementation/ralph_loop.py
       ├─> initial_implementation/agent_factory.py
       │    ├─> src/tools.py
       │    └─> input/SKILL.md (injected)
       ├─> src/config.py
       ├─> src/state_manager.py
       └─> src/token_tracker.py
```

### v2 Dependencies
```
ralph_minimal/main_minimal.py
  ├─> ralph_minimal/agent_factory_minimal.py
  │    └─> src/tools.py
  ├─> src/config.py
  ├─> src/state_manager.py
  └─> skills/SKILL.md (copied to workspace)
```

## Configuration Files

### Root Level
- `.env` - API keys (OPENAI_API_KEY, TAVILY_API_KEY)
- `.env.example` - Example environment file
- `.gitignore` - Git ignore rules
- `pyproject.toml` - Python package config
- `README.md` - Main documentation

### Generated at Runtime
- `state.md` - Created in workspace (current directory)
- `output/` - Created in workspace
- `.ralph_tokens.json` - Token tracking (v1 only)
- `.ralph_last_iteration_time` - Rate limit tracking (v1 only)

## Key Differences Summary

| Aspect | v1 (initial_implementation/) | v2 (ralph_minimal/) |
|--------|---------------|---------------------|
| Entry Point | `initial_implementation/main.py` | `ralph_minimal/main_minimal.py` |
| Agent Factory | `initial_implementation/agent_factory.py` | `ralph_minimal/agent_factory_minimal.py` |
| Main Loop | `initial_implementation/ralph_loop.py` | In main_minimal.py |
| Skills Source | `input/SKILL.md` | `skills/SKILL.md` |
| Skills Usage | Injected in prompt | Copied to workspace |
| System Prompt | ~5000 tokens | ~200 tokens |
| Token Tracking | Comprehensive | Basic |
| Rate Limiting | Automatic (65s between iterations) | Manual (Ctrl+C to stop) |
| Status | Legacy | **Recommended** |

## Migration from v1 to v2

If you're using v1 and want to migrate to v2:

1. **No code changes needed** - Both use same workspace format
2. **Existing workspaces work** - state.md format is compatible
3. **Change command:**
   ```bash
   # Old
   python initial_implementation/main.py "task"

   # New
   python ralph_minimal/main_minimal.py "task"
   ```

4. **Skills file:** Copy `input/SKILL.md` to `skills/SKILL.md` if you've customized it

## Future Organization

Potential improvements:
- [ ] Move v1 to `initial_implementation/v1/` subdirectory
- [ ] Create `ralph/` package for v2 main implementation
- [ ] Merge SKILL.md files into single source
- [ ] Add tests/ directory
- [ ] Add initial_implementation/demos/ for usage examples
