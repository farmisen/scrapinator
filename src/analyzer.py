"""Web Task Analyzer module for understanding natural language task descriptions."""

import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional, Protocol

from src.models.task import Task
from src.prompts.task_analysis import TASK_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

# Constants
RESPONSE_PREVIEW_LENGTH = 200


class LLMClient(Protocol):
    """Protocol for LLM client interface."""

    async def complete(self, prompt: str) -> str:
        """Complete a prompt and return the response."""
        ...


class WebTaskAnalyzer:
    """Analyzes natural language task descriptions and converts them to structured Task objects."""

    def __init__(self, llm_client: LLMClient, timeout: Optional[float] = 30.0) -> None:
        """
        Initialize the WebTaskAnalyzer with an LLM client.

        Args:
            llm_client: The LLM client instance to use for analysis
            timeout: Maximum time in seconds to wait for LLM response (default: 30.0)
        """
        self.llm = llm_client
        self.timeout = timeout

    async def analyze_task(self, task_description: str, url: str) -> Task:
        """
        Analyze a natural language task description and return a structured Task object.

        Args:
            task_description: Natural language description of the task to perform
            url: The URL where the task should be performed

        Returns:
            Task: A structured Task object containing objectives, success criteria, etc.

        Raises:
            ValueError: If the task cannot be parsed or is invalid
            Exception: If the LLM call fails
        """
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(task_description, url)
        logger.debug("Sending prompt to LLM: %s", prompt)

        try:
            # Call the LLM to analyze the task with timeout
            if self.timeout:
                response = await asyncio.wait_for(self.llm.complete(prompt), timeout=self.timeout)
            else:
                response = await self.llm.complete(prompt)

            logger.debug("Received LLM response: %s", response)

            # Parse the response into a Task object
            task_data = self._parse_llm_response(response)

            # Create and return the Task object
            return Task(**task_data)

        except asyncio.TimeoutError as e:
            logger.exception("LLM request timed out after %s seconds", self.timeout)
            error_msg = f"LLM request timed out after {self.timeout} seconds"
            raise TimeoutError(error_msg) from e
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse LLM response as JSON")
            error_msg = f"Could not parse LLM response: {e}"
            raise ValueError(error_msg) from e
        except Exception:
            logger.exception("Failed to analyze task")
            raise

    def _build_analysis_prompt(self, task_description: str, url: str) -> str:
        """
        Build the prompt for the LLM to analyze the task.

        Args:
            task_description: The task description from the user
            url: The target URL

        Returns:
            str: The formatted prompt for the LLM
        """
        return TASK_ANALYSIS_PROMPT.format(url=url, task_description=task_description)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a dictionary suitable for Task creation.

        Args:
            response: The raw response from the LLM

        Returns:
            Dict[str, Any]: Parsed data ready for Task object creation

        Raises:
            ValueError: If the response cannot be parsed or is missing required fields
        """
        # Try to extract JSON from the response
        # Sometimes LLMs add extra text before/after JSON
        response = response.strip()

        # Try multiple JSON extraction strategies
        json_data = None

        # Strategy 1: Try to parse the entire response as JSON
        try:
            json_data = json.loads(response)
            logger.debug("Successfully parsed entire response as JSON")
        except json.JSONDecodeError:
            pass

        # Strategy 2: Find JSON using regex pattern
        if not json_data:
            json_pattern = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
            matches = json_pattern.findall(response)

            for match in matches:
                try:
                    json_data = json.loads(match)
                    logger.debug("Successfully extracted JSON using regex")
                    break
                except json.JSONDecodeError:
                    continue

        # Strategy 3: Find JSON object boundaries (original method)
        if not json_data:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx != -1 and end_idx > 0:
                try:
                    json_str = response[start_idx:end_idx]
                    json_data = json.loads(json_str)
                    logger.debug("Successfully extracted JSON using bracket search")
                except json.JSONDecodeError:
                    pass

        if not json_data:
            error_msg = (
                f"No valid JSON object found in LLM response. "
                f"Expected a JSON object with task analysis, but received: "
                f"{response[:RESPONSE_PREVIEW_LENGTH]}{'...' if len(response) > RESPONSE_PREVIEW_LENGTH else ''}"
            )
            raise ValueError(error_msg)

        # Parse the JSON
        data = json_data

        # Validate required fields
        required_fields = ["description", "objectives", "success_criteria"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            error_msg = (
                f"Missing required fields: {', '.join(missing_fields)}. "
                f"Expected all of: {', '.join(required_fields)}. "
                f"Received fields: {', '.join(data.keys())}"
            )
            raise ValueError(error_msg)

        # Ensure lists have required minimum items
        if not data.get("objectives") or len(data["objectives"]) == 0:
            error_msg = (
                "Field 'objectives' must contain at least one item. "
                f"Received: {data.get('objectives', 'field not present')}"
            )
            raise ValueError(error_msg)

        if not data.get("success_criteria") or len(data["success_criteria"]) == 0:
            error_msg = (
                "Field 'success_criteria' must contain at least one item. "
                f"Received: {data.get('success_criteria', 'field not present')}"
            )
            raise ValueError(error_msg)

        # Set defaults for optional fields
        data.setdefault("constraints", [])
        data.setdefault("context", {})

        # Ensure None instead of null strings or other representations
        if data.get("data_to_extract") in [None, "null", "None", []]:
            data["data_to_extract"] = None

        if data.get("actions_to_perform") in [None, "null", "None", []]:
            data["actions_to_perform"] = None

        return data
