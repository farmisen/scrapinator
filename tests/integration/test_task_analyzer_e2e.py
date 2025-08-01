"""End-to-end integration tests for WebTaskAnalyzer with real LLM providers."""

import asyncio
import os
import time

import pytest

from src.analyzer import WebTaskAnalyzer
from src.exceptions import (
    InvalidResponseFormatError,
    LLMCommunicationError,
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

    # Class-level rate limit tracking
    _last_api_call_time = 0
    _min_time_between_calls = 2.0  # Minimum 2 seconds between API calls

    @pytest.fixture(autouse=True)
    async def add_delay_between_tests(self, request):
        """Add a small delay between tests to avoid rate limits."""
        # Ensure minimum time between API calls
        current_time = time.time()
        time_since_last_call = current_time - TestTaskAnalyzerE2E._last_api_call_time
        if time_since_last_call < TestTaskAnalyzerE2E._min_time_between_calls:
            await asyncio.sleep(TestTaskAnalyzerE2E._min_time_between_calls - time_since_last_call)

        TestTaskAnalyzerE2E._last_api_call_time = time.time()

        yield

        # Update last API call time
        TestTaskAnalyzerE2E._last_api_call_time = time.time()

        # Add longer delays after tests that make multiple API calls
        test_name = request.node.name
        if any(
            name in test_name
            for name in [
                "test_different_task_types",
                "test_context_switching",
                "test_rate_limit",
                "test_performance_benchmark",
                "test_invalid_api_key",  # Also delay after invalid API key tests
            ]
        ):
            await asyncio.sleep(5.0)  # 5 seconds for heavy tests
        else:
            await asyncio.sleep(3.0)  # 3 seconds for normal tests

    @pytest.fixture
    def vcr_config(self, request):
        """Configure VCR to filter sensitive data."""
        # Check if recording is disabled
        if request.config.getoption("--disable-recording"):
            return {
                "record_mode": "none",  # Don't record anything
                "allow_playback_repeats": True,
            }

        # Check if this test expects failures
        test_name = request.node.name
        expects_failure = any(
            name in test_name
            for name in [
                "test_invalid_api_key",
                "test_timeout_handling",
            ]
        )

        def before_record_response(response):
            """Only record successful responses unless test expects failure."""
            status_code = response["status"]["code"]

            # For tests that expect failures, record everything
            if expects_failure:
                return response

            # For normal tests, only record successful responses
            if status_code >= 400:
                return None  # Don't record errors

            return response

        return {
            "filter_headers": ["authorization", "x-api-key"],
            "filter_query_parameters": ["api_key"],
            "filter_post_data_parameters": ["api_key"],
            "record_mode": "once",  # Record if cassette doesn't exist
            "match_on": ["method", "scheme", "host", "port", "path", "query"],
            "before_record_response": before_record_response,
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

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
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

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    @pytest.mark.vcr
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

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
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

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    @pytest.mark.vcr
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

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
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

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_empty_description_edge_case(self, anthropic_client):
        """Test handling of empty task description."""
        analyzer = WebTaskAnalyzer(anthropic_client)
        edge_case = EDGE_CASES[0]

        # Empty description might either raise an error or return a minimal task
        try:
            task = await analyzer.analyze_task(edge_case["description"], edge_case["url"])
            # If it doesn't raise an error, it should return a minimal task
            assert isinstance(task, Task)
            assert len(task.objectives) > 0  # Should have at least one objective
        except InvalidResponseFormatError as e:
            # The LLM correctly identifies there's no task to analyze
            assert "don't see a task" in str(e).lower() or "no task provided" in str(e).lower()

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_very_long_description(self, openai_client):
        """Test handling of very long task descriptions."""
        # Use longer timeout for very long descriptions
        analyzer = WebTaskAnalyzer(openai_client, provider="openai", timeout=60.0)
        edge_case = EDGE_CASES[2]  # The extremely long description

        task = await analyzer.analyze_task(edge_case["description"], edge_case["url"])

        # Should handle complex requirements
        assert len(task.objectives) >= edge_case["expected_min_objectives"]
        assert task.is_complex()

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_contradictory_instructions(self, anthropic_client):
        """Test handling of contradictory instructions."""
        analyzer = WebTaskAnalyzer(anthropic_client)
        edge_case = EDGE_CASES[3]

        task = await analyzer.analyze_task(edge_case["description"], edge_case["url"])

        # Should identify constraints from contradictory instructions
        assert len(task.constraints) > 0
        # Check for various ways the LLM might express the constraint
        constraints_text = " ".join(c.lower() for c in task.constraints)
        assert any(
            word in constraints_text
            for word in ["disabled", "enabled", "condition", "if", "unless"]
        )

    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_invalid_api_key_anthropic(self):
        """Test error handling with invalid Anthropic API key."""
        client = LangChainLLMClient(provider="anthropic", api_key="invalid-key-123")
        analyzer = WebTaskAnalyzer(client)

        with pytest.raises(LLMCommunicationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")

        assert exc_info.value.retry_count > 0  # Should have retried

    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_invalid_api_key_openai(self):
        """Test error handling with invalid OpenAI API key."""
        client = LangChainLLMClient(provider="openai", api_key="invalid-key-456")
        analyzer = WebTaskAnalyzer(client, provider="openai")

        with pytest.raises(LLMCommunicationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")

        assert exc_info.value.retry_count > 0

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limit_simulation(self, anthropic_client):
        """Test rate limit handling (may not trigger actual rate limit)."""
        analyzer = WebTaskAnalyzer(anthropic_client, max_retries=2, retry_delay=0.5)

        # Just test that we can make a request without hitting rate limits
        # Real rate limit testing would require many more requests
        task_desc = "Click the submit button"
        task = await analyzer.analyze_task(task_desc, "https://example.com")

        # Verify the task was created successfully
        assert isinstance(task, Task)
        assert len(task.objectives) > 0

        # Note: Actual rate limit testing is better done with mocked responses
        # to avoid hitting real API limits and incurring costs

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
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

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_performance_benchmark_anthropic(self, anthropic_client):
        """Benchmark performance with Anthropic."""
        analyzer = WebTaskAnalyzer(anthropic_client, provider="anthropic")
        perf_task = PERFORMANCE_TASKS[0]  # Simple task

        # Measure response time
        start_time = time.time()
        task = await analyzer.analyze_task(perf_task["description"], perf_task["url"])
        response_time = time.time() - start_time

        # Verify task was analyzed correctly
        assert isinstance(task, Task)

        # Check performance (be generous with timeout for real API calls)
        assert response_time < 10.0  # 10 seconds max

        print(f"Anthropic benchmark - {perf_task['category']}: {response_time:.2f}s")

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_performance_benchmark_openai(self, openai_client):
        """Benchmark performance with OpenAI."""
        analyzer = WebTaskAnalyzer(openai_client, provider="openai")
        perf_task = PERFORMANCE_TASKS[0]  # Simple task

        # Measure response time
        start_time = time.time()
        task = await analyzer.analyze_task(perf_task["description"], perf_task["url"])
        response_time = time.time() - start_time

        # Verify task was analyzed correctly
        assert isinstance(task, Task)

        # Check performance (be generous with timeout for real API calls)
        assert response_time < 10.0  # 10 seconds max

        print(f"OpenAI benchmark - {perf_task['category']}: {response_time:.2f}s")

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.vcr
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
            # Add delay between API calls to avoid rate limits
            await asyncio.sleep(1.0)

        # Verify each task type was handled appropriately
        assert results["navigation"]["has_actions"]
        assert results["search"]["objectives_count"] >= 1
        assert results["interaction"]["has_actions"]

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or not os.getenv("OPENAI_API_KEY"),
        reason="Both ANTHROPIC_API_KEY and OPENAI_API_KEY required",
    )
    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_context_switching_providers(self, anthropic_client, openai_client):
        """Test switching between providers for same task."""
        task_desc = "Find all products under $50 and add them to cart"
        url = "https://shop.example.com"

        # Analyze with Anthropic
        analyzer_anthropic = WebTaskAnalyzer(anthropic_client, provider="anthropic")
        task_anthropic = await analyzer_anthropic.analyze_task(task_desc, url)

        # Add delay before second API call
        await asyncio.sleep(1.5)

        # Analyze with OpenAI
        analyzer_openai = WebTaskAnalyzer(openai_client, provider="openai")
        task_openai = await analyzer_openai.analyze_task(task_desc, url)

        # Both should produce valid tasks with similar structure
        assert isinstance(task_anthropic, Task)
        assert isinstance(task_openai, Task)

        # Both should identify this as having actions
        assert task_anthropic.has_actions()
        assert task_openai.has_actions()

        # At least one should identify data extraction (providers may differ)
        assert task_anthropic.has_data_extraction() or task_openai.has_data_extraction()

        # Objectives might differ slightly but should be present
        assert len(task_anthropic.objectives) > 0
        assert len(task_openai.objectives) > 0
