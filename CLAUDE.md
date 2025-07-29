# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**IMPORTANT**: This file is tracked by git and contains shared project instructions and development workflows for the team.

## Project Overview

Scrapinator is a web task automation system that uses LLMs to understand natural language task descriptions and automatically creates browser automation scripts using Playwright.

## Development Commands

```bash
# Install project with dev dependencies
./make.sh install

# Code quality checks
./make.sh lint        # Run Ruff linter
./make.sh format      # Format code with Ruff
./make.sh format-check # Check code formatting without modifying files
./make.sh fix         # Auto-fix code issues (format + safe linting fixes)
./make.sh type-check  # Run Pyright type checker
./make.sh dev-check   # Run all checks (format-check, lint, type-check)

# Testing
./make.sh test        # Run pytest tests

# Cleanup
./make.sh clean       # Remove cache files
```

## Architecture

The system follows a multi-stage pipeline architecture documented in `/doc/web_task_automation_system.md`:

1. **Input Processing**: URL + natural language task → structured Task object
2. **LLM Analysis**: Multi-stage webpage analysis using Claude/OpenAI APIs
3. **Plan Generation**: Creates JSON execution plan with specific browser actions
4. **Browser Automation**: Executes plan using Playwright
5. **Result Output**: Returns data, downloads, and screenshots

### Core Components (to be implemented)

- `WebTaskAnalyzer`: Parses natural language tasks using LLM
- `WebExplorer`: Analyzes webpage structure and elements
- `PlanGenerator`: Creates executable automation plans
- `PlanExecutor`: Executes browser automation with Playwright
- `WebTaskAutomation`: Main orchestration class

### Key Data Models (Pydantic v2)

- `Task`: Structured task representation with goals and constraints
- `PageAnalysis`: Complete webpage analysis with elements and navigation
- `ExecutionPlan`: Step-by-step automation plan
- `Step`: Individual actions (click, fill, select, etc.)

## Code Standards

- **Python 3.12+** with strict type annotations
- **Line length**: 100 characters max
- **Quotes**: Double quotes for strings
- **Type checking**: Pyright in strict mode
- **Async**: Use async/await for all browser operations
- **Error handling**: Comprehensive error handling with detailed messages

## Testing Approach

- Use pytest for all tests
- Mock LLM API calls in tests
- Test browser automation with Playwright's testing utilities
- Ensure all data models validate correctly with Pydantic

## Important Notes

1. The project structure is defined but implementation is pending
2. Follow the detailed specification in `/doc/web_task_automation_system.md`
3. API keys are stored in `.envrc` - handle securely
4. All browser operations should be async for performance
5. Use structured logging for debugging automation flows

## Development Workflow

**Always** follow the following workflow unless told otherwise. **Never** skip a step unless told otherwise.

**IMPORTANT**: When starting work on a ticket, IMMEDIATELY create a TodoWrite list with all these steps as individual todos. Use the template bellow and mark each as completed as you progress. This ensures no steps are missed.

1. **Fetch Ticket Details**: ALWAYS fetch the latest ticket description before starting implementation in case changes have been made in Linear since last time it was viewed.
2. **Create a new branch**: ALWAYS create a new branch from main for the ticket. Refer to the `Branch Management` section below.
3. **Search Documentation**: ALWAYS check the doc folder for relevant information related to the current task.
4. **Online Research**: ALWAYS conduct an online search to gather external information regarding the current task. In particular look up open source libraries that can be leveraged to complete the current task.
5. **Plan**: ALWAYS suggest a plan before starting the actual implementation.
6. **Implement Feature/Fix**: ALWAYS wait for plan approval before starting implementation.
7. **Run Quality Checks**: ALWAYS run `./make.sh fix` to auto-fix code issues, then run `./make.sh dev-check` to verify remaining issues. Fix all issues before proceeding.
8. **Test Your Changes**: ALWAYS run `./make.sh test` to ensure all tests pass before committing.
9. **Commit Your Changes**: ALWAYS stage all changes with `git add` and commit with a descriptive message. NEVER create a PR without committing first.
10. **Update Documentation**: ALWAYS update the documentation if needed, Refer to the `Documentation Updates` section bellow.
11. **Create a pull request**: ALWAYS create a pull request, refer to the `Pull Request Standards` section bellow.
12. **Self Review the pull request**: NEVER skip this step, refer to the `PR Review Instructions` sction bellow.
13. **Address the comments**: ALWAYS wait for the PR to have been reviewed by a human and address all the comments left open.


