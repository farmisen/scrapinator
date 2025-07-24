#!/usr/bin/env bash
# Wrapper script to ensure we use the system make command
# This works around shell function overrides

# Find the actual make binary, bypassing shell functions/aliases
MAKE_CMD=$(command -v make)

# Check if make was found
if [ -z "$MAKE_CMD" ]; then
    echo "Error: make command not found in PATH" >&2
    exit 1
fi

# Execute make with all passed arguments
exec "$MAKE_CMD" "$@"