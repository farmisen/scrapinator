"""LLM client implementations using langchain."""

import os
from typing import cast

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.constants import DEFAULT_ANTHROPIC_MODEL, DEFAULT_OPENAI_MODEL
from src.llm_provider import LLMProvider


class LangChainLLMClient:
    """LLM client implementation using the langchain library."""

    def __init__(
        self,
        provider: str = LLMProvider.ANTHROPIC.value,
        model_name: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> None:
        """
        Initialize the LLM client with langchain.

        Args:
            provider: The LLM provider to use ("anthropic", "openai")
            model_name: Specific model name to use (e.g., "claude-3-opus-20240229", "gpt-4")
                       If None, uses default model for the provider
            api_key: API key for the provider. If None, reads from environment variables
                    (ANTHROPIC_API_KEY or OPENAI_API_KEY)
            temperature: Temperature setting for response randomness (default: 0.3)
            max_tokens: Maximum tokens in the response (default: 1000)

        Raises:
            ValueError: If an unsupported provider is specified
        """
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model_name = model_name
        self.api_key = api_key

        # Initialize the appropriate model
        if provider == LLMProvider.ANTHROPIC.value:
            # Get API key from parameter or environment
            anthropic_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not provided")
                
            # Note: langchain-anthropic uses different parameter names
            self.model = ChatAnthropic(
                model=model_name or DEFAULT_ANTHROPIC_MODEL,  # pyright: ignore[reportCallIssue]
                anthropic_api_key=anthropic_api_key,
                temperature=temperature,
                max_tokens_to_sample=max_tokens,
            )
        elif provider == LLMProvider.OPENAI.value:
            # Get API key from parameter or environment
            openai_api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not provided")
                
            self.model = ChatOpenAI(  # type: ignore[call-arg]
                model=model_name or DEFAULT_OPENAI_MODEL,
                openai_api_key=openai_api_key,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )
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
        # Create a message with the prompt
        messages = [HumanMessage(content=prompt_text)]

        # Use ainvoke for async operation
        response = await self.model.ainvoke(messages)

        # Extract and return the string content
        # LangChain returns AIMessage with content attribute
        return cast("str", response.content)

    def complete_with_config(
        self,
        prompt_text: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
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
        """
        # Build messages list
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt_text))

        # Create a new model instance with custom parameters if provided
        if temperature is not None or max_tokens is not None:
            # Use provided values or fall back to instance defaults
            temp = temperature if temperature is not None else self.temperature
            max_tok = max_tokens if max_tokens is not None else self.max_tokens

            if self.provider == LLMProvider.ANTHROPIC.value:
                anthropic_api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
                model = ChatAnthropic(
                    model=self.model_name or DEFAULT_ANTHROPIC_MODEL,  # pyright: ignore[reportCallIssue]
                    anthropic_api_key=anthropic_api_key,
                    temperature=temp,
                    max_tokens_to_sample=max_tok,
                )
            else:  # OpenAI
                openai_api_key = self.api_key or os.getenv("OPENAI_API_KEY")
                model = ChatOpenAI(  # type: ignore[call-arg]
                    model=self.model_name or DEFAULT_OPENAI_MODEL,
                    openai_api_key=openai_api_key,
                    temperature=temp,
                    max_completion_tokens=max_tok,
                )
        else:
            model = self.model

        # Synchronous invoke
        response = model.invoke(messages)
        return cast("str", response.content)
