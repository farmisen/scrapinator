"""Tests for prompt templates."""

import pytest

from src.llm_provider import LLMProvider
from src.prompts.task_analysis import (
    PROVIDER_CONFIGS,
    TASK_ANALYSIS_PROMPT,
    TASK_ANALYSIS_PROMPT_COMPACT,
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

    def test_compact_prompt_has_placeholders(self) -> None:
        """Test that the compact prompt has required placeholders."""
        assert "{url}" in TASK_ANALYSIS_PROMPT_COMPACT
        assert "{task_description}" in TASK_ANALYSIS_PROMPT_COMPACT

    def test_compact_prompt_is_shorter(self) -> None:
        """Test that the compact prompt is significantly shorter."""
        assert len(TASK_ANALYSIS_PROMPT_COMPACT) < len(TASK_ANALYSIS_PROMPT) / 2

    def test_compact_prompt_has_structure(self) -> None:
        """Test that the compact prompt includes JSON structure."""
        assert "Required JSON structure:" in TASK_ANALYSIS_PROMPT_COMPACT
        assert "objectives" in TASK_ANALYSIS_PROMPT_COMPACT
        assert "success_criteria" in TASK_ANALYSIS_PROMPT_COMPACT

    def test_provider_configs_exist(self) -> None:
        """Test that provider configurations are defined."""
        assert "anthropic" in PROVIDER_CONFIGS
        assert "openai" in PROVIDER_CONFIGS
        assert "compact" in PROVIDER_CONFIGS

    def test_provider_configs_have_required_fields(self) -> None:
        """Test that each provider config has required fields."""
        for provider, config in PROVIDER_CONFIGS.items():
            assert "prompt" in config, f"{provider} missing 'prompt'"
            assert "system_message" in config, f"{provider} missing 'system_message'"
            assert "temperature" in config, f"{provider} missing 'temperature'"
            assert "max_tokens" in config, f"{provider} missing 'max_tokens'"

    def test_anthropic_config_uses_full_prompt(self) -> None:
        """Test that Anthropic config uses the full prompt."""
        assert PROVIDER_CONFIGS["anthropic"]["prompt"] == TASK_ANALYSIS_PROMPT
        assert PROVIDER_CONFIGS["anthropic"]["max_tokens"] == 1000

    def test_openai_config_uses_full_prompt(self) -> None:
        """Test that OpenAI config uses the full prompt."""
        assert PROVIDER_CONFIGS["openai"]["prompt"] == TASK_ANALYSIS_PROMPT
        assert PROVIDER_CONFIGS["openai"]["max_tokens"] == 1000

    def test_compact_config_uses_compact_prompt(self) -> None:
        """Test that compact config uses the compact prompt."""
        assert PROVIDER_CONFIGS["compact"]["prompt"] == TASK_ANALYSIS_PROMPT_COMPACT
        assert PROVIDER_CONFIGS["compact"]["max_tokens"] < 1000

    def test_get_prompt_config_default(self) -> None:
        """Test get_prompt_config with default provider."""
        config = get_prompt_config()
        assert config == PROVIDER_CONFIGS["anthropic"]

    def test_get_prompt_config_specific_provider(self) -> None:
        """Test get_prompt_config with specific providers."""
        assert get_prompt_config("anthropic") == PROVIDER_CONFIGS["anthropic"]
        assert get_prompt_config("openai") == PROVIDER_CONFIGS["openai"]
        assert get_prompt_config("compact") == PROVIDER_CONFIGS["compact"]

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
        
        # Test compact prompt formatting
        formatted_compact = TASK_ANALYSIS_PROMPT_COMPACT.format(
            url=url, task_description=task
        )
        assert url in formatted_compact
        assert task in formatted_compact