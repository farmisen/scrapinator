"""Simple LLM client wrappers for demonstration purposes."""

import json
import time
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standard response format for LLM calls."""

    content: str
    model: str
    tokens_used: int
    response_time: float
    cost: float


class MockLLMClient:
    """Mock LLM client for testing without API calls."""

    def __init__(self, model: str = "mock-model"):
        self.model = model
        self.call_count = 0

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Simulate LLM completion."""
        self.call_count += 1
        start_time = time.time()

        # Simulate processing time
        await self._simulate_delay()

        # Generate mock response based on prompt content
        if "extract" in prompt.lower():
            content = json.dumps(
                {
                    "elements": [
                        {
                            "type": "button",
                            "text": "Add to Cart",
                            "selector": "button[type='submit']",
                        },
                        {"type": "input", "purpose": "quantity", "selector": "#quantity"},
                        {"type": "link", "text": "Products", "selector": "a[href='/products']"},
                    ]
                }
            )
        elif "analyze" in prompt.lower():
            content = json.dumps(
                {
                    "page_type": "product_detail",
                    "main_elements": ["navigation", "product_info", "add_to_cart_form"],
                    "interactive_elements": 5,
                }
            )
        else:
            content = "Mock response for: " + prompt[:100]

        response_time = time.time() - start_time
        tokens = len(prompt.split()) + len(content.split())

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=tokens,
            response_time=response_time,
            cost=self._calculate_cost(tokens),
        )

    async def _simulate_delay(self):
        """Simulate API latency."""
        import asyncio

        await asyncio.sleep(0.1)  # 100ms simulated latency

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate mock cost based on tokens."""
        # Mock pricing: $0.01 per 1K tokens
        return (tokens / 1000) * 0.01


class LLMClientFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def create(provider: str, api_key: str | None = None) -> MockLLMClient:
        """Create an LLM client for the given provider."""
        # For demonstration, always return mock client
        # In production, this would return real clients based on provider
        if provider == "openai":
            return MockLLMClient(model="gpt-4-turbo")
        if provider == "anthropic":
            return MockLLMClient(model="claude-3-sonnet")
        return MockLLMClient(model="mock-model")


# Model pricing information (per million tokens)
MODEL_PRICING = {
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a given model and token counts."""
    if model not in MODEL_PRICING:
        return 0.0

    pricing = MODEL_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def compare_model_costs(input_tokens: int, output_tokens: int) -> dict[str, float]:
    """Compare costs across different models."""
    costs = {}
    for model in MODEL_PRICING:
        costs[model] = estimate_cost(model, input_tokens, output_tokens)
    return dict(sorted(costs.items(), key=lambda x: x[1]))


# Example prompts for testing
EXAMPLE_PROMPTS = {
    "element_extraction": """Analyze this HTML and extract all interactive elements:

{html}

Return a JSON list of elements with their type, purpose, and CSS selector.""",
    "page_classification": """Classify this webpage into one of these categories:
- product_detail
- product_listing  
- form
- article
- navigation

HTML:
{html}

Return the category and confidence score.""",
    "form_analysis": """Analyze this form and identify the purpose of each field:

{html}

Return a JSON object mapping field names to their purposes.""",
}
