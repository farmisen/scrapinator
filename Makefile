.PHONY: help install lint format format-check type-check test clean all dev-check fix

# Note: If you see "make: function definition file not found", this is due to a shell
# function overriding the make command. Use ./make.sh as a workaround.

# Default target
all: lint type-check

help:
	@echo "Available commands:"
	@echo "  make install      - Install project with dev dependencies"
	@echo "  make lint         - Run Ruff linter"
	@echo "  make format       - Format code with Ruff (includes tests)"
	@echo "  make format-check - Check code formatting"
	@echo "  make fix          - Auto-fix code issues (format + safe linting fixes)"
	@echo "  make type-check   - Run Pyright type checker"
	@echo "  make test         - Run pytest tests"
	@echo "  make clean        - Remove cache files"
	@echo "  make all          - Run lint and type-check"
	@echo "  make dev-check    - Run all checks (format-check, lint, type-check)"

install:
	uv pip install -e ".[dev]"

lint:
	@echo "Running Ruff linter..."
	uv run ruff check src/ examples/

format:
	@echo "Formatting code with Ruff..."
	uv run ruff format src/ examples/ tests/
	uv run ruff check src/ examples/ tests/ --fix

format-check:
	@echo "Checking code formatting..."
	uv run ruff format src/ examples/ --check

fix:
	@echo "🔧 Auto-fixing code issues..."
	@echo "Running Ruff formatter..."
	uv run ruff format src/ examples/ tests/
	@echo "Running Ruff linter with safe fixes..."
	uv run ruff check src/ examples/ tests/ --fix
	@echo "✅ Safe fixes applied!"
	@echo ""
	@echo "Note: Some issues may require manual fixes:"
	@echo "- Type errors (run 'make type-check' to see them)"
	@echo "- Complex linting issues (run 'make lint' to see remaining)"
	@echo ""
	@echo "For unsafe fixes, run: uv run ruff check --fix --unsafe-fixes"

type-check:
	@echo "Running Pyright type checker..."
	uv run pyright src/ examples/

test:
	@echo "Running tests..."
	uv run pytest

clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Development workflow
dev-check: format-check lint type-check
	@echo "✅ All checks passed!"