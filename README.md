# Scrapinator - Web Task Automation System

An intelligent web automation system that uses LLM (Large Language Model) to understand natural language tasks and automatically creates browser automation scripts. Just provide a URL and describe what you want to do - Scrapinator figures out the rest!

## 🚀 Features

- **Natural Language Understanding**: Describe tasks in plain English
- **AI-Powered Analysis**: Uses LLM to analyze website structures dynamically
- **Universal Compatibility**: Works with any website
- **Multi-Page Support**: Navigate across multiple pages seamlessly
- **File Downloads**: Download images, PDFs, and other files automatically
- **Data Extraction**: Extract structured data from any webpage
- **Smart Error Recovery**: Automatic retry with fallback strategies
- **Organized Output**: Clean directory structure with JSON results

## 📦 Installation

### Using pip with pyproject.toml

```bash
# Clone the repository
git clone https://github.com/farmisen/scrapinator.git
cd scrapinator

# Install in editable mode with all dependencies
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Set up API Key

```bash
export ANTHROPIC_API_KEY='your-api-key-here'˜
# or
export OPENAI_API_KEY='your-api-key-here'
```

## 🎮 Usage

### Command Line

```bash
# Run the task automation
scrapinator
```

### Python API

```python
from scrapinator import WebTaskAutomation

# Initialize automation
automation = WebTaskAutomation(llm_client)

# Example: Extract data
result = await automation.automate_task(
    url="https://news.ycombinator.com",
    task="Extract the titles and scores of the top 5 stories"
)

# Example: Download files
result = await automation.automate_task(
    url="https://example.com",
    task="Find and download all PDF documents from the resources section"
)

# Example: Multi-page navigation
result = await automation.automate_task(
    url="https://blog.example.com",
    task="Go to the archive, find all posts about Python, and extract their titles and dates"
)
```

## 📁 Project Structure

```
scrapinator/
├── src/
│   ├── web_task_automation.py   # Main automation engine
│   ├── models.py                # Pydantic data models
│   ├── analyzer.py              # LLM-powered analysis
│   ├── executor.py              # Browser automation executor
│   └── adaptive_downloader.py   # Legacy ROM downloader (to be refactored)
├── doc/
│   ├── web_task_automation_system.md # Full system specification
├── pyproject.toml               # Modern Python project configuration
└── README.md                    # This file
```

## 🛠️ Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Run linting
ruff check src/

# Run type checking
pyright
```

## 📚 Example Tasks

### Data Extraction
- "Extract all product names and prices from the electronics category"
- "Get the headlines and publication dates from the blog"
- "Find all email addresses on the contact page"

### File Downloads
- "Download all images from the gallery"
- "Get the latest PDF report from investor relations"
- "Save all product specification sheets"

### Form Interaction
- "Fill out the contact form with test data and submit"
- "Search for 'laptop' and extract results"
- "Login and download my invoice history"

### Multi-Page Navigation
- "Go through all pages of search results and collect product links"
- "Navigate to each article and extract the full text"
- "Follow pagination to get all forum posts"

## 🔧 Configuration

Configure automation behavior through environment variables:

```bash
# LLM Provider
export LLM_PROVIDER="anthropic"  # or "openai"

# Browser settings
export HEADLESS_BROWSER="true"
export BROWSER_TIMEOUT="30"

# Download directory
export DOWNLOAD_DIR="./downloads"
```

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Legal Notice

This tool should be used responsibly and in compliance with website terms of service. Always respect robots.txt and rate limits. Users are responsible for ensuring their usage complies with all applicable laws and regulations.