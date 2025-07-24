"""End-to-end integration tests for WebTaskAnalyzer with real LLM providers."""

import os
import time
from typing import Any

import pytest

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

from .fixtures.task_descriptions import (
    COMPLEX_TASKS,
    EDGE_CASES,
    PERFORMANCE_TASKS,
    SIMPLE_TASKS,
    get_tasks_by_category,
)

# Skip all tests in this module if no API keys are available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.external,
]


class TestTaskAnalyzerE2E:
    """End-to-end tests for WebTaskAnalyzer with real LLM APIs."""

    @pytest.fixture
    def vcr_config(self):
        """Configure VCR to filter sensitive data."""
        return {
            "filter_headers": ["authorization", "x-api-key"],
            "filter_query_parameters": ["api_key"],
            "filter_post_data_parameters": ["api_key"],
            "record_mode": "once",  # Record if cassette doesn't exist
            "match_on": ["method", "scheme", "host", "port", "path", "query"],
        }

    @pytest.fixture
    def anthropic_client(self):
        """Create Anthropic LLM client if API key is available."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")
        return LangChainLLMClient(provider="anthropic", api_key=api_key)

    @pytest.fixture
    def openai_client(self):
        """Create OpenAI LLM client if API key is available."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        return LangChainLLMClient(provider="openai", api_key=api_key)

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_simple_task_anthropic(self, anthropic_client):
        """Test simple task analysis with Anthropic API."""
        analyzer = WebTaskAnalyzer(anthropic_client, provider="anthropic")
        task_info = SIMPLE_TASKS[0]

        start_time = time.time()
        task = await analyzer.analyze_task(task_info["description"], task_info["url"])
        response_time = time.time() - start_time

        # Validate response
        assert isinstance(task, Task)
        assert task.description == task_info["description"]
        assert len(task.objectives) >= task_info["expected_objectives_count"]
        assert task.has_actions() == task_info["expected_has_actions"]
        assert task.has_data_extraction() == task_info["expected_has_data"]
        assert response_time < 10.0  # Should complete within 10 seconds

        # Log performance metric
        print(f"Anthropic simple task response time: {response_time:.2f}s")

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_simple_task_openai(self, openai_client):
        """Test simple task analysis with OpenAI API."""
        analyzer = WebTaskAnalyzer(openai_client, provider="openai")
        task_info = SIMPLE_TASKS[1]

        start_time = time.time()
        task = await analyzer.analyze_task(task_info["description"], task_info["url"])
        response_time = time.time() - start_time

        # Validate response
        assert isinstance(task, Task)
        assert task.description == task_info["description"]
        assert len(task.objectives) >= task_info["expected_objectives_count"]
        assert task.has_actions() == task_info["expected_has_actions"]
        assert task.has_data_extraction() == task_info["expected_has_data"]
        assert response_time < 10.0

        # Log performance metric
        print(f"OpenAI simple task response time: {response_time:.2f}s")

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_complex_navigation_task(self, anthropic_client):
        """Test complex multi-step navigation task."""
        analyzer = WebTaskAnalyzer(anthropic_client)
        task_info = COMPLEX_TASKS[0]

        task = await analyzer.analyze_task(task_info["description"], task_info["url"])

        # Complex tasks should have multiple objectives
        assert len(task.objectives) >= task_info["expected_min_objectives"]
        assert task.has_actions() == task_info["expected_has_actions"]
        assert task.has_data_extraction() == task_info["expected_has_data"]
        assert task.is_complex()  # Should be identified as complex

        # Should have constraints for filtering
        assert len(task.constraints) > 0

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_form_filling_task(self, openai_client):
        """Test form filling task analysis."""
        analyzer = WebTaskAnalyzer(openai_client, provider="openai")
        task_desc = get_tasks_by_category("form_filling")[0]

        task = await analyzer.analyze_task(task_desc, "https://forms.example.com")

        # Form filling tasks should have actions
        assert task.has_actions()
        assert "fill" in task.description.lower() or any(
            "fill" in obj.lower() for obj in task.objectives
        )
        assert len(task.actions_to_perform) > 0

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_data_extraction_task(self, anthropic_client):
        """Test pure data extraction task."""
        analyzer = WebTaskAnalyzer(anthropic_client)
        task_desc = get_tasks_by_category("data_extraction")[0]

        task = await analyzer.analyze_task(task_desc, "https://data.example.com")

        # Data extraction tasks should specify what to extract
        assert task.has_data_extraction()
        assert not task.has_actions()  # Pure extraction, no navigation
        assert len(task.data_to_extract) > 0

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_empty_description_edge_case(self, anthropic_client):
        """Test handling of empty task description."""
        analyzer = WebTaskAnalyzer(anthropic_client)
        edge_case = EDGE_CASES[0]

        # Should still work but with minimal objectives
        task = await analyzer.analyze_task(edge_case["description"], edge_case["url"])

        assert isinstance(task, Task)
        assert len(task.objectives) >= 1  # At least one objective
        assert len(task.success_criteria) >= 1

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_very_long_description(self, openai_client):
        """Test handling of very long task descriptions."""
        analyzer = WebTaskAnalyzer(openai_client, provider="openai")
        edge_case = EDGE_CASES[2]  # The extremely long description

        task = await analyzer.analyze_task(edge_case["description"], edge_case["url"])

        # Should handle complex requirements
        assert len(task.objectives) >= edge_case["expected_min_objectives"]
        assert task.is_complex()

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_contradictory_instructions(self, anthropic_client):
        """Test handling of contradictory instructions."""
        analyzer = WebTaskAnalyzer(anthropic_client)
        edge_case = EDGE_CASES[3]

        task = await analyzer.analyze_task(edge_case["description"], edge_case["url"])

        # Should identify constraints from contradictory instructions
        assert len(task.constraints) > 0
        assert any("disabled" in c.lower() for c in task.constraints)

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_invalid_api_key_anthropic(self):
        """Test error handling with invalid Anthropic API key."""
        client = LangChainLLMClient(provider="anthropic", api_key="invalid-key-123")
        analyzer = WebTaskAnalyzer(client)

        with pytest.raises(LLMCommunicationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")

        assert exc_info.value.retry_count > 0  # Should have retried

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_invalid_api_key_openai(self):
        """Test error handling with invalid OpenAI API key."""
        client = LangChainLLMClient(provider="openai", api_key="invalid-key-456")
        analyzer = WebTaskAnalyzer(client, provider="openai")

        with pytest.raises(LLMCommunicationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")

        assert exc_info.value.retry_count > 0

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limit_simulation(self, anthropic_client):
        """Test rate limit handling (may not trigger actual rate limit)."""
        analyzer = WebTaskAnalyzer(anthropic_client, max_retries=2, retry_delay=0.1)

        # Make multiple rapid requests (cassette will prevent actual API calls)
        tasks = []
        for i in range(5):
            task_desc = f"Task {i}: Click button {i}"
            try:
                task = await analyzer.analyze_task(task_desc, "https://example.com")
                tasks.append(task)
            except RateLimitError:
                # If we hit a rate limit, that's what we're testing
                assert True
                return

        # If no rate limit, verify tasks were created
        assert len(tasks) == 5

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_timeout_handling(self, anthropic_client):
        """Test timeout handling with very short timeout."""
        # Use extremely short timeout to force timeout
        analyzer = WebTaskAnalyzer(anthropic_client, timeout=0.001, max_retries=1)

        with pytest.raises(LLMCommunicationError) as exc_info:
            await analyzer.analyze_task(
                "This is a test task that should timeout", "https://example.com"
            )

        assert "timed out" in str(exc_info.value)

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    @pytest.mark.parametrize("provider", ["anthropic", "openai"])
    async def test_performance_benchmarks(self, provider, anthropic_client, openai_client):
        """Benchmark performance across providers."""
        client = anthropic_client if provider == "anthropic" else openai_client
        analyzer = WebTaskAnalyzer(client, provider=provider)

        perf_task = PERFORMANCE_TASKS[0]  # Simple task
        
        # Measure response time
        start_time = time.time()
        task = await analyzer.analyze_task(perf_task["description"], perf_task["url"])
        response_time = time.time() - start_time

        # Verify task was analyzed correctly
        assert isinstance(task, Task)
        
        # Check performance (with cassette, should be very fast)
        assert response_time < perf_task["expected_response_time"]
        
        print(f"{provider} benchmark - {perf_task['category']}: {response_time:.2f}s")

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_different_task_types_anthropic(self, anthropic_client):
        """Test various task types with Anthropic."""
        analyzer = WebTaskAnalyzer(anthropic_client)
        
        results = {}
        for category, descriptions in [
            ("navigation", get_tasks_by_category("navigation")[0]),
            ("search", get_tasks_by_category("search")[0]),
            ("interaction", get_tasks_by_category("interaction")[0]),
        ]:
            task = await analyzer.analyze_task(descriptions, f"https://{category}.example.com")
            results[category] = {
                "objectives_count": len(task.objectives),
                "has_actions": task.has_actions(),
                "has_data": task.has_data_extraction(),
                "is_complex": task.is_complex(),
            }

        # Verify each task type was handled appropriately
        assert results["navigation"]["has_actions"]
        assert results["search"]["objectives_count"] >= 1
        assert results["interaction"]["has_actions"]

    @pytest.mark.vcr()
    @pytest.mark.asyncio
    async def test_context_switching_providers(self, anthropic_client, openai_client):
        """Test switching between providers for same task."""
        task_desc = "Find all products under $50 and add them to cart"
        url = "https://shop.example.com"

        # Analyze with Anthropic
        analyzer_anthropic = WebTaskAnalyzer(anthropic_client, provider="anthropic")
        task_anthropic = await analyzer_anthropic.analyze_task(task_desc, url)

        # Analyze with OpenAI
        analyzer_openai = WebTaskAnalyzer(openai_client, provider="openai")
        task_openai = await analyzer_openai.analyze_task(task_desc, url)

        # Both should produce valid tasks with similar structure
        assert isinstance(task_anthropic, Task)
        assert isinstance(task_openai, Task)
        
        # Both should identify this as having actions and data extraction
        assert task_anthropic.has_actions()
        assert task_anthropic.has_data_extraction()
        assert task_openai.has_actions()
        assert task_openai.has_data_extraction()

        # Objectives might differ slightly but should be present
        assert len(task_anthropic.objectives) > 0
        assert len(task_openai.objectives) > 0