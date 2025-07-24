"""Tests for custom exceptions."""

import pytest

from src.exceptions import (
    ContextLengthExceededError,
    InvalidResponseFormatError,
    LLMCommunicationError,
    RateLimitError,
    TaskAnalysisError,
    ValidationError,
)


class TestTaskAnalysisError:
    """Test the base TaskAnalysisError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = TaskAnalysisError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with additional details."""
        details = {"key": "value", "count": 42}
        error = TaskAnalysisError("Error occurred", details)
        assert str(error) == "Error occurred"
        assert error.details == details
        assert error.details["key"] == "value"
        assert error.details["count"] == 42


class TestInvalidResponseFormatError:
    """Test InvalidResponseFormatError exception."""

    def test_basic_format_error(self):
        """Test basic format error."""
        error = InvalidResponseFormatError("Invalid JSON")
        assert str(error) == "Invalid JSON"
        assert error.response is None
        assert error.expected_format is None

    def test_format_error_with_response(self):
        """Test format error with response details."""
        response = "This is not JSON at all"
        error = InvalidResponseFormatError(
            "Could not parse response",
            response=response,
            expected_format="JSON object with task details",
        )
        assert error.response == response
        assert error.expected_format == "JSON object with task details"
        assert error.details["response"] == response
        assert error.details["response_length"] == len(response)

    def test_format_error_truncates_long_response(self):
        """Test that long responses are truncated in details."""
        long_response = "x" * 1000
        error = InvalidResponseFormatError("Error", response=long_response)
        assert len(error.details["response"]) == 500
        assert error.details["response_length"] == 1000
        assert error.response == long_response  # Full response still available


class TestValidationError:
    """Test ValidationError exception."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid data")
        assert str(error) == "Invalid data"
        assert error.field is None
        assert error.value is None

    def test_validation_error_with_field_details(self):
        """Test validation error with field information."""
        error = ValidationError(
            "Invalid field type",
            field="objectives",
            value=[],
            expected_type="non-empty list",
        )
        assert error.field == "objectives"
        assert error.value == []
        assert error.expected_type == "non-empty list"
        assert error.details["field"] == "objectives"
        assert error.details["value"] == "[]"
        assert error.details["expected_type"] == "non-empty list"


class TestLLMCommunicationError:
    """Test LLMCommunicationError exception."""

    def test_basic_communication_error(self):
        """Test basic communication error."""
        error = LLMCommunicationError("API request failed")
        assert str(error) == "API request failed"
        assert error.original_error is None
        assert error.retry_count == 0

    def test_communication_error_with_original(self):
        """Test communication error with original exception."""
        original = ConnectionError("Network error")
        error = LLMCommunicationError(
            "Failed to connect to LLM", original_error=original, retry_count=3
        )
        assert error.original_error is original
        assert error.retry_count == 3
        assert error.details["retry_count"] == 3
        assert error.details["original_error"] == "Network error"
        assert error.details["error_type"] == "ConnectionError"


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_basic_rate_limit_error(self):
        """Test basic rate limit error."""
        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after is None

    def test_rate_limit_error_with_retry_after(self):
        """Test rate limit error with retry information."""
        error = RateLimitError("Too many requests", retry_after=60.5, retry_count=2)
        assert error.retry_after == 60.5
        assert error.retry_count == 2
        assert error.details["retry_after"] == 60.5
        assert error.details["retry_count"] == 2


class TestContextLengthExceededError:
    """Test ContextLengthExceededError exception."""

    def test_basic_context_error(self):
        """Test basic context length error."""
        error = ContextLengthExceededError("Prompt too long")
        assert str(error) == "Prompt too long"
        assert error.prompt_length is None
        assert error.max_length is None

    def test_context_error_with_lengths(self):
        """Test context error with length details."""
        error = ContextLengthExceededError(
            "Exceeded context window", prompt_length=5000, max_length=4096
        )
        assert error.prompt_length == 5000
        assert error.max_length == 4096
        assert error.details["prompt_length"] == 5000
        assert error.details["max_length"] == 4096
        assert error.details["excess_length"] == 904


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_inherit_from_base(self):
        """Test that all custom exceptions inherit from TaskAnalysisError."""
        errors = [
            InvalidResponseFormatError("test"),
            ValidationError("test"),
            LLMCommunicationError("test"),
            RateLimitError("test"),
            ContextLengthExceededError("test"),
        ]

        for error in errors:
            assert isinstance(error, TaskAnalysisError)
            assert isinstance(error, Exception)

    def test_rate_limit_inherits_from_communication(self):
        """Test that RateLimitError inherits from LLMCommunicationError."""
        error = RateLimitError("test")
        assert isinstance(error, LLMCommunicationError)
        assert isinstance(error, TaskAnalysisError)