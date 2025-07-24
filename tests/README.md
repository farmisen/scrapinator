# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the Scrapinator web task automation system, focusing on the Task Analyzer components.

## Test Coverage

As of the latest run, the test suite achieves **90% code coverage** (excluding `llm_client.py` which contains actual API implementations).

### Coverage by Module:
- `src/analyzer.py`: 83% coverage
- `src/exceptions.py`: 100% coverage  
- `src/models/task.py`: 100% coverage
- `src/prompts/task_analysis.py`: 100% coverage
- `src/utils/json_utils.py`: 93% coverage
- `src/llm_provider.py`: 90% coverage

## Test Files

### `test_analyzer.py`
Tests for the WebTaskAnalyzer class including:
- Successful task analysis with various response formats
- Error handling (invalid JSON, missing fields, type validation)
- Retry logic and timeout handling
- Rate limit detection and handling
- Context length exceeded errors
- Edge cases (empty descriptions, invalid URLs)
- Provider configuration and fallback behavior

### `test_models.py`
Tests for the Task model including:
- Valid task creation with all fields
- Required field validation
- Type validation for all fields
- Default value handling
- Helper methods (has_data_extraction, has_actions, is_complex)

### `test_exceptions.py`
Tests for the custom exception hierarchy:
- Exception initialization and attributes
- Error detail handling
- Exception inheritance relationships

### `test_json_utils.py`
Tests for JSON extraction and normalization utilities:
- JSON extraction from various text formats
- Handling of malformed JSON
- Normalization of optional fields
- Edge cases and boundary conditions

### `test_prompts.py`
Tests for prompt configuration:
- Provider-specific prompt templates
- Default configurations
- System message handling

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_analyzer.py

# Run with verbose output
uv run pytest -v
```

## Mocking Strategy

All LLM API calls are mocked using `unittest.mock` to ensure:
- Tests run quickly without external dependencies
- No API costs or rate limits
- Predictable test behavior
- Focus on business logic rather than API integration

The actual LLM client implementation (`src/llm_client.py`) is excluded from coverage as it would require real API calls to test properly.