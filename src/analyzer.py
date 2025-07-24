"""Web Task Analyzer module for understanding natural language task descriptions."""

import json
import logging
from typing import Any, Dict, Protocol

from src.models.task import Task

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM client interface."""

    async def complete(self, prompt: str) -> str:
        """Complete a prompt and return the response."""
        ...


class WebTaskAnalyzer:
    """Analyzes natural language task descriptions and converts them to structured Task objects."""

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Initialize the WebTaskAnalyzer with an LLM client.

        Args:
            llm_client: The LLM client instance to use for analysis
        """
        self.llm = llm_client

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

        try:
            # Call the LLM to analyze the task
            response = await self.llm.complete(prompt)

            # Parse the response into a Task object
            task_data = self._parse_llm_response(response)

            # Create and return the Task object
            return Task(**task_data)

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
        return f"""Analyze this web automation task and extract structured information.

URL: {url}
Task: {task_description}

Please analyze this task and provide a JSON response with the following structure:
{{
    "description": "The original task description",
    "objectives": ["List of main objectives to accomplish"],
    "success_criteria": ["List of criteria that determine success"],
    "data_to_extract": ["Optional list of data to extract"] or null,
    "actions_to_perform": ["Optional list of actions like click, fill, submit"] or null,
    "constraints": ["List of constraints or limitations"],
    "context": {{"any": "additional context as key-value pairs"}}
}}

Important:
- objectives and success_criteria must have at least one item each
- data_to_extract and actions_to_perform can be null if not applicable
- constraints can be an empty list if there are none
- context should be an empty object {{}} if no additional context is needed

Return only the JSON object, no additional text."""

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

        # Find JSON object boundaries
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1

        if start_idx == -1 or end_idx == 0:
            error_msg = "No JSON object found in LLM response"
            raise ValueError(error_msg)

        json_str = response[start_idx:end_idx]

        # Parse the JSON
        data = json.loads(json_str)

        # Validate required fields
        required_fields = ["description", "objectives", "success_criteria"]
        for field in required_fields:
            if field not in data:
                error_msg = f"Missing required field: {field}"
                raise ValueError(error_msg)

        # Ensure lists have required minimum items
        if not data.get("objectives") or len(data["objectives"]) == 0:
            error_msg = "objectives must contain at least one item"
            raise ValueError(error_msg)

        if not data.get("success_criteria") or len(data["success_criteria"]) == 0:
            error_msg = "success_criteria must contain at least one item"
            raise ValueError(error_msg)

        # Set defaults for optional fields
        data.setdefault("constraints", [])
        data.setdefault("context", {})

        return data
