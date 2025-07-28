"""
Efficient Page Loading Examples for Playwright

This module demonstrates best practices for loading web pages efficiently,
including resource blocking, parallel loading, and optimal wait strategies.
"""

import asyncio
import time
from typing import Any

from playwright.async_api import Browser, BrowserContext, async_playwright


class EfficientPageLoader:
    """Demonstrates efficient page loading techniques"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Browser | None = None
        self.playwright = None

    async def setup(self):
        """Initialize browser with optimized settings"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
            ],
        )

    async def teardown(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def load_with_resource_blocking(self, url: str) -> dict[str, Any]:
        """Load page while blocking unnecessary resources"""
        context = await self.browser.new_context()
        page = await context.new_page()

        # Track blocked resources
        blocked_count = {"images": 0, "stylesheets": 0, "fonts": 0, "media": 0}

        async def handle_route(route):
            resource_type = route.request.resource_type
            if resource_type in ["image", "stylesheet", "font", "media"]:
                # Update count based on resource type
                if resource_type == "image":
                    blocked_count["images"] += 1
                elif resource_type == "stylesheet":
                    blocked_count["stylesheets"] += 1
                elif resource_type == "font":
                    blocked_count["fonts"] += 1
                elif resource_type == "media":
                    blocked_count["media"] += 1
                await route.abort()
            else:
                await route.continue_()

        # Set up resource blocking
        await page.route("**/*", handle_route)

        # Measure load time
        start_time = time.time()
        await page.goto(url, wait_until="networkidle")
        load_time = time.time() - start_time

        # Get page metrics
        metrics = await page.evaluate("""
            () => {
                const timing = performance.getEntriesByType('navigation')[0];
                return {
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.fetchStart,
                    loadComplete: timing.loadEventEnd - timing.fetchStart,
                    domNodes: document.getElementsByTagName('*').length,
                    documentSize: document.documentElement.outerHTML.length
                };
            }
        """)

        await context.close()

        return {
            "url": url,
            "load_time": load_time,
            "blocked_resources": blocked_count,
            "metrics": metrics,
        }

    async def load_pages_concurrently(
        self, urls: list[str], max_concurrent: int = 5
    ) -> list[dict[str, Any]]:
        """Load multiple pages concurrently with controlled parallelism"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def load_page(url: str) -> dict[str, Any]:
            async with semaphore:
                context = await self.browser.new_context()
                page = await context.new_page()

                try:
                    start_time = time.time()
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    # Extract basic info
                    title = await page.title()

                    result = {
                        "url": url,
                        "status": response.status if response else None,
                        "title": title,
                        "load_time": time.time() - start_time,
                        "success": True,
                    }
                except Exception as e:
                    result = {"url": url, "error": str(e), "success": False}
                finally:
                    await context.close()

                return result

        # Create tasks for all URLs
        tasks = [load_page(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def smart_wait_strategy(self, url: str) -> dict[str, Any]:
        """Demonstrate different wait strategies for different scenarios"""
        context = await self.browser.new_context()
        page = await context.new_page()
        results = {}

        # Strategy 1: Wait for specific element (good for known pages)
        try:
            start = time.time()
            await page.goto(url)
            await page.wait_for_selector("body", state="visible")
            results["element_wait"] = time.time() - start
        except:
            results["element_wait"] = None

        # Strategy 2: Wait for network idle (good for SPAs)
        try:
            start = time.time()
            await page.goto(url, wait_until="networkidle")
            results["network_idle"] = time.time() - start
        except:
            results["network_idle"] = None

        # Strategy 3: Custom wait function (good for dynamic content)
        try:
            start = time.time()
            await page.goto(url)
            await page.wait_for_function(
                "document.readyState === 'complete' && document.images.length > 0"
            )
            results["custom_wait"] = time.time() - start
        except:
            results["custom_wait"] = None

        await context.close()
        return results

    async def preload_contexts(self, num_contexts: int = 5) -> list[BrowserContext]:
        """Pre-create browser contexts for faster page creation"""
        contexts = []

        for _ in range(num_contexts):
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            contexts.append(context)

        return contexts


async def main():
    """Example usage of efficient page loading techniques"""
    loader = EfficientPageLoader(headless=True)
    await loader.setup()

    try:
        # Example 1: Load with resource blocking
        print("Loading with resource blocking...")
        result = await loader.load_with_resource_blocking("https://example.com")
        print(f"Load time: {result['load_time']:.2f}s")
        print(f"Blocked resources: {result['blocked_resources']}")
        print(f"DOM nodes: {result['metrics']['domNodes']}")
        print()

        # Example 2: Concurrent loading
        print("Loading multiple pages concurrently...")
        urls = ["https://example.com", "https://example.org", "https://example.net"]
        results = await loader.load_pages_concurrently(urls, max_concurrent=3)
        for result in results:
            if result["success"]:
                print(f"{result['url']}: {result['load_time']:.2f}s - {result['title']}")
            else:
                print(f"{result['url']}: Failed - {result.get('error', 'Unknown error')}")
        print()

        # Example 3: Wait strategies comparison
        print("Comparing wait strategies...")
        wait_results = await loader.smart_wait_strategy("https://example.com")
        for strategy, time_taken in wait_results.items():
            if time_taken:
                print(f"{strategy}: {time_taken:.2f}s")

    finally:
        await loader.teardown()


if __name__ == "__main__":
    asyncio.run(main())
