"""
Error Handling Patterns for Playwright

This module demonstrates comprehensive error handling strategies including
timeout management, retry mechanisms, and navigation failure recovery.
"""

import asyncio
import logging
import random
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from playwright.async_api import Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors we handle"""

    TIMEOUT = "timeout"
    NAVIGATION = "navigation"
    ELEMENT_NOT_FOUND = "element_not_found"
    NETWORK = "network"
    JAVASCRIPT = "javascript"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors"""

    error_type: ErrorType
    url: str
    action: str
    selector: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error_message: str = ""
    stack_trace: str = ""
    screenshot_path: str | None = None
    retry_count: int = 0
    recovery_attempted: bool = False


class RetryStrategy:
    """Configurable retry strategy with exponential backoff"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 30.0,
        jitter: bool = True,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
        non_retryable_exceptions: tuple[type[Exception], ...] = (),
    ) -> None:
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.non_retryable_exceptions = non_retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = min(self.initial_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)

        if self.jitter:
            delay *= 0.5 + random.random()

        return delay

    def should_retry(self, exception: Exception) -> bool:
        """Determine if exception should trigger retry"""
        if isinstance(exception, self.non_retryable_exceptions):
            return False
        return isinstance(exception, self.retryable_exceptions)

    def __call__(self, func: Callable) -> Callable:
        """Decorator for applying retry logic"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not self.should_retry(e) or attempt == self.max_attempts:
                        raise

                    delay = self.calculate_delay(attempt)
                    logger.warning("Attempt {attempt} failed: {e}. Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper


class TimeoutManager:
    """Manages different timeout strategies"""

    def __init__(self, default_timeout: int = 30000) -> None:
        self.default_timeout = default_timeout
        self.timeouts = {"navigation": 30000, "action": 10000, "wait": 5000, "network": 60000}

    def get_timeout(self, operation: str) -> int:
        """Get timeout for specific operation"""
        return self.timeouts.get(operation, self.default_timeout)

    async def with_timeout(self, coro, timeout: int | None = None, operation: str = "default"):
        """Execute coroutine with timeout"""
        timeout = timeout or self.get_timeout(operation)

        try:
            return await asyncio.wait_for(coro, timeout=timeout / 1000)
        except TimeoutError:
            raise PlaywrightTimeout(f"Operation '{operation}' timed out after {timeout}ms")


class NavigationHandler:
    """Handles navigation with fallbacks and recovery"""

    def __init__(self, timeout_manager: TimeoutManager) -> None:
        self.timeout_manager = timeout_manager

    async def navigate_with_fallback(
        self,
        page: Page,
        primary_url: str,
        fallback_urls: list[str] = None,
        options: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Navigate with fallback URLs"""

        fallback_urls = fallback_urls or []
        all_urls = [primary_url] + fallback_urls
        options = options or {}

        for i, url in enumerate(all_urls):
            try:
                start_time = time.time()

                response = await page.goto(
                    url,
                    timeout=self.timeout_manager.get_timeout("navigation"),
                    wait_until=options.get("wait_until", "networkidle"),
                    **{k: v for k, v in options.items() if k != "wait_until"},
                )

                # Verify successful navigation
                if response and 200 <= response.status < 400:
                    return {
                        "success": True,
                        "url": url,
                        "final_url": page.url,
                        "status": response.status,
                        "time": time.time() - start_time,
                        "attempt": i + 1,
                        "redirected": url != page.url,
                    }

                # Log non-success status
                logger.warning("Navigation to %s returned status %d", url, response.status)

            except Exception as e:
                logger.error("Navigation to %s failed: %s", url, e)

                if i == len(all_urls) - 1:  # Last URL
                    raise

        raise Exception(f"Failed to navigate to any URL: {all_urls}")

    async def handle_navigation_timeout(self, page: Page, url: str) -> bool:
        """Handle navigation timeout with recovery strategies"""

        strategies = [
            # Strategy 1: Reload with shorter timeout
            {
                "name": "reload_quick",
                "action": lambda: page.goto(url, timeout=10000, wait_until="domcontentloaded"),
            },
            # Strategy 2: Stop loading and check if content is available
            {"name": "stop_and_check", "action": lambda: self._stop_and_check(page)},
            # Strategy 3: Navigate to home then to target
            {"name": "via_home", "action": lambda: self._navigate_via_home(page, url)},
        ]

        for strategy in strategies:
            try:
                logger.info("Trying recovery strategy: {strategy['name']}")
                await strategy["action"]()
                return True
            except Exception:
                continue

        return False

    async def _stop_and_check(self, page: Page) -> None:
        """Stop loading and check if enough content is available"""
        await page.evaluate("window.stop()")
        await page.wait_for_timeout(1000)

        # Check if we have enough content
        content_length = await page.evaluate("document.body?.innerHTML?.length || 0")
        if content_length < 100:
            raise Exception("Insufficient content after stopping load")

    async def _navigate_via_home(self, page: Page, target_url: str) -> None:
        """Navigate to home page first, then to target"""

        parsed = urlparse(target_url)
        home_url = f"{parsed.scheme}://{parsed.netloc}"

        await page.goto(home_url, wait_until="domcontentloaded")
        await page.goto(target_url, wait_until="domcontentloaded")


class ElementHandler:
    """Handles element interactions with error recovery"""

    def __init__(self, timeout_manager: TimeoutManager) -> None:
        self.timeout_manager = timeout_manager

    @RetryStrategy(max_attempts=3, retryable_exceptions=(PlaywrightTimeout,))
    async def click_with_retry(
        self, page: Page, selector: str, options: dict[str, Any] = None
    ) -> None:
        """Click element with retry logic"""
        options = options or {}
        timeout = options.pop("timeout", self.timeout_manager.get_timeout("action"))

        await page.click(selector, timeout=timeout, **options)

    async def find_element_with_fallback(
        self,
        page: Page,
        selectors: list[str],
        action: str = "click",
        options: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Try multiple selectors with fallback"""

        options = options or {}
        errors = []

        for i, selector in enumerate(selectors):
            try:
                element = await page.wait_for_selector(
                    selector, timeout=self.timeout_manager.get_timeout("wait"), state="visible"
                )

                if element:
                    # Perform action
                    if action == "click":
                        await element.click(**options)
                    elif action == "fill":
                        await element.fill(options.get("value", ""))
                    elif action == "text":
                        return {"text": await element.text_content(), "selector": selector}

                    return {"success": True, "selector": selector, "attempt": i + 1}

            except Exception as e:
                errors.append({"selector": selector, "error": str(e)})
                continue

        raise Exception(f"Failed to find element with any selector. Errors: {errors}")

    async def wait_for_element_safely(
        self, page: Page, selector: str, timeout: int | None = None, state: str = "visible"
    ) -> Any | None:
        """Wait for element with proper error handling"""

        timeout = timeout or self.timeout_manager.get_timeout("wait")

        try:
            element = await page.wait_for_selector(selector, timeout=timeout, state=state)
            return element
        except PlaywrightTimeout:
            # Check if element exists but in different state
            exists = await page.locator(selector).count() > 0

            if exists:
                logger.warning("Element {selector} exists but not in state '{state}'")

                # Try alternative states
                for alt_state in ["attached", "visible", "enabled"]:
                    if alt_state != state:
                        try:
                            return await page.wait_for_selector(
                                selector, timeout=1000, state=alt_state
                            )
                        except:
                            continue

            return None


class ErrorRecovery:
    """Comprehensive error recovery system"""

    def __init__(self, screenshot_dir: str = "./error_screenshots") -> None:
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(exist_ok=True)
        self.error_log: list[ErrorContext] = []
        self.recovery_strategies = {
            ErrorType.TIMEOUT: self._recover_from_timeout,
            ErrorType.NAVIGATION: self._recover_from_navigation_error,
            ErrorType.ELEMENT_NOT_FOUND: self._recover_from_missing_element,
            ErrorType.NETWORK: self._recover_from_network_error,
        }

    async def handle_error(
        self, page: Page, error: Exception, context: dict[str, Any]
    ) -> ErrorContext:
        """Handle error with context preservation and recovery"""

        # Classify error
        error_type = self._classify_error(error)

        # Create error context
        error_context = ErrorContext(
            error_type=error_type,
            url=page.url,
            action=context.get("action", "unknown"),
            selector=context.get("selector"),
            error_message=str(error),
            retry_count=context.get("retry_count", 0),
        )

        # Capture screenshot
        try:
            screenshot_path = await self._capture_screenshot(page, error_type)
            error_context.screenshot_path = str(screenshot_path)
        except Exception:
            logger.error("Failed to capture error screenshot")

        # Log error
        self.error_log.append(error_context)

        # Attempt recovery
        recovery_strategy = self.recovery_strategies.get(error_type)
        if recovery_strategy and context.get("attempt_recovery", True):
            try:
                await recovery_strategy(page, error_context)
                error_context.recovery_attempted = True
            except:
                logger.error("Recovery failed for {error_type}")

        return error_context

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type"""
        error_str = str(error).lower()

        if isinstance(error, PlaywrightTimeout) or "timeout" in error_str:
            return ErrorType.TIMEOUT
        if "navigation" in error_str or "goto" in error_str:
            return ErrorType.NAVIGATION
        if "element" in error_str or "selector" in error_str:
            return ErrorType.ELEMENT_NOT_FOUND
        if "net::" in error_str or "network" in error_str:
            return ErrorType.NETWORK
        if "evaluation" in error_str:
            return ErrorType.JAVASCRIPT
        return ErrorType.UNKNOWN

    async def _capture_screenshot(self, page: Page, error_type: ErrorType) -> Path:
        """Capture screenshot for error"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{error_type.value}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        await page.screenshot(path=filepath, full_page=True)
        return filepath

    async def _recover_from_timeout(self, page: Page, context: ErrorContext):
        """Recovery strategy for timeout errors"""
        logger.info("Attempting timeout recovery")

        # Try reloading with shorter timeout
        try:
            await page.reload(timeout=5000, wait_until="domcontentloaded")
        except Exception:
            # If reload fails, try going back and forward
            with suppress(Exception):
                await page.go_back(timeout=5000)
                await page.go_forward(timeout=5000)

    async def _recover_from_navigation_error(self, page: Page, context: ErrorContext):
        """Recovery strategy for navigation errors"""
        logger.info("Attempting navigation recovery")

        # Wait a bit for network to stabilize
        await page.wait_for_timeout(2000)

        # Try navigating to a simpler version
        current_url = page.url
        if "?" in current_url:
            # Remove query parameters
            base_url = current_url.split("?")[0]
            try:
                await page.goto(base_url, wait_until="domcontentloaded", timeout=10000)
            except Exception:
                pass

    async def _recover_from_missing_element(self, page: Page, context: ErrorContext):
        """Recovery strategy for missing elements"""
        logger.info("Attempting element recovery")

        # Try scrolling to reveal element
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)

        # Try removing overlays that might be blocking
        await page.evaluate("""
            () => {
                // Remove common overlay elements
                const selectors = [
                    '[class*="modal"]',
                    '[class*="overlay"]',
                    '[class*="popup"]',
                    '[id*="cookie"]',
                    '[class*="banner"]'
                ];
                
                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        if (el.style.position === 'fixed' || el.style.position === 'absolute') {
                            el.remove();
                        }
                    });
                });
            }
        """)

    async def _recover_from_network_error(self, page: Page, context: ErrorContext):
        """Recovery strategy for network errors"""
        logger.info("Attempting network recovery")

        # Wait for network to stabilize
        await page.wait_for_timeout(5000)

        # Check if page is offline
        is_offline = await page.evaluate("!navigator.onLine")
        if is_offline:
            logger.warning("Browser appears to be offline")
            # In a real scenario, might trigger reconnection logic

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of all errors"""
        summary = {
            "total_errors": len(self.error_log),
            "by_type": {},
            "recovery_success_rate": 0.0,
            "recent_errors": [],
        }

        # Count by type
        for error in self.error_log:
            error_type = error.error_type.value
            summary["by_type"][error_type] = summary["by_type"].get(error_type, 0) + 1

        # Calculate recovery success rate
        if self.error_log:
            recovered = sum(1 for e in self.error_log if e.recovery_attempted)
            summary["recovery_success_rate"] = recovered / len(self.error_log)

        # Get recent errors
        summary["recent_errors"] = [
            {
                "type": e.error_type.value,
                "url": e.url,
                "action": e.action,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self.error_log[-5:]
        ]

        return summary


async def demonstrate_error_handling() -> None:
    """Demonstrate error handling patterns"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Initialize components
        timeout_manager = TimeoutManager()
        nav_handler = NavigationHandler(timeout_manager)
        element_handler = ElementHandler(timeout_manager)
        error_recovery = ErrorRecovery()

        try:
            # Example 1: Navigation with fallback
            print("Testing navigation with fallback...")
            result = await nav_handler.navigate_with_fallback(
                page,
                "https://nonexistent.example.com",
                fallback_urls=["https://www.example.com"],
                options={"wait_until": "networkidle"},
            )
            print(f"Navigation result: {result}")

            # Example 2: Element interaction with retry
            print("\nTesting element interaction with retry...")
            try:
                await element_handler.click_with_retry(
                    page, "button.nonexistent", options={"timeout": 2000}
                )
            except Exception as e:
                error_ctx = await error_recovery.handle_error(
                    page, e, {"action": "click", "selector": "button.nonexistent"}
                )
                print(f"Error handled: {error_ctx.error_type.value}")

            # Example 3: Multiple selector fallback
            print("\nTesting multiple selector fallback...")
            selectors = [
                "a.nonexistent",
                "a[href*='nonexistent']",
                "a[href*='more']",  # This should work on www.example.com
            ]

            try:
                result = await element_handler.find_element_with_fallback(
                    page, selectors, action="text"
                )
                print(f"Found element with selector: {result['selector']}")
                print(f"Text: {result.get('text', 'N/A')}")
            except Exception as e:
                print(f"All selectors failed: {e}")

            # Show error summary
            print("\nError Summary:")
            summary = error_recovery.get_error_summary()
            print(f"Total errors: {summary['total_errors']}")
            print(f"By type: {summary['by_type']}")
            print(f"Recovery success rate: {summary['recovery_success_rate']:.2%}")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(demonstrate_error_handling())
