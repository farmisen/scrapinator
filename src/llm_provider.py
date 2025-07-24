"""LLM provider configuration and types."""

from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers for the WebTaskAnalyzer."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid provider name."""
        return value in {provider.value for provider in cls}

    @classmethod
    def get_default(cls) -> "LLMProvider":
        """Get the default provider."""
        return cls.ANTHROPIC
