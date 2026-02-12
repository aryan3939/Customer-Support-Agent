"""
Simple Metrics Tracking — request counts and latency.

Production apps use Prometheus/Datadog, but this shows the concept:
tracking how your AI agent performs over time.
"""

import time
from collections import defaultdict
from contextlib import asynccontextmanager

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Simple counters
_counters: dict[str, int] = defaultdict(int)
_latencies: dict[str, list[float]] = defaultdict(list)


def increment(metric_name: str, value: int = 1) -> None:
    """Increment a counter metric."""
    _counters[metric_name] += value


@asynccontextmanager
async def track_latency(operation_name: str):
    """
    Context manager to track operation latency.
    
    Usage:
        async with track_latency("agent_processing"):
            result = await process_ticket(...)
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        _latencies[operation_name].append(elapsed)
        logger.debug(
            "operation_latency",
            operation=operation_name,
            latency_seconds=round(elapsed, 3),
        )


def get_metrics() -> dict:
    """Return all collected metrics."""
    latency_stats = {}
    for op, times in _latencies.items():
        if times:
            latency_stats[op] = {
                "count": len(times),
                "avg_seconds": round(sum(times) / len(times), 3),
                "min_seconds": round(min(times), 3),
                "max_seconds": round(max(times), 3),
            }
    
    return {
        "counters": dict(_counters),
        "latencies": latency_stats,
    }
