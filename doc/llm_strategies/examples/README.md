# LLM Strategies Examples

This directory contains example scripts demonstrating various LLM strategies for web page analysis. Each script is self-contained and can be run independently to explore different approaches.

## Setup

Before running the examples, install the required dependencies:

```bash
pip install beautifulsoup4 html2text markdownify
```

## Available Examples

### 1. HTML to Markdown Conversion (`html_to_markdown.py`)
Demonstrates how converting HTML to Markdown can reduce token usage by 80-90% while preserving content structure.

```bash
python html_to_markdown.py
```

**Key Findings:**
- Markdownify provides the best balance of token reduction and content preservation
- Processing time is minimal (<100ms for most pages)
- Essential interactive elements remain identifiable

### 2. HTML Truncation Strategies (`html_truncation.py`)
Shows various approaches to truncating large HTML documents while preserving important information.

```bash
python html_truncation.py
```

**Strategies Demonstrated:**
- Simple length truncation
- Middle-out truncation (keep beginning and end)
- DOM depth limiting
- Structure-preserving truncation
- Importance-based truncation
- Section extraction
- Sliding window approach

### 3. Element Extraction Prompts (`element_extraction_prompts.py`)
Compares different prompt engineering strategies for extracting interactive elements from HTML.

```bash
python element_extraction_prompts.py
```

**Prompt Strategies:**
- Zero-shot prompting
- Few-shot with examples
- Structured prompts
- Chain-of-thought reasoning
- Role-based prompts
- Multi-shot with reasoning

### 4. More Examples (Coming Soon)

Additional examples to be implemented:
- `multishot_vs_single.py` - Compare multi-shot vs single-shot analysis
- `structured_output_formats.py` - JSON mode vs function calling comparison
- `claude_vs_gpt4_analysis.py` - Side-by-side model comparison
- `cost_performance_analysis.py` - Calculate costs for different models
- `interactive_elements_detection.py` - Advanced element detection techniques
- `semantic_similarity_caching.py` - Demonstrate embedding-based caching

## Utilities

The `utils/` directory contains shared utilities:
- `html_utils.py` - HTML processing and conversion functions
- `llm_clients.py` - Mock LLM clients for testing
- `metrics.py` - Performance measurement utilities

## Key Learnings

1. **Token Optimization**: HTML→Markdown conversion is the single most effective optimization
2. **Prompt Engineering**: Few-shot prompting with 3 examples provides optimal accuracy
3. **Truncation**: Importance-based truncation best preserves elements needed for automation
4. **Structure**: Always preserve HTML structure when possible for better LLM understanding

## Running All Examples

To run all examples in sequence:

```bash
for script in html_to_markdown.py html_truncation.py element_extraction_prompts.py; do
    echo "Running $script..."
    python $script
    echo -e "\n\n"
done
```

## Notes

- These examples use mock LLM clients to avoid API costs during experimentation
- To use real LLMs, replace `MockLLMClient` with actual client implementations
- Token counts are approximated as 1 token ≈ 4 characters

## References

For more details, see the research documentation in the parent directory:
- `../research_findings.md` - Comprehensive research findings
- `../strategy_comparison.md` - Detailed strategy comparisons
- `../recommendations.md` - Practical recommendations for implementation