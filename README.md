# Ralph Agent

An autonomous looping agent built with LangChain DeepAgents. Ralph operates in continuous iterations, maintaining context through filesystem-based memory rather than conversation history.

## Overview

Ralph is designed to tackle complex tasks by breaking them down into manageable iterations. Each iteration:
- Starts with fresh LLM context (no message history overhead)
- Reads previous progress from filesystem (`state.md`)
- Executes focused work
- Updates state for the next iteration

This approach provides:
- **Unlimited task execution** without context window limitations
- **Persistent memory** through files
- **Cost efficiency** through token optimization
- **Incremental progress** with clear state tracking

## Project Structure

```
ralph-agent/
├── ralph_minimal/          # Main implementation (recommended) - v2
│   ├── agent_factory_minimal.py
│   ├── main_minimal.py
│   └── README.md
├── initial_implementation/               # Legacy implementation - v1
│   ├── agent_factory.py
│   ├── main.py
│   ├── ralph_loop.py
│   └── README.md
├── src/                    # Shared core modules (used by both)
│   ├── config.py          # Configuration management
│   ├── state_manager.py   # State persistence
│   ├── tools.py           # Tool definitions
│   └── token_tracker.py   # Token usage tracking
├── input/                  # Skills for v1 (legacy)
│   ├── SKILL.md           # Used by initial_implementation/ralph_loop.py
│   └── README.md
├── skills/                 # Skills for v2 (minimal)
│   └── SKILL.md           # Used by ralph_minimal/
├── docs/                   # Documentation
│   └── ARCHITECTURE_PLAN.md
├── .deepagents/            # DeepAgent CLI integration
│   ├── AGENTS.md
│   └── skills/ralph-mode/
└── pyproject.toml          # Project configuration
```

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Tavily API key (for web search)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ralph-agent
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys:
# OPENAI_API_KEY=your_openai_key_here
# TAVILY_API_KEY=your_tavily_key_here
```

### Usage

#### Recommended: Minimal Implementation (v2)

```bash
# Run with task as argument
python ralph_minimal/main_minimal.py "Create a Python tutorial on async/await"

# Or run interactively
python ralph_minimal/main_minimal.py
# Then enter your task when prompted
```

The agent will:
1. Create a workspace in your current directory
2. Run in an autonomous loop
3. Save all outputs to `output/` directory
4. Track progress in `state.md`
5. Continue until you press Ctrl+C

#### Legacy Implementation (v1)

```bash
python initial_implementation/main.py "Your task here"
```

Note: v1 uses ~5000 token system prompts vs ~200 tokens in v2. Use v2 for production.

## Key Features

### Token Optimization

**v2 (ralph_minimal)** uses a minimal system prompt approach:
- System prompt: ~200 tokens (vs ~5000 in v1)
- **10x reduction** in token usage per iteration
- Skills placed in filesystem instead of prompt
- Agent discovers context organically

### Filesystem-Based Memory

Ralph maintains context through files:
- `state.md`: Current iteration, completed work, files created
- `SKILL.md`: Execution patterns and best practices
- `output/`: All generated artifacts

### Autonomous Looping

Ralph continues working indefinitely:
- Fresh LLM context each iteration (prevents context pollution)
- Reads state to understand previous progress
- Plans focused work for current iteration
- Updates state before finishing
- Repeats until task completion or user interrupt

### Available Tools

- **Web Search**: Tavily integration for research
- **Filesystem**: Read, write, edit files, glob, grep
- **Planning**: Todo list creation for iteration planning

## Implementations Comparison

| Feature | v1 (initial_implementation/) | v2 (ralph_minimal/) |
|---------|---------------|---------------------|
| System Prompt | ~5000 tokens | ~200 tokens |
| Token Usage | High | 10x lower |
| Skills Injection | In prompt | In filesystem |
| State Format | Prescribed | Agent-discovered |
| Status | Legacy | **Recommended** |

## Configuration

Edit `src/config.py` or set environment variables:

```python
config = RalphConfig(
    workspace_dir=Path.cwd(),  # Where to store files
    verbose=True,              # Enable detailed logging
    max_iterations=0,          # 0 = unlimited
    model_name="gpt-4o",       # OpenAI model to use
)
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Code Style

```bash
ruff check .
ruff format .
```

### Project Scripts

```bash
# Entry point defined in pyproject.toml
ralph "Your task here"
```

## DeepAgent CLI Integration

This project includes DeepAgent CLI integration in `.deepagents/`:

```bash
# Use Ralph as a custom agent in DeepAgent CLI
deepagent --agent ralph-mode "Your task"
```

See `.deepagents/AGENTS.md` for details.

## How Ralph Works

### Iteration Flow

```
┌─────────────────────────────────────────┐
│  1. Read state.md                       │
│     - What iteration?                   │
│     - What's completed?                 │
│     - What's next?                      │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  2. Check filesystem                    │
│     - ls output/                        │
│     - Verify files match state          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  3. Plan iteration                      │
│     - Create focused todos              │
│     - Build on previous work            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  4. Execute                             │
│     - Research if needed                │
│     - Create/edit files                 │
│     - Write to output/                  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  5. Update state.md                     │
│     - Increment iteration               │
│     - Record completed work             │
│     - List new files                    │
│     - Notes for next iteration          │
└─────────────────────────────────────────┘
                  ↓
              [LOOP BACK]
```

### State Management

Ralph tracks progress in `state.md`:

```markdown
# Ralph State

## Task
Create a Python course on async programming

## Iteration
3

## Status
in_progress

## Completed Work
- [x] Created course outline
- [x] Built module 1: Introduction
- [x] Built module 2: Basics

## Files Created
- /output/README.md
- /output/01-intro/lesson.md
- /output/02-basics/lesson.md

## Notes for Next Iteration
Build module 3: Control Flow (if/else, loops).
Follow same structure as modules 1-2.

## Last Updated
2026-01-12T10:30:00Z
```

## Architecture

Ralph is built on:
- **LangChain**: Agent framework
- **LangGraph**: Agent state management
- **DeepAgents**: File-aware agent pattern
- **OpenAI**: LLM provider
- **Tavily**: Web search tool

See `docs/ARCHITECTURE_PLAN.md` for detailed architecture documentation.

## Use Cases

Ralph excels at:
- **Content Creation**: Courses, tutorials, documentation
- **Research Projects**: Gathering and synthesizing information
- **Code Generation**: Building projects incrementally
- **Long-running Tasks**: Anything requiring multiple steps
- **Iterative Refinement**: Building and improving over time

## Troubleshooting

### Import Errors
Ensure you're running from the project root:
```bash
cd /path/to/ralph-agent
python ralph_minimal/main_minimal.py "task"
```

### Missing API Keys
Check `.env` file contains:
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

### State Corruption
Delete `state.md` to start fresh:
```bash
rm state.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Credits

Built with:
- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [DeepAgents](https://github.com/langchain-ai/deepagents)
- [Tavily](https://tavily.com)

## Support

For issues and questions:
- Open an issue on GitHub
- Check `docs/` for detailed documentation
- Review `skills/SKILL.md` for execution patterns
