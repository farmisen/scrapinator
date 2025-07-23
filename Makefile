.PHONY: help install lint format type-check test clean all

# Default target
all: lint type-check

help:
	@echo "Available commands:"
	@echo "  make install      - Install project with dev dependencies"
	@echo "  make lint         - Run Ruff linter"
	@echo "  make format       - Format code with Ruff"
	@echo "  make type-check   - Run Pyright type checker"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Remove cache files"
	@echo "  make all          - Run lint and type-check"

install:
	pip install -e ".[dev]"

lint:
	@echo "Running Ruff linter..."
	ruff check src/

format:
	@echo "Formatting code with Ruff..."
	ruff format src/
	ruff check src/ --fix

type-check:
	@echo "Running Pyright type checker..."
	pyright src/

test:
	@echo "Running tests..."
	pytest

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
dev-check: format lint type-check
	@echo "✅ All checks passed!"