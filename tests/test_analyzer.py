"""Tests for the WebTaskAnalyzer class."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from src.analyzer import WebTaskAnalyzer
from src.exceptions import (
    ContextLengthExceededError,
    InvalidResponseFormatError,
    LLMCommunicationError,
    RateLimitError,
    ValidationError,
)
from src.models.task import Task
from src.prompts.task_analysis import get_prompt_config


class TestWebTaskAnalyzer:
    """Test cases for WebTaskAnalyzer."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock()
        client.complete = AsyncMock()
        return client

    @pytest.fixture
    def analyzer(self, mock_llm_client):
        """Create a WebTaskAnalyzer instance with mock LLM client."""
        return WebTaskAnalyzer(mock_llm_client, timeout=5.0)

    @pytest.mark.asyncio
    async def test_analyze_task_success(self, analyzer, mock_llm_client):
        """Test successful task analysis."""
        # Setup mock response
        mock_response = json.dumps({
            "description": "Extract product prices from e-commerce site",
            "objectives": ["Navigate to products page", "Extract all prices"],
            "success_criteria": ["All product prices extracted"],
            "data_to_extract": ["Product names", "Prices"],
            "actions_to_perform": ["Click on products link"],
            "constraints": ["Only extract visible products"],
            "context": {"category": "electronics"}
        })
        mock_llm_client.complete.return_value = mock_response

        # Call analyze_task
        task = await analyzer.analyze_task(
            "Extract product prices from e-commerce site",
            "https://example.com"
        )

        # Verify the result
        assert isinstance(task, Task)
        assert task.description == "Extract product prices from e-commerce site"
        assert len(task.objectives) == 2
        assert len(task.success_criteria) == 1
        assert task.data_to_extract == ["Product names", "Prices"]
        assert task.constraints == ["Only extract visible products"]
        assert task.context["category"] == "electronics"

        # Verify LLM was called with proper prompt
        mock_llm_client.complete.assert_called_once()
        prompt = mock_llm_client.complete.call_args[0][0]
        assert "https://example.com" in prompt
        assert "Extract product prices from e-commerce site" in prompt

    @pytest.mark.asyncio
    async def test_analyze_task_minimal_response(self, analyzer, mock_llm_client):
        """Test task analysis with minimal required fields."""
        mock_response = json.dumps({
            "description": "Simple task",
            "objectives": ["Do something"],
            "success_criteria": ["Task completed"]
        })
        mock_llm_client.complete.return_value = mock_response

        task = await analyzer.analyze_task("Simple task", "https://example.com")

        assert isinstance(task, Task)
        assert task.description == "Simple task"
        assert task.data_to_extract is None
        assert task.actions_to_perform is None
        assert task.constraints == []
        assert task.context == {}

    @pytest.mark.asyncio
    async def test_analyze_task_with_extra_text(self, analyzer, mock_llm_client):
        """Test parsing when LLM adds extra text around JSON."""
        mock_response = """Here's the analysis:
        {
            "description": "Test task",
            "objectives": ["Test objective"],
            "success_criteria": ["Test passed"]
        }
        That's the JSON response."""
        mock_llm_client.complete.return_value = mock_response

        task = await analyzer.analyze_task("Test task", "https://example.com")

        assert isinstance(task, Task)
        assert task.description == "Test task"

    @pytest.mark.asyncio
    async def test_analyze_task_invalid_json(self, analyzer, mock_llm_client):
        """Test error handling for invalid JSON response."""
        mock_llm_client.complete.return_value = "This is not JSON"

        with pytest.raises(InvalidResponseFormatError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "No valid JSON object found" in str(exc_info.value)
        assert exc_info.value.response == "This is not JSON"
        assert exc_info.value.expected_format is not None

    @pytest.mark.asyncio
    async def test_analyze_task_missing_required_field(self, analyzer, mock_llm_client):
        """Test error handling when required fields are missing."""
        mock_response = json.dumps({
            "description": "Test task",
            "objectives": ["Test objective"]
            # Missing success_criteria
        })
        mock_llm_client.complete.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Missing required fields: success_criteria" in str(exc_info.value)
        assert exc_info.value.field == "success_criteria"
        assert exc_info.value.value is None

    @pytest.mark.asyncio
    async def test_analyze_task_empty_objectives(self, analyzer, mock_llm_client):
        """Test error handling when objectives list is empty."""
        mock_response = json.dumps({
            "description": "Test task",
            "objectives": [],
            "success_criteria": ["Done"]
        })
        mock_llm_client.complete.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Field 'objectives' must contain at least one item" in str(exc_info.value)
        assert exc_info.value.field == "objectives"
        assert exc_info.value.value == []

    @pytest.mark.asyncio
    async def test_analyze_task_llm_error(self, analyzer, mock_llm_client):
        """Test error handling when LLM call fails."""
        mock_llm_client.complete.side_effect = Exception("LLM API error")

        with pytest.raises(LLMCommunicationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Failed to analyze task" in str(exc_info.value)
        assert exc_info.value.original_error is not None
        assert str(exc_info.value.original_error) == "LLM API error"

    @pytest.mark.asyncio
    async def test_analyze_task_timeout(self, mock_llm_client):
        """Test timeout handling for LLM calls."""
        # Create a slow mock that takes longer than timeout
        async def slow_complete(prompt):
            await asyncio.sleep(10)  # Sleep longer than timeout
            return '{"description": "test", "objectives": ["obj"], "success_criteria": ["success"]}'
        
        mock_llm_client.complete = slow_complete
        analyzer = WebTaskAnalyzer(mock_llm_client, timeout=0.1, max_retries=1)  # Short timeout, no retries
        
        with pytest.raises(LLMCommunicationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "timed out after 0.1 seconds" in str(exc_info.value)
        assert exc_info.value.retry_count == 1

    def test_build_analysis_prompt(self, analyzer):
        """Test prompt building."""
        prompt = analyzer._build_analysis_prompt(
            "Extract prices from products",
            "https://shop.example.com"
        )

        assert "https://shop.example.com" in prompt
        assert "Extract prices from products" in prompt
        assert "objectives" in prompt
        assert "success_criteria" in prompt
        assert "JSON" in prompt

    def test_parse_llm_response_valid(self, analyzer):
        """Test parsing valid LLM response."""
        response = json.dumps({
            "description": "Test",
            "objectives": ["Obj1"],
            "success_criteria": ["Success"],
            "constraints": ["Limit1"],
            "context": {"key": "value"}
        })

        result = analyzer._parse_llm_response(response)

        assert result["description"] == "Test"
        assert result["objectives"] == ["Obj1"]
        assert result["success_criteria"] == ["Success"]
        assert result["constraints"] == ["Limit1"]
        assert result["context"]["key"] == "value"

    def test_parse_llm_response_with_defaults(self, analyzer):
        """Test parsing adds default values for optional fields."""
        response = json.dumps({
            "description": "Test",
            "objectives": ["Obj1"],
            "success_criteria": ["Success"]
        })

        result = analyzer._parse_llm_response(response)

        assert result["constraints"] == []
        assert result["context"] == {}
        
    def test_parse_llm_response_null_handling(self, analyzer):
        """Test that null strings are converted to None."""
        response = json.dumps({
            "description": "Test",
            "objectives": ["Obj1"],
            "success_criteria": ["Success"],
            "data_to_extract": "null",
            "actions_to_perform": []
        })

        result = analyzer._parse_llm_response(response)

        assert result["data_to_extract"] is None
        assert result["actions_to_perform"] is None

    def test_analyzer_with_different_providers(self, mock_llm_client):
        """Test analyzer initialization with different providers."""
        # Test default provider (anthropic)
        analyzer_default = WebTaskAnalyzer(mock_llm_client)
        assert analyzer_default.provider == "anthropic"
        assert "examples" in analyzer_default.prompt_config["prompt"].lower()
        
        # Test openai provider
        analyzer_openai = WebTaskAnalyzer(mock_llm_client, provider="openai")
        assert analyzer_openai.provider == "openai"
        assert analyzer_openai.prompt_config["system_message"] == "You are a web automation expert. Always respond with valid JSON only."
        
        # Test invalid provider falls back to anthropic
        # We can't test the logger.warning directly, but we can verify the fallback behavior
        analyzer_invalid = WebTaskAnalyzer(mock_llm_client, provider="invalid_provider")
        
        assert analyzer_invalid.provider == "anthropic"
        assert analyzer_invalid.prompt_config == get_prompt_config("anthropic")

    def test_build_prompt_uses_provider_config(self, mock_llm_client):
        """Test that prompt building uses the correct provider template."""
        # Test with openai provider
        analyzer = WebTaskAnalyzer(mock_llm_client, provider="openai")
        prompt = analyzer._build_analysis_prompt("Test task", "https://example.com")
        
        # Should have the examples from the full prompt
        assert "Example 1:" in prompt
        assert "Important guidelines:" in prompt

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, mock_llm_client):
        """Test that transient errors trigger retries."""
        # First two calls fail, third succeeds
        mock_llm_client.complete.side_effect = [
            Exception("Network error"),
            Exception("Connection timeout"),
            json.dumps({
                "description": "Test task",
                "objectives": ["Do something"],
                "success_criteria": ["Task completed"]
            })
        ]
        
        analyzer = WebTaskAnalyzer(mock_llm_client, max_retries=3, retry_delay=0.01)
        task = await analyzer.analyze_task("Test task", "https://example.com")
        
        assert isinstance(task, Task)
        assert mock_llm_client.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, mock_llm_client):
        """Test rate limit error detection and handling."""
        mock_llm_client.complete.side_effect = ValueError("Rate limit exceeded")
        
        analyzer = WebTaskAnalyzer(mock_llm_client, max_retries=2, retry_delay=0.01)
        
        with pytest.raises(RateLimitError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_count == 2

    @pytest.mark.asyncio
    async def test_validation_error_type_checking(self, mock_llm_client):
        """Test type validation for response fields."""
        mock_response = json.dumps({
            "description": 123,  # Should be string
            "objectives": ["Test"],
            "success_criteria": ["Done"]
        })
        mock_llm_client.complete.return_value = mock_response
        
        analyzer = WebTaskAnalyzer(mock_llm_client)
        
        with pytest.raises(ValidationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Field 'description' must be a string" in str(exc_info.value)
        assert exc_info.value.field == "description"
        assert exc_info.value.value == 123

    @pytest.mark.asyncio
    async def test_validation_error_list_items(self, mock_llm_client):
        """Test validation of list item types."""
        mock_response = json.dumps({
            "description": "Test",
            "objectives": ["Valid", 123, "Another"],  # Second item invalid
            "success_criteria": ["Done"]
        })
        mock_llm_client.complete.return_value = mock_response
        
        analyzer = WebTaskAnalyzer(mock_llm_client)
        
        with pytest.raises(ValidationError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Item 1 in field 'objectives' must be a string" in str(exc_info.value)
        assert exc_info.value.field == "objectives[1]"

    @pytest.mark.asyncio
    async def test_no_retry_on_validation_error(self, mock_llm_client):
        """Test that validation errors don't trigger retries."""
        mock_llm_client.complete.return_value = json.dumps({
            "description": "Test",
            "objectives": [],  # Empty list
            "success_criteria": ["Done"]
        })
        
        analyzer = WebTaskAnalyzer(mock_llm_client, max_retries=3)
        
        with pytest.raises(ValidationError):
            await analyzer.analyze_task("Test task", "https://example.com")
        
        # Should only call once, no retries for validation errors
        assert mock_llm_client.complete.call_count == 1

    @pytest.mark.asyncio
    async def test_context_length_exceeded_error(self, mock_llm_client):
        """Test handling of context length exceeded errors."""
        # For simplicity, we'll test that context length errors in _is_retryable_error work correctly
        # The actual ValueError would be caught and re-raised as ContextLengthExceededError in _handle_llm_response
        analyzer = WebTaskAnalyzer(mock_llm_client)
        
        # Test that context length ValueError is not retryable
        context_error = ValueError("context length exceeded")
        assert not analyzer._is_retryable_error(context_error)
        
        token_error = ValueError("token limit exceeded")
        assert not analyzer._is_retryable_error(token_error)
        
        # Also test the actual flow by mocking a successful response followed by
        # the error in the response handler
        mock_response = json.dumps({
            "description": "Test",
            "objectives": ["Test"],
            "success_criteria": ["Test"] 
        })
        mock_llm_client.complete.return_value = mock_response
        
        # Patch _parse_llm_response to raise the context length error
        original_parse = analyzer._parse_llm_response
        def mock_parse(response):
            raise ValueError("context length exceeded while parsing")
        
        analyzer._parse_llm_response = mock_parse
        
        with pytest.raises(ContextLengthExceededError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        # The ValueError should be converted to ContextLengthExceededError
        assert "Prompt exceeds LLM context length limit" in str(exc_info.value)
        assert exc_info.value.prompt_length > 0

    @pytest.mark.asyncio 
    async def test_empty_task_description(self, analyzer, mock_llm_client):
        """Test handling of empty task description."""
        mock_response = json.dumps({
            "description": "",
            "objectives": ["Generic objective"],
            "success_criteria": ["Task completed"]
        })
        mock_llm_client.complete.return_value = mock_response
        
        # Should still work with empty description
        task = await analyzer.analyze_task("", "https://example.com")
        assert isinstance(task, Task)
        assert task.description == ""

    @pytest.mark.asyncio
    async def test_invalid_url_format(self, analyzer, mock_llm_client):
        """Test handling of invalid URL format."""
        mock_response = json.dumps({
            "description": "Task with invalid URL",
            "objectives": ["Handle invalid URL"],
            "success_criteria": ["Gracefully handle the URL"]
        })
        mock_llm_client.complete.return_value = mock_response
        
        # Should still work - URL validation is not done in analyzer
        task = await analyzer.analyze_task("Test task", "not-a-valid-url")
        assert isinstance(task, Task)
        # Verify the invalid URL was still passed to the LLM
        prompt = mock_llm_client.complete.call_args[0][0]
        assert "not-a-valid-url" in prompt

    @pytest.mark.asyncio
    async def test_analyzer_without_timeout(self, mock_llm_client):
        """Test analyzer behavior when timeout is None."""
        mock_response = json.dumps({
            "description": "Test task",
            "objectives": ["Test objective"],
            "success_criteria": ["Success"]
        })
        mock_llm_client.complete.return_value = mock_response
        
        # Create analyzer without timeout
        analyzer = WebTaskAnalyzer(mock_llm_client, timeout=None)
        task = await analyzer.analyze_task("Test task", "https://example.com")
        
        assert isinstance(task, Task)
        # Verify the LLM was called without timeout wrapper
        mock_llm_client.complete.assert_called_once()

    def test_is_retryable_error(self, analyzer):
        """Test the _is_retryable_error method."""
        # Non-retryable errors
        assert not analyzer._is_retryable_error(InvalidResponseFormatError("test"))
        assert not analyzer._is_retryable_error(ValidationError("test"))
        assert not analyzer._is_retryable_error(ContextLengthExceededError("test"))
        assert not analyzer._is_retryable_error(json.JSONDecodeError("test", "doc", 0))
        
        # Context length ValueError is not retryable
        assert not analyzer._is_retryable_error(ValueError("context length exceeded"))
        assert not analyzer._is_retryable_error(ValueError("token limit reached"))
        
        # Other errors are retryable
        assert analyzer._is_retryable_error(Exception("generic error"))
        assert analyzer._is_retryable_error(ValueError("some other error"))
        assert analyzer._is_retryable_error(TimeoutError("timeout"))