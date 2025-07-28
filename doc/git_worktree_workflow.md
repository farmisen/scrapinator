# Git Worktree Workflow Scripts

This document describes the optional git worktree workflow scripts available for developers who prefer using git worktrees to manage multiple branches simultaneously.

## Overview

Git worktrees allow you to have multiple branches checked out simultaneously in different directories. This is particularly useful when you need to:
- Work on multiple tickets simultaneously without stashing
- Keep separate directories for each feature
- Run tests on one branch while coding on another
- Avoid context switching overhead

## Scripts

Two automation scripts are available in the `bin/` directory:

### create-worktree Script

Creates a new git worktree for a Linear ticket:

```bash
# Usage
bin/create-worktree ROY-123

# Requirements:
# - uv (Python package manager) must be installed
# - Claude Code CLI must be installed

# What it does:
# 1. Validates the ticket ID format
# 2. Queries Claude Code for an appropriate branch name
# 3. Ensures you're on main and pulls latest changes
# 4. Creates worktree at ../scrapinator-<ticket-id>
# 5. Symlinks .envrc from main repository
# 6. Symlinks CLAUDE.md from main repository
# 7. Navigates to worktree and runs direnv allow
# 8. Sets up Python environment using uv:
#    - Creates virtual environment with uv venv
#    - Installs dev dependencies with uv pip install -e ".[dev]"
# 9. Ensures Claude command is available in PATH
# 10. Launches Claude Code to implement the ticket
```

### cleanup-worktree Script

Removes a git worktree after the PR is merged:

```bash
# Usage (run from within the worktree)
bin/cleanup-worktree

# Options
bin/cleanup-worktree --dry-run  # Show what would be done
bin/cleanup-worktree --help     # Show help

# What it does:
# 1. Verifies you're in a git worktree
# 2. Checks if branch is merged to main
# 3. Prompts for confirmation if branch isn't merged
# 4. Navigates to main repository
# 5. Removes the worktree
# 6. Optionally deletes the remote branch
```

## Configuration

### Worktree Configuration (worktree.rc)

The create-worktree script uses a configuration file `worktree.rc` in the repository root to specify which files should be symlinked from the main repository to worktrees.

Example configuration:
```bash
# Files to symlink from main repository to worktree
# One file per line
SYMLINK_FILES="
.envrc
CLAUDE.md
.mcp.json
"
```

By symlinking `.mcp.json` from the main repository, worktrees automatically inherit the same MCP server configurations.

## Benefits of Git Worktrees

1. **Parallel Development**: Work on multiple features simultaneously without the overhead of switching branches
2. **Isolated Environments**: Each worktree has its own working directory, preventing conflicts
3. **Performance**: No need to stash/unstash changes when switching between tasks
4. **Testing**: Run tests on one branch while developing on another

## Example Workflow

1. Start working on a new ticket:
   ```bash
   bin/create-worktree ROY-123
   ```

2. The script automatically:
   - Creates a new worktree directory
   - Sets up the Python environment
   - Opens Claude Code with the ticket context

3. After your PR is merged:
   ```bash
   bin/cleanup-worktree
   ```

4. The script cleans up the worktree and optionally removes the remote branch

## Troubleshooting

### Common Issues

1. **"uv: command not found"**
   - Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`

2. **"claude: command not found"**
   - Ensure Claude Code CLI is installed and in your PATH

3. **Worktree creation fails**
   - Make sure you're in the main repository (not in a worktree)
   - Check that the ticket ID follows the correct format (e.g., ROY-123)