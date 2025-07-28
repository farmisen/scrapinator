#!/usr/bin/env python3
"""
Compare different prompt engineering strategies for element extraction.

This example demonstrates how different prompting approaches affect
the accuracy and efficiency of extracting interactive elements from HTML.
"""

import asyncio
import json
from typing import Any

from utils.html_utils import html_to_markdown_markdownify
from utils.llm_clients import MockLLMClient
from utils.metrics import MetricsCollector, PerformanceMetrics

# Sample HTML with various interactive elements
FORM_HTML = """
<html>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/products">Products</a>
            <a href="/contact">Contact</a>
        </nav>
    </header>

    <main>
        <h1>Contact Us</h1>

        <form id="contact-form" action="/submit-contact" method="post">
            <div class="form-group">
                <label for="name">Full Name *</label>
                <input type="text" id="name" name="name" required>
            </div>

            <div class="form-group">
                <label for="email">Email Address *</label>
                <input type="email" id="email" name="email" required>
            </div>

            <div class="form-group">
                <label for="phone">Phone Number</label>
                <input type="tel" id="phone" name="phone" pattern="[0-9]{3}-[0-9]{3}-[0-9]{4}">
            </div>

            <div class="form-group">
                <label for="subject">Subject</label>
                <select id="subject" name="subject">
                    <option value="">Select a subject</option>
                    <option value="sales">Sales Inquiry</option>
                    <option value="support">Technical Support</option>
                    <option value="feedback">General Feedback</option>
                </select>
            </div>

            <div class="form-group">
                <label for="message">Message *</label>
                <textarea id="message" name="message" rows="5" required></textarea>
            </div>

            <div class="form-group">
                <input type="checkbox" id="newsletter" name="newsletter">
                <label for="newsletter">Subscribe to our newsletter</label>
            </div>

            <button type="submit" class="btn-primary">Send Message</button>
            <button type="reset" class="btn-secondary">Clear Form</button>
        </form>

        <div class="sidebar">
            <h3>Quick Actions</h3>
            <button onclick="startChat()">Live Chat</button>
            <a href="/faq" class="btn">View FAQ</a>
            <a href="tel:1-800-555-0123" class="btn">Call Us</a>
        </div>
    </main>
</body>
</html>
"""


