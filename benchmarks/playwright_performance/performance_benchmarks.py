"""
Performance Benchmarks for Playwright

This module runs performance benchmarks to measure the impact of different
configurations and strategies on web exploration performance.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page
import psutil
import os


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run"""
    name: str
    duration: float
    memory_peak_mb: float
    cpu_peak_percent: float
    pages_processed: int
    errors: int
    success_rate: float
    avg_page_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    suite_name: str
    timestamp: datetime
    results: List[BenchmarkResult] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmark:
    """Base class for performance benchmarks"""
    
    def __init__(self, name: str):
        self.name = name
        self.process = psutil.Process(os.getpid())
        self.start_memory = 0
        self.peak_memory = 0
        self.peak_cpu = 0
        self.monitor_task = None
    
    async def start_monitoring(self):
        """Start resource monitoring"""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = self.start_memory
        self.peak_cpu = 0
        self.monitor_task = asyncio.create_task(self._monitor_resources())
    
    async def stop_monitoring(self):
        """Stop resource monitoring"""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_resources(self):
        """Monitor resources continuously"""
        while True:
            try:
                # Memory
                current_memory = self.process.memory_info().rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, current_memory)
                
                # CPU
                current_cpu = self.process.cpu_percent(interval=0.1)
                self.peak_cpu = max(self.peak_cpu, current_cpu)
                
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
    
    async def run(self, urls: List[str]) -> BenchmarkResult:
        """Run the benchmark"""
        raise NotImplementedError("Subclasses must implement run()")


class SequentialBenchmark(PerformanceBenchmark):
    """Benchmark for sequential page loading"""
    
    def __init__(self):
        super().__init__("Sequential Loading")
    
    async def run(self, urls: List[str]) -> BenchmarkResult:
        await self.start_monitoring()
        start_time = time.time()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            successful = 0
            errors = 0
            page_times = []
            
            for url in urls:
                page_start = time.time()
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    successful += 1
                except:
                    errors += 1
                page_times.append(time.time() - page_start)
            
            await browser.close()
        
        await self.stop_monitoring()
        
        total_time = time.time() - start_time
        
        return BenchmarkResult(
            name=self.name,
            duration=total_time,
            memory_peak_mb=self.peak_memory - self.start_memory,
            cpu_peak_percent=self.peak_cpu,
            pages_processed=len(urls),
            errors=errors,
            success_rate=successful / len(urls) if urls else 0,
            avg_page_time=statistics.mean(page_times) if page_times else 0,
            metadata={
                "urls_per_second": len(urls) / total_time if total_time > 0 else 0
            }
        )


class ConcurrentBenchmark(PerformanceBenchmark):
    """Benchmark for concurrent page loading"""
    
    def __init__(self, max_concurrent: int = 5):
        super().__init__(f"Concurrent Loading (max={max_concurrent})")
        self.max_concurrent = max_concurrent
    
    async def run(self, urls: List[str]) -> BenchmarkResult:
        await self.start_monitoring()
        start_time = time.time()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def load_page(url: str) -> tuple[bool, float]:
                async with semaphore:
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    page_start = time.time()
                    success = False
                    
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        success = True
                    except:
                        pass
                    finally:
                        await context.close()
                    
                    return success, time.time() - page_start
            
            results = await asyncio.gather(*[load_page(url) for url in urls])
            
            await browser.close()
        
        await self.stop_monitoring()
        
        total_time = time.time() - start_time
        
        successful = sum(1 for success, _ in results if success)
        page_times = [time for _, time in results]
        
        return BenchmarkResult(
            name=self.name,
            duration=total_time,
            memory_peak_mb=self.peak_memory - self.start_memory,
            cpu_peak_percent=self.peak_cpu,
            pages_processed=len(urls),
            errors=len(urls) - successful,
            success_rate=successful / len(urls) if urls else 0,
            avg_page_time=statistics.mean(page_times) if page_times else 0,
            metadata={
                "urls_per_second": len(urls) / total_time if total_time > 0 else 0,
                "max_concurrent": self.max_concurrent
            }
        )


