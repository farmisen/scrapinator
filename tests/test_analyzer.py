"""Tests for the WebTaskAnalyzer class."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from src.analyzer import WebTaskAnalyzer
from src.models.task import Task


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

        with pytest.raises(ValueError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "No valid JSON object found" in str(exc_info.value)
        assert "Expected a JSON object" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_task_missing_required_field(self, analyzer, mock_llm_client):
        """Test error handling when required fields are missing."""
        mock_response = json.dumps({
            "description": "Test task",
            "objectives": ["Test objective"]
            # Missing success_criteria
        })
        mock_llm_client.complete.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Missing required fields: success_criteria" in str(exc_info.value)
        assert "Expected all of:" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_task_empty_objectives(self, analyzer, mock_llm_client):
        """Test error handling when objectives list is empty."""
        mock_response = json.dumps({
            "description": "Test task",
            "objectives": [],
            "success_criteria": ["Done"]
        })
        mock_llm_client.complete.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "Field 'objectives' must contain at least one item" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_task_llm_error(self, analyzer, mock_llm_client):
        """Test error handling when LLM call fails."""
        mock_llm_client.complete.side_effect = Exception("LLM API error")

        with pytest.raises(Exception) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "LLM API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_task_timeout(self, mock_llm_client):
        """Test timeout handling for LLM calls."""
        # Create a slow mock that takes longer than timeout
        async def slow_complete(prompt):
            await asyncio.sleep(10)  # Sleep longer than timeout
            return '{"description": "test", "objectives": ["obj"], "success_criteria": ["success"]}'
        
        mock_llm_client.complete = slow_complete
        analyzer = WebTaskAnalyzer(mock_llm_client, timeout=0.1)  # Very short timeout
        
        with pytest.raises(TimeoutError) as exc_info:
            await analyzer.analyze_task("Test task", "https://example.com")
        
        assert "timed out after 0.1 seconds" in str(exc_info.value)

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