"""Prompt templates for task analysis."""

from typing import Any, Dict

from src.llm_provider import LLMProvider

# Base prompt template with few-shot examples
TASK_ANALYSIS_PROMPT = """You are an expert at analyzing web automation tasks. Given a URL and a natural language task description, extract structured information about what needs to be done.

Here are some examples of how to analyze tasks:

# Note: In the JSON examples below, double braces {{{{ }}}} are used to escape literal braces
# in Python format strings. The actual JSON should use single braces {{}}.

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

Example 4:
URL: https://account.example.com
Task: Download all invoices from the last 3 months after logging in with username "user@example.com"

Response:
{{
    "description": "Download all invoices from the last 3 months after logging in with username \"user@example.com\"",
    "objectives": [
        "Navigate to login page",
        "Log in with provided credentials",
        "Navigate to invoices section",
        "Filter invoices by date range (last 3 months)",
        "Download all filtered invoices"
    ],
    "success_criteria": [
        "Successfully logged in",
        "All invoices from the last 3 months are found",
        "All invoices are successfully downloaded",
        "Downloaded files are saved locally"
    ],
    "data_to_extract": [
        "Invoice numbers",
        "Invoice dates",
        "Invoice amounts",
        "Download URLs"
    ],
    "actions_to_perform": [
        "Fill username field",
        "Fill password field",
        "Click login button",
        "Navigate to invoices page",
        "Set date filter",
        "Click download for each invoice"
    ],
    "constraints": [
        "Only invoices from the last 3 months",
        "Must use provided username",
        "Must download all matching invoices",
        "Handle pagination if present"
    ],
    "context": {{
        "username": "user@example.com",
        "date_range": "last_3_months",
        "action_type": "bulk_download"
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


# Provider-specific prompt configurations
# Note: temperature and max_tokens are recommended settings for LLM client implementations
# The actual enforcement of these limits depends on the LLM client being used
PROVIDER_CONFIGS = {
    LLMProvider.ANTHROPIC.value: {
        "prompt": TASK_ANALYSIS_PROMPT,
        "system_message": "You are a web automation expert that analyzes tasks and returns structured JSON.",
        "temperature": 0.3,  # Recommended for consistent, focused responses
        "max_tokens": 1000,  # Recommended limit for response size
    },
    LLMProvider.OPENAI.value: {
        "prompt": TASK_ANALYSIS_PROMPT,
        "system_message": "You are a web automation expert. Always respond with valid JSON only.",
        "temperature": 0.3,  # Recommended for consistent, focused responses
        "max_tokens": 1000,  # Recommended limit for response size
    },
}


def get_prompt_config(provider: str = LLMProvider.ANTHROPIC.value) -> Dict[str, Any]:
    """
    Get prompt configuration for a specific LLM provider.

    Args:
        provider: The LLM provider name ('anthropic', 'openai')

    Returns:
        Dictionary with prompt configuration
    """
    return PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS[LLMProvider.ANTHROPIC.value])