class BrowserPoolBenchmark(PerformanceBenchmark):
    """Benchmark for browser pool strategy"""
    
    def __init__(self, pool_size: int = 3, contexts_per_browser: int = 5):
        super().__init__(f"Browser Pool (size={pool_size}, contexts={contexts_per_browser})")
        self.pool_size = pool_size
        self.contexts_per_browser = contexts_per_browser
    
    async def run(self, urls: List[str]) -> BenchmarkResult:
        await self.start_monitoring()
        start_time = time.time()
        
        async with async_playwright() as p:
            # Create browser pool
            browsers = []
            for _ in range(self.pool_size):
                browser = await p.chromium.launch(headless=True)
                browsers.append(browser)
            
            # Distribute work across browsers
            browser_queues = [asyncio.Queue() for _ in range(self.pool_size)]
            
            # Fill queues
            for i, url in enumerate(urls):
                await browser_queues[i % self.pool_size].put(url)
            
            # Add sentinel values
            for queue in browser_queues:
                await queue.put(None)
            
            async def process_browser_queue(browser: Browser, queue: asyncio.Queue) -> List[tuple[bool, float]]:
                results = []
                context_semaphore = asyncio.Semaphore(self.contexts_per_browser)
                
                async def process_url(url: str) -> tuple[bool, float]:
                    async with context_semaphore:
                        context = await browser.new_context()
                        page = await context.new_page()
                        
                        page_start = time.time()
                        success = False
                        
                        try:
                            await page.goto(url, wait_until="networkidle", timeout=30000)
                            success = True
                        except:
                            pass
                        finally:
                            await context.close()
                        
                        return success, time.time() - page_start
                
                tasks = []
                while True:
                    url = await queue.get()
                    if url is None:
                        break
                    tasks.append(process_url(url))
                
                return await asyncio.gather(*tasks)
            
            # Process all queues
            all_results = await asyncio.gather(*[
                process_browser_queue(browser, queue)
                for browser, queue in zip(browsers, browser_queues)
            ])
            
            # Close browsers
            for browser in browsers:
                await browser.close()
        
        await self.stop_monitoring()
        
        total_time = time.time() - start_time
        
        # Flatten results
        flat_results = [item for sublist in all_results for item in sublist]
        successful = sum(1 for success, _ in flat_results if success)
        page_times = [time for _, time in flat_results]
        
        return BenchmarkResult(
            name=self.name,
            duration=total_time,
            memory_peak_mb=self.peak_memory - self.start_memory,
            cpu_peak_percent=self.peak_cpu,
            pages_processed=len(urls),
            errors=len(urls) - successful,
            success_rate=successful / len(urls) if urls else 0,
            avg_page_time=statistics.mean(page_times) if page_times else 0,
            metadata={
                "urls_per_second": len(urls) / total_time if total_time > 0 else 0,
                "pool_size": self.pool_size,
                "contexts_per_browser": self.contexts_per_browser
            }
        )


class ResourceOptimizedBenchmark(PerformanceBenchmark):
    """Benchmark with resource optimization (blocking images/CSS)"""
    
    def __init__(self, max_concurrent: int = 5):
        super().__init__(f"Resource Optimized (no images/CSS)")
        self.max_concurrent = max_concurrent
    
    async def run(self, urls: List[str]) -> BenchmarkResult:
        await self.start_monitoring()
        start_time = time.time()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def load_page_optimized(url: str) -> tuple[bool, float]:
                async with semaphore:
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    # Block resources
                    await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,css,font,woff,woff2}", 
                                   lambda route: route.abort())
                    
                    page_start = time.time()
                    success = False
                    
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        success = True
                    except:
                        pass
                    finally:
                        await context.close()
                    
                    return success, time.time() - page_start
            
            results = await asyncio.gather(*[load_page_optimized(url) for url in urls])
            
            await browser.close()
        
        await self.stop_monitoring()
        
        total_time = time.time() - start_time
        
        successful = sum(1 for success, _ in results if success)
        page_times = [time for _, time in results]
        
        return BenchmarkResult(
            name=self.name,
            duration=total_time,
            memory_peak_mb=self.peak_memory - self.start_memory,
            cpu_peak_percent=self.peak_cpu,
            pages_processed=len(urls),
            errors=len(urls) - successful,
            success_rate=successful / len(urls) if urls else 0,
            avg_page_time=statistics.mean(page_times) if page_times else 0,
            metadata={
                "urls_per_second": len(urls) / total_time if total_time > 0 else 0,
                "resources_blocked": ["images", "css", "fonts"]
            }
        )


