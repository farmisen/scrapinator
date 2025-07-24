"""LLM client implementations using magentic."""

import os
from typing import Optional

from magentic import prompt
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel
from magentic.chat_model.openai_chat_model import OpenaiChatModel

from src.llm_provider import LLMProvider


class MagenticLLMClient:
    """LLM client implementation using the magentic library."""

    def __init__(
        self,
        provider: str = LLMProvider.ANTHROPIC.value,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize the LLM client with magentic.

        Args:
            provider: The LLM provider to use ("anthropic", "openai")
            model_name: Specific model name to use (e.g., "claude-3-opus-20240229", "gpt-4")
                       If None, uses default model for the provider
            api_key: API key for the provider. If None, reads from environment variables
                    (ANTHROPIC_API_KEY or OPENAI_API_KEY)

        Raises:
            ValueError: If an unsupported provider is specified
        """
        self.provider = provider

        # Set up API key
        if api_key:
            if provider == LLMProvider.ANTHROPIC.value:
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif provider == LLMProvider.OPENAI.value:
                os.environ["OPENAI_API_KEY"] = api_key

        # Initialize the appropriate model
        if provider == LLMProvider.ANTHROPIC.value:
            default_model = "claude-3-opus-20240229"
            self.model = AnthropicChatModel(model_name or default_model)
        elif provider == LLMProvider.OPENAI.value:
            default_model = "gpt-4"
            self.model = OpenaiChatModel(model_name or default_model)
        else:
            error_msg = f"Unsupported provider: {provider}"
            raise ValueError(error_msg)

    async def complete(self, prompt_text: str) -> str:
        """
        Complete a prompt and return the response.

        This method satisfies the LLMClient protocol used by WebTaskAnalyzer.

        Args:
            prompt_text: The prompt to send to the LLM

        Returns:
            The LLM's response as a string
        """

        # Create a dynamic prompt function using magentic
        @prompt(prompt_text)
        def _complete() -> str: ...

        # Execute the prompt (magentic handles async internally)
        return _complete()

    def complete_with_config(
        self,
        prompt_text: str,
        system_message: Optional[str] = None,  # noqa: ARG002
        temperature: Optional[float] = None,  # noqa: ARG002
        max_tokens: Optional[int] = None,  # noqa: ARG002
    ) -> str:
        """
        Complete a prompt with additional configuration options.

        This method allows using the recommended settings from prompt configs.

        Args:
            prompt_text: The prompt to send to the LLM
            system_message: System message to set context (if supported by model)
            temperature: Temperature setting for response randomness
            max_tokens: Maximum tokens in the response

        Returns:
            The LLM's response as a string

        Note:
            Not all models support all configuration options. The implementation
            will use what's available for each model.
        """

        # For now, we use the simple completion
        # In a full implementation, these parameters would be passed to the model
        # magentic's API for these advanced features is still evolving
        @prompt(prompt_text)
        def _complete() -> str: ...

        return _complete()
