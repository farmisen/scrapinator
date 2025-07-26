# Scrapinator Examples

This directory contains example scripts demonstrating how to use the Scrapinator web task automation system.

## Examples

### 1. Task Analyzer Demo (`task_analyzer_demo.py`)

A comprehensive example showing how to use the `WebTaskAnalyzer` class with real LLM integration. This demo showcases:

- **Multiple task scenarios**: Simple extraction, navigation, form filling, downloads, and complex tasks
- **LLM provider support**: Works with both Anthropic (Claude) and OpenAI models
- **Error handling**: Demonstrates handling of rate limits, validation errors, and other exceptions
- **Async patterns**: Shows proper async/await usage throughout
- **Pretty output**: Formatted results with timing information

## Setup

### Prerequisites

1. Python 3.12 or higher
2. All project dependencies installed:
   ```bash
   make install
   ```

### Environment Variables

Set up your LLM API keys:

```bash
# For Anthropic (Claude)
export ANTHROPIC_API_KEY='your-anthropic-api-key'

# For OpenAI
export OPENAI_API_KEY='your-openai-api-key'
```

## Running the Examples

### Task Analyzer Demo

Run with default settings (Anthropic/Claude):
```bash
python examples/task_analyzer_demo.py
```

Use OpenAI instead:
```bash
python examples/task_analyzer_demo.py --provider openai
```

Use a specific model:
```bash
python examples/task_analyzer_demo.py --provider anthropic --model claude-3-haiku-20240307
python examples/task_analyzer_demo.py --provider openai --model gpt-4
```

Run specific task scenarios:
```bash
# Run only the simple extraction example
python examples/task_analyzer_demo.py --tasks simple_extraction

# Run multiple specific examples
python examples/task_analyzer_demo.py --tasks simple_extraction form_filling

# Skip error handling demonstrations
python examples/task_analyzer_demo.py --skip-errors
```

### Available Task Scenarios

1. **simple_extraction**: Extract data from a webpage (e.g., Hacker News stories)
2. **multi_step_navigation**: Navigate through multiple pages to extract data
3. **form_filling**: Fill and submit web forms
4. **file_download**: Download files from websites
5. **complex_with_constraints**: Complex tasks with multiple constraints and filters

## Expected Output

The demo will show:

1. **Task Analysis Results**: 
   - Parsed objectives
   - Success criteria
   - Constraints
   - Data to extract
   - Actions to perform

2. **Timing Information**: How long each analysis takes

3. **Error Handling**: Examples of how different error types are handled

### Example Output

```
================================================================================
                     WebTaskAnalyzer Integration Example                        
================================================================================

📅 Date: 2024-01-15 10:30:45
🤖 Provider: anthropic
🧠 Model: Default for provider

🔧 Initializing LLM client...
✅ Initialization complete

================================================================================
                         Task Analysis Examples                                 
================================================================================

📋 Task: Simple Data Extraction
🌐 URL: https://news.ycombinator.com
📝 Description: Extract the titles and scores of the top 5 stories on Hacker News
--------------------------------------------------------------------------------

✅ Analysis completed in 2.34 seconds

📊 Task Analysis Result:
--------------------------------------------------------------------------------
📄 Description: Extract the titles and scores of the top 5 stories on Hacker News

🎯 Objectives (2):
   1. Navigate to the Hacker News homepage
   2. Extract title and score data for the top 5 stories

✔️  Success Criteria (2):
   1. Successfully extracted 5 story titles
   2. Successfully extracted 5 story scores

📊 Data to Extract (2):
   1. Story titles (text content)
   2. Story scores (numeric values)

📈 Task Complexity: Simple
💾 Has Data Extraction: Yes
⚡ Has Actions: No
```

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   - Error: `ANTHROPIC_API_KEY environment variable not set`
   - Solution: Export your API key as shown in the setup section

2. **Rate Limits**
   - Error: `Rate limit exceeded for LLM API`
   - Solution: The demo includes automatic retry with exponential backoff

3. **Network Issues**
   - Error: `LLM request timed out`
   - Solution: Check your internet connection; the timeout is set to 30 seconds

4. **Invalid Model Name**
   - Error: `Model not found`
   - Solution: Use a valid model name for your provider (see provider documentation)

## Next Steps

After running these examples, you can:

1. Modify the task descriptions to test different scenarios
2. Integrate the `WebTaskAnalyzer` into your own automation workflows
3. Extend the examples with additional error handling or output formats
4. Use the analyzed tasks with the plan generator and executor (when implemented)

## Contributing

When adding new examples:

1. Follow the existing pattern of comprehensive documentation
2. Include error handling demonstrations
3. Show both simple and complex use cases
4. Add clear setup instructions
5. Update this README with your new example