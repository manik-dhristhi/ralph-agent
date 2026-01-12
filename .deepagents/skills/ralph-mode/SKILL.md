---
name: ralph-mode
description: Autonomous looping execution pattern with persistent file-based memory. Each iteration starts fresh but builds on previous work through the filesystem.
---

# Ralph Mode - Autonomous Looping Agent

This skill defines how to operate in Ralph Mode - an autonomous execution pattern where you work on tasks iteratively with fresh context each loop, using the filesystem as your memory.

## Core Principles

### Fresh Context, Persistent Memory
- Each iteration starts with a **clean LLM context** (no message history)
- **ALL memory persists through files**: `/state.md`, `/skills.md`, `/output/`
- You have NO memory of previous iterations except what's in files
- **CRITICAL**: Always read `/state.md` FIRST to understand what's been done

### Iteration Structure
1. **Read Context** - Check `/state.md` to see previous progress
2. **Plan** - Create exactly 3 todos for THIS iteration only
3. **Execute** - Complete your todos, write outputs to `/output/`
4. **Update State** - Edit `/state.md` with your progress before finishing

## Starting a New Task (First Iteration)

### How to Detect First Iteration
Check if `/state.md` exists using `read_file`:
- If it returns "File not found" → This is iteration 1
- If it contains content → Read it to see what iteration you're on

### First Iteration Checklist
When starting a new task:

1. **Read `/state.md`** to check iteration number
   - If file doesn't exist, you're on iteration 1
   - If it exists, check "## Iteration" section

2. **Read `/skills.md`** to understand HOW to execute this type of task
   - Contains methodology and best practices
   - Tells you how to break down work

3. **Check existing files** with `ls /output`
   - See if any work already exists
   - Avoid redoing completed work

4. **Create your plan** - Break the task into phases:
   - Phase 1 (iterations 1-2): Setup and planning
   - Phase 2 (iterations 3-N): Main execution
   - Phase 3 (final iterations): Review and polish

5. **Create exactly 3 todos** for iteration 1:
   - Todo 1: Analyze task and create project structure
   - Todo 2: Research/gather information if needed
   - Todo 3: Create initial files and update state

## Continuing Work (Subsequent Iterations)

### Always Start By Reading State

```markdown
FIRST ACTION: read_file /state.md
```

The state file tells you:
- What iteration you're on
- What's been completed already
- What files exist in `/output/`
- What to do next (in "Notes for Next Iteration")

### Understanding State.md Format

```markdown
# Ralph State

## Task
{Original task - what you're building}

## Iteration
{Current iteration number, e.g., 3}

## Status
in_progress

## Completed Work
- [x] Created project outline
- [x] Built module 1
- [x] Built module 2

## Files Created
- /output/README.md
- /output/01-intro/lesson.md
- /output/02-basics/lesson.md

## Notes for Next Iteration
Continue with module 3: Control Flow.
Follow the same structure as modules 1-2.

## Last Updated
2026-01-11T10:30:00Z
```

### Iteration Planning Based on State

1. **Read what's done** - Look at "Completed Work" section
2. **Read notes** - "Notes for Next Iteration" tells you what's next
3. **Verify files exist** - Use `ls /output` to confirm
4. **Read recent files** - Use `read_file` to see what was created
5. **Plan next 3 todos** - Build on existing work, don't repeat

## Creating Your 3 Todos

### Todo Guidelines
- **Exactly 3 todos** - No more, no less
- **Concrete and specific** - Each todo produces tangible output
- **Build incrementally** - Don't try to do everything at once
- **File-focused** - Each todo should create/edit files

### Good Todo Examples

```
✓ Create course outline in /output/README.md
✓ Research Python fundamentals using web_search
✓ Write lesson 1 content to /output/01-intro/lesson.md

✗ Work on the course (too vague)
✗ Create all modules (too broad)
✗ Fix everything (not specific)
```

### Todo Structure by Task Type

**For Content/Documentation:**
1. Plan structure/outline
2. Write section N
3. Review and improve section N

**For Research:**
1. Search for information on topic X
2. Synthesize findings into document
3. Create summary report

**For Coding:**
1. Set up project structure
2. Implement core functionality
3. Write tests and documentation

## Using Tools Effectively

### Web Search (tavily_search_results_json)
Use when you need current information:

```
When to search:
- Beginning of project (gather requirements, examples, best practices)
- When stuck (find solutions, similar implementations)
- For factual information (latest syntax, current best practices)

How to search:
- Be specific: "Python async/await tutorial 2025" not "Python"
- Search early in iteration to inform your work
- Save findings to files for later reference
```

### Filesystem Tools

**Essential tools:**
- `ls(path)` - Check what exists before creating
- `read_file(file_path)` - Read existing files
- `write_file(file_path, content)` - Create NEW files only
- `edit_file(file_path, old_string, new_string)` - Modify existing files
- `glob(pattern)` - Find files by pattern (e.g., "*.md")

**File operations workflow:**
```
1. Check if file exists: ls /output
2. If creating new file: write_file /output/new.md "content"
3. If modifying existing: edit_file /output/existing.md "old" "new"
4. NEVER use write_file on existing files (will error)
```

