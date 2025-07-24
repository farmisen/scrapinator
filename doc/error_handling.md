# Error Handling and Retry Logic

This document describes the error handling and retry mechanisms implemented in the Scrapinator WebTaskAnalyzer.

## Overview

The WebTaskAnalyzer implements comprehensive error handling with automatic retry logic for transient failures. This ensures robust operation when interacting with LLM APIs, which can occasionally experience timeouts, rate limits, or other temporary issues.

## Exception Hierarchy

All custom exceptions inherit from `TaskAnalysisError`, making it easy to catch all task-related errors:

```
TaskAnalysisError (base)
├── InvalidResponseFormatError - Malformed or unparseable responses
├── ValidationError - Invalid data types or missing required fields
├── LLMCommunicationError - Network/API communication failures
│   └── RateLimitError - API rate limit exceeded
└── ContextLengthExceededError - Prompt too long for LLM
```

## Error Types and Handling

### 1. InvalidResponseFormatError

**When raised**: The LLM response cannot be parsed as JSON or doesn't contain valid JSON.

**Retry behavior**: Not retryable - indicates a fundamental issue with response format.

**Example**:
```python
try:
    task = await analyzer.analyze_task(description, url)
except InvalidResponseFormatError as e:
    print(f"Invalid response format: {e}")
    print(f"Raw response: {e.response[:200]}...")
```

### 2. ValidationError

**When raised**: The parsed response is missing required fields or contains invalid data types.

**Retry behavior**: Not retryable - indicates the LLM didn't understand the task format.

**Fields validated**:
- `description` must be a string
- `objectives` must be a non-empty list of strings
- `success_criteria` must be a non-empty list of strings
- `constraints` must be a list of strings (can be empty)
- `context` must be a dictionary
- `data_to_extract` must be a list of strings or None
- `actions_to_perform` must be a list of strings or None

**Example**:
```python
try:
    task = await analyzer.analyze_task(description, url)
except ValidationError as e:
    print(f"Validation failed for field '{e.field}': {e}")
    print(f"Invalid value: {e.value}")
    print(f"Expected: {e.expected_type}")
```

### 3. LLMCommunicationError

**When raised**: Network errors, timeouts, or unexpected exceptions during LLM communication.

**Retry behavior**: Retryable with exponential backoff.

**Example**:
```python
try:
    task = await analyzer.analyze_task(description, url)
except LLMCommunicationError as e:
    print(f"Communication failed after {e.retry_count} attempts: {e}")
    if e.original_error:
        print(f"Original error: {e.original_error}")
```

### 4. RateLimitError

**When raised**: The LLM API returns a rate limit error.

**Retry behavior**: Retryable with extended delays (5x normal backoff).

**Example**:
```python
try:
    task = await analyzer.analyze_task(description, url)
except RateLimitError as e:
    print(f"Rate limit hit after {e.retry_count} attempts")
    if e.retry_after:
        print(f"API suggests waiting {e.retry_after} seconds")
```

### 5. ContextLengthExceededError

**When raised**: The prompt exceeds the LLM's maximum context length.

**Retry behavior**: Not retryable - the prompt must be shortened.

**Example**:
```python
try:
    task = await analyzer.analyze_task(very_long_description, url)
except ContextLengthExceededError as e:
    print(f"Prompt too long: {e.prompt_length} characters")
    if e.max_length:
        print(f"Maximum allowed: {e.max_length}")
```

## Retry Configuration

The WebTaskAnalyzer supports configurable retry behavior:

```python
analyzer = WebTaskAnalyzer(
    llm_client,
    max_retries=3,      # Maximum retry attempts (default: 3)
    retry_delay=1.0,    # Base delay in seconds (default: 1.0)
    timeout=30.0        # Request timeout in seconds (default: 30.0)
)
```

### Retry Logic

1. **Exponential backoff**: Delay = base_delay × 2^attempt
2. **Maximum delay**: Capped at 60 seconds
3. **Rate limit multiplier**: 5x normal delay for rate limits
4. **Not retryable**: Validation errors, format errors, context length errors

### Example Retry Timeline

For a transient error with base delay of 1 second:
- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds

For a rate limit error:
- Attempt 1: Immediate
- Attempt 2: Wait 5 seconds
- Attempt 3: Wait 10 seconds
- Attempt 4: Wait 20 seconds

## Logging

The analyzer provides detailed logging at different levels:

- **INFO**: Task start/completion, retry attempts, waiting periods
- **WARNING**: Timeouts, rate limits, unexpected errors
- **ERROR**: JSON parsing failures (with exception details)
- **DEBUG**: Prompt details, response parsing, validation steps

### Structured Logging

Log entries include structured `extra` fields for easier filtering:

```python
logger.info(
    "Starting task analysis",
    extra={
        "url": url,
        "task_description_length": len(task_description),
        "prompt_length": prompt_length,
        "provider": provider,
    }
)
```

## Best Practices

1. **Catch specific exceptions** when you need to handle different errors differently
2. **Log the details** from exception objects for debugging
3. **Consider retry configuration** based on your LLM provider's limits
4. **Monitor for patterns** in validation errors to improve prompts
5. **Use timeouts** appropriate for your task complexity

## Example Usage

```python
from src.analyzer import WebTaskAnalyzer
from src.exceptions import (
    InvalidResponseFormatError,
    ValidationError,
    RateLimitError,
    ContextLengthExceededError,
)

async def analyze_with_error_handling(description: str, url: str):
    analyzer = WebTaskAnalyzer(
        llm_client,
        max_retries=5,
        retry_delay=2.0,
        timeout=45.0
    )
    
    try:
        task = await analyzer.analyze_task(description, url)
        return task
        
    except ValidationError as e:
        # Log and potentially reformulate the task
        logger.error(f"Task validation failed: {e}")
        # Maybe try with a simpler description
        
    except RateLimitError as e:
        # Could queue for later processing
        logger.warning(f"Rate limited, retry after {e.retry_after}s")
        
    except ContextLengthExceededError as e:
        # Need to shorten the description
        logger.error(f"Description too long by {e.details.get('excess_length')} chars")
        
    except InvalidResponseFormatError as e:
        # Might indicate LLM issues or prompt problems
        logger.error(f"LLM returned invalid format: {e}")
        
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error: {e}")
        raise
```