# Playwright Best Practices Examples

This directory contains practical code examples demonstrating best practices for using Playwright in web exploration scenarios.

## Examples

### 1. efficient_page_loading.py
Demonstrates techniques for efficient page loading:
- Resource blocking (images, CSS, fonts)
- Concurrent page loading with semaphores
- Different wait strategies
- Browser context preloading

### 2. element_discovery_patterns.py
Shows advanced element discovery patterns:
- Shadow DOM handling
- IFrame interaction
- Multiple selector fallback strategies
- Dynamic content detection
- Common UI pattern recognition

### 3. browser_pool_manager.py
Implements a sophisticated browser pool for scalability:
- Automatic browser lifecycle management
- Context isolation per operation
- Resource monitoring and limits
- Concurrent request handling
- Performance statistics

### 4. error_handling_patterns.py
Comprehensive error handling strategies:
- Timeout management with different strategies
- Retry mechanisms with exponential backoff
- Navigation failure recovery
- Element interaction error handling
- Error context preservation with screenshots

### 5. security_patterns.py
Security best practices for untrusted content:
- Sandboxed browser execution
- Resource usage monitoring
- Content sanitization
- Isolated execution contexts
- Security auditing

## Installation

To run these examples, you need to install the project with its dependencies:

```bash
# Install project with dev dependencies (recommended)
make install

# Or using uv directly
uv pip install -e ".[dev]"

# Install Playwright browsers (if not already installed)
playwright install chromium
```

**Note**: The security_patterns.py example requires `psutil` for resource monitoring, which is not included in the base dependencies. Install it separately if needed:

```bash
uv pip install psutil
```

## Running the Examples

Each example can be run independently from the project root:

```bash
python doc/playwright_best_practices/examples/efficient_page_loading.py
python doc/playwright_best_practices/examples/element_discovery_patterns.py
python doc/playwright_best_practices/examples/browser_pool_manager.py
python doc/playwright_best_practices/examples/error_handling_patterns.py
python doc/playwright_best_practices/examples/security_patterns.py
```

**Important Notes:**
- These examples connect to real websites (example.com, example.org) for demonstration purposes
- Some examples may take 30-60 seconds to complete due to multiple page loads
- The performance benchmarks example intentionally performs many operations and may take several minutes
- If examples hang or timeout, check your internet connection and ensure the target sites are accessible

## Key Takeaways

1. **Resource Optimization**: Blocking unnecessary resources can significantly improve performance
2. **Concurrency**: Proper concurrent handling with semaphores prevents resource exhaustion
3. **Error Resilience**: Comprehensive error handling with retry logic improves reliability
4. **Security**: Always sanitize inputs and limit resources when dealing with untrusted content
5. **Monitoring**: Track performance metrics to identify bottlenecks and optimize accordingly

## Notes

- All examples use psutil for resource monitoring, which is included in the project's dev dependencies
- Examples are designed to run with minimal external dependencies
- Some examples may take time to complete due to network operations and timeouts
- Error handling examples intentionally trigger errors for demonstration purposes
- These examples prioritize clarity and educational value over strict linting compliance
- Some linting warnings (e.g., catching general exceptions, missing type annotations) are intentionally left in place to keep the examples focused and readable