## Updating State.md

### When to Update
**LAST ACTION of every iteration** - Before finishing, update state

### How to Update
Use `edit_file` to modify `/state.md`:

```
1. Increment iteration number
2. Add your completed todos to "Completed Work"
3. Add new files to "Files Created"
4. Write helpful notes for next iteration
5. Update timestamp
```

### Update Example

```
OLD:
## Iteration
2

NEW:
## Iteration
3
```

```
OLD:
## Completed Work
- [x] Created outline
- [x] Built module 1

NEW:
## Completed Work
- [x] Created outline
- [x] Built module 1
- [x] Built module 2
- [x] Added exercises to module 2
- [x] Updated README
```

```
OLD:
## Notes for Next Iteration
Build module 2

NEW:
## Notes for Next Iteration
Build module 3: Control Flow (if/else, loops).
Follow same structure as modules 1-2.
Module 3 should be similar length (~1000 words).
```

## Handling Different Task Types

### Course/Tutorial Creation
**Phase 1:** Create outline and structure
**Phase 2:** Build modules/lessons one at a time
**Phase 3:** Add exercises, review, create introduction

**Structure:**
```
/output/
├── README.md (course overview)
├── 01-introduction/
│   ├── lesson.md
│   └── exercises.md
├── 02-basics/
│   ├── lesson.md
│   └── exercises.md
```

### Research Tasks
**Phase 1:** Define research questions, initial searches
**Phase 2:** Deep dive into each subtopic
**Phase 3:** Synthesize findings, create report

**Always:**
- Use `tavily_search_results_json` for web research
- Save search results to files immediately
- Cite sources in your output

### Code Projects
**Phase 1:** Set up project structure, README, requirements
**Phase 2:** Implement features incrementally
**Phase 3:** Add tests, documentation, examples

**Structure:**
```
/output/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   └── main.py
└── tests/
    └── test_main.py
```

### Documentation
**Phase 1:** Analyze existing code/project, create outline
**Phase 2:** Document each section/module
**Phase 3:** Add examples, review for completeness

## Edge Cases and Error Handling

### Missing or Corrupt State.md
If `read_file /state.md` fails:
1. Assume this is iteration 1
2. Check `/output/` for existing files with `ls`
3. If files exist, read them to understand context
4. Create initial state based on what exists

### Files Don't Match State
If state.md says files exist but `ls` shows they don't:
1. Trust the filesystem (ls results)
2. Recreate missing files
3. Update state.md to reflect reality

### Unclear What to Do Next
If "Notes for Next Iteration" is vague:
1. Read the task again (in state.md)
2. Check what's been completed
3. Identify logical next steps
4. Use web search for guidance if needed

### Running Out of Work
If task seems complete but iteration continues:
1. Review all output files
2. Look for improvements, polish, documentation
3. Add examples, tests, or refinements
4. Update README with usage instructions

## Success Criteria

### Each Iteration Should:
- [x] Start by reading `/state.md`
- [x] Create exactly 3 todos
- [x] Complete all 3 todos
- [x] Produce tangible file outputs
- [x] Update `/state.md` before finishing

### Each Todo Should:
- [x] Be specific and measurable
- [x] Create or modify files in `/output/`
- [x] Build on previous work
- [x] Move the task forward

### State Updates Should:
- [x] Increment iteration number
- [x] List all completed work
- [x] List all created files
- [x] Provide clear notes for next iteration
- [x] Include current timestamp

## Anti-Patterns (What NOT to Do)

❌ **Don't skip reading state.md** - You'll repeat work
❌ **Don't create more than 3 todos** - Keep focused
❌ **Don't try to complete everything at once** - Incremental progress
❌ **Don't forget to update state.md** - Next iteration won't know what's done
❌ **Don't use relative paths** - Always use absolute paths from /
❌ **Don't assume files exist** - Check with ls first
❌ **Don't repeat completed work** - Read state to see what's done

## Example Iteration Flow

```
=== ITERATION 3 ===

1. READ STATE
   read_file /state.md
   → Iteration 2, modules 1-2 done, need module 3

2. CHECK EXISTING FILES
   ls /output
   → Confirms README, 01-intro/, 02-basics/ exist

3. CREATE TODOS
   write_todos [
     "Research control flow concepts for Python course",
     "Write lesson content for module 3: Control Flow",
     "Create exercises file for module 3"
   ]

4. EXECUTE TODO 1
   tavily_search_results_json "Python if else loops tutorial"
   → Got examples and explanations

5. EXECUTE TODO 2
   write_file /output/03-control-flow/lesson.md "# Control Flow..."

6. EXECUTE TODO 3
   write_file /output/03-control-flow/exercises.md "# Exercises..."

7. UPDATE STATE
   edit_file /state.md
   → Increment to iteration 3
   → Add completed todos
   → Add new files
   → Notes: "Next build module 4: Functions"

=== END ITERATION 3 ===
```

## Remember
- You are operating in a LOOP
- Each iteration is a FRESH START
- The FILESYSTEM is your only memory
- READ first, PLAN second, EXECUTE third, UPDATE fourth
- Build INCREMENTALLY - Rome wasn't built in one iteration
