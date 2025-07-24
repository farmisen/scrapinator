"""Web Task Analyzer module for understanding natural language task descriptions."""

import asyncio
import json
import logging
import time
from typing import Any, Protocol

import tenacity
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
)

from src.exceptions import (
    ContextLengthExceededError,
    InvalidResponseFormatError,
    LLMCommunicationError,
    RateLimitError,
    ValidationError,
)
from src.llm_provider import LLMProvider
from src.models.task import Task
from src.prompts.task_analysis import get_prompt_config
from src.utils.json_utils import extract_json_from_text, normalize_optional_fields

logger = logging.getLogger(__name__)

# Constants
RESPONSE_PREVIEW_LENGTH = 200
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # Base delay in seconds
MAX_RETRY_DELAY = 60.0  # Maximum delay between retries
RATE_LIMIT_RETRY_MULTIPLIER = 5.0  # Multiplier for rate limit delays


class LLMClient(Protocol):
    """Protocol for LLM client interface."""

    async def complete(self, prompt: str) -> str:
        """Complete a prompt and return the response."""
        ...


class WebTaskAnalyzer:
    """Analyzes natural language task descriptions and converts them to structured Task objects."""

    def __init__(
        self,
        llm_client: LLMClient,
        timeout: float | None = 30.0,
        provider: str = LLMProvider.ANTHROPIC.value,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        """
        Initialize the WebTaskAnalyzer with an LLM client.

        Args:
            llm_client: The LLM client instance to use for analysis
            timeout: Maximum time in seconds to wait for LLM response (default: 30.0)
            provider: LLM provider name for prompt configuration (default: "anthropic")
                     Valid values: "anthropic", "openai"
                     Falls back to "anthropic" if invalid provider is specified
            max_retries: Maximum number of retry attempts for transient errors (default: 3)
            retry_delay: Base delay in seconds between retries (default: 1.0)

        Note:
            The prompt configuration includes recommended settings for temperature
            and max_tokens, but these must be implemented by the LLM client.
            The system_message in the config should be passed to the LLM if supported.
        """
        self.llm = llm_client
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Validate provider and fall back to default if invalid
        if not LLMProvider.is_valid(provider):
            logger.warning(
                "Invalid provider '%s' specified. Falling back to '%s'",
                provider,
                LLMProvider.ANTHROPIC.value,
            )
            provider = LLMProvider.ANTHROPIC.value

        self.provider = provider
        self.prompt_config = get_prompt_config(provider)

    def _is_retryable_error(self, exception: BaseException) -> bool:
        """Determine if an exception should trigger a retry.

        Args:
            exception: The exception to check

        Returns:
            bool: True if the error is retryable, False otherwise
        """
        # Non-retryable errors
        if isinstance(
            exception,
            InvalidResponseFormatError | ValidationError | ContextLengthExceededError | json.JSONDecodeError,
        ):
            return False

        # Rate limit errors are retryable but handled specially
        if isinstance(exception, ValueError):
            error_msg = str(exception).lower()
            if "context length" in error_msg or "token limit" in error_msg:
                return False

        # All other errors are retryable
        return True

    def _create_retry_decorator(self) -> Any:
        """Create a tenacity retry decorator with custom configuration.

        Returns:
            retry: Configured retry decorator
        """

        def before_retry(retry_state: tenacity.RetryCallState) -> None:
            """Log retry attempts."""
            if retry_state.attempt_number > 1:
                logger.info(
                    "Retrying task analysis",
                    extra={
                        "attempt": retry_state.attempt_number,
                        "max_retries": self.max_retries,
                    },
                )

        def after_attempt(retry_state: tenacity.RetryCallState) -> None:
            """Called after each attempt."""
            if retry_state.outcome and retry_state.outcome.failed:
                exception = retry_state.outcome.exception()
                # Update retry count for our custom exceptions
                if isinstance(exception, LLMCommunicationError | RateLimitError):
                    exception.retry_count = retry_state.attempt_number

        def determine_wait(retry_state: tenacity.RetryCallState) -> float:
            """Determine wait time based on error type."""
            if retry_state.outcome and retry_state.outcome.failed:
                exception = retry_state.outcome.exception()
                if isinstance(exception, ValueError):
                    error_msg = str(exception).lower()
                    if "rate limit" in error_msg or "too many requests" in error_msg:
                        # Use longer delay for rate limits
                        wait_time = min(
                            self.retry_delay
                            * (2 ** (retry_state.attempt_number - 1))
                            * RATE_LIMIT_RETRY_MULTIPLIER,
                            MAX_RETRY_DELAY,
                        )
                        logger.warning(
                            "Rate limit detected, using extended delay",
                            extra={"wait_time": wait_time, "attempt": retry_state.attempt_number},
                        )
                        return wait_time

            # Default exponential backoff
            return min(
                self.retry_delay * (2 ** (retry_state.attempt_number - 1)),
                MAX_RETRY_DELAY,
            )

        return retry(
            retry=retry_if_exception(self._is_retryable_error),
            stop=stop_after_attempt(self.max_retries),
            wait=determine_wait,
            before=before_retry,
            after=after_attempt,
            reraise=True,
        )

    async def analyze_task(self, task_description: str, url: str) -> Task:
        """
        Analyze a natural language task description and return a structured Task object.

        Implements retry logic with exponential backoff for transient errors.

        Args:
            task_description: Natural language description of the task to perform
            url: The URL where the task should be performed

        Returns:
            Task: A structured Task object containing objectives, success criteria, etc.

        Raises:
            InvalidResponseFormatError: If the response format is invalid
            ValidationError: If the task data validation fails
            LLMCommunicationError: If communication with LLM fails after retries
            RateLimitError: If rate limit is exceeded
            ContextLengthExceededError: If prompt is too long
        """
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(task_description, url)
        prompt_length = len(prompt)

        logger.info(
            "Starting task analysis",
            extra={
                "url": url,
                "task_description_length": len(task_description),
                "prompt_length": prompt_length,
                "provider": self.provider,
            },
        )

        # Create the retry decorator dynamically
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _analyze_with_retry() -> Task:
            """Inner function that performs the actual analysis with retry logic."""
            response = ""  # Initialize response for error handling
            
            try:
                # Call the LLM with timeout
                start_time = time.time()

                if self.timeout:
                    response = await asyncio.wait_for(
                        self.llm.complete(prompt), timeout=self.timeout
                    )
                else:
                    response = await self.llm.complete(prompt)

                elapsed_time = time.time() - start_time

                logger.info(
                    "Received LLM response",
                    extra={
                        "response_length": len(response),
                        "elapsed_time": elapsed_time,
                    },
                )

                # Parse and validate the response
                task_data = self._parse_llm_response(response)

                # Create and validate the Task object
                task = Task(**task_data)

                logger.info(
                    "Task analysis completed successfully",
                    extra={"task_id": id(task)},
                )

                return task

            except TimeoutError as e:
                logger.warning(
                    "LLM request timed out",
                    extra={"timeout": self.timeout},
                )
                msg = f"LLM request timed out after {self.timeout} seconds"
                raise LLMCommunicationError(
                    msg,
                    original_error=e,
                ) from e

            except json.JSONDecodeError as e:
                # JSON decode errors are not retryable
                logger.exception(
                    "Failed to parse LLM response as JSON",
                    extra={"error": str(e), "response_preview": response[:200]},
                )
                msg = f"Could not parse LLM response as JSON: {e}"
                raise InvalidResponseFormatError(
                    msg,
                    response=response,
                    expected_format="Valid JSON object with task analysis",
                ) from e

            except ValueError as e:
                # Check if it's a specific error we should handle differently
                error_msg = str(e).lower()

                if "rate limit" in error_msg or "too many requests" in error_msg:
                    logger.warning("Rate limit detected")
                    msg = "Rate limit exceeded for LLM API"
                    raise RateLimitError(
                        msg,
                    ) from e

                if "context length" in error_msg or "token limit" in error_msg:
                    # Context length errors are not retryable
                    msg = "Prompt exceeds LLM context length limit"
                    raise ContextLengthExceededError(
                        msg,
                        prompt_length=prompt_length,
                    ) from e
                # Other ValueError types (validation errors) are not retryable
                raise

            except (InvalidResponseFormatError, ValidationError, ContextLengthExceededError):
                # These are our custom exceptions - don't wrap them
                raise

            except Exception as e:
                logger.warning(
                    "Unexpected error during task analysis",
                    extra={"error": str(e), "error_type": type(e).__name__},
                )
                msg = "Failed to analyze task"
                raise LLMCommunicationError(
                    msg,
                    original_error=e,
                ) from e

        try:
            return await _analyze_with_retry()
        except tenacity.RetryError as e:
            # Extract the last exception from tenacity
            last_exception = e.last_attempt.exception() if e.last_attempt else None
            attempts = e.last_attempt.attempt_number if e.last_attempt else self.max_retries

            if isinstance(last_exception, RateLimitError | LLMCommunicationError):
                # Update retry count in our custom exceptions
                last_exception.retry_count = attempts
                raise last_exception from e

            # Wrap other exceptions in LLMCommunicationError
            msg = f"Failed to analyze task after {attempts} attempts"
            raise LLMCommunicationError(
                msg,
                original_error=last_exception if isinstance(last_exception, Exception) else None,
                retry_count=attempts,
            ) from last_exception

    def _build_analysis_prompt(self, task_description: str, url: str) -> str:
        """
        Build the prompt for the LLM to analyze the task.

        Args:
            task_description: The task description from the user
            url: The target URL

        Returns:
            str: The formatted prompt for the LLM
        """
        prompt_template = self.prompt_config["prompt"]
        return prompt_template.format(url=url, task_description=task_description)

    def _parse_llm_response(self, response: str) -> dict[str, Any]:
        """
        Parse the LLM response into a dictionary suitable for Task creation.

        Args:
            response: The raw response from the LLM

        Returns:
            Dict[str, Any]: Parsed data ready for Task object creation

        Raises:
            InvalidResponseFormatError: If the response format is invalid
            ValidationError: If validation of parsed data fails
        """
        # Extract JSON from the response
        parse_start = time.time()
        data = extract_json_from_text(response)
        parse_time = time.time() - parse_start

        logger.debug(
            "JSON extraction completed",
            extra={"parse_time": parse_time, "found_json": data is not None},
        )

        if not data:
            error_msg = (
                f"No valid JSON object found in LLM response. "
                f"Expected a JSON object with task analysis, but received: "
                f"{response[:RESPONSE_PREVIEW_LENGTH]}{'...' if len(response) > RESPONSE_PREVIEW_LENGTH else ''}"
            )
            raise InvalidResponseFormatError(
                error_msg,
                response=response,
                expected_format="JSON object with fields: description, objectives, success_criteria",
            )

        # Validate required fields
        required_fields = ["description", "objectives", "success_criteria"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            error_msg = (
                f"Missing required fields: {', '.join(missing_fields)}. "
                f"Expected all of: {', '.join(required_fields)}. "
                f"Received fields: {', '.join(data.keys())}"
            )
            raise ValidationError(
                error_msg,
                field=missing_fields[0],  # Report the first missing field
                value=None,
                expected_type="Required field must be present",
            )

        # Set defaults for optional fields
        data.setdefault("constraints", [])
        data.setdefault("context", {})

        # Normalize optional fields (convert "null", [], etc. to None)
        normalize_optional_fields(data, ["data_to_extract", "actions_to_perform"])

        # Validate field types (after normalization)
        self._validate_field_types(data)

        # Ensure lists have required minimum items
        if not data.get("objectives") or len(data["objectives"]) == 0:
            msg = "Field 'objectives' must contain at least one item"
            raise ValidationError(
                msg,
                field="objectives",
                value=data.get("objectives"),
                expected_type="Non-empty list of strings",
            )

        if not data.get("success_criteria") or len(data["success_criteria"]) == 0:
            msg = "Field 'success_criteria' must contain at least one item"
            raise ValidationError(
                msg,
                field="success_criteria",
                value=data.get("success_criteria"),
                expected_type="Non-empty list of strings",
            )

        logger.debug(
            "Response parsing completed",
            extra={
                "objectives_count": len(data.get("objectives", [])),
                "success_criteria_count": len(data.get("success_criteria", [])),
                "has_data_to_extract": data.get("data_to_extract") is not None,
                "has_actions": data.get("actions_to_perform") is not None,
            },
        )

        return data

    def _validate_field_types(self, data: dict[str, Any]) -> None:
        """
        Validate that fields have the correct types.

        Args:
            data: The parsed data dictionary

        Raises:
            ValidationError: If any field has an incorrect type
        """
        # Validate string fields
        if not isinstance(data.get("description"), str):
            msg = "Field 'description' must be a string"
            raise ValidationError(
                msg,
                field="description",
                value=data.get("description"),
                expected_type="string",
            )

        # Validate list fields
        list_fields = ["objectives", "success_criteria", "constraints"]
        for field in list_fields:
            if field in data and not isinstance(data[field], list):
                msg = f"Field '{field}' must be a list"
                raise ValidationError(
                    msg,
                    field=field,
                    value=data[field],
                    expected_type="list of strings",
                )

            # Validate list items are strings
            if data.get(field):
                for i, item in enumerate(data[field]):
                    if not isinstance(item, str):
                        msg = f"Item {i} in field '{field}' must be a string"
                        raise ValidationError(
                            msg,
                            field=f"{field}[{i}]",
                            value=item,
                            expected_type="string",
                        )

        # Validate optional list fields
        optional_list_fields = ["data_to_extract", "actions_to_perform"]
        for field in optional_list_fields:
            if field in data and data[field] is not None and not isinstance(data[field], list):
                msg = f"Field '{field}' must be a list or null"
                raise ValidationError(
                    msg,
                    field=field,
                    value=data[field],
                    expected_type="list of strings or null",
                )

        # Validate context is a dictionary
        if "context" in data and not isinstance(data["context"], dict):
            msg = "Field 'context' must be a dictionary"
            raise ValidationError(
                msg,
                field="context",
                value=data["context"],
                expected_type="dictionary",
            )
