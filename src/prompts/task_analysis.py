"""Prompt templates for task analysis."""

TASK_ANALYSIS_PROMPT = """Analyze this web automation task and extract structured information.

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