class BenchmarkRunner:
    """Run and compare multiple benchmarks"""
    
    def __init__(self, output_dir: str = "./benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_suite(self, urls: List[str], benchmarks: List[PerformanceBenchmark]) -> BenchmarkSuite:
        """Run a suite of benchmarks"""
        
        suite = BenchmarkSuite(
            suite_name=f"Playwright Performance Benchmarks",
            timestamp=datetime.now(),
            environment={
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "python_version": os.sys.version,
                "url_count": len(urls)
            }
        )
        
        print(f"Running benchmarks with {len(urls)} URLs...")
        print(f"{'='*60}")
        
        for benchmark in benchmarks:
            print(f"\nRunning: {benchmark.name}")
            
            result = await benchmark.run(urls)
            suite.results.append(result)
            
            # Print summary
            print(f"  Duration: {result.duration:.2f}s")
            print(f"  Success rate: {result.success_rate*100:.1f}%")
            print(f"  Avg page time: {result.avg_page_time:.2f}s")
            print(f"  URLs/second: {result.metadata.get('urls_per_second', 0):.2f}")
            print(f"  Memory used: {result.memory_peak_mb:.1f}MB")
            print(f"  Peak CPU: {result.cpu_peak_percent:.1f}%")
        
        # Save results
        self._save_results(suite)
        
        # Print comparison
        self._print_comparison(suite)
        
        return suite
    
    def _save_results(self, suite: BenchmarkSuite):
        """Save results to JSON file"""
        
        filename = f"benchmark_{suite.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        data = {
            "suite_name": suite.suite_name,
            "timestamp": suite.timestamp.isoformat(),
            "environment": suite.environment,
            "results": [
                {
                    "name": r.name,
                    "duration": r.duration,
                    "memory_peak_mb": r.memory_peak_mb,
                    "cpu_peak_percent": r.cpu_peak_percent,
                    "pages_processed": r.pages_processed,
                    "errors": r.errors,
                    "success_rate": r.success_rate,
                    "avg_page_time": r.avg_page_time,
                    "metadata": r.metadata
                }
                for r in suite.results
            ]
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\nResults saved to: {filepath}")
    
    def _print_comparison(self, suite: BenchmarkSuite):
        """Print comparison table"""
        
        print(f"\n{'='*80}")
        print("PERFORMANCE COMPARISON")
        print(f"{'='*80}")
        
        # Find best performers
        fastest = min(suite.results, key=lambda r: r.duration)
        highest_throughput = max(suite.results, key=lambda r: r.metadata.get('urls_per_second', 0))
        most_efficient = min(suite.results, key=lambda r: r.memory_peak_mb)
        
        print(f"\n🏆 Fastest: {fastest.name} ({fastest.duration:.2f}s)")
        print(f"🚀 Highest throughput: {highest_throughput.name} ({highest_throughput.metadata.get('urls_per_second', 0):.2f} URLs/s)")
        print(f"💾 Most memory efficient: {most_efficient.name} ({most_efficient.memory_peak_mb:.1f}MB)")
        
        # Comparison table
        print(f"\n{'Strategy':<35} {'Time (s)':<10} {'URLs/s':<10} {'Memory (MB)':<12} {'Success %':<10}")
        print("-" * 80)
        
        for result in sorted(suite.results, key=lambda r: r.duration):
            print(f"{result.name:<35} {result.duration:<10.2f} "
                  f"{result.metadata.get('urls_per_second', 0):<10.2f} "
                  f"{result.memory_peak_mb:<12.1f} "
                  f"{result.success_rate*100:<10.1f}")


async def run_benchmarks():
    """Run performance benchmarks"""
    
    # Test URLs (mix of different sites)
    test_urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net",
        "https://httpbin.org/html",
        "https://httpbin.org/delay/1",
    ] * 10  # 50 URLs total
    
    # Create benchmarks
    benchmarks = [
        SequentialBenchmark(),
        ConcurrentBenchmark(max_concurrent=5),
        ConcurrentBenchmark(max_concurrent=10),
        BrowserPoolBenchmark(pool_size=3, contexts_per_browser=5),
        ResourceOptimizedBenchmark(max_concurrent=10),
    ]
    
    # Run suite
    runner = BenchmarkRunner()
    await runner.run_suite(test_urls, benchmarks)


if __name__ == "__main__":
    asyncio.run(run_benchmarks())