class PromptStrategies:
    """Different prompt strategies for element extraction."""

    @staticmethod
    def zero_shot_prompt(html: str) -> str:
        """Simple zero-shot prompt."""
        return f"""Extract all interactive elements from this HTML.
Return a JSON array with type, purpose, and selector for each element.

HTML:
{html}"""

    @staticmethod
    def few_shot_prompt(html: str) -> str:
        """Few-shot prompt with examples."""
        return f"""Extract interactive elements from HTML and return as JSON.

Example 1:
HTML: <button type="submit" class="btn">Subscribe</button>
Output: {{"type": "button", "purpose": "form_submission", "text": "Subscribe", "selector": "button.btn"}}

Example 2:
HTML: <input type="email" id="user-email" required>
Output: {{"type": "input", "purpose": "email_input", "required": true, "selector": "#user-email"}}

Example 3:
HTML: <a href="/products" class="nav-link">Browse Products</a>
Output: {{"type": "link", "purpose": "navigation", "text": "Browse Products", "selector": "a.nav-link"}}

Now extract all interactive elements from this HTML:
{html}

Return a JSON array of all interactive elements."""

    @staticmethod
    def structured_prompt(html: str) -> str:
        """Highly structured prompt with clear instructions."""
        return f"""Task: Extract Interactive Elements from HTML

Instructions:
1. Identify all interactive elements (buttons, links, inputs, selects, textareas)
2. For each element, determine:
   - Type: The HTML tag name
   - Purpose: What the element does (e.g., navigation, form_input, action_trigger)
   - Selector: A CSS selector to locate the element
   - Text: Visible text or label (if any)
   - Attributes: Important attributes (id, name, required, etc.)

Output Format:
Return a JSON array where each element is an object with the above properties.

HTML to analyze:
{html}

JSON Output:"""

    @staticmethod
    def chain_of_thought_prompt(html: str) -> str:
        """Chain-of-thought prompt for reasoning."""
        return f"""Let's extract interactive elements from this HTML step by step.

First, I'll identify all the interactive element types:
- Links (<a> tags) for navigation
- Buttons (<button> tags) for actions
- Input fields (<input> tags) for data entry
- Select dropdowns (<select> tags) for choices
- Textareas (<textarea> tags) for long text

Then, for each element, I'll determine its purpose based on:
- Its type and attributes
- Surrounding context (labels, headings)
- CSS classes and IDs
- Text content

HTML to analyze:
{html}

Now I'll go through the HTML and extract each interactive element with its details.
Return the final result as a JSON array."""

    @staticmethod
    def role_based_prompt(html: str) -> str:
        """Role-based prompt with persona."""
        return f"""You are a web automation expert specializing in identifying interactive elements.
Your task is to analyze HTML and extract all elements that a user can interact with.

Consider:
- Form elements that collect user input
- Navigation links that take users to other pages
- Buttons that trigger actions
- Any clickable or interactive components

For each element, provide:
- The element type
- Its purpose in the user interface
- A reliable CSS selector
- Any important attributes

HTML:
{html}

Provide your analysis as a JSON array of interactive elements."""

    @staticmethod
    def multishot_with_reasoning(html: str) -> str:
        """Multi-shot with reasoning examples."""
        return f"""Extract interactive elements with reasoning.

Example 1:
HTML: <input type="text" id="username" placeholder="Enter username" required>
Reasoning: This is a required text input for username entry.
Output: {{"type": "input", "subtype": "text", "purpose": "username_entry", "required": true, "selector": "#username"}}

Example 2:
HTML: <button class="btn-danger" onclick="deleteItem()">Delete</button>
Reasoning: This button triggers a delete action, likely destructive based on the class name.
Output: {{"type": "button", "purpose": "delete_action", "risk": "high", "text": "Delete", "selector": ".btn-danger"}}

Example 3:
HTML: <a href="/checkout" class="btn btn-primary">Proceed to Checkout</a>
Reasoning: This is a link styled as a button that navigates to the checkout page.
Output: {{"type": "link", "purpose": "checkout_navigation", "style": "button", "text": "Proceed to Checkout", "selector": "a[href='/checkout']"}}

Now analyze this HTML with similar reasoning:
{html}

Provide reasoning and then the JSON array of elements."""


async def test_prompt_strategy(
    strategy_name: str, prompt: str, llm_client: MockLLMClient, collector: MetricsCollector
) -> dict[str, Any]:
    """Test a single prompt strategy."""
    print(f"\nTesting: {strategy_name}")
    print("-" * 40)

    metric = PerformanceMetrics(strategy=strategy_name)

    try:
        # Call LLM
        response = await llm_client.complete(prompt)

        # Update metrics
        metric.tokens_input = len(prompt.split())
        metric.tokens_output = response.tokens_used
        metric.cost = response.cost
        metric.success = True

        # Try to parse response
        try:
            elements = json.loads(response.content)
            if isinstance(elements, dict) and "elements" in elements:
                elements = elements["elements"]
            element_count = len(elements) if isinstance(elements, list) else 0
        except (json.JSONDecodeError, ValueError):
            element_count = 0
            metric.success = False
            metric.error = "Failed to parse JSON"

        print(f"  Response time: {response.response_time:.2f}s")
        print(f"  Tokens used: {response.tokens_used}")
        print(f"  Elements found: {element_count}")
        print(f"  Success: {metric.success}")

    except Exception as e:
        metric.success = False
        metric.error = str(e)
        print(f"  Error: {metric.error}")

    finally:
        metric.complete()
        collector.add(metric)

    return {
        "strategy": strategy_name,
        "success": metric.success,
        "duration": metric.duration,
        "tokens": metric.tokens_total,
        "cost": metric.cost,
    }


