"""Tests for prompt templates."""

import pytest

from src.llm_provider import LLMProvider
from src.prompts.task_analysis import (
    PROVIDER_CONFIGS,
    TASK_ANALYSIS_PROMPT,
    get_prompt_config,
)


class TestPromptTemplates:
    """Test cases for prompt templates."""

    def test_task_analysis_prompt_has_placeholders(self) -> None:
        """Test that the main prompt has required placeholders."""
        assert "{url}" in TASK_ANALYSIS_PROMPT
        assert "{task_description}" in TASK_ANALYSIS_PROMPT

    def test_task_analysis_prompt_has_examples(self) -> None:
        """Test that the main prompt includes few-shot examples."""
        assert "Example 1:" in TASK_ANALYSIS_PROMPT
        assert "Example 2:" in TASK_ANALYSIS_PROMPT
        assert "Example 3:" in TASK_ANALYSIS_PROMPT
        # Check for specific example content
        assert "products under $50" in TASK_ANALYSIS_PROMPT
        assert "customer satisfaction survey" in TASK_ANALYSIS_PROMPT
        assert "today's headlines" in TASK_ANALYSIS_PROMPT

    def test_task_analysis_prompt_has_guidelines(self) -> None:
        """Test that the prompt includes important guidelines."""
        assert "Important guidelines:" in TASK_ANALYSIS_PROMPT
        assert "vague" in TASK_ANALYSIS_PROMPT
        assert "JSON" in TASK_ANALYSIS_PROMPT


    def test_provider_configs_exist(self) -> None:
        """Test that provider configurations are defined."""
        assert LLMProvider.ANTHROPIC.value in PROVIDER_CONFIGS
        assert LLMProvider.OPENAI.value in PROVIDER_CONFIGS

    def test_provider_configs_have_required_fields(self) -> None:
        """Test that each provider config has required fields."""
        for provider, config in PROVIDER_CONFIGS.items():
            assert "prompt" in config, f"{provider} missing 'prompt'"
            assert "system_message" in config, f"{provider} missing 'system_message'"
            assert "temperature" in config, f"{provider} missing 'temperature'"
            assert "max_tokens" in config, f"{provider} missing 'max_tokens'"

    def test_anthropic_config_uses_full_prompt(self) -> None:
        """Test that Anthropic config uses the full prompt."""
        assert PROVIDER_CONFIGS[LLMProvider.ANTHROPIC.value]["prompt"] == TASK_ANALYSIS_PROMPT
        assert PROVIDER_CONFIGS[LLMProvider.ANTHROPIC.value]["max_tokens"] == 1000

    def test_openai_config_uses_full_prompt(self) -> None:
        """Test that OpenAI config uses the full prompt."""
        assert PROVIDER_CONFIGS[LLMProvider.OPENAI.value]["prompt"] == TASK_ANALYSIS_PROMPT
        assert PROVIDER_CONFIGS[LLMProvider.OPENAI.value]["max_tokens"] == 1000


    def test_get_prompt_config_default(self) -> None:
        """Test get_prompt_config with default provider."""
        config = get_prompt_config()
        assert config == PROVIDER_CONFIGS[LLMProvider.ANTHROPIC.value]

    def test_get_prompt_config_specific_provider(self) -> None:
        """Test get_prompt_config with specific providers."""
        assert get_prompt_config(LLMProvider.ANTHROPIC.value) == PROVIDER_CONFIGS[LLMProvider.ANTHROPIC.value]
        assert get_prompt_config(LLMProvider.OPENAI.value) == PROVIDER_CONFIGS[LLMProvider.OPENAI.value]

    def test_get_prompt_config_unknown_provider(self) -> None:
        """Test get_prompt_config with unknown provider falls back to default."""
        config = get_prompt_config("unknown_provider")
        assert config == PROVIDER_CONFIGS[LLMProvider.ANTHROPIC.value]

    def test_prompt_formatting(self) -> None:
        """Test that prompts can be formatted correctly."""
        url = "https://test.example.com"
        task = "Test task description"
        
        # Test main prompt formatting
        formatted = TASK_ANALYSIS_PROMPT.format(url=url, task_description=task)
        assert url in formatted
        assert task in formatted
