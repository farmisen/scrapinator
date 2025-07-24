"""LLM client implementations using langchain."""

import os
from typing import cast

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

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

        # Set API key in environment if provided
        if api_key:
            if provider == LLMProvider.ANTHROPIC.value:
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif provider == LLMProvider.OPENAI.value:
                os.environ["OPENAI_API_KEY"] = api_key

        # Initialize the appropriate model
        if provider == LLMProvider.ANTHROPIC.value:
            default_model = "claude-3-opus-20240229"
            # Note: langchain-anthropic uses different parameter names
            self.model = ChatAnthropic(
                model=model_name or default_model,  # pyright: ignore[reportCallIssue]
                temperature=temperature,
                max_tokens_to_sample=max_tokens,
            )
        elif provider == LLMProvider.OPENAI.value:
            default_model = "gpt-4"
            self.model = ChatOpenAI(  # type: ignore[call-arg]
                model=model_name or default_model,
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
                model = ChatAnthropic(
                    model=self.model_name or "claude-3-opus-20240229",  # pyright: ignore[reportCallIssue]
                    temperature=temp,
                    max_tokens_to_sample=max_tok,
                )
            else:  # OpenAI
                model = ChatOpenAI(  # type: ignore[call-arg]
                    model=self.model_name or "gpt-4",
                    temperature=temp,
                    max_completion_tokens=max_tok,
                )
        else:
            model = self.model

        # Synchronous invoke
        response = model.invoke(messages)
        return cast("str", response.content)
