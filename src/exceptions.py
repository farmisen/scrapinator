"""Custom exceptions for the Scrapinator web task automation system."""

from typing import Any


class TaskAnalysisError(Exception):
    """Base exception for all task analysis errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """
        Initialize the exception with a message and optional details.

        Args:
            message: The error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.details = details or {}


class InvalidResponseFormatError(TaskAnalysisError):
    """Raised when the LLM response format is invalid."""

    def __init__(
        self,
        message: str,
        response: str | None = None,
        expected_format: str | None = None,
    ) -> None:
        """
        Initialize with response details.

        Args:
            message: The error message
            response: The actual response received
            expected_format: Description of the expected format
        """
        details = {}
        if response is not None:
            details["response"] = response[:500]  # Truncate long responses
            details["response_length"] = len(response)
        if expected_format is not None:
            details["expected_format"] = expected_format

        super().__init__(message, details)
        self.response = response
        self.expected_format = expected_format


class ValidationError(TaskAnalysisError):
    """Raised when task data validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        expected_type: str | None = None,
    ) -> None:
        """
        Initialize with validation details.

        Args:
            message: The error message
            field: The field that failed validation
            value: The invalid value
            expected_type: Description of the expected type/format
        """
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if expected_type is not None:
            details["expected_type"] = expected_type

        super().__init__(message, details)
        self.field = field
        self.value = value
        self.expected_type = expected_type


class LLMCommunicationError(TaskAnalysisError):
    """Raised when communication with the LLM fails."""

    def __init__(
        self,
        message: str,
        original_error: Exception | None = None,
        retry_count: int = 0,
    ) -> None:
        """
        Initialize with communication error details.

        Args:
            message: The error message
            original_error: The underlying exception that caused this error
            retry_count: Number of retry attempts made
        """
        details = {"retry_count": retry_count}
        if original_error is not None:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(message, details)
        self.original_error = original_error
        self.retry_count = retry_count


class RateLimitError(LLMCommunicationError):
    """Raised when the LLM API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        retry_count: int = 0,
    ) -> None:
        """
        Initialize with rate limit details.

        Args:
            message: The error message
            retry_after: Seconds to wait before retrying (if provided by API)
            retry_count: Number of retry attempts made
        """
        super().__init__(message, retry_count=retry_count)
        if retry_after is not None:
            self.details["retry_after"] = retry_after
        self.retry_after = retry_after


class ContextLengthExceededError(TaskAnalysisError):
    """Raised when the prompt exceeds the LLM's context length limit."""

    def __init__(
        self,
        message: str,
        prompt_length: int | None = None,
        max_length: int | None = None,
    ) -> None:
        """
        Initialize with context length details.

        Args:
            message: The error message
            prompt_length: The length of the prompt that was too long
            max_length: The maximum allowed length
        """
        details = {}
        if prompt_length is not None:
            details["prompt_length"] = prompt_length
        if max_length is not None:
            details["max_length"] = max_length
        if prompt_length and max_length:
            details["excess_length"] = prompt_length - max_length

        super().__init__(message, details)
        self.prompt_length = prompt_length
        self.max_length = max_length