### Workflow Checklist Template

When starting a new ticket, create todos with this template:
```
1. [ ] Fetch latest [TICKET-ID] details from Linear
2. [ ] Create new branch from main: farmisen/[ticket-id]-[description]
3. [ ] Search /doc folder for relevant information
4. [ ] Search online for relevant information
5. [ ] Write implementation plan and get approval
6. [ ] Implement the feature/fix
7. [ ] Run ./make.sh fix and ./make.sh dev-check
8. [ ] Run ./make.sh test
9. [ ] Update documentation if needed
10. [ ] Commit changes with proper message format
11. [ ] Create PR with standard format: [TICKET-ID] Title
12. [ ] Self-review PR and add comments
13. [ ] Address review comments
```

### Linear Project and Ticket Creation

This codebase is associated with the **Scrapinator** project in Linear. When creating, fetching, listing, or updating issues, always use this project context.

When creating new Linear tickets:
- **Project**: ALWAYS associate tickets with the **Scrapinator** project 
- **Initial Status**: ALWAYS set the initial status to **Todo** 
- **Team**: Use the **Royale** team 


### Branch Management

-   **Branch Creation**: ALWAYS create a new branch from main for each ticket:
    ```bash
    # IMPORTANT: Always ensure you're on main and have the latest changes
    git checkout main
    git pull origin main
    
    # Create new branch from main
    git checkout -b farmisen/[ticket-id]-[description]
    
    # Example for ticket ROY-42:
    git checkout -b farmisen/roy-42-implement-core-web-explorer-class
    ```
-   **Pull Latest Changes**: ALWAYS pull the latest changes from `main` before creating a new branch (`git pull origin main`).
-   **Branch Naming**: Fetch the suggested branch name from the Linear ticket when available. If not available, construct branch names using the pattern: `farmisen/<ticket-id-slugified>-<ticket-title-slugified>` (all lowercase).
-   **Base Branch**: Always create new branches from `main`.

### Git Worktree Workflow Scripts (Optional)

For developers who prefer using git worktrees to manage multiple branches simultaneously, automation scripts are available. See `/doc/git_worktree_workflow.md` for detailed documentation on:

- `create-worktree` script for setting up new worktrees
- `cleanup-worktree` script for removing worktrees after PR merge
- Benefits and configuration options

### Pull Request Standards

-   **Title Format**: Always use `[<ticket-id>] Ticket Title` format for PR titles (e.g., `[ROY-24] Add .claude to .gitignore`).
-   **Description**: Provide comprehensive descriptions that explain the changes, their purpose, and any relevant context.

### Documentation Updates

-   **Always Update Documentation**: When code changes affect core functionality, commands, or setup procedures, ALWAYS update relevant documentation (README.md, or other docs).
-   **Keep Documentation Current**: Documentation should reflect the actual state of the codebase and available commands.
-   **Include New Commands**: Any new scripts or commands added to the `Makefile` must be documented in the README.md.

-   **Always Cite Sources**: When a document is created as the result of an online research task ALWAYS cite the source and provide an ULR when possible.

### Code Quality Standards

-   **Always Check Code Quality**: ALWAYS run `./make.sh dev-check` and fix all linting and type errors before committing code.
-   **Never Silence Rules**: Do not disable or silence Ruff or Pyright rules using `# noqa` or `# pyright: ignore` without explicit user confirmation — fix the underlying issues instead.

### PR Review Instructions

- Focus on:
    - Code quality and best practices
        - avoiding code duplication
        - avoiding anti-patterns
    - Potential bugs or issues
    - Potential improvements
    - Performance considerations
    - Security implications
    - Test coverage
    - Documentation updates if needed

- Provide constructive feedback with specific suggestions for improvement.
ALWAYS use inline comments to highlight specific areas of concern.