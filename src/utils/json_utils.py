"""JSON utility functions for robust JSON extraction and parsing."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> dict[str, Any] | None:
    """
    Extract JSON object from text that may contain additional content.

    Tries multiple strategies to find and parse JSON:
    1. Direct parsing if the entire text is valid JSON
    2. Regex pattern matching to find JSON objects
    3. Simple bracket matching for JSON objects

    Args:
        text: Text that may contain a JSON object

    Returns:
        Parsed JSON as a dictionary, or None if no valid JSON found

    Examples:
        >>> extract_json_from_text('{"key": "value"}')
        {'key': 'value'}

        >>> extract_json_from_text('Some text before {"key": "value"} and after')
        {'key': 'value'}

        >>> extract_json_from_text('No JSON here')
        None
    """
    if not text:
        return None

    text = text.strip()

    # Strategy 1: Try to parse the entire text as JSON
    try:
        json_data = json.loads(text)
        if isinstance(json_data, dict):
            logger.debug("Successfully parsed entire text as JSON")
            return json_data
    except json.JSONDecodeError:
        pass

    # Strategy 2: Find JSON using regex pattern
    # This pattern matches balanced braces
    json_pattern = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
    matches = json_pattern.findall(text)

    for match in matches:
        try:
            json_data = json.loads(match)
            if isinstance(json_data, dict):
                logger.debug("Successfully extracted JSON using regex")
                return json_data
        except json.JSONDecodeError:
            continue

    # Strategy 3: Find JSON object boundaries
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1

    if start_idx != -1 and end_idx > 0 and start_idx < end_idx:
        try:
            json_str = text[start_idx:end_idx]
            json_data = json.loads(json_str)
            if isinstance(json_data, dict):
                logger.debug("Successfully extracted JSON using bracket search")
                return json_data
        except json.JSONDecodeError:
            pass

    logger.debug("No valid JSON object found in text")
    return None


def normalize_optional_fields(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """
    Normalize optional fields that might be represented as null strings or empty lists.

    Converts various null representations to Python None:
    - None (already None)
    - "null" (string)
    - "None" (string)
    - [] (empty list)

    Args:
        data: Dictionary to normalize
        fields: List of field names to check and normalize

    Returns:
        The same dictionary with normalized fields

    Examples:
        >>> data = {"field1": "null", "field2": [], "field3": "value"}
        >>> normalize_optional_fields(data, ["field1", "field2"])
        {'field1': None, 'field2': None, 'field3': 'value'}
    """
    for field in fields:
        if field in data and data[field] in [None, "null", "None", []]:
            data[field] = None

    return data
