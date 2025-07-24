#!/bin/bash
# Wrapper script to ensure we use the system make command
# This works around shell function overrides

exec /usr/bin/make "$@"