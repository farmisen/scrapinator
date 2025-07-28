"""
Browser Pool Manager for Playwright

This module demonstrates efficient browser pool management for handling
concurrent operations at scale with proper resource management.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator  # noqa: TC004

from playwright.async_api import Browser, Page, async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BrowserStats:
    """Statistics for browser instance"""

    browser_id: str
    created_at: datetime
    contexts_created: int = 0
    contexts_active: int = 0
    pages_created: int = 0
    errors: int = 0
    last_used: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PoolStats:
    """Overall pool statistics"""

    browsers_created: int = 0
    browsers_active: int = 0
    contexts_created: int = 0
    contexts_active: int = 0
    pages_created: int = 0
    total_errors: int = 0
    queue_size: int = 0
    avg_wait_time: float = 0.0


class BrowserPool:
    """
    Efficient browser pool manager with automatic scaling and resource management.

    Features:
    - Automatic browser creation and disposal
    - Context isolation per operation
    - Resource usage monitoring
    - Graceful error handling
    - Queue management for high load
    """

    def __init__(
        self,
        min_browsers: int = 1,
        max_browsers: int = 5,
        max_contexts_per_browser: int = 10,
        browser_idle_timeout: int = 300,  # seconds
        headless: bool = True,
    ) -> None:
        self.min_browsers = min_browsers
        self.max_browsers = max_browsers
        self.max_contexts_per_browser = max_contexts_per_browser
        self.browser_idle_timeout = browser_idle_timeout
        self.headless = headless

        self._playwright = None
        self._browsers: dict[str, Browser] = {}
        self._browser_stats: dict[str, BrowserStats] = {}
        self._context_counts: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._queue = asyncio.Queue()
        self._shutdown = False
        self._monitor_task = None

        # Browser launch arguments
        self._browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
        ]

    async def start(self) -> None:
        """Start the browser pool"""
        self._playwright = await async_playwright().start()

        # Create minimum browsers
        for i in range(self.min_browsers):
            await self._create_browser(f"browser-{i}")

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_browsers())

        logger.info("Browser pool started with %d browsers", self.min_browsers)

    async def stop(self) -> None:
        """Stop the browser pool and clean up resources"""
        self._shutdown = True

        if self._monitor_task:
            self._monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._monitor_task

        # Close all browsers
        async with self._lock:
            for _browser_id, browser in list(self._browsers.items()):
                with suppress(Exception):
                    await browser.close()

            self._browsers.clear()
            self._browser_stats.clear()

        if self._playwright:
            await self._playwright.stop()

        logger.info("Browser pool stopped")

    async def _create_browser(self, browser_id: str) -> Browser:
        """Create a new browser instance"""
        browser = await self._playwright.chromium.launch(
            headless=self.headless, args=self._browser_args
        )

        self._browsers[browser_id] = browser
        self._browser_stats[browser_id] = BrowserStats(
            browser_id=browser_id, created_at=datetime.now(UTC)
        )
        self._context_counts[browser_id] = 0

        logger.info("Created browser: %s", browser_id)
        return browser

    async def _get_available_browser(self) -> tuple[str, Browser] | None:
        """Get an available browser or create a new one"""
        async with self._lock:
            # Find browser with capacity
            for browser_id, browser in self._browsers.items():
                if self._context_counts[browser_id] < self.max_contexts_per_browser:
                    self._browser_stats[browser_id].last_used = datetime.now(UTC)
                    return browser_id, browser

            # Create new browser if under limit
            if len(self._browsers) < self.max_browsers:
                browser_id = f"browser-{len(self._browsers)}"
                browser = await self._create_browser(browser_id)
                return browser_id, browser

            return None

    @asynccontextmanager
    async def acquire_page(
        self, context_options: dict[str, Any] | None = None
    ) -> AsyncIterator[Page]:
        """
        Acquire a page from the pool with automatic context management.

        Args:
            context_options: Options for browser context creation

        Yields:
            Page instance
        """
        browser_id = None
        context = None
        page = None
        wait_start = time.time()

        try:
            # Get available browser or wait
            while True:
                result = await self._get_available_browser()
                if result:
                    browser_id, browser = result
                    break

                if self._shutdown:
                    msg = "Browser pool is shutting down"
                    raise RuntimeError(msg)

                await asyncio.sleep(0.1)

            wait_time = time.time() - wait_start  # noqa: F841

            # Create context
            async with self._lock:
                self._context_counts[browser_id] += 1
                stats = self._browser_stats[browser_id]
                stats.contexts_created += 1
                stats.contexts_active += 1

            context_options = context_options or {}
            context = await browser.new_context(**context_options)

            # Create page
            page = await context.new_page()

            async with self._lock:
                self._browser_stats[browser_id].pages_created += 1

            yield page

        except Exception as e:
            logger.exception("Error in browser pool: %s", e)
            if browser_id:
                async with self._lock:
                    self._browser_stats[browser_id].errors += 1
            raise

        finally:
            # Cleanup
            if page:
                with suppress(Exception):
                    await page.close()

            if context:
                with suppress(Exception):
                    await context.close()

            if browser_id:
                async with self._lock:
                    self._context_counts[browser_id] -= 1
                    self._browser_stats[browser_id].contexts_active -= 1

    async def _monitor_browsers(self) -> None:
        """Monitor browsers and clean up idle ones"""
        while not self._shutdown:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                async with self._lock:
                    current_time = datetime.now(UTC)
                    browsers_to_remove = []

                    for browser_id, stats in self._browser_stats.items():
                        # Skip if browser has active contexts
                        if self._context_counts[browser_id] > 0:
                            continue

                        # Skip minimum browsers
                        if len(self._browsers) <= self.min_browsers:
                            continue

                        # Check idle time
                        idle_time = (current_time - stats.last_used).seconds
                        if idle_time > self.browser_idle_timeout:
                            browsers_to_remove.append(browser_id)

                    # Remove idle browsers
                    for browser_id in browsers_to_remove:
                        browser = self._browsers.pop(browser_id)
                        del self._browser_stats[browser_id]
                        del self._context_counts[browser_id]

                        with suppress(Exception):
                            await browser.close()
                            logger.info("Closed idle browser: %s", browser_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in browser monitor: %s", e)

    def get_stats(self) -> PoolStats:
        """Get current pool statistics"""
        stats = PoolStats()

        with self._lock:
            stats.browsers_created = len(self._browser_stats)
            stats.browsers_active = len(self._browsers)

            for browser_stats in self._browser_stats.values():
                stats.contexts_created += browser_stats.contexts_created
                stats.contexts_active += browser_stats.contexts_active
                stats.pages_created += browser_stats.pages_created
                stats.total_errors += browser_stats.errors

        return stats


class ConcurrentScraper:
    """Example scraper using the browser pool"""

    def __init__(self, browser_pool: BrowserPool) -> None:
        self.pool = browser_pool

    async def scrape_url(self, url: str) -> dict[str, Any]:
        """Scrape a single URL"""
        async with self.pool.acquire_page() as page:
            start_time = time.time()

            try:
                # Navigate to URL
                response = await page.goto(url, wait_until="networkidle", timeout=30000)

                # Extract data
                data = await page.evaluate("""
                    () => ({
                        title: document.title,
                        description: document.querySelector('meta[name="description"]')?.content || '',
                        headings: Array.from(document.querySelectorAll('h1, h2')).map(h => h.textContent.trim()),
                        links: Array.from(document.querySelectorAll('a[href]')).length,
                        images: Array.from(document.querySelectorAll('img')).length
                    })
                """)

                return {
                    "url": url,
                    "status": response.status if response else None,
                    "data": data,
                    "time": time.time() - start_time,
                    "success": True,
                }

            except Exception as e:  # noqa: BLE001
                return {
                    "url": url,
                    "error": str(e),
                    "time": time.time() - start_time,
                    "success": False,
                }

    async def scrape_urls(self, urls: list[str]) -> list[dict[str, Any]]:
        """Scrape multiple URLs concurrently"""
        tasks = [self.scrape_url(url) for url in urls]
        return await asyncio.gather(*tasks)


async def demonstrate_browser_pool() -> None:
    """Demonstrate browser pool usage"""

    # Create browser pool
    pool = BrowserPool(min_browsers=2, max_browsers=5, max_contexts_per_browser=10, headless=True)

    await pool.start()

    try:
        # Create scraper
        scraper = ConcurrentScraper(pool)

        # Example URLs
        urls = [
            "https://example.com",
            "https://example.org",
            "https://example.net",
            "https://example.edu",
            "https://example.io",
        ] * 4  # 20 URLs total

        print(f"Scraping {len(urls)} URLs concurrently...")
        start_time = time.time()

        # Scrape all URLs
        results = await scraper.scrape_urls(urls)

        # Print results
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        total_time = time.time() - start_time

        print("\nResults:")
        print(f"  Total: {len(results)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg time per URL: {total_time / len(results):.2f}s")

        # Show pool statistics
        stats = pool.get_stats()
        print("\nPool Statistics:")
        print(f"  Browsers created: {stats.browsers_created}")
        print(f"  Browsers active: {stats.browsers_active}")
        print(f"  Contexts created: {stats.contexts_created}")
        print(f"  Pages created: {stats.pages_created}")
        print(f"  Total errors: {stats.total_errors}")

    finally:
        await pool.stop()


async def performance_test() -> None:
    """Test performance with different pool configurations"""

    configurations = [
        {"name": "Small Pool", "min": 1, "max": 2, "contexts": 5},
        {"name": "Medium Pool", "min": 2, "max": 5, "contexts": 10},
        {"name": "Large Pool", "min": 5, "max": 10, "contexts": 20},
    ]

    test_urls = ["https://example.com"] * 50

    for config in configurations:
        print(f"\nTesting {config['name']}...")

        pool = BrowserPool(
            min_browsers=config["min"],
            max_browsers=config["max"],
            max_contexts_per_browser=config["contexts"],
            headless=True,
        )

        await pool.start()

        try:
            scraper = ConcurrentScraper(pool)
            start_time = time.time()

            results = await scraper.scrape_urls(test_urls)

            total_time = time.time() - start_time
            successful = sum(1 for r in results if r["success"])

            print(f"  Time: {total_time:.2f}s")
            print(f"  Success rate: {successful / len(results) * 100:.1f}%")
            print(f"  URLs/second: {len(results) / total_time:.2f}")

        finally:
            await pool.stop()


if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demonstrate_browser_pool())

    # Run performance test
    # Uncomment to run performance test:
    # asyncio.run(performance_test())
