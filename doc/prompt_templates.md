# Prompt Templates Documentation

This document explains the prompt template system used in the Scrapinator project for analyzing web automation tasks.

## Overview

The prompt template system provides structured prompts for LLMs to analyze natural language task descriptions and convert them into structured `Task` objects. The system supports multiple LLM providers and includes optimizations for different model capabilities.

## Providers

The system supports two provider configurations:

### 1. Anthropic (Default)
- **Provider ID**: `anthropic`
- **Characteristics**: Full prompt with detailed examples and guidelines
- **Recommended Model**: Claude 3 Opus
- **Max Tokens**: 1000
- **Use When**: You need the most accurate and detailed task analysis

### 2. OpenAI
- **Provider ID**: `openai` 
- **Characteristics**: Full prompt optimized for OpenAI's response style
- **Recommended Model**: GPT-4
- **Max Tokens**: 1000
- **Use When**: You're using OpenAI's API infrastructure


## Usage

### Basic Usage with WebTaskAnalyzer

```python
from src.analyzer import WebTaskAnalyzer
from src.llm_client import LangChainLLMClient

# Create LLM client
llm_client = LangChainLLMClient(provider="anthropic")

# Create analyzer with default provider (anthropic)
analyzer = WebTaskAnalyzer(llm_client)

# Or specify a different provider
analyzer = WebTaskAnalyzer(llm_client, provider="openai")

# Analyze a task
task = await analyzer.analyze_task(
    "Download all PDF reports from the last month",
    "https://reports.example.com"
)
```

### Using Different Providers

```python
# For Anthropic (Claude)
analyzer = WebTaskAnalyzer(llm_client, provider="anthropic")

# For OpenAI (GPT-4)
analyzer = WebTaskAnalyzer(llm_client, provider="openai")

```

## Prompt Structure

All prompts are designed to extract the following information:

- **description**: The original task description
- **objectives**: List of steps to accomplish the task
- **success_criteria**: How to determine if the task succeeded
- **data_to_extract**: Optional list of data to collect
- **actions_to_perform**: Optional list of user actions needed
- **constraints**: Any limitations or requirements
- **context**: Additional key-value pairs for context

## Configuration Parameters

Each provider configuration includes:

### Temperature
- **Purpose**: Controls response randomness/creativity
- **Recommended**: 0.3 for consistent, focused responses
- **Note**: Must be implemented by the LLM client

### Max Tokens
- **Purpose**: Limits response size
- **Default**: 1000 (500 for compact mode)
- **Note**: Must be enforced by the LLM client

### System Message
- **Purpose**: Sets the LLM's role and behavior
- **Usage**: Should be passed to the LLM if supported
- **Note**: Implementation depends on the LLM client

## Examples in Prompts

The full prompts (anthropic, openai) include 4 detailed examples:

1. **Data Extraction**: Finding products under $50
2. **Form Filling**: Completing a satisfaction survey
3. **Content Retrieval**: Getting today's headlines
4. **Complex Task**: Downloading invoices with login

These examples help the LLM understand the expected response format and level of detail.

## Error Handling

The system includes fallback behavior:

- Invalid provider names fall back to "anthropic"
- A warning is logged when fallback occurs
- The LLMProvider enum provides validation methods

## Extending the System

To add a new provider:

1. Add the provider to the `LLMProvider` enum
2. Create a configuration in `PROVIDER_CONFIGS`
3. Update documentation
4. Add tests for the new provider

## Best Practices

1. **Choose the Right Provider**: Use Anthropic for Claude models, OpenAI for GPT models
2. **Monitor Token Usage**: Both providers use similar token counts
3. **Test with Examples**: Verify your LLM client handles the prompt format correctly
4. **Handle Timeouts**: Set appropriate timeouts for your use case (default: 30s)