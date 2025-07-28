"""Metrics utilities for performance measurement."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    strategy: str
    start_time: float = field(default_factory=time.time)
    end_time: float = 0
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0
    success: bool = True
    error: str = ""

    @property
    def duration(self) -> float:
        """Calculate duration in seconds."""
        return self.end_time - self.start_time if self.end_time else 0

    @property
    def tokens_total(self) -> int:
        """Total tokens used."""
        return self.tokens_input + self.tokens_output

    def complete(self):
        """Mark the metric as complete."""
        self.end_time = time.time()


class MetricsCollector:
    """Collect and aggregate performance metrics."""

    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []

    def add(self, metric: PerformanceMetrics):
        """Add a metric to the collection."""
        self.metrics.append(metric)

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        if not self.metrics:
            return {}

        successful = [m for m in self.metrics if m.success]

        return {
            "total_runs": len(self.metrics),
            "successful_runs": len(successful),
            "success_rate": len(successful) / len(self.metrics) * 100,
            "average_duration": sum(m.duration for m in successful) / len(successful)
            if successful
            else 0,
            "total_tokens": sum(m.tokens_total for m in self.metrics),
            "total_cost": sum(m.cost for m in self.metrics),
            "by_strategy": self._group_by_strategy(),
        }

    def _group_by_strategy(self) -> dict[str, dict[str, Any]]:
        """Group metrics by strategy."""
        strategies = {}

        for metric in self.metrics:
            if metric.strategy not in strategies:
                strategies[metric.strategy] = {
                    "runs": 0,
                    "successes": 0,
                    "total_duration": 0,
                    "total_tokens": 0,
                    "total_cost": 0,
                }

            stats = strategies[metric.strategy]
            stats["runs"] += 1
            if metric.success:
                stats["successes"] += 1
                stats["total_duration"] += metric.duration
            stats["total_tokens"] += metric.tokens_total
            stats["total_cost"] += metric.cost

        # Calculate averages
        for strategy, stats in strategies.items():
            if stats["successes"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["successes"]
                stats["success_rate"] = stats["successes"] / stats["runs"] * 100
            else:
                stats["avg_duration"] = 0
                stats["success_rate"] = 0

        return strategies

    def print_report(self):
        """Print a formatted report."""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("PERFORMANCE METRICS REPORT")
        print("=" * 60)
        print(f"Total Runs: {summary.get('total_runs', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
        print(f"Average Duration: {summary.get('average_duration', 0):.2f}s")
        print(f"Total Tokens: {summary.get('total_tokens', 0):,}")
        print(f"Total Cost: ${summary.get('total_cost', 0):.4f}")

        print("\n" + "-" * 60)
        print("BY STRATEGY:")
        print("-" * 60)

        for strategy, stats in summary.get("by_strategy", {}).items():
            print(f"\n{strategy}:")
            print(f"  Runs: {stats['runs']}")
            print(f"  Success Rate: {stats['success_rate']:.1f}%")
            print(f"  Avg Duration: {stats['avg_duration']:.2f}s")
            print(f"  Total Tokens: {stats['total_tokens']:,}")
            print(f"  Total Cost: ${stats['total_cost']:.4f}")


def measure_performance(strategy: str):
    """Decorator to measure performance of a function."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            metric = PerformanceMetrics(strategy=strategy)
            try:
                result = await func(*args, **kwargs)
                metric.success = True
                return result
            except Exception as e:
                metric.success = False
                metric.error = str(e)
                raise
            finally:
                metric.complete()
                # In a real implementation, this would save to a collector
                print(f"[{strategy}] Duration: {metric.duration:.2f}s")

        return wrapper

    return decorator


def format_tokens(tokens: int) -> str:
    """Format token count for display."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def calculate_token_reduction(original: int, processed: int) -> float:
    """Calculate percentage reduction in tokens."""
    if original == 0:
        return 0
    return ((original - processed) / original) * 100


def compare_strategies(results: dict[str, dict[str, Any]]) -> None:
    """Print comparison of different strategies."""
    print("\n" + "=" * 70)
    print("STRATEGY COMPARISON")
    print("=" * 70)
    print(f"{'Strategy':<30} {'Tokens':<15} {'Reduction':<15} {'Time':<10}")
    print("-" * 70)

    baseline_tokens = results.get("original", {}).get("tokens", 0)

    for strategy, data in results.items():
        tokens = data.get("tokens", 0)
        reduction = calculate_token_reduction(baseline_tokens, tokens)
        time_ms = data.get("time", 0) * 1000  # Convert to milliseconds

        print(
            f"{strategy:<30} {format_tokens(tokens):<15} "
            f"{reduction:>6.1f}%{'':<8} {time_ms:>6.0f}ms"
        )

    print("=" * 70)
