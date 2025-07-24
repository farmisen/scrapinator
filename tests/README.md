# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the Scrapinator web task automation system, including both unit tests and end-to-end integration tests.

## Test Coverage

As of the latest run, the test suite achieves **90% code coverage** (excluding `llm_client.py` which contains actual API implementations).

### Coverage by Module:
- `src/analyzer.py`: 83% coverage
- `src/exceptions.py`: 100% coverage  
- `src/models/task.py`: 100% coverage
- `src/prompts/task_analysis.py`: 100% coverage
- `src/utils/json_utils.py`: 93% coverage
- `src/llm_provider.py`: 90% coverage

## Unit Tests

### Test Files

#### `test_analyzer.py`
Tests for the WebTaskAnalyzer class including:
- Successful task analysis with various response formats
- Error handling (invalid JSON, missing fields, type validation)
- Retry logic and timeout handling
- Rate limit detection and handling
- Context length exceeded errors
- Edge cases (empty descriptions, invalid URLs)
- Provider configuration and fallback behavior

#### `test_models.py`
Tests for the Task model including:
- Valid task creation with all fields
- Required field validation
- Type validation for all fields
- Default value handling
- Helper methods (has_data_extraction, has_actions, is_complex)

#### `test_exceptions.py`
Tests for the custom exception hierarchy:
- Exception initialization and attributes
- Error detail handling
- Exception inheritance relationships

#### `test_json_utils.py`
Tests for JSON extraction and normalization utilities:
- JSON extraction from various text formats
- Handling of malformed JSON
- Normalization of optional fields
- Edge cases and boundary conditions

#### `test_prompts.py`
Tests for prompt configuration:
- Provider-specific prompt templates
- Default configurations
- System message handling

## Integration Tests

The `tests/integration/` directory contains end-to-end tests that verify the WebTaskAnalyzer works correctly with real LLM APIs.

### Running Integration Tests

Integration tests require API keys to be set as environment variables:

```bash
# Set API keys
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"

# Run integration tests
uv run pytest tests/integration -v -m integration

# Run with coverage
uv run pytest tests/integration -v -m integration --cov=src

# Run with specific recording mode
uv run pytest tests/integration -v -m integration --record-mode=once
```

### VCR.py Recording Modes

Integration tests use VCR.py to record and replay API responses:

- `once` (default): Records new interactions if no cassette exists
- `new_episodes`: Records new interactions while replaying existing ones
- `none`: Only plays back existing recordings (used in CI/CD)
- `all`: Always records new interactions

### Managing Cassettes

VCR.py cassettes are stored in `tests/integration/cassettes/` and contain recorded API responses.

To refresh cassettes when APIs change:
1. Delete the relevant cassette files
2. Run tests with `--record-mode=once`
3. Review the new cassettes to ensure no sensitive data

### Cost Management

- Initial recording session: ~$0.20-0.50 depending on test coverage
- Subsequent runs use cassettes: $0
- CI/CD runs use `--record-mode=none` to prevent API calls

### Writing Integration Tests

When adding new integration tests:

1. Use appropriate markers:
   ```python
   @pytest.mark.integration
   @pytest.mark.external
   @pytest.mark.vcr()
   ```

2. Configure VCR to filter sensitive data:
   ```python
   @pytest.fixture
   def vcr_config(self):
       return {
           "filter_headers": ["authorization"],
           "filter_query_parameters": ["api_key"],
       }
   ```

3. Skip tests if API keys are missing:
   ```python
   if not os.getenv("ANTHROPIC_API_KEY"):
       pytest.skip("ANTHROPIC_API_KEY not set")
   ```

### CI/CD Integration

Integration tests run in CI/CD when:
- Pushing to main branch
- PR has `run-integration-tests` label
- Manual workflow dispatch

Configure API keys as GitHub secrets:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

## Running Tests

```bash
# Run all unit tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_analyzer.py

# Run with verbose output
uv run pytest -v

# Run only unit tests (exclude integration)
uv run pytest -m "not integration"

# Run only integration tests
uv run pytest -m integration

# Run tests matching a pattern
uv run pytest -k "test_error_handling"
```

## Mocking Strategy

All LLM API calls in unit tests are mocked using `unittest.mock` to ensure:
- Tests run quickly without external dependencies
- No API costs or rate limits
- Predictable test behavior
- Focus on business logic rather than API integration

The actual LLM client implementation (`src/llm_client.py`) is excluded from coverage as it would require real API calls to test properly. This is tested separately in the integration test suite.

## Test Organization

Tests are organized by:
- **Unit tests**: In the root `tests/` directory
- **Integration tests**: In `tests/integration/`
- **Fixtures**: Shared test data in `tests/integration/fixtures/`
- **Cassettes**: VCR recordings in `tests/integration/cassettes/`

## Troubleshooting

### Integration Test Authentication Errors

If you see authentication errors when running integration tests:

1. **Verify API key is set correctly**:
   ```bash
   echo $ANTHROPIC_API_KEY  # Should show your key (or partial)
   echo $OPENAI_API_KEY     # Should show your key (or partial)
   ```

2. **Delete corrupted cassettes**:
   ```bash
   # Remove all cassettes with auth errors
   rm -rf tests/integration/cassettes/
   ```

3. **Re-record cassettes**:
   ```bash
   # Record new cassettes with valid API keys
   pytest tests/integration -v -m integration --record-mode=once
   ```

4. **Check for expired or invalid API keys**:
   - Verify keys are active in the provider's dashboard
   - Ensure keys have appropriate permissions

### Common Issues

- **Deprecation warnings**: Update model names in `src/llm_client.py`
- **Rate limits**: Reduce test parallelism or add delays
- **Timeout errors**: Increase timeout in test configuration
- **Cassette mismatches**: Delete and re-record when API changes

## Contributing

When adding new tests:
1. Follow existing patterns and naming conventions
2. Use descriptive test names that explain what is being tested
3. Include docstrings for complex test scenarios
4. Mock external dependencies in unit tests
5. Use integration tests sparingly for critical paths
6. Ensure tests are deterministic and don't depend on timing