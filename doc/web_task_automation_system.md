# Web Task Automation System

## Overview

A system that takes a URL and a natural language task description, then uses LLM API calls to analyze the website structure and create an executable plan to accomplish the task using browser automation.

## Core Concept

```
Input: URL + Task Description
  ↓
LLM Analysis (Multi-stage)
  ↓
Executable Plan (JSON/structured format)
  ↓
Browser Automation Execution
  ↓
Result/Output
```

## System Components

### 1. Task Analyzer
- **Input**: Natural language task description
- **Process**: Extract key objectives, success criteria, and constraints
- **Output**: Structured task representation

### 2. Web Explorer
- **Input**: Starting URL
- **Process**: 
  - Crawl and analyze page structure
  - Identify interactive elements
  - Discover linked pages relevant to task
  - Extract patterns and navigation flows
- **Output**: Site map with annotated elements

### 3. Plan Generator
- **Input**: Task representation + Site analysis
- **Process**: Create step-by-step execution plan
- **Output**: Executable plan in structured format

### 4. Plan Executor
- **Input**: Structured plan
- **Process**: Execute steps using browser automation
- **Output**: Task results and artifacts

## Data Models

### Task Representation

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Literal
from enum import Enum
from datetime import datetime
import uuid

class Task(BaseModel):
    description: str
    objectives: List[str]
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str]
    data_to_extract: List[str] | None = None
    actions_to_perform: List[str] | None = None
    context: Dict[str, Any] = Field(default_factory=dict)
```

### Web Analysis

```python
class PageElement(BaseModel):
    selector: str
    element_type: str  # button, link, input, etc.
    text: str
    attributes: Dict[str, str] = Field(default_factory=dict)
    purpose: str  # LLM-inferred purpose
    confidence: float = Field(ge=0.0, le=1.0)  # How confident the LLM is
    
    @validator('selector')
    def validate_selector(cls, v):
        if not v.strip():
            raise ValueError("Selector cannot be empty")
        return v

class PageAnalysis(BaseModel):
    url: str
    title: str
    elements: List[PageElement]
    navigation_options: List[Dict[str, str]]
    forms: List[Dict[str, Any]] = Field(default_factory=list)
    data_patterns: List[Dict[str, str]] = Field(default_factory=list)
    page_type: str  # e.g., "listing", "detail", "form", "navigation"
```

### Execution Plan

```python
class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    DOWNLOAD = "download"

class Step(BaseModel):
    action: ActionType
    target: str | None = None  # CSS selector or URL
    value: str | None = None  # For fill actions
    wait_condition: str | None = None
    fallback_selectors: List[str] = Field(default_factory=list)  # Alternative selectors
    description: str  # Human-readable description
    save_path: str | None = None  # For download actions
    timeout: int = Field(default=30, ge=1, le=300)
    
    @validator('target')
    def validate_target(cls, v, values):
        if values.get('action') in [ActionType.CLICK, ActionType.FILL, ActionType.EXTRACT, ActionType.DOWNLOAD] and not v:
            raise ValueError(f"Target required for {values.get('action')} action")
        return v
    
