# Ralph Mode Architecture Plan

> **This document is the single source of truth for the Ralph Agent project.**
> Refer here whenever confused about architecture, file purposes, or implementation details.

---

## Table of Contents

1. [Overview](#overview)
2. [Separation of Concerns](#separation-of-concerns)
3. [Project Structure](#project-structure)
4. [Core Components](#core-components)
5. [File Specifications](#file-specifications)
6. [Execution Flow](#execution-flow)
7. [Implementation Details](#implementation-details)
8. [Dependencies](#dependencies)
9. [Build Checklist](#build-checklist)

---

## Overview

Ralph Mode is an autonomous looping agent pattern where:
- Each iteration starts with **fresh context** (clean LLM memory)
- **Persistence** is achieved through filesystem (`state.md`, `skills.md`, output files)
- Agent executes **exactly 3 todos** per iteration
- Loop continues until `max_iterations` reached or `Ctrl+C`

### Architecture Diagram

```
                     USER INPUT
                         │
                         ▼
              ┌──────────────────┐
              │  TASK (Query)    │
              │  "Build a Python │
              │   course"        │
              └────────┬─────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                     RALPH LOOP CONTROLLER                     │
│                      (ralph_loop.py)                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐ │
│  │ Read        │   │ Read        │   │ Read existing       │ │
│  │ skills.md   │   │ state.md    │   │ output/ files       │ │
│  │ (HOW)       │   │ (PROGRESS)  │   │ (ARTIFACTS)         │ │
│  └──────┬──────┘   └──────┬──────┘   └──────────┬──────────┘ │
│         │                 │                      │            │
│         └─────────────────┼──────────────────────┘            │
│                           │                                   │
│                           ▼                                   │
│              ┌────────────────────────┐                       │
│              │   BUILD AGENT PROMPT   │                       │
│              │   - System Prompt      │                       │
│              │   - Skills content     │                       │
│              │   - State content      │                       │
│              │   - Task query         │                       │
│              └───────────┬────────────┘                       │
│                          │                                    │
│                          ▼                                    │
│              ┌────────────────────────┐                       │
│              │   CREATE DEEP AGENT    │                       │
│              │   (Fresh Instance)     │                       │
│              │   - FilesystemBackend  │                       │
│              │   - TodoMiddleware     │                       │
│              │   - 3 todo limit       │                       │
│              └───────────┬────────────┘                       │
│                          │                                    │
│                          ▼                                    │
│              ┌────────────────────────┐                       │
│              │   EXECUTE ITERATION    │                       │
│              │   1. Create 3 todos    │                       │
│              │   2. Execute todos     │                       │
│              │   3. Write outputs     │                       │
│              │   4. Update state.md   │                       │
│              └───────────┬────────────┘                       │
│                          │                                    │
│                          ▼                                    │
│              ┌────────────────────────┐                       │
│              │   CHECK LOOP CONTINUE  │                       │
│              │   - max_iters reached? │                       │
│              │   - Ctrl+C pressed?    │                       │
│              │   - Task complete?     │                       │
│              └───────────┬────────────┘                       │
│                          │                                    │
│              ┌───────────┴───────────┐                        │
│              │                       │                        │
│              ▼                       ▼                        │
│         [CONTINUE]              [EXIT]                        │
│         Loop back               Print summary                 │
│         Fresh context           Show files created            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Separation of Concerns

### The Four Layers

| Layer | File/Location | Purpose | Changes When | Controlled By |
|-------|---------------|---------|--------------|---------------|
| **System Prompt** | Hardcoded in `agent_factory.py` | Agent identity, loop mechanics, rules | Never | Developer |
| **Skills** | `workspace/skills.md` | HOW to execute (methodology, patterns) | Per project/task type | User |
| **State** | `workspace/state.md` | Progress tracking, context for next iteration | Every iteration | Agent (auto) |
| **Task** | Runtime argument | WHAT to do | Each new task | User (at runtime) |

### What Goes Where

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT (hardcoded in agent_factory.py)                          │
│  ════════════════════════════════════════════                           │
│  • Agent identity ("You are Ralph, an autonomous looping agent")        │
│  • Loop mechanics (how iterations work, fresh context each time)        │
│  • File interaction rules (read state.md first, update at end)          │
│  • Todo constraints (MUST create exactly 3 todos per iteration)         │
│  • Output structure (where to save files, naming conventions)           │
│  • State.md format specification (how to read/write progress)           │
│  • Available tools and how to use them                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  SKILLS.MD (user-configurable, lives in workspace/)                     │
│  ══════════════════════════════════════════════════                     │
│  • HOW to execute the type of task (methodology, workflow patterns)     │
│  • Quality standards (what "good" looks like for this task)             │
│  • Domain expertise ("when building a course, start with outline...")   │
│  • Best practices (coding style, documentation standards)               │
│  • Iteration strategy (how to chunk work across multiple iterations)    │
│  • Output organization (folder structure, naming conventions)           │
│                                                                         │
│  NOTE: This does NOT contain the task itself, only HOW to do tasks      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  STATE.MD (auto-managed by agent, lives in workspace/)                  │
│  ═════════════════════════════════════════════════════                  │
│  • Current iteration number                                             │
│  • Task description (copied from initial query)                         │
│  • Status (in_progress / completed)                                     │
│  • Completed work from previous iterations                              │
│  • Files created so far                                                 │
│  • Notes/context for next iteration                                     │
│  • Last updated timestamp                                               │
│                                                                         │
│  NOTE: Agent reads this at START, updates at END of each iteration      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  TASK QUERY (runtime input)                                             │
│  ══════════════════════════                                             │
│  • WHAT to do ("Build a Python course for beginners")                   │
│  • Passed as command line argument or function parameter                │
│  • Injected into agent as user message each iteration                   │
│                                                                         │
│  NOTE: Same task is passed every iteration; agent uses state.md to      │
│        know what's already done and continue from there                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ralph-agent/
├── ARCHITECTURE_PLAN.md        # THIS FILE - single source of truth
├── README.md                   # User-facing documentation
├── pyproject.toml              # Dependencies and project config
├── main.py                     # CLI entry point
├── .env.example                # Environment template
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Configuration dataclass
│   ├── state_manager.py        # Read/write state.md
│   ├── skills_loader.py        # Load skills.md
│   ├── tools.py                # Additional tools (Tavily search, etc.)
│   ├── agent_factory.py        # Create DeepAgent with system prompt
│   └── ralph_loop.py           # Main loop controller
│
├── workspace/                  # Default working directory (created at runtime)
│   ├── skills.md               # User's execution methodology
│   ├── state.md                # Auto-managed progress state
│   └── output/                 # Generated artifacts
│       └── ...
│
└── deepagents/                 # Cloned reference (read-only)
    └── ...                     # LangChain DeepAgents library
```

### File Responsibilities

| File | Responsibility |
|------|----------------|
| `main.py` | Parse CLI args, initialize config, call `ralph_loop()` |
| `config.py` | `RalphConfig` dataclass with all settings |
| `state_manager.py` | `RalphState` dataclass, `read_state()`, `write_state()`, `create_initial_state()` |
| `skills_loader.py` | `load_skills()`, `create_default_skills()` |
| `tools.py` | `get_ralph_tools()`, Tavily search tool setup |
| `agent_factory.py` | `RALPH_SYSTEM_PROMPT`, `create_ralph_agent()` |
| `ralph_loop.py` | `ralph_loop()` async function - main orchestrator |

---

## Core Components

### 1. Configuration (`src/config.py`)

```python
@dataclass
class RalphConfig:
    # Model (OpenAI)
    model_name: str = "gpt-4o"

    # Loop
    max_iterations: int = 0  # 0 = unlimited
    max_todos_per_iteration: int = 3

    # Paths
    workspace_dir: Path = Path("./workspace")
    skills_file: str = "skills.md"
    state_file: str = "state.md"
    output_dir: str = "output"

    # Behavior
    auto_create_workspace: bool = True
    verbose: bool = True
```

### 2. State Manager (`src/state_manager.py`)

```python
@dataclass
class RalphState:
    iteration: int
    task: str
    status: str  # "in_progress" | "completed"
    completed_items: list[str]
    files_created: list[str]
    notes: str
    last_updated: str

def read_state(workspace_dir: Path) -> RalphState | None:
    """Parse state.md into RalphState. Returns None if file doesn't exist."""

def write_state(workspace_dir: Path, state: RalphState) -> None:
    """Write RalphState to state.md in markdown format."""

def create_initial_state(task: str) -> RalphState:
    """Create initial state for a new task."""

def state_to_markdown(state: RalphState) -> str:
    """Convert RalphState to markdown string."""

def markdown_to_state(content: str) -> RalphState:
    """Parse markdown string to RalphState."""
```

### 3. Skills Loader (`src/skills_loader.py`)

```python
def load_skills(workspace_dir: Path) -> str:
    """Load skills.md content. Returns empty string if not found."""

def create_default_skills(workspace_dir: Path) -> None:
    """Create default skills.md template if it doesn't exist."""

DEFAULT_SKILLS_TEMPLATE = """..."""  # Template content
```

### 4. Agent Factory (`src/agent_factory.py`)

```python
RALPH_SYSTEM_PROMPT = """..."""  # Full system prompt

def create_ralph_agent(
    model: BaseChatModel,
    workspace_dir: Path,
    skills_content: str,
    state_content: str,
) -> CompiledStateGraph:
    """
    Create a DeepAgent configured for Ralph mode.

    Uses:
    - FilesystemBackend rooted at workspace_dir
    - Custom system prompt with skills and state injected
    - Standard filesystem tools (read_file, write_file, etc.)
    """
```

### 5. Ralph Loop (`src/ralph_loop.py`)

```python
async def ralph_loop(
    task: str,
    config: RalphConfig,
) -> None:
    """
    Main Ralph loop controller.

    Flow:
    1. Setup workspace (create dirs, default files)
    2. Loop:
       a. Read skills.md and state.md
       b. Create fresh agent with injected context
       c. Execute agent (it creates 3 todos, executes, updates state)
       d. Check continue conditions
       e. Repeat or exit
    """
```

---

## File Specifications

### skills.md Format

```markdown
# Execution Skills

## Task Type
{General description of what kind of tasks these skills apply to}

## Workflow
1. {First phase of work}
2. {Second phase of work}
3. {Third phase of work}

## Quality Standards
- {Standard 1}
- {Standard 2}
- {Standard 3}

## Iteration Strategy
{How to break work across iterations - what to do first, second, etc.}

## Output Structure
```
/output/
├── {expected folder/file 1}
├── {expected folder/file 2}
└── ...
```

## Best Practices
- {Practice 1}
- {Practice 2}
```

### state.md Format

```markdown
# Ralph State

## Task
{Original task description - copied from initial query}

## Iteration
{Current iteration number, starting from 1}

## Status
{in_progress | completed}

## Completed Work
- [x] {Completed item 1}
- [x] {Completed item 2}
- [ ] {Planned but not done - optional}

## Files Created
- /output/{file1}
- /output/{file2}

## Notes for Next Iteration
{Important context, what to do next, any blockers or decisions}

## Last Updated
{ISO 8601 timestamp}
```

### System Prompt (in agent_factory.py)

```markdown
# Ralph Mode Agent

You are Ralph, an autonomous agent operating in a continuous loop. Each iteration you start with fresh context, but you have persistent memory through files in your workspace.

## Your Current Context

### Task
{task}

### Iteration
{iteration_number}

### Skills (How to Execute)
{skills_content}

### State (Your Progress)
{state_content}

## How You Work

1. **Understand Context**: You've just started a new iteration. Read the state above to understand what's been done.
2. **Plan**: Create EXACTLY 3 todos for this iteration. No more, no less.
3. **Execute**: Complete your todos, writing outputs to `/output/`
4. **Update State**: Before finishing, you MUST update `/state.md` with:
   - Increment the iteration number
   - Add completed items to "Completed Work"
   - Add any new files to "Files Created"
   - Write helpful notes for your next iteration
   - Update the timestamp

## Critical Rules

1. **3 Todos Only**: Create exactly 3 todos per iteration. This keeps work focused.
2. **Read State First**: Always check state.md to understand previous progress.
3. **Don't Repeat Work**: Check what's already done before starting.
4. **Update State Last**: Your final action must be updating state.md.
5. **Build Incrementally**: Each iteration should make concrete progress.
6. **Persist Important Info**: Your context resets - write important decisions to files.

## Output Location

All generated files go in `/output/`. Use clear, descriptive names.
Example: `/output/01-introduction/lesson.md`

## State Update Format

When updating state.md, follow this exact format:
```markdown
# Ralph State

## Task
{keep the original task}

## Iteration
{increment by 1}

## Status
in_progress

## Completed Work
- [x] {previous items}
- [x] {what you did this iteration}

## Files Created
- {previous files}
- {new files you created}

## Notes for Next Iteration
{what should be done next, any context}

## Last Updated
{current ISO timestamp}
```

## Available Tools

- `ls(path)`: List directory contents
- `read_file(file_path)`: Read file content
- `write_file(file_path, content)`: Create new file
- `edit_file(file_path, old_string, new_string)`: Edit existing file
- `glob(pattern)`: Find files by pattern
- `grep(pattern, path)`: Search file contents

Now, begin your iteration. First, acknowledge your current state, then create your 3 todos.
```

---

## Execution Flow

### Startup Flow

```
main.py called with: python main.py "Build a Python course"
│
├─► Parse CLI arguments
│   └─► task = "Build a Python course"
│   └─► config = RalphConfig(...)
│
├─► Create workspace directory if needed
│   └─► mkdir -p workspace/output
│
├─► Create default skills.md if not exists
│   └─► Write DEFAULT_SKILLS_TEMPLATE
│
├─► Create initial state.md if not exists
│   └─► iteration: 1, status: in_progress, task: "Build a Python course"
│
└─► Call ralph_loop(task, config)
```

### Iteration Flow

```
ralph_loop() iteration N
│
├─► Read skills.md content
│   └─► skills_content = load_skills(workspace_dir)
│
├─► Read state.md content
│   └─► state = read_state(workspace_dir)
│   └─► state_content = state_to_markdown(state)
│
├─► Build full prompt
│   └─► prompt = RALPH_SYSTEM_PROMPT.format(
│           task=task,
│           iteration=state.iteration,
│           skills_content=skills_content,
│           state_content=state_content
│       )
│
├─► Create fresh DeepAgent
│   └─► agent = create_ralph_agent(model, workspace_dir, prompt)
│
├─► Execute agent
│   └─► result = await agent.ainvoke({
│           "messages": [{"role": "user", "content": task}]
│       })
│   └─► Agent internally:
│       1. Creates 3 todos
│       2. Executes each todo
│       3. Writes files to /output/
│       4. Updates /state.md
│
├─► Check continue conditions
│   ├─► if iteration >= max_iterations and max_iterations > 0: EXIT
│   ├─► if KeyboardInterrupt: EXIT
│   └─► else: CONTINUE
│
└─► Loop back (fresh agent instance)
```

---

## Implementation Details

### Using DeepAgents Library

We use these components from the cloned `deepagents/` library:

```python
# From deepagents
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

# Create agent with filesystem backend
agent = create_deep_agent(
    model=model,
    system_prompt=full_system_prompt,
    backend=FilesystemBackend(root_dir=workspace_dir),
)
```

### Key Implementation Notes

1. **Fresh Context Each Iteration**
   - Create a NEW agent instance each loop iteration
   - Don't reuse agent or carry over message history
   - All continuity comes from files (state.md, output/)

2. **3 Todo Limit**
   - Enforced via system prompt instructions
   - Agent is told "EXACTLY 3 todos, no more, no less"
   - This is a soft limit (prompt-based), not hard-coded

3. **State Update Responsibility**
   - Agent is responsible for updating state.md
   - System prompt tells agent exact format to use
   - Agent's last action should be edit_file on state.md

4. **Error Handling**
   - If agent fails to update state, loop continues anyway
   - State from previous iteration is preserved
   - Keyboard interrupt (Ctrl+C) exits gracefully

---

## Dependencies

### pyproject.toml

```toml
[project]
name = "ralph-agent"
version = "0.1.0"
description = "Autonomous looping agent using DeepAgents"
requires-python = ">=3.11"
dependencies = [
    "langchain>=0.3.0",
    "langgraph>=0.2.0",
    "langchain-openai>=0.3.0",
    "rich>=13.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
ralph = "main:main"
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Required for web search
TAVILY_API_KEY=tvly-...

# Optional
RALPH_MODEL=gpt-4o
RALPH_MAX_ITERATIONS=10
RALPH_WORKSPACE=./workspace
```

### Tools

Ralph has access to these tools:

| Tool | Source | Description |
|------|--------|-------------|
| `tavily_search_results_json` | `src/tools.py` | Web search via Tavily API |
| `write_todos` | DeepAgents | Create todo list |
| `ls` | DeepAgents | List directory |
| `read_file` | DeepAgents | Read file |
| `write_file` | DeepAgents | Create file |
| `edit_file` | DeepAgents | Edit file |
| `glob` | DeepAgents | Find files by pattern |
| `grep` | DeepAgents | Search file contents |

---

## Build Checklist

Use this to track implementation progress:

- [ ] **Phase 1: Project Setup**
  - [ ] Create `pyproject.toml`
  - [ ] Create `src/__init__.py`
  - [ ] Create `src/config.py`

- [ ] **Phase 2: Core Utilities**
  - [ ] Create `src/state_manager.py`
  - [ ] Create `src/skills_loader.py`

- [ ] **Phase 3: Agent Creation**
  - [ ] Create `src/agent_factory.py` with system prompt
  - [ ] Test agent creation

- [ ] **Phase 4: Main Loop**
  - [ ] Create `src/ralph_loop.py`
  - [ ] Create `main.py` with CLI

- [ ] **Phase 5: Testing**
  - [ ] Test with simple task
  - [ ] Test iteration persistence
  - [ ] Test Ctrl+C handling

---

## Quick Reference

### Running Ralph

```bash
# Basic usage
python main.py "Build a Python course"

# With options
python main.py "Build a REST API" --iterations 5

# Custom workspace
python main.py "Create a CLI tool" --workspace ./my-project
```

### Key Files to Check

| When you need... | Check this file |
|------------------|-----------------|
| Overall architecture | `ARCHITECTURE_PLAN.md` (this file) |
| Configuration options | `src/config.py` |
| System prompt / agent behavior | `src/agent_factory.py` |
| State format / parsing | `src/state_manager.py` |
| Main loop logic | `src/ralph_loop.py` |

---

## Sources

- [DeepAgents Repository](https://github.com/langchain-ai/deepagents) - Cloned at `./deepagents/`
- [Original Ralph Mode](./deepagents/examples/ralph_mode/ralph_mode.py)
- [DeepAgents graph.py](./deepagents/libs/deepagents/deepagents/graph.py) - `create_deep_agent()`
- [FilesystemBackend](./deepagents/libs/deepagents/deepagents/backends/filesystem.py)
- [StateBackend](./deepagents/libs/deepagents/deepagents/backends/state.py)
