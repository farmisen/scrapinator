#!/usr/bin/env python3
"""
WebTaskAnalyzer Integration Example

This example demonstrates how to use the WebTaskAnalyzer with real LLM integration.
It shows multiple task scenarios, error handling, and configuration for different providers.

Requirements:
    - Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variables
    - Python 3.12+
    - All project dependencies installed (run: make install)

Usage:
    python examples/task_analyzer_demo.py
    python examples/task_analyzer_demo.py --provider openai
    python examples/task_analyzer_demo.py --provider anthropic --model claude-3-haiku-20240307
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyzer import WebTaskAnalyzer
from src.exceptions import (
    ContextLengthExceededError,
    InvalidResponseFormatError,
    LLMCommunicationError,
    RateLimitError,
    ValidationError,
)
from src.llm_client import LangChainLLMClient
from src.models.task import Task

# Example task descriptions for different scenarios
EXAMPLE_TASKS = {
    "simple_extraction": {
        "url": "https://news.ycombinator.com",
        "description": "Extract the titles and scores of the top 5 stories on Hacker News",
        "category": "Simple Data Extraction",
    },
    "multi_step_navigation": {
        "url": "https://github.com/trending",
        "description": (
            "Navigate to the trending repositories page, filter by Python language, "
            "and extract repository names, star counts, and descriptions of the top 10 projects"
        ),
        "category": "Multi-Step Navigation",
    },
    "form_filling": {
        "url": "https://example.com/contact",
        "description": (
            "Fill out the contact form with the following details: "
            "Name: 'John Doe', Email: 'john@example.com', Subject: 'Product Inquiry', "
            "Message: 'I would like more information about your services', then submit the form"
        ),
        "category": "Form Filling",
    },
    "file_download": {
        "url": "https://example-reports.com/quarterly",
        "description": (
            "Find the Q4 2023 financial report PDF, download it, "
            "and save it with the filename 'Q4_2023_Financial_Report.pdf'"
        ),
        "category": "File Download",
    },
    "complex_with_constraints": {
        "url": "https://example-shop.com",
        "description": (
            "Search for laptops under $1000, filter by at least 16GB RAM and 512GB SSD, "
            "sort by customer rating, extract the top 5 results including product name, "
            "price, specs, and rating. Do not include refurbished items."
        ),
        "category": "Complex Task with Constraints",
    },
}


def print_separator(char: str = "-", length: int = 80) -> None:
    """Print a separator line."""
    print(char * length)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print_separator("=")
    print(f"{text:^80}")
    print_separator("=")


def print_task_info(task_info: dict[str, str]) -> None:
    """Print task information."""
    print(f"\n📋 Task: {task_info['category']}")
    print(f"🌐 URL: {task_info['url']}")
    print(f"📝 Description: {task_info['description']}")
    print_separator()


def print_task_result(task: Task, elapsed_time: float) -> None:
    """Pretty print the task analysis result."""
    print(f"\n✅ Analysis completed in {elapsed_time:.2f} seconds")
    print("\n📊 Task Analysis Result:")
    print_separator()

    # Print basic info
    print(f"📄 Description: {task.description}")

    # Print objectives
    print(f"\n🎯 Objectives ({len(task.objectives)}):")
    for i, objective in enumerate(task.objectives, 1):
        print(f"   {i}. {objective}")

    # Print success criteria
    print(f"\n✔️  Success Criteria ({len(task.success_criteria)}):")
    for i, criterion in enumerate(task.success_criteria, 1):
        print(f"   {i}. {criterion}")

    # Print constraints if any
    if task.constraints:
        print(f"\n⚠️  Constraints ({len(task.constraints)}):")
        for i, constraint in enumerate(task.constraints, 1):
            print(f"   {i}. {constraint}")

    # Print data to extract if any
    if task.data_to_extract:
        print(f"\n📊 Data to Extract ({len(task.data_to_extract)}):")
        for i, data in enumerate(task.data_to_extract, 1):
            print(f"   {i}. {data}")

    # Print actions to perform if any
    if task.actions_to_perform:
        print(f"\n🔧 Actions to Perform ({len(task.actions_to_perform)}):")
        for i, action in enumerate(task.actions_to_perform, 1):
            print(f"   {i}. {action}")

    # Print task complexity
    print(f"\n📈 Task Complexity: {'Complex' if task.is_complex() else 'Simple'}")
    print(f"💾 Has Data Extraction: {'Yes' if task.has_data_extraction() else 'No'}")
    print(f"⚡ Has Actions: {'Yes' if task.has_actions() else 'No'}")


def print_error(error: Exception) -> None:
    """Print error information."""
    print(f"\n❌ Error: {type(error).__name__}")
    print(f"   Message: {error!s}")

    # Print additional context for specific errors
    if isinstance(error, InvalidResponseFormatError):
        print(f"   Expected Format: {error.expected_format}")
        if error.response:
            print(f"   Response Preview: {error.response[:100]}...")
    elif isinstance(error, ValidationError):
        print(f"   Field: {error.field}")
        print(f"   Expected Type: {error.expected_type}")
    elif isinstance(error, ContextLengthExceededError):
        print(f"   Prompt Length: {error.prompt_length}")
    elif isinstance(error, RateLimitError | LLMCommunicationError):
        if error.retry_count:
            print(f"   Retry Count: {error.retry_count}")


async def analyze_single_task(
    analyzer: WebTaskAnalyzer, task_name: str, task_info: dict[str, str]  # noqa: ARG001
) -> None:
    """Analyze a single task and print results."""
    print_task_info(task_info)

    try:
        # Measure execution time
        start_time = time.time()

        # Analyze the task
        task = await analyzer.analyze_task(
            task_description=task_info["description"],
            url=task_info["url"],
        )

        elapsed_time = time.time() - start_time

        # Print results
        print_task_result(task, elapsed_time)

    except (
        InvalidResponseFormatError,
        ValidationError,
        LLMCommunicationError,
        RateLimitError,
        ContextLengthExceededError,
    ) as e:
        print_error(e)
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e!s}")


async def demonstrate_error_handling(analyzer: WebTaskAnalyzer) -> None:
    """Demonstrate error handling scenarios."""
    print_header("Error Handling Demonstration")

    # Test 1: Invalid task description (should trigger validation error)
    print("\n🧪 Test 1: Empty task description")
    print_separator()
    try:
        await analyzer.analyze_task(
            task_description="",  # Empty description should fail
            url="https://example.com",
        )
    except Exception as e:
        print_error(e)

    # Test 2: Very long task description (might trigger context length error)
    print("\n\n🧪 Test 2: Extremely long task description")
    print_separator()
    try:
        # Create a very long task description
        long_description = (
            "Extract all product information including " + "very detailed specifications, " * 500
        )
        await analyzer.analyze_task(
            task_description=long_description,
            url="https://example.com",
        )
    except Exception as e:
        print_error(e)


async def main() -> None:
    """Main demonstration function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="WebTaskAnalyzer Integration Example")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider to use (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model to use (e.g., claude-3-haiku-20240307, gpt-4)",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        choices=[*list(EXAMPLE_TASKS.keys()), "all"],
        default=["all"],
        help="Specific tasks to run (default: all)",
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Skip error handling demonstration",
    )

    args = parser.parse_args()

    # Print header
    print_header("WebTaskAnalyzer Integration Example")
    print(f"\n📅 Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🤖 Provider: {args.provider}")
    print(f"🧠 Model: {args.model or 'Default for provider'}")

    # Check for API keys
    if args.provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("   Please set it with: export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)
    elif args.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set it with: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        # Initialize LLM client
        print("\n🔧 Initializing LLM client...")
        llm_client = LangChainLLMClient(
            provider=args.provider,
            model_name=args.model,
            temperature=0.3,
            max_tokens=1000,
        )

        # Initialize analyzer
        analyzer = WebTaskAnalyzer(
            llm_client=llm_client,
            timeout=30.0,
            provider=args.provider,
            max_retries=3,
            retry_delay=1.0,
        )

        print("✅ Initialization complete")

        # Determine which tasks to run
        tasks_to_run = list(EXAMPLE_TASKS.keys()) if "all" in args.tasks else args.tasks

        # Run example tasks
        print_header("Task Analysis Examples")

        for task_name in tasks_to_run:
            if task_name in EXAMPLE_TASKS:
                await analyze_single_task(analyzer, task_name, EXAMPLE_TASKS[task_name])
                print("\n" + "=" * 80 + "\n")

        # Demonstrate error handling
        if not args.skip_errors:
            await demonstrate_error_handling(analyzer)

        print_header("Demo Complete!")
        print("\n✨ All demonstrations completed successfully!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {type(e).__name__}: {e!s}")
        raise


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
