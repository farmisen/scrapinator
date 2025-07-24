"""Web Task Analyzer module for understanding natural language task descriptions."""

import asyncio
import json
import logging
import time
from typing import Any, Protocol

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

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                # Log retry attempt if not the first
                if attempt > 0:
                    logger.info(
                        "Retrying task analysis",
                        extra={"attempt": attempt + 1, "max_retries": self.max_retries},
                    )

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
                        "attempt": attempt + 1,
                    },
                )

                # Parse and validate the response
                task_data = self._parse_llm_response(response)

                # Create and validate the Task object
                task = Task(**task_data)

                logger.info(
                    "Task analysis completed successfully",
                    extra={"attempts": attempt + 1, "task_id": id(task)},
                )

                return task

            except TimeoutError as e:
                last_error = e
                logger.warning(
                    "LLM request timed out",
                    extra={"timeout": self.timeout, "attempt": attempt + 1},
                )

                if attempt < self.max_retries - 1:
                    await self._wait_before_retry(attempt)
                    continue

                raise LLMCommunicationError(
                    f"LLM request timed out after {self.timeout} seconds",
                    original_error=e,
                    retry_count=attempt + 1,
                ) from e

            except json.JSONDecodeError as e:
                # JSON decode errors are not retryable
                logger.exception(
                    "Failed to parse LLM response as JSON",
                    extra={"error": str(e), "response_preview": response[:200]},
                )
                raise InvalidResponseFormatError(
                    f"Could not parse LLM response as JSON: {e}",
                    response=response,
                    expected_format="Valid JSON object with task analysis",
                ) from e

            except (InvalidResponseFormatError, ValidationError):
                # These are our custom exceptions - don't retry, just re-raise
                raise

            except ValueError as e:
                # Check if it's a specific error we should handle differently
                error_msg = str(e).lower()

                if "rate limit" in error_msg or "too many requests" in error_msg:
                    last_error = e
                    logger.warning("Rate limit detected", extra={"attempt": attempt + 1})

                    if attempt < self.max_retries - 1:
                        # Use longer delay for rate limits
                        await self._wait_before_retry(attempt, multiplier=5.0)
                        continue

                    raise RateLimitError(
                        "Rate limit exceeded for LLM API",
                        retry_count=attempt + 1,
                    ) from e

                if "context length" in error_msg or "token limit" in error_msg:
                    # Context length errors are not retryable
                    raise ContextLengthExceededError(
                        "Prompt exceeds LLM context length limit",
                        prompt_length=prompt_length,
                    ) from e
                # Other ValueError types (validation errors) are not retryable
                raise

            except Exception as e:
                last_error = e
                logger.warning(
                    "Unexpected error during task analysis",
                    extra={"error": str(e), "attempt": attempt + 1, "error_type": type(e).__name__},
                )

                if attempt < self.max_retries - 1:
                    await self._wait_before_retry(attempt)
                    continue

                raise LLMCommunicationError(
                    f"Failed to analyze task after {attempt + 1} attempts",
                    original_error=e,
                    retry_count=attempt + 1,
                ) from e

        # This should not be reached, but just in case
        raise LLMCommunicationError(
            f"Failed to analyze task after {self.max_retries} attempts",
            original_error=last_error,
            retry_count=self.max_retries,
        )

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

    async def _wait_before_retry(self, attempt: int, multiplier: float = 1.0) -> None:
        """
        Wait before retrying with exponential backoff.

        Args:
            attempt: The current attempt number (0-based)
            multiplier: Multiplier for the delay (e.g., 5.0 for rate limits)
        """
        # Calculate delay with exponential backoff
        delay = min(self.retry_delay * (2**attempt) * multiplier, MAX_RETRY_DELAY)

        logger.info(
            "Waiting before retry",
            extra={"delay": delay, "attempt": attempt + 1},
        )

        await asyncio.sleep(delay)

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
            raise ValidationError(
                "Field 'objectives' must contain at least one item",
                field="objectives",
                value=data.get("objectives"),
                expected_type="Non-empty list of strings",
            )

        if not data.get("success_criteria") or len(data["success_criteria"]) == 0:
            raise ValidationError(
                "Field 'success_criteria' must contain at least one item",
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
            raise ValidationError(
                "Field 'description' must be a string",
                field="description",
                value=data.get("description"),
                expected_type="string",
            )

        # Validate list fields
        list_fields = ["objectives", "success_criteria", "constraints"]
        for field in list_fields:
            if field in data and not isinstance(data[field], list):
                raise ValidationError(
                    f"Field '{field}' must be a list",
                    field=field,
                    value=data[field],
                    expected_type="list of strings",
                )

            # Validate list items are strings
            if data.get(field):
                for i, item in enumerate(data[field]):
                    if not isinstance(item, str):
                        raise ValidationError(
                            f"Item {i} in field '{field}' must be a string",
                            field=f"{field}[{i}]",
                            value=item,
                            expected_type="string",
                        )

        # Validate optional list fields
        optional_list_fields = ["data_to_extract", "actions_to_perform"]
        for field in optional_list_fields:
            if field in data and data[field] is not None and not isinstance(data[field], list):
                    raise ValidationError(
                        f"Field '{field}' must be a list or null",
                        field=field,
                        value=data[field],
                        expected_type="list of strings or null",
                    )

        # Validate context is a dictionary
        if "context" in data and not isinstance(data["context"], dict):
            raise ValidationError(
                "Field 'context' must be a dictionary",
                field="context",
                value=data["context"],
                expected_type="dictionary",
            )
