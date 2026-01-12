# Input Configuration

This directory contains configuration files for Ralph Agent.

## Files

### SKILL.md (Required)
Defines **HOW** Ralph should execute tasks. This file contains:
- Workflow patterns (planning, building, refinement phases)
- Quality standards
- Iteration strategy
- Best practices for different types of tasks

**Note:** This file is required for Ralph to run. Customize it based on your needs.

## Usage

Ralph reads `SKILL.md` from this directory on startup. You can modify it to:
- Change the iteration strategy
- Add custom workflow patterns for specific task types
- Update quality standards and best practices
- Define project-specific execution guidelines

The skills content is injected into the agent's system prompt, so it influences how Ralph approaches every task.
