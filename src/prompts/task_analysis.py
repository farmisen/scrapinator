"""Prompt templates for task analysis."""

from typing import Any, Dict

# Base prompt template with few-shot examples
TASK_ANALYSIS_PROMPT = """You are an expert at analyzing web automation tasks. Given a URL and a natural language task description, extract structured information about what needs to be done.

Here are some examples of how to analyze tasks:

Example 1:
URL: https://shop.example.com
Task: Find all products under $50 and extract their names and prices

Response:
{{
    "description": "Find all products under $50 and extract their names and prices",
    "objectives": [
        "Navigate to products listing",
        "Filter or identify products under $50",
        "Extract product names and prices"
    ],
    "success_criteria": [
        "All products under $50 are found",
        "Product names are correctly extracted",
        "Product prices are correctly extracted"
    ],
    "data_to_extract": [
        "Product names",
        "Product prices"
    ],
    "actions_to_perform": null,
    "constraints": [
        "Only products under $50",
        "Must extract both name and price for each product"
    ],
    "context": {{
        "price_limit": 50,
        "currency": "USD"
    }}
}}

Example 2:
URL: https://forms.example.com/survey
Task: Fill out the customer satisfaction survey with positive feedback

Response:
{{
    "description": "Fill out the customer satisfaction survey with positive feedback",
    "objectives": [
        "Navigate to the survey form",
        "Fill all required fields with positive responses",
        "Submit the completed survey"
    ],
    "success_criteria": [
        "All required fields are completed",
        "Survey is successfully submitted",
        "Confirmation of submission is received"
    ],
    "data_to_extract": null,
    "actions_to_perform": [
        "Fill text fields",
        "Select positive ratings",
        "Click submit button"
    ],
    "constraints": [
        "Provide positive feedback only",
        "Complete all required fields"
    ],
    "context": {{
        "feedback_type": "positive",
        "form_type": "survey"
    }}
}}

Example 3:
URL: https://news.example.com
Task: Get today's headlines

Response:
{{
    "description": "Get today's headlines",
    "objectives": [
        "Navigate to the main news page",
        "Identify today's headlines",
        "Extract headline text"
    ],
    "success_criteria": [
        "Current date headlines are found",
        "All main headlines are extracted"
    ],
    "data_to_extract": [
        "Headline text",
        "Publication date"
    ],
    "actions_to_perform": null,
    "constraints": [
        "Only headlines from current date",
        "Main headlines only, not sidebar content"
    ],
    "context": {{
        "content_type": "news",
        "date_filter": "today"
    }}
}}

Now analyze this task:

URL: {url}
Task: {task_description}

Important guidelines:
- If the task is vague, infer reasonable objectives based on common patterns
- Always include at least one objective and one success criterion
- Set data_to_extract to null if the task doesn't involve extracting data
- Set actions_to_perform to null if the task is only about data extraction
- Include relevant constraints even if not explicitly mentioned
- Add useful context that helps clarify the task
- For ambiguous tasks, choose the most likely interpretation

Return only the JSON response, no additional text or explanation."""

# Optimized prompt for models with smaller context windows
TASK_ANALYSIS_PROMPT_COMPACT = """Analyze this web automation task and return a JSON response.

URL: {url}
Task: {task_description}

Required JSON structure:
{{
    "description": "original task",
    "objectives": ["list of steps to accomplish"],
    "success_criteria": ["how to know when done"],
    "data_to_extract": ["data to collect"] or null,
    "actions_to_perform": ["user actions needed"] or null,
    "constraints": ["limitations or requirements"],
    "context": {{"additional": "key-value pairs"}}
}}

Rules:
- objectives and success_criteria need at least 1 item
- data_to_extract: null if no data collection
- actions_to_perform: null if only extracting data
- constraints: can be empty list
- context: can be empty object

Return only JSON, no text."""

# Provider-specific prompt configurations
PROVIDER_CONFIGS = {
    "anthropic": {
        "prompt": TASK_ANALYSIS_PROMPT,
        "system_message": "You are a web automation expert that analyzes tasks and returns structured JSON.",
        "temperature": 0.3,
        "max_tokens": 1000,
    },
    "openai": {
        "prompt": TASK_ANALYSIS_PROMPT,
        "system_message": "You are a web automation expert. Always respond with valid JSON only.",
        "temperature": 0.3,
        "max_tokens": 1000,
    },
    "compact": {
        "prompt": TASK_ANALYSIS_PROMPT_COMPACT,
        "system_message": "Analyze web tasks. Return only JSON.",
        "temperature": 0.3,
        "max_tokens": 500,
    },
}


def get_prompt_config(provider: str = "anthropic") -> Dict[str, Any]:
    """
    Get prompt configuration for a specific LLM provider.

    Args:
        provider: The LLM provider name ('anthropic', 'openai', 'compact')

    Returns:
        Dictionary with prompt configuration
    """
    return PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["anthropic"])