class ExecutionPlan(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str
    url: str
    steps: List[Step]
    expected_outcomes: List[str]
    error_handling: Dict[str, List[Step]] = Field(default_factory=dict)
    confidence_score: float = Field(ge=0.0, le=1.0)
    plan_version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

## Implementation

### Phase 1: Task Understanding

```python
# analyzer.py
class WebTaskAnalyzer:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def analyze_task(self, task_description: str, url: str) -> Task:
        """Use LLM to understand what the user wants to achieve"""
        prompt = f"""
        Analyze this web automation task:
        URL: {url}
        Task: {task_description}
        
        Extract:
        1. Main objectives
        2. Success criteria
        3. Data to extract (if any)
        4. Actions to perform
        5. Constraints or limitations
        """
        # LLM call to structure the task
        response = await self.llm.complete(prompt)
        return Task(**response)
```

### Phase 2: Web Exploration

```python
async def explore_website(self, url: str, task: Task, max_depth: int = 2) -> PageAnalysis:
    """Explore website structure relevant to the task"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(url)
        html = await page.content()
        
        # Analyze page structure
        analysis_prompt = f"""
        Analyze this webpage for the task: {task.description}
        HTML: {html[:3000]}...
        
        Identify:
        1. Main navigation elements
        2. Interactive forms
        3. Important buttons/links
        4. Data containers
        5. Elements relevant to: {task.objectives}
        """
        
        analysis = await self.llm.complete(analysis_prompt)
        await browser.close()
        
        return PageAnalysis(**analysis)
```

### Phase 3: Plan Generation

```python
async def generate_plan(self, task: Task, page_analysis: PageAnalysis) -> ExecutionPlan:
    """Create executable plan using LLM analysis"""
    prompt = f"""
    Create a step-by-step plan to accomplish this task:
    {task.description}
    
    Available elements and pages:
    {page_analysis}
    
    Generate specific browser automation steps using these actions:
    - navigate: go to a URL
    - click: click an element
    - fill: fill a form field
    - extract: get data from elements
    - wait: wait for conditions
    - download: download files
    - scroll: scroll page or element
    
    Return as structured steps with selectors and descriptions.
    """
    
    plan_data = await self.llm.complete(prompt)
    return ExecutionPlan(**plan_data)
```

### Phase 4: Plan Execution

```python
# executor.py
from playwright.async_api import async_playwright
from pathlib import Path

class PlanExecutor:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
    async def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                downloads_path=str(self.download_dir / plan.task_id)
            )
            context = await browser.new_context(
                accept_downloads=True
            )
            page = await context.new_page()
            
            results = {
                "task_id": plan.task_id,
                "success": False,
                "data": {},
                "downloads": [],
                "errors": [],
                "screenshots": []
            }
            
            try:
                for step in plan.steps:
                    await self._execute_step(page, step, results)
                
                results["success"] = self._check_success(
                    results, plan.expected_outcomes
                )
            except Exception as e:
                results["errors"].append(str(e))
            finally:
                await browser.close()
            
            return results
    
    async def _execute_step(self, page, step: Step, results: Dict):
        """Execute a single step of the plan"""
        try:
            if step.action == ActionType.NAVIGATE:
                await page.goto(step.target)
                
            elif step.action == ActionType.CLICK:
                await self._click_with_fallbacks(page, step)
                
            elif step.action == ActionType.FILL:
                await page.fill(step.target, step.value)
                
            elif step.action == ActionType.EXTRACT:
                data = await page.locator(step.target).all_text_contents()
                results["data"][step.description] = data
                
            elif step.action == ActionType.WAIT:
                if step.target:
                    await page.wait_for_selector(step.target, timeout=step.timeout * 1000)
                else:
                    await page.wait_for_timeout(float(step.value) * 1000)
                    
            elif step.action == ActionType.DOWNLOAD:
                # Start download
                async with page.expect_download() as download_info:
                    await page.click(step.target)
                download = await download_info.value
                
                # Save file
                save_path = self.download_dir / plan.task_id / (step.save_path or download.suggested_filename)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                await download.save_as(save_path)
                results["downloads"].append(str(save_path))
                
            elif step.action == ActionType.SCREENSHOT:
                screenshot_path = self.download_dir / plan.task_id / f"screenshot_{len(results['screenshots'])}.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=screenshot_path)
                results["screenshots"].append(str(screenshot_path))
                
            elif step.action == ActionType.SCROLL:
                if step.target:
                    await page.locator(step.target).scroll_into_view_if_needed()
                else:
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    
        except Exception as e:
            # Try fallback selectors
            if step.fallback_selectors and step.action in [ActionType.CLICK, ActionType.FILL, ActionType.EXTRACT]:
                for fallback in step.fallback_selectors:
                    try:
                        step_copy = step.copy()
                        step_copy.target = fallback
                        await self._execute_step(page, step_copy, results)
                        return  # Success with fallback
                    except:
                        continue
            
            results["errors"].append(f"Step failed: {step.description} - {str(e)}")
            raise
    
    async def _click_with_fallbacks(self, page, step: Step):
        """Click with retry logic and fallbacks"""
        try:
            await page.click(step.target, timeout=step.timeout * 1000)
        except:
            # Try with force
            await page.locator(step.target).click(force=True)
```

### Main Interface

```python
# web_task_automation.py
class WebTaskAutomation:
    def __init__(self, llm_client):
        self.analyzer = WebTaskAnalyzer(llm_client)
        self.executor = PlanExecutor()
        self.cache = {}
    
    async def automate_task(self, url: str, task: str) -> Dict[str, Any]:
        """Main entry point for task automation"""
        
        # 1. Understand the task
        structured_task = await self.analyzer.analyze_task(task, url)
        
        # 2. Explore and analyze the website
        page_analysis = await self.analyzer.explore_website(url, structured_task)
        
        # 3. Generate execution plan
        plan = await self.analyzer.generate_plan(structured_task, page_analysis)
        
        # 4. Execute the plan
        results = await self.executor.execute(plan)
        
        # 5. Return comprehensive results
        return {
            "task": structured_task.dict(),
            "plan": plan.dict(),
            "results": results,
            "success": results["success"]
        }
```

## Example Usage

```python
# example.py
import asyncio
from web_task_automation import WebTaskAutomation

async def main():
    # Initialize with your LLM client
    automation = WebTaskAutomation(llm_client)
    
    # Example 1: Extract data
    result = await automation.automate_task(
        url="https://news.ycombinator.com",
        task="Extract the titles and scores of the top 5 stories"
    )
    print(f"Extracted data: {result['results']['data']}")
    
    # Example 2: Multi-page navigation
    result = await automation.automate_task(
        url="https://example-blog.com",
        task="Go to the blog section, find all articles about Python, and extract titles and dates"
    )
    
    # Example 3: Download images
    result = await automation.automate_task(
        url="https://example-shop.com",
        task="Search for 'laptop' and download all product images from the first page"
    )
    print(f"Downloaded files: {result['results']['downloads']}")
    
    # Example 4: Form submission with file download
    result = await automation.automate_task(
        url="https://example.com/contact",
        task="Fill the contact form with name 'John Doe' and email 'john@example.com', submit it, then download the confirmation PDF"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## MVP Features

### 1. Core Execution
- Single and multi-page task execution
- Session state management across pages
- Basic element interaction (click, fill, extract, scroll)

### 2. File Handling
- Download images and files
- Handle different file types (PDF, images, documents)
- Organize downloaded files by task

### 3. Navigation
- Follow links across multiple pages
- Handle redirects and dynamic navigation
- Maintain context throughout task execution

### 4. Validation & Error Handling
- Success criteria validation
- Retry failed steps with fallback selectors
- Detailed error reporting

### 5. Data Management
- Extract and structure data from pages
- Save results in JSON format
- Basic task history/caching

## Key Implementation Details

### 1. Progressive Enhancement
- Start with simple single-page tasks
- Add multi-page navigation
- Implement error recovery
- Add caching for repeated tasks

### 2. LLM Optimization
- Use structured output formats (JSON mode)
- Implement prompt templates
- Cache analyses for similar pages
- Use smaller models for simple tasks

### 3. Robustness
- Retry failed steps with variations
- Implement multiple selector strategies
- Add visual validation (screenshots)
- Handle dynamic content (wait strategies)

### 4. Observability
- Log all LLM calls and costs
- Track execution times
- Save screenshots at key steps
- Provide detailed error messages

## Technology Stack

- **LLM Integration**: OpenAI/Anthropic APIs for analysis
- **Browser Automation**: Playwright for reliable cross-browser automation
- **Data Storage**: JSON/SQLite for caching analyses
- **Async Execution**: Python asyncio for concurrent operations

## Security Considerations

1. Sandbox browser execution
2. Validate and sanitize all inputs
3. Respect robots.txt and rate limits
4. Handle sensitive data appropriately
5. Implement timeouts and resource limits

## Next Steps

1. Build proof-of-concept with simple task (e.g., "extract all headlines")
2. Implement core analysis engine
3. Create plan generation system
4. Build execution framework
5. Add validation and error handling

## Future Enhancements

### 1. Self-Learning System
- Track selector reliability across executions
- Build reusable task templates from successful runs
- Learn optimal wait times and timeouts per site
- Automatic error recovery based on past failures
- Pattern recognition for similar websites

### 2. Advanced Automation Features
- Complex form handling (multi-step forms, conditional logic)
- Advanced authentication handling (OAuth, 2FA)
- Parallel execution for batch tasks
- Visual AI for element detection when selectors fail
- Task recording and replay functionality
- API integration for hybrid automation
- Browser extension for easier task creation

### 3. Natural Language Enhancements
- Conversational task refinement
- Natural language feedback loop
- Voice command support
- Multi-language task descriptions

### 4. Performance & Scalability
- Intelligent caching of site analyses
- Smart navigation optimization
- Automatic retry with exponential backoff
- Distributed execution across multiple machines
- Resource usage optimization
- Real-time monitoring dashboard

### 5. Platform Extensions
- Cross-browser support (Firefox, Safari, Edge)
- Mobile web automation
- Desktop application automation
- API-first design for integration
- Webhook support for event-driven automation