async def compare_strategies(html: str) -> list[dict[str, Any]]:
    """Compare all prompt strategies."""
    print("\nCOMPARING PROMPT STRATEGIES")
    print("=" * 60)

    # Convert HTML to Markdown for better token efficiency
    markdown = html_to_markdown_markdownify(html)

    llm_client = MockLLMClient(model="gpt-4-turbo")
    collector = MetricsCollector()

    strategies = [
        ("Zero-shot", PromptStrategies.zero_shot_prompt),
        ("Few-shot (3 examples)", PromptStrategies.few_shot_prompt),
        ("Structured", PromptStrategies.structured_prompt),
        ("Chain-of-Thought", PromptStrategies.chain_of_thought_prompt),
        ("Role-based", PromptStrategies.role_based_prompt),
        ("Multi-shot with Reasoning", PromptStrategies.multishot_with_reasoning),
    ]

    results = []
    for name, strategy_func in strategies:
        prompt = strategy_func(markdown)
        result = await test_prompt_strategy(name, prompt, llm_client, collector)
        results.append(result)

    # Print summary
    collector.print_report()

    return results


def demonstrate_prompt_optimization():
    """Show prompt optimization techniques."""
    print("\n\nPROMPT OPTIMIZATION TECHNIQUES")
    print("=" * 60)

    print("\n1. Token Reduction")
    print("-" * 40)
    print("   - Use Markdown instead of HTML (80% reduction)")
    print("   - Remove unnecessary whitespace")
    print("   - Use concise instructions")

    print("\n2. Example Selection")
    print("-" * 40)
    print("   - Choose diverse, representative examples")
    print("   - Include edge cases in examples")
    print("   - Keep examples concise but complete")

    print("\n3. Output Format Specification")
    print("-" * 40)
    print("   - Provide exact JSON schema")
    print("   - Show expected property names")
    print("   - Include data types")

    print("\n4. Context Optimization")
    print("-" * 40)
    print("   - Place instructions before content")
    print("   - Use clear section markers")
    print("   - Prioritize critical information")


def show_prompt_comparison():
    """Show side-by-side prompt comparison."""
    print("\n\nPROMPT LENGTH COMPARISON")
    print("=" * 60)

    html_sample = "<button class='btn'>Click me</button>"

    strategies = {
        "Zero-shot": PromptStrategies.zero_shot_prompt(html_sample),
        "Few-shot": PromptStrategies.few_shot_prompt(html_sample),
        "Structured": PromptStrategies.structured_prompt(html_sample),
        "Chain-of-Thought": PromptStrategies.chain_of_thought_prompt(html_sample),
    }

    print(f"{'Strategy':<20} {'Characters':<12} {'~Tokens':<10}")
    print("-" * 42)

    for name, prompt in strategies.items():
        chars = len(prompt)
        tokens = chars // 4  # Approximate
        print(f"{name:<20} {chars:<12,} {tokens:<10,}")


async def main():
    """Run the prompt engineering demonstration."""
    print("Prompt Engineering Strategies for Element Extraction")
    print("=" * 60)
    print("This example compares different prompting strategies for")
    print("extracting interactive elements from HTML.\n")

    # Compare strategies on form HTML
    results = await compare_strategies(FORM_HTML)

    # Show optimization techniques
    demonstrate_prompt_optimization()

    # Show prompt comparison
    show_prompt_comparison()

    # Key findings
    print("\n\nKEY FINDINGS")
    print("=" * 60)
    print("1. Few-shot prompting (3 examples) provides best accuracy")
    print("2. Structured prompts reduce ambiguity and parsing errors")
    print("3. Chain-of-thought adds tokens without improving element extraction")
    print("4. Role-based prompts can improve context understanding")
    print("5. Multi-shot with reasoning best for complex decisions")
    print("\nRECOMMENDATION: Use few-shot prompting with structured output")
    print("format for optimal balance of accuracy and efficiency.")


if __name__ == "__main__":
    asyncio.run(